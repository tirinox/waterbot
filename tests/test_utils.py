import pytest

from backend.utils import parse_timespan_to_seconds


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("30", 30),
        ("45s", 45),
        ("2h 30m", 9_000),
        ("1d, 12h", 129_600),
    ],
)
def test_parse_timespan(value, expected):
    assert parse_timespan_to_seconds(value) == expected


def test_parse_timespan_reports_invalid_input():
    assert parse_timespan_to_seconds("one hour").startswith("Error!")
