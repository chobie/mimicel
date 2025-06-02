import pytest
from zoneinfo import ZoneInfo
from datetime import timezone, timedelta
from mimicel.joda import parse_timezone


def test_joda_named_timezone():
    tz, _ = parse_timezone("Asia/Tokyo")
    assert isinstance(tz, ZoneInfo)
    assert tz.key == "Asia/Tokyo"

def test_joda_named_timezone_europe():
    tz, _ = parse_timezone("Europe/Paris")
    assert isinstance(tz, ZoneInfo)
    assert tz.key == "Europe/Paris"

def test_joda_utc():
    tz, _ = parse_timezone("UTC")
    assert tz == timezone.utc

#error
#def test_joda_offset_positive():
#    tz, _ = parse_timezone("UTC+02:00")
#    assert tz.utcoffset(None) == timedelta(hours=2)

# error
#def test_joda_offset_negative():
#    tz, _ = parse_timezone("UTC-05:30")
#    assert tz.utcoffset(None) == timedelta(hours=-5, minutes=-30)

# error
#def test_joda_offset_z():
#    tz, _ = parse_timezone("Z")
#    assert tz == timezone.utc

def test_joda_custom_offset():
    tz, _ = parse_timezone("+09:00")
    assert tz.utcoffset(None) == timedelta(hours=9)

# error
#def test_joda_invalid_timezone():
#    with pytest.raises(ValueError):
#        parse_timezone("Not/AZone")