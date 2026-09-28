# Original raw inputs (PENDING)

`tests/test_raw_baseline_reproduction.py` is skipped until these files are placed here,
**unmodified**, exactly as produced by the 2026-09-17 run:

| File name here | What it is | Practicum `snapshot.json` key |
|---|---|---|
| `autoharness-list.stdout.txt` or `.txt.gz` | stdout of `kani autoharness --list --std ...` | `listFile` |
| `kani-list.json` or `.json.gz` | the `kani list` JSON from the same run | `kaniListFile` |
| `snapshot.json` | the hand-written snapshot manifest | (itself) |

Do not reconstruct, re-render, or edit these files. If a file was captured with stderr
mixed in, keep it as it is and note that in `../PROVENANCE.md`.

Once they are present, the test must reproduce `../expected.toml` exactly from the raw
listing, and must match `../golden/` row by row.
