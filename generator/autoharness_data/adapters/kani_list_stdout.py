"""Adapter for the text tables Kani prints for `kani autoharness` (with or without --list).

Format source (Kani, kani-driver/src/autoharness/mod.rs, print_autoharness_metadata /
print_chosen_table / print_skipped_table; unchanged between b07abe8a and cab1b150):

    Kani generated automatic harnesses for N function(s):
    +-------+-------------------+
    | Crate | Selected Function |
    +===========================+
    | core  | a::b              |
    |-------+-------------------|
    | core  | a::c              |
    +-------+-------------------+

    Kani did not generate automatic harnesses for M function(s).
    If you believe that the provided reason is incorrect ...
    +-------+------------------+---------------------+
    | Crate | Skipped Function | Reason for Skipping |
    +================================================+
    | core  | x::y             | <reason text>       |
    +-------+------------------+---------------------+

or, for empty tables, "Selected Functions: None. ..." / "Skipped Functions: None. ...".
The tables are comfy-table's default ASCII_FULL preset. Kani omits KaniImpl skips from
the skipped table, so they are not observable here.

The parser is strict inside a table (any unexpected line is an error) and ignores
everything outside the two tables (build logs, the verification summary, etc.).
"""

from __future__ import annotations

import re

from ..model import Listing, RawEntry

NAME = "kani-list-stdout-v1"

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_GEN_HEADER = re.compile(r"^Kani generated automatic harnesses for (\d+) function\(s\):$")
_SKIP_HEADER = re.compile(r"^Kani did not generate automatic harnesses for (\d+) function\(s\)\.$")
_GEN_NONE = "Selected Functions: None."
_SKIP_NONE = "Skipped Functions: None."
_SKIP_PREAMBLE = "If you believe that the provided reason is incorrect"
_BORDER = re.compile(r"^\+(?:-+\+)+$")
_HEADER_RULE = re.compile(r"^\+=+\+$")
_ROW_RULE = re.compile(r"^\|(?:-+\+)*-+\|$")

_EXPECTED_HEADERS = {
    "generated": ["Crate", "Selected Function"],
    "skipped": ["Crate", "Skipped Function", "Reason for Skipping"],
}


class ParseError(ValueError):
    def __init__(self, line_no: int, message: str):
        super().__init__(f"line {line_no}: {message}")
        self.line_no = line_no


def _clean(line: str) -> str:
    return _ANSI.sub("", line).rstrip("\r\n").rstrip()


def _split_row(line: str, bounds: list[int], ncols: int, line_no: int) -> list[str]:
    """Split a table row into cells.

    Primary method: slice at the column boundaries taken from the table's top border,
    which is robust to `|` inside cell text. comfy-table pads by display width, so a
    row containing wide Unicode characters will not line up; in that case fall back to
    splitting on `|`, which is only safe when the row has exactly the structural pipes.
    """
    if len(line) == bounds[-1] + 1 and all(line[b] == "|" for b in bounds):
        return [line[bounds[i] + 1 : bounds[i + 1]].strip() for i in range(ncols)]
    if line.startswith("|") and line.endswith("|") and line.count("|") == ncols + 1:
        return [c.strip() for c in line[1:-1].split("|")]
    raise ParseError(line_no, f"table row does not match the table's column layout: {line!r}")


def _parse_table(lines: list[str], start: int, kind: str) -> tuple[list[list[str]], int, list[str]]:
    """Parse one table beginning at lines[start] (its top border).

    Returns (rows, index after the bottom border, warnings).
    """
    warnings: list[str] = []
    ncols = len(_EXPECTED_HEADERS[kind])
    top = lines[start]
    if not _BORDER.match(top):
        raise ParseError(start + 1, f"expected table top border, found {top!r}")
    bounds = [i for i, ch in enumerate(top) if ch == "+"]
    if len(bounds) != ncols + 1:
        raise ParseError(start + 1, f"expected {ncols} columns, border has {len(bounds) - 1}")

    i = start + 1
    header = _split_row(lines[i], bounds, ncols, i + 1) if i < len(lines) else None
    if header != _EXPECTED_HEADERS[kind]:
        raise ParseError(i + 1, f"unexpected table header {header!r} for {kind} table")
    i += 1
    if i >= len(lines) or not _HEADER_RULE.match(lines[i]):
        raise ParseError(i + 1, "expected header rule '+===...+'")
    i += 1

    rows: list[list[str]] = []
    while i < len(lines):
        line = lines[i]
        if line == top:  # bottom border is identical to the top border
            return rows, i + 1, warnings
        if _ROW_RULE.match(line):
            i += 1
            continue
        cells = _split_row(line, bounds, ncols, i + 1)
        if cells[0] == "" and rows:
            # Continuation line of a multi-line cell (comfy-table renders embedded
            # newlines this way). Kani's current strings have none; keep it lossless.
            for c, extra in enumerate(cells):
                if extra:
                    rows[-1][c] = f"{rows[-1][c]}\n{extra}"
            warnings.append(f"line {i + 1}: merged a continuation line into the previous row")
        elif cells[0] == "":
            raise ParseError(i + 1, "row with empty Crate cell at start of table")
        else:
            rows.append(cells + [str(i + 1)])  # carry line number in a trailing slot
        i += 1
    raise ParseError(start + 1, f"{kind} table is not terminated")


def parse(text: str) -> Listing:
    lines = [_clean(l) for l in text.splitlines()]
    entries: list[RawEntry] = []
    declared: dict[str, int | None] = {"generated": None, "skipped": None}
    seen: set[str] = set()
    warnings: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        kind = None
        if m := _GEN_HEADER.match(line):
            kind, count = "generated", int(m.group(1))
        elif m := _SKIP_HEADER.match(line):
            kind, count = "skipped", int(m.group(1))
        elif line.startswith(_GEN_NONE):
            kind, count = "generated", 0
        elif line.startswith(_SKIP_NONE):
            kind, count = "skipped", 0
        if kind is None:
            i += 1
            continue

        if kind in seen:
            raise ParseError(i + 1, f"second {kind} section found; expected exactly one listing per file")
        seen.add(kind)
        declared[kind] = count
        i += 1
        if count == 0:
            continue
        if kind == "skipped" and i < len(lines) and lines[i].startswith(_SKIP_PREAMBLE):
            i += 1
        rows, i, table_warnings = _parse_table(lines, i, kind)
        warnings.extend(table_warnings)
        for row in rows:
            line_no = int(row[-1])
            if kind == "generated":
                entries.append(RawEntry(row[0], row[1], "generated", None, line_no))
            else:
                entries.append(RawEntry(row[0], row[1], "skipped", row[2], line_no))

    return Listing(
        entries=entries,
        declared_generated=declared["generated"],
        declared_skipped=declared["skipped"],
        adapter=NAME,
        warnings=warnings,
    )
