"""Run metadata: what was measured, with which tools, where, and how.

In CI this file is written by the workflow from its inputs (Phase 2). For fixtures it is
written by hand in fixtures/<run>/run-meta.toml, with provenance = "manual" and every
value traceable to a source recorded in that fixture's PROVENANCE.md.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import tomllib
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{7,40}$")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RunMetaError(ValueError):
    pass


# finished_at: an ISO-8601 calendar date ("2026-09-17") or a datetime with an explicit
# timezone ("2026-09-17T18:05:00Z", "2026-09-17T11:05:00-07:00"). A datetime without a
# timezone is rejected because it is ambiguous. Output is normalised: dates stay dates,
# datetimes are converted to UTC and written with a trailing "Z".
FINISHED_AT_PATTERN = r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z)?$"
HOST_KEYS = ("os", "arch", "cpus", "memory_gb")


def normalize_finished_at(value, where: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):  # unquoted TOML datetime
        parsed = value
    elif isinstance(value, dt.date):  # unquoted TOML date
        return value.isoformat()
    elif isinstance(value, str):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            try:
                return dt.date.fromisoformat(value).isoformat()
            except ValueError as exc:
                raise RunMetaError(f"{where}: finished_at {value!r} is not a valid date") from exc
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RunMetaError(
                f"{where}: finished_at {value!r} is not ISO-8601 (use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)"
            ) from exc
    else:
        raise RunMetaError(f"{where}: finished_at must be an ISO-8601 string, got {type(value).__name__}")
    if parsed.tzinfo is None:
        raise RunMetaError(f"{where}: finished_at {value!s} has no timezone; add 'Z' or an offset")
    return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_host(value, where: str) -> dict | None:
    """host is {os, arch, cpus, memory_gb}; unknown values are null, unknown keys rejected."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise RunMetaError(f"{where}: host must be a table")
    extra = sorted(set(value) - set(HOST_KEYS))
    if extra:
        raise RunMetaError(f"{where}: unknown host key(s) {extra}; allowed: {list(HOST_KEYS)}")
    for key in ("os", "arch"):
        if not isinstance(value.get(key), str) or not value[key]:
            raise RunMetaError(f"{where}: host.{key} is required and must be a non-empty string")
    cpus = value.get("cpus")
    if cpus is not None and (not isinstance(cpus, int) or isinstance(cpus, bool) or cpus < 1):
        raise RunMetaError(f"{where}: host.cpus must be a positive integer")
    mem = value.get("memory_gb")
    if mem is not None and (not isinstance(mem, (int, float)) or isinstance(mem, bool) or mem <= 0):
        raise RunMetaError(f"{where}: host.memory_gb must be a positive number")
    return {"os": value["os"], "arch": value["arch"], "cpus": cpus, "memory_gb": mem}


def load(path: Path) -> dict:
    m = tomllib.loads(Path(path).read_text(encoding="utf-8"))

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
    m["finished_at"] = normalize_finished_at(m.get("finished_at"), str(path))
    m["host"] = normalize_host(m.get("host"), str(path))
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
