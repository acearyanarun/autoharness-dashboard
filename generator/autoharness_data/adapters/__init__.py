"""Adapters turn one Kani output format into a model.Listing.

Everything downstream of an adapter is independent of Kani's output format. When Kani
gains a machine-readable skip-reason output, add an adapter here; nothing else changes.
"""

from . import functions_json, kani_list_stdout

ADAPTERS = {
    kani_list_stdout.NAME: kani_list_stdout.parse,
    functions_json.NAME: functions_json.parse,
}
DEFAULT = kani_list_stdout.NAME
