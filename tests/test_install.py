"""The package works after a normal install, not only from a source checkout (audit finding I2).

Builds a wheel, installs it with --no-deps into isolated virtual environments, and runs the
installed CLI from a directory outside the checkout:

  env "with-validator": created with --system-site-packages so jsonschema (a declared
      dependency) comes from the test interpreter. The test asserts that autoharness_data
      itself is imported from the venv, not from the checkout.
  env "without-validator": fully isolated, so jsonschema really is absent. The CLI must refuse.

No network is needed. The wheel is built without build isolation (setuptools and wheel are
dev dependencies).
"""

import json
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import pytest

from conftest import ROOT, SMALL


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    out = tmp_path_factory.mktemp("wheel")
    src = tmp_path_factory.mktemp("src") / "autoharness-dashboard"
    # Build from a clean copy so no build/ or egg-info artifacts land in the checkout.
    shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "build", ".pytest_cache"))
    r = run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "-w", str(out), str(src)])
    assert r.returncode == 0, r.stdout + r.stderr
    (whl,) = out.glob("autoharness_data-*.whl")
    return whl


def make_env(path: Path, wheel: Path, system_site: bool) -> Path:
    venv.EnvBuilder(with_pip=True, system_site_packages=system_site).create(path)
    py = path / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    r = run([str(py), "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)])
    assert r.returncode == 0, r.stdout + r.stderr
    return py


def test_wheel_contains_config_and_schemas(wheel):
    import zipfile

    names = set(zipfile.ZipFile(wheel).namelist())
    assert "autoharness_data/config/categories.toml" in names
    for s in ("manifest", "run", "summary", "categories", "functions-index", "functions-crate", "validation"):
        assert f"autoharness_data/schema/{s}.schema.json" in names


def test_installed_cli_finds_bundled_resources(tmp_path, wheel):
    py = make_env(tmp_path / "with-validator", wheel, system_site=True)
    workdir = tmp_path / "elsewhere"
    workdir.mkdir()

    where = run([str(py), "-c", "import autoharness_data, jsonschema; print(autoharness_data.__file__)"], cwd=workdir)
    assert where.returncode == 0, where.stderr
    location = Path(where.stdout.strip()).resolve()
    assert (tmp_path / "with-validator").resolve() in location.parents, location
    assert ROOT.resolve() not in location.parents

    out = tmp_path / "data"
    r = run([str(py), "-m", "autoharness_data", "build",
             "--listing", str(SMALL / "all_variants.stdout.txt"),
             "--run-meta", str(SMALL / "run-meta.toml"), "--out", str(out)], cwd=workdir)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["status"] == "pass"
    v = json.loads((out / "validation.json").read_text(encoding="utf-8"))
    assert any(c["id"] == "schema.valid:run.json" and c["status"] == "pass" for c in v["checks"])

    r = run([str(py), "-m", "autoharness_data", "verify", "--data", str(out)], cwd=workdir)
    assert r.returncode == 0 and "verify: ok" in r.stdout, r.stdout + r.stderr


def test_installed_cli_without_validator_refuses(tmp_path, wheel):
    py = make_env(tmp_path / "without-validator", wheel, system_site=False)
    assert run([str(py), "-c", "import jsonschema"]).returncode != 0, "env unexpectedly has jsonschema"

    out = tmp_path / "data"
    r = run([str(py), "-m", "autoharness_data", "build",
             "--listing", str(SMALL / "all_variants.stdout.txt"),
             "--run-meta", str(SMALL / "run-meta.toml"), "--out", str(out)], cwd=tmp_path)
    assert r.returncode == 2
    assert "'jsonschema' package is required" in r.stderr
    assert not out.exists()
