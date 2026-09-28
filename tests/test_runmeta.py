"""finished_at (ISO-8601) and host (fixed structure) in run metadata."""

import datetime as dt

import pytest

from autoharness_data import runmeta
from autoharness_data.runmeta import RunMetaError, normalize_finished_at, normalize_host


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-09-17", "2026-09-17"),
        (dt.date(2026, 9, 17), "2026-09-17"),  # unquoted TOML date
        ("2026-09-17T18:05:00Z", "2026-09-17T18:05:00Z"),
        ("2026-09-17T11:05:00-07:00", "2026-09-17T18:05:00Z"),  # normalised to UTC
        ("2026-09-17T18:05:00.250000+00:00", "2026-09-17T18:05:00.250000Z"),
        (dt.datetime(2026, 9, 17, 18, 5, tzinfo=dt.timezone.utc), "2026-09-17T18:05:00Z"),
        (None, None),
    ],
)
def test_finished_at_accepted(value, expected):
    assert normalize_finished_at(value, "t") == expected


@pytest.mark.parametrize(
    "value,match",
    [
        ("2026-09-17T18:05:00", "no timezone"),
        (dt.datetime(2026, 9, 17, 18, 5), "no timezone"),
        ("17/09/2026", "not ISO-8601"),
        ("2026-02-30", "not a valid date"),
        ("yesterday", "not ISO-8601"),
        (20260917, "must be an ISO-8601 string"),
    ],
)
def test_finished_at_rejected(value, match):
    with pytest.raises(RunMetaError, match=match):
        normalize_finished_at(value, "t")


def test_finished_at_pattern_matches_normalised_output():
    import re

    for v in ("2026-09-17", "2026-09-17T18:05:00Z", "2026-09-17T18:05:00.250000Z"):
        assert re.fullmatch(runmeta.FINISHED_AT_PATTERN, v)


def test_host_is_normalised_to_fixed_keys():
    assert normalize_host({"os": "linux", "arch": "x86_64", "memory_gb": 47}, "t") == {
        "os": "linux", "arch": "x86_64", "cpus": None, "memory_gb": 47,
    }
    assert normalize_host(None, "t") is None


@pytest.mark.parametrize(
    "host,match",
    [
        ({"os": "linux", "arch": "x86_64", "gpu": "none"}, "unknown host key"),
        ({"arch": "x86_64"}, "host.os is required"),
        ({"os": "linux", "arch": ""}, "host.arch is required"),
        ({"os": "linux", "arch": "x86_64", "cpus": 0}, "positive integer"),
        ({"os": "linux", "arch": "x86_64", "cpus": True}, "positive integer"),
        ({"os": "linux", "arch": "x86_64", "memory_gb": -1}, "positive number"),
        ("linux", "must be a table"),
    ],
)
def test_host_rejected(host, match):
    with pytest.raises(RunMetaError, match=match):
        normalize_host(host, "t")


def test_unquoted_toml_date_round_trips(tmp_path):
    p = tmp_path / "m.toml"
    p.write_text(
        'run_id = "x"\nprovenance = "manual"\nfinished_at = 2026-09-17\ntarget = "t"\n'
        '[kani]\ncommit = "abcdef0"\n[library]\ncommit = "abcdef1"\n[flags]\nbounded_arguments = false\n'
        '[host]\nos = "linux"\narch = "x86_64"\n',
        encoding="utf-8",
    )
    m = runmeta.load(p)
    assert m["finished_at"] == "2026-09-17"
    assert m["host"] == {"os": "linux", "arch": "x86_64", "cpus": None, "memory_gb": None}
