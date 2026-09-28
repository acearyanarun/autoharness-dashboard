"""Locate bundled resources (category config, JSON schemas) and the schema validator.

Resources ship inside the package and are found through importlib.resources, so the
generator works the same from a git checkout and after a normal `pip install`.
Callers may pass their own directory (--config / --schema-dir) to override them.
"""

from __future__ import annotations

from importlib import resources
from importlib.abc import Traversable
from pathlib import Path

PACKAGE = "autoharness_data"

Dir = Path | Traversable


def config_dir() -> Traversable:
    return resources.files(PACKAGE) / "config"


def schema_dir() -> Traversable:
    return resources.files(PACKAGE) / "schema"


def as_dir(value: str | Path | Traversable | None, default: Traversable) -> Dir:
    return default if value is None else (Path(value) if isinstance(value, str) else value)


class ValidatorUnavailable(RuntimeError):
    """Schema validation is mandatory; it is never skipped."""


def require_validator():
    """Return the jsonschema module, or raise if it cannot be imported."""
    try:
        import jsonschema  # noqa: PLC0415
    except ImportError as exc:
        raise ValidatorUnavailable(
            "the 'jsonschema' package is required to validate output against the data contract, "
            "and it could not be imported. Install it (python -m pip install jsonschema, or "
            "install this package normally so its dependencies come with it). "
            "Schema validation is never skipped, so nothing was written."
        ) from exc
    return jsonschema
