"""Test-only renderer that mimics the listing Kani prints, for synthetic fixtures.

It reproduces comfy-table's ASCII_FULL preset for ASCII content (one space of padding,
columns as wide as their widest cell). test_renderer_matches_kani.py checks this renderer
byte-for-byte against tables taken from Kani's own test suite, so synthetic fixtures made
with it use the real format. It is NOT a substitute for an original Kani listing.
"""

from __future__ import annotations

SKIP_PREAMBLE = (
    "If you believe that the provided reason is incorrect and Kani should have generated an "
    "automatic harness, please comment on this issue: https://github.com/model-checking/kani/issues/3832"
)


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    widths = [max(len(r[i]) for r in [header, *rows]) + 2 for i in range(len(header))]
    border = "+" + "+".join("-" * w for w in widths) + "+"

    def row(cells):
        return "|" + "|".join(" " + c.ljust(w - 2) + " " for c, w in zip(cells, widths)) + "|"

    out = [border, row(header), "+" + "=" * (len(border) - 2) + "+"]
    for i, r in enumerate(rows):
        if i:
            out.append("|" + "+".join("-" * w for w in widths) + "|")
        out.append(row(r))
    out.append(border)
    return out


def listing(generated: list[tuple[str, str]], skipped: list[tuple[str, str, str]]) -> str:
    """Render the two sections exactly as kani-driver prints them (leading blank lines included)."""
    lines: list[str] = []
    if generated:
        lines += ["", f"Kani generated automatic harnesses for {len(generated)} function(s):"]
        lines += table(["Crate", "Selected Function"], [list(g) for g in generated])
    else:
        lines += ["", "Selected Functions: None. Kani did not generate automatic harnesses for any functions in the available crate(s)."]
    if skipped:
        lines += ["", f"Kani did not generate automatic harnesses for {len(skipped)} function(s).", SKIP_PREAMBLE]
        lines += table(["Crate", "Skipped Function", "Reason for Skipping"], [list(s) for s in skipped])
    else:
        lines += ["", "Skipped Functions: None. Kani generated automatic harnesses for all functions in the available crate(s)."]
    return "\n".join(lines) + "\n"
