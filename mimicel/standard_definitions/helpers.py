# standard_definitions/helpers.py
import re
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Optional

# --- Helper Functions (moved from functions.py) ---

def _parse_string_to_int(s_val: str, op_name: str) -> int:
    s = s_val.strip()
    base = 10
    sign = 1

    if not s:
        raise ValueError(f"Invalid string format for {op_name} (empty string): '{s_val}'")

    if s.startswith('+'):
        s = s[1:]
    elif s.startswith('-'):
        sign = -1
        s = s[1:]

    if not s:
        raise ValueError(f"Invalid string format for {op_name} (sign only): '{s_val}'")

    if s.startswith(('0x', '0X')):
        base = 16
        s = s[2:]
        if not s:
            raise ValueError(f"Invalid hex string for {op_name} (prefix only): '{s_val}'")
    try:
        val = int(s, base)
        return sign * val
    except ValueError:
        raise ValueError(f"Invalid string format for {op_name}: '{s_val}'")


def _parse_string_to_uint(s_val: str, op_name: str) -> int:
    s = s_val.strip()
    if s.lower().endswith('u'):
        s = s[:-1]
        if not s:
            raise ValueError(f"Invalid string format for {op_name} (suffix only): '{s_val}'")

    # Note: This relies on _parse_string_to_int which is now in the same file.
    parsed_int = _parse_string_to_int(s, op_name)

    if parsed_int < 0:
        raise ValueError(f"Cannot convert negative value to {op_name}: '{s_val}'")
    return parsed_int


def _parse_fixed_offset_tz(tz_str: str) -> Optional[timezone]:
    match = re.fullmatch(r"([+-])(\d{2}):(\d{2})", tz_str)
    if match:
        sign, hh, mm = match.groups()
        hours = int(hh)
        minutes = int(mm)
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            return None
        offset_seconds = (hours * 3600 + minutes * 60)
        if sign == '-':
            offset_seconds *= -1
        return timezone(timedelta(seconds=offset_seconds))
    return None


def _get_timezone_from_str(tz_name_str: str) -> Optional[tzinfo]:
    if tz_name_str.upper() == "UTC":
        return timezone.utc

    fixed_offset = _parse_fixed_offset_tz(tz_name_str)
    if fixed_offset:
        return fixed_offset

    try:  # Python 3.9+
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            return ZoneInfo(tz_name_str)
        except ZoneInfoNotFoundError:
            raise ValueError(f"Unknown IANA timezone name: '{tz_name_str}'")
    except ImportError:
        # zoneinfoがない古いPythonバージョンの場合、pytzの利用を検討するか、
        # IANA名のサポートを限定的とする。
        raise NotImplementedError(
            f"Full support for IANA timezone name '{tz_name_str}' requires 'zoneinfo' (Python 3.9+) or 'pytz'. Use 'UTC' or fixed offset like '+09:00'.")