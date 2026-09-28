"""Load and sanity-check the category config (bundled config/categories.toml by default)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from .resources import Dir

_ID = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    kani_variant: str
    axis: str
    umbrella_repo: str | None
    umbrella_number: int | None
    prefixes: tuple[str, ...]
    args: bool
    expected_behavior: bool


@dataclass(frozen=True)
class Diagnostic:
    prefixes: tuple[str, ...]
    hint: str


@dataclass(frozen=True)
class Config:
    categories: tuple[Category, ...]
    diagnostics: tuple[Diagnostic, ...]


class ConfigError(ValueError):
    pass


def load(config_dir: Dir) -> Config:
    path = config_dir / "categories.toml"
    raw = tomllib.loads(path.read_bytes().decode("utf-8"))
    if raw.get("config_version") != 1:
        raise ConfigError(f"{path}: unsupported config_version {raw.get('config_version')!r}")

    cats: list[Category] = []
    for c in raw.get("category", []):
        cid = c["id"]
        if not _ID.match(cid):
            raise ConfigError(f"category id {cid!r} must match {_ID.pattern}")
        umbrella = c.get("umbrella") or {}
        prefixes = tuple(c["prefixes"])
        if not prefixes or any(not p for p in prefixes):
            raise ConfigError(f"category {cid!r} needs non-empty prefixes")
        cats.append(
            Category(
                id=cid,
                label=c["label"],
                kani_variant=c["kani_variant"],
                axis=c.get("axis", "coverage"),
                umbrella_repo=umbrella.get("repo"),
                umbrella_number=umbrella.get("number"),
                prefixes=prefixes,
                args=bool(c.get("args", False)),
                expected_behavior=bool(c.get("expected_behavior", False)),
            )
        )
    ids = [c.id for c in cats]
    if len(set(ids)) != len(ids):
        raise ConfigError("duplicate category ids")

    diags = tuple(Diagnostic(tuple(d["prefixes"]), d["hint"]) for d in raw.get("diagnostic", []))

    # No prefix may be a prefix of another category's prefix: that would make the
    # first-match order significant, and classification must be order-independent.
    all_prefixes = [(p, c.id) for c in cats for p in c.prefixes] + [
        (p, "<diagnostic>") for d in diags for p in d.prefixes
    ]
    for p1, o1 in all_prefixes:
        for p2, o2 in all_prefixes:
            if o1 != o2 and p2.startswith(p1):
                raise ConfigError(f"prefix {p1!r} ({o1}) overlaps {p2!r} ({o2})")

    return Config(tuple(cats), diags)
