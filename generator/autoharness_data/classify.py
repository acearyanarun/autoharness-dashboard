"""Assign each skipped function to exactly one configured category."""

from __future__ import annotations

from .config import Config
from .model import Classified, RawEntry, Unclassified

_OPEN = {"<": ">", "(": ")", "[": "]", "{": "}"}
_CLOSE = {v: k for k, v in _OPEN.items()}


def split_args(text: str) -> tuple[tuple[str, str], ...] | None:
    """Split 'a: T, b: HashMap<K, V>' into (name, type) pairs.

    Kani joins the pairs with ", " (autoharness/mod.rs), and types may themselves
    contain ", ". Split only at bracket depth 0, treating '->' as an arrow, not a
    closing bracket. Return None when the text cannot be split unambiguously; the
    verbatim reason is always kept, so nothing is lost.
    """
    parts: list[str] = []
    depth: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "-" and text[i : i + 2] == "->":
            buf.append("->")
            i += 2
            continue
        if ch in _OPEN:
            depth.append(ch)
        elif ch in _CLOSE:
            if not depth or depth[-1] != _CLOSE[ch]:
                return None
            depth.pop()
        if ch == "," and not depth and text[i : i + 2] == ", ":
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        buf.append(ch)
        i += 1
    if depth:
        return None
    parts.append("".join(buf))

    pairs = []
    for part in parts:
        name, sep, ty = part.partition(": ")
        if not sep or not name or not ty or " " in name:
            return None
        pairs.append((name, ty))
    return tuple(pairs)


def classify(entries: list[RawEntry], config: Config) -> tuple[list[Classified], list[Unclassified]]:
    out: list[Classified] = []
    unclassified: list[Unclassified] = []
    for e in entries:
        if e.status == "generated":
            out.append(Classified(e.crate, e.function, "generated", None, None, None))
            continue
        reason = e.reason or ""
        matches = [c for c in config.categories if any(reason.startswith(p) for p in c.prefixes)]
        if len(matches) == 1:
            cat = matches[0]
            args = None
            if cat.args:
                prefix = next(p for p in cat.prefixes if reason.startswith(p))
                args = split_args(reason[len(prefix) :].strip())
            out.append(Classified(e.crate, e.function, "skipped", cat.id, reason, args))
            continue
        hint = None
        if len(matches) > 1:
            hint = "matched several categories: " + ", ".join(c.id for c in matches)
        else:
            for d in config.diagnostics:
                if any(reason.startswith(p) for p in d.prefixes):
                    hint = d.hint
                    break
        unclassified.append(Unclassified(e.crate, e.function, reason, hint))
    return out, unclassified
