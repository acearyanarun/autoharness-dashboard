"""Run metadata: what was measured, with which tools, where, and how.

In CI this file is written by the workflow from its inputs (Phase 2). For fixtures it is
written by hand in fixtures/<run>/run-meta.toml, with provenance = "manual" and every
value traceable to a source recorded in that fixture's PROVENANCE.md.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{7,40}$")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RunMetaError(ValueError):
    pass


def load(path: Path) -> dict:
    with open(path, "rb") as fh:
        m = tomllib.load(fh)

    def need(obj: dict, key: str, where: str):
        if key not in obj:
            raise RunMetaError(f"{path}: missing {where}{key}")
        return obj[key]

    run_id = need(m, "run_id", "")
    if not _RUN_ID.match(run_id):
        raise RunMetaError(f"{path}: run_id {run_id!r} must match {_RUN_ID.pattern}")
    if need(m, "provenance", "") not in ("ci", "manual"):
        raise RunMetaError(f"{path}: provenance must be 'ci' or 'manual'")
    for section in ("kani", "library"):
        commit = need(need(m, section, ""), "commit", f"{section}.")
        if not _SHA.match(commit):
            raise RunMetaError(f"{path}: {section}.commit {commit!r} is not a hex git SHA")
    need(m, "target", "")
    need(need(m, "flags", ""), "bounded_arguments", "flags.")
    return m


def build_run(meta: dict, kani_version_from_list: str | None, source_files: list[dict], adapter: str) -> dict:
    """Assemble run.json (without schema_version, which emit adds)."""
    kani = dict(meta["kani"])
    declared_version = kani.get("version")
    if kani_version_from_list and declared_version and declared_version != kani_version_from_list:
        raise RunMetaError(
            f"run meta says Kani {declared_version} but the kani list JSON says {kani_version_from_list}"
        )
    kani_version = kani_version_from_list or declared_version

    library = dict(meta["library"])
    toolchain = meta.get("toolchain", {}).get("channel")
    flags = {"bounded_arguments": bool(meta["flags"]["bounded_arguments"])}

    # Two runs are comparable only if every input that can move the numbers is equal.
    key_material = json.dumps(
        [kani["commit"], library["commit"], toolchain, meta["target"], flags["bounded_arguments"]],
        separators=(",", ":"),
    )
    comparability_key = hashlib.sha256(key_material.encode()).hexdigest()[:16]

    return {
        "run_id": meta["run_id"],
        "provenance": meta["provenance"],
        "finished_at": meta.get("finished_at"),
        "duration_seconds": meta.get("duration_seconds"),
        "kani": {
            "repo": kani.get("repo"),
            "ref": kani.get("ref"),
            "commit": kani["commit"],
            "commit_is_full": len(kani["commit"]) == 40,
            "version": kani_version,
        },
        "library": {
            "repo": library.get("repo"),
            "ref": library.get("ref"),
            "commit": library["commit"],
            "commit_is_full": len(library["commit"]) == 40,
        },
        "toolchain": toolchain,
        "target": meta["target"],
        "flags": flags,
        "command": meta.get("command"),
        "host": meta.get("host"),
        "workflow_url": meta.get("workflow_url"),
        "adapter": adapter,
        "source_files": source_files,
        "comparability_key": comparability_key,
    }
