"""Plain data types shared by the pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["generated", "skipped"]


@dataclass(frozen=True)
class RawEntry:
    """One function as reported by an adapter, before classification."""

    crate: str
    function: str
    status: Status
    # Kani's "Reason for Skipping" cell, verbatim (skipped entries only).
    reason: str | None = None
    # 1-based line number in the source file, for error messages.
    line: int | None = None


@dataclass
class Listing:
    """What an adapter extracted from one Kani listing."""

    entries: list[RawEntry]
    # Counts Kani itself announced ("... for N function(s)"), independent of
    # the table rows. None means the header was not found.
    declared_generated: int | None
    declared_skipped: int | None
    adapter: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Classified:
    """A function after classification."""

    crate: str
    function: str
    status: Status
    category: str | None  # stable category id; None for generated functions
    detail: str | None  # Kani's reason text, verbatim
    args: tuple[tuple[str, str], ...] | None  # (name, type) pairs when unambiguous


@dataclass(frozen=True)
class Unclassified:
    crate: str
    function: str
    reason: str
    hint: str | None  # e.g. "Kani UserFilter: listing was run with include/exclude patterns"


@dataclass
class Check:
    id: str
    severity: Literal["error", "warning"]
    status: Literal["pass", "fail", "skipped"]
    message: str
    expected: object = None
    actual: object = None
