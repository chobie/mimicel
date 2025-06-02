from datetime import datetime, timezone, timedelta
import re2
from ..cel_values import (
    CelValue, CelInt, CelBool, CelString, CelBytes, CelMap,
    CelList, CelProtobufStruct, CelProtobufListValue, CelProtobufValue
)
from google.protobuf.timestamp_pb2 import Timestamp as PbTimestamp
from google.protobuf.duration_pb2 import Duration as PbDuration
from typing import Optional

from ..cel_values.well_known_types import CelProtobufTimestamp, CelDuration

try:
    # Python 3.9+ for IANA timezone database support
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    # Fallback for Python < 3.9 or if zoneinfo is not available.
    # This mock only supports "UTC" and raises error for other IANA names.
    # For full IANA timezone support on older Python, consider using the 'pytz' library.
    class ZoneInfoNotFoundError(Exception):  # type: ignore
        pass


    class ZoneInfo:  # type: ignore
        def __init__(self, key: str):
            if key is None or key.upper() != "UTC":
                raise ZoneInfoNotFoundError(
                    f"Timezone '{key}' not found (zoneinfo module not available or key unsupported by mock).")
            self._offset = timedelta(0)
            self._name = "UTC"

        def utcoffset(self, dt: Optional[datetime]) -> Optional[timedelta]: return self._offset

        def tzname(self, dt: Optional[datetime]) -> Optional[str]: return self._name

        def dst(self, dt: Optional[datetime]) -> Optional[timedelta]: return None



def cel_len_impl(arg: CelValue) -> CelInt:
    if isinstance(arg, CelProtobufValue):
        try:
            actual_container = arg._dynamic_convert()  # CelProtobufListValue or CelProtobufStruct
            if hasattr(actual_container, "__len__"):
                return CelInt(len(actual_container))
            else:  # Value がリストやマップに変換されなかった場合
                raise TypeError(
                    f"size() not supported for dynamically converted type '{actual_container.cel_type.name}' from Value kind '{arg.get_kind()}'")
        except NotImplementedError:  # Value の Struct/List 変換が未実装の場合
            raise TypeError(f"size() not supported for Value kind '{arg.get_kind()}' (conversion not implemented)")
    # ... (既存の CelList, CelMap, CelString などの処理) ...
    elif hasattr(arg, "__len__") and isinstance(arg, (CelList, CelString, CelBytes, CelMap, CelProtobufStruct,
                                                      CelProtobufListValue)):
        return CelInt(len(arg))

    type_name = arg.cel_type.name if hasattr(arg, 'cel_type') and hasattr(arg.cel_type, 'name') else type(arg).__name__
    raise TypeError(f"No matching overload for size({type_name}) or type does not support size.")


# String functions - 実装と登録は変更なし
def string_contains_impl(target: CelString, substr: CelString) -> CelBool:
    return CelBool(substr.value in target.value)

def string_ends_with_impl(target: CelString, suffix: CelString) -> CelBool:
    return CelBool(target.value.endswith(suffix.value))

def string_matches_impl(target: CelString, regex_pattern: CelString) -> CelBool:
    try:
        return CelBool(re2.search(regex_pattern.value, target.value) is not None)
    except re2.error as e:
        raise RuntimeError(f"Regex error in 'matches': {e}") from e

def string_starts_with_impl(target: CelString, prefix: CelString) -> CelBool:
    return CelBool(target.value.startswith(prefix.value))

# --- Placeholder CEL type definitions (adapt to your actual type system) ---

# Assuming PbTimestamp and PbDuration are aliases for Google's Protobuf types

def _parse_timezone_string(tz_cel: Optional[CelString]) -> timezone:
    """
    Parses a CEL string representing a timezone into a Python timezone object.
    Supports IANA names (via zoneinfo), RFC3339 offsets (e.g., +05:00, -08:00),
    and positive offsets without a leading '+' (e.g., 02:00).
    Defaults to UTC if tz_cel is None or empty.
    """
    if tz_cel is None or not tz_cel.value:
        return timezone.utc

    tz_str = tz_cel.value.strip()
    if not tz_str:
        return timezone.utc

    # Try IANA timezone name first
    try:
        return ZoneInfo(tz_str)
    except ZoneInfoNotFoundError:
        pass
    except Exception:
        pass

    # Try to parse as offset (e.g., "+05:00", "-08:00", or "02:00" for +02:00)
    # ▼▼▼ 正規表現とロジックの修正 ▼▼▼
    # ([+-])? : 符号 (+ または -) をオプションにする (キャプチャグループ1)
    # (\d{2})  : 時 (HH) (キャプチャグループ2)
    # :(\d{2}) : 分 (MM) (キャプチャグループ3)
    offset_match = re2.fullmatch(r"([+-])?(\d{2}):(\d{2})", tz_str)
    if offset_match:
        sign_char = offset_match.group(1)  # '+' or '-' or None
        hours_str = offset_match.group(2)
        minutes_str = offset_match.group(3)
        try:
            hours = int(hours_str)
            minutes = int(minutes_str)

            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError("Offset hours/minutes out of range.")

            offset_delta_seconds = (hours * 3600 + minutes * 60)

            # 符号が '-' の場合のみ負にする。符号がない場合や '+' の場合は正。
            if sign_char == '-':
                offset_delta_seconds *= -1

            return timezone(timedelta(seconds=offset_delta_seconds))
        except ValueError:
            # int変換失敗や範囲外の場合は、無効なオフセット文字列としてフォールスルー
            pass
    # ▲▲▲ 正規表現とロジックの修正 ▲▲▲

    # Handle "UTC" explicitly if ZoneInfo("UTC") might have failed
    if tz_str.upper() == "UTC":
        return timezone.utc

    raise ValueError(f"Invalid or unsupported timezone string: '{tz_str}'")


# タイムスタンプアクセサ関数 (getHoursなど) は、この修正された _parse_timezone_string を使用します。
# その他の関数 (get_timestamp_hours など) の本体は変更の必要はありません。
# 以下は get_timestamp_hours の例（変更なし、_parse_timezone_string の修正が影響）
# from .cel_types import CelProtobufTimestamp, CelInt # Your actual imports
# from .utils import _datetime_from_pb_timestamp     # Your actual imports

# def get_timestamp_hours(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
#     if ts_cel is None or ts_cel.pb_timestamp is None:
#         raise ValueError("Cannot call getHours on a null timestamp.")
#     pb_ts = ts_cel.pb_timestamp
#
#     dt_utc = _datetime_from_pb_timestamp(pb_ts)
#     target_tz = _parse_timezone_string(tz_cel) #修正されたこの関数が呼ばれる
#     dt_local = dt_utc.astimezone(target_tz)
#     return CelInt(dt_local.hour)


def _datetime_from_pb_timestamp(pb_ts: PbTimestamp) -> datetime:
    """Converts a google.protobuf.Timestamp to a timezone-aware Python datetime object (UTC)."""
    if pb_ts is None:
        # This case should ideally be handled by the caller checking CelProtobufTimestamp._pb_value
        raise ValueError("Input protobuf timestamp is null")

    # google.protobuf.Timestamp is seconds and nanos from UTC epoch.
    # Python datetime can be constructed from UTC epoch.
    # Max/min protobuf timestamp values are within Python datetime's representable year range.
    try:
        # Create datetime from seconds and microseconds (derived from nanos)
        # This will be a UTC datetime.
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        # Add seconds and microseconds (from nanos)
        # timedelta handles large seconds values correctly.
        dt_utc = epoch + timedelta(seconds=pb_ts.seconds, microseconds=pb_ts.nanos // 1000)
        return dt_utc
    except OverflowError:  # seconds might be too large for timedelta intermediate if not careful
        # However, Timestamp seconds should fit within standard date calculations
        # A more direct, but potentially less standard way for extreme dates (though timedelta should be fine):
        # dt = datetime.utcfromtimestamp(0) + timedelta(seconds=pb_ts.seconds) # Still relies on timedelta
        # dt = dt.replace(microsecond=pb_ts.nanos // 1000)
        # The above epoch + timedelta is generally robust for valid Timestamp seconds/nanos.
        raise ValueError(f"Timestamp value {pb_ts.seconds}s, {pb_ts.nanos}ns out of range for datetime conversion.")


# --- Timestamp Accessor Implementations ---

def get_timestamp_full_year(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the full year from the timestamp in the given timezone (or UTC)."""
    if ts_cel is None or ts_cel._pb_value is None:
        raise ValueError("Cannot call getFullYear on a null timestamp.")
    pb_ts = ts_cel._pb_value

    dt_utc = _datetime_from_pb_timestamp(pb_ts)
    target_tz = _parse_timezone_string(tz_cel)
    dt_local = dt_utc.astimezone(target_tz)
    return CelInt(dt_local.year)


def get_timestamp_month(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the month (0-11) from the timestamp in the given timezone (or UTC)."""
    if ts_cel is None or ts_cel._pb_value is None:
        raise ValueError("Cannot call getMonth on a null timestamp.")
    pb_ts = ts_cel._pb_value

    # Assuming _datetime_from_pb_timestamp is the correct helper function name
    dt_utc = _datetime_from_pb_timestamp(pb_ts)
    target_tz = _parse_timezone_string(tz_cel)
    dt_local = dt_utc.astimezone(target_tz)

    # CEL spec for getMonth() is 0-11 (e.g., 0 for January).
    # Python's datetime.month is 1-12.
    # So, subtract 1 from Python's result.
    month_0_based = dt_local.month - 1

    return CelInt(month_0_based)

def get_timestamp_day_of_month(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the day of the month (0-30) from the timestamp in the given timezone (or UTC)."""
    if ts_cel is None or ts_cel._pb_value is None:
        raise ValueError("Cannot call getDayOfMonth on a null timestamp.")
    pb_ts = ts_cel._pb_value

    dt_utc = _datetime_from_pb_timestamp(pb_ts)
    target_tz = _parse_timezone_string(tz_cel)
    dt_local = dt_utc.astimezone(target_tz)
    # CEL spec: getDayOfMonth() returns 0-30 (0 for 1st). Python's datetime.day is 1-31.
    return CelInt(dt_local.day - 1)


def get_timestamp_day_of_month_1_based(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the day of the month (1-31) for the custom 'getDate' function."""
    if ts_cel is None or ts_cel._pb_value is None:
        raise ValueError("Cannot call getDate on a null timestamp.")
    pb_ts = ts_cel._pb_value

    dt_utc = _datetime_from_pb_timestamp(pb_ts)
    target_tz = _parse_timezone_string(tz_cel)
    dt_local = dt_utc.astimezone(target_tz)
    return CelInt(dt_local.day)  # Python's datetime.day is 1-31


def get_timestamp_day_of_year(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the day of the year (0-365) from the timestamp in the given timezone (or UTC)."""
    if ts_cel is None or ts_cel._pb_value is None:  # Corrected to access _pb_value
        raise ValueError("Cannot call getDayOfYear on a null timestamp.")
    pb_ts = ts_cel._pb_value

    # Assuming _datetime_from_pb_timestamp is the correct helper function name
    dt_utc = _datetime_from_pb_timestamp(pb_ts)
    target_tz = _parse_timezone_string(tz_cel)
    dt_local = dt_utc.astimezone(target_tz)

    # CEL spec for getDayOfYear() is 0-365. Python's tm_yday is 1-366.
    # So, subtract 1 from Python's result.
    day_of_year_0_based = dt_local.timetuple().tm_yday - 1

    return CelInt(day_of_year_0_based)

def get_timestamp_day_of_week(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the day of the week (0 for Sunday, 1 for Monday, ..., 6 for Saturday)."""
    if ts_cel is None or ts_cel._pb_value is None:
        raise ValueError("Cannot call getDayOfWeek on a null timestamp.")
    pb_ts = ts_cel._pb_value

    dt_utc = _datetime_from_pb_timestamp(pb_ts)
    target_tz = _parse_timezone_string(tz_cel)
    dt_local = dt_utc.astimezone(target_tz)
    # Python's datetime.weekday(): Monday is 0 and Sunday is 6.
    # CEL spec: Sunday is 0, Monday is 1, ..., Saturday is 6.
    # Conversion: (python_weekday + 1) % 7 maps Mon(0)->1, Tue(1)->2, ..., Sun(6)->0.
    cel_day_of_week = (dt_local.weekday() + 1) % 7
    return CelInt(cel_day_of_week)


def get_timestamp_hours(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the hours (0-23) from the timestamp in the given timezone (or UTC)."""
    if ts_cel is None or ts_cel._pb_value is None:
        raise ValueError("Cannot call getHours on a null timestamp.")
    pb_ts = ts_cel._pb_value

    dt_utc = _datetime_from_pb_timestamp(pb_ts)
    target_tz = _parse_timezone_string(tz_cel)
    dt_local = dt_utc.astimezone(target_tz)
    return CelInt(dt_local.hour)


def get_timestamp_minutes(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the minutes (0-59) from the timestamp in the given timezone (or UTC)."""
    if ts_cel is None or ts_cel._pb_value is None:
        raise ValueError("Cannot call getMinutes on a null timestamp.")
    pb_ts = ts_cel._pb_value

    dt_utc = _datetime_from_pb_timestamp(pb_ts)
    target_tz = _parse_timezone_string(tz_cel)
    dt_local = dt_utc.astimezone(target_tz)
    return CelInt(dt_local.minute)


def get_timestamp_seconds(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the seconds (0-59) from the timestamp in the given timezone (or UTC)."""
    if ts_cel is None or ts_cel._pb_value is None:
        raise ValueError("Cannot call getSeconds on a null timestamp.")
    pb_ts = ts_cel._pb_value

    dt_utc = _datetime_from_pb_timestamp(pb_ts)
    target_tz = _parse_timezone_string(tz_cel)
    dt_local = dt_utc.astimezone(target_tz)
    return CelInt(dt_local.second)


def get_timestamp_milliseconds(ts_cel: CelProtobufTimestamp, tz_cel: Optional[CelString] = None) -> CelInt:
    """Gets the milliseconds (0-999) from the timestamp's sub-second component."""
    if ts_cel is None or ts_cel._pb_value is None:
        raise ValueError("Cannot call getMilliseconds on a null timestamp.")
    pb_ts = ts_cel._pb_value
    # The 'nanos' part of a google.protobuf.Timestamp is the fractional second,
    # independent of timezone transformations that affect the main date/time parts.
    # It's already aligned with the UTC 'seconds' field.
    # Milliseconds = nanos / 1,000,000.
    milliseconds = pb_ts.nanos // 1_000_000
    return CelInt(milliseconds)


# --- Duration Accessor Implementations ---

_NANOS_PER_MILLISECOND = 1_000_000
_NANOS_PER_SECOND = 1_000_000_000
_NANOS_PER_MINUTE = 60 * _NANOS_PER_SECOND
_NANOS_PER_HOUR = 60 * _NANOS_PER_MINUTE


def _get_total_nanos_from_cel_duration(dur_cel: CelDuration) -> int:
    """Extracts total nanoseconds from CelDuration, handling potential nulls."""
    if dur_cel is None or dur_cel._pb_value is None:
        raise ValueError("Cannot operate on a null duration.")
    pb_dur = dur_cel._pb_value

    # A google.protobuf.Duration should be normalized:
    # - nanos is in the range -999,999,999 to +999,999,999 inclusive.
    # - seconds and nanos must have the same sign (unless one is zero).
    # If not normalized, results of accessors might be unexpected by CEL spec.
    # We assume pb_dur is already normalized as per protobuf spec.
    if not (-999_999_999 <= pb_dur.nanos <= 999_999_999):
        raise ValueError("Duration nanos component out of range [-999999999, 999999999].")
    if pb_dur.seconds > 0 and pb_dur.nanos < 0:
        raise ValueError("Duration seconds is positive but nanos is negative.")
    if pb_dur.seconds < 0 and pb_dur.nanos > 0:
        raise ValueError("Duration seconds is negative but nanos is positive.")

    return pb_dur.seconds * _NANOS_PER_SECOND + pb_dur.nanos


def get_duration_hours(dur_cel: CelDuration) -> CelInt:
    """Gets the hour component of the duration."""
    total_nanos = _get_total_nanos_from_cel_duration(dur_cel)
    # Integer division, truncates towards zero (which is usually correct for these extractors)
    return CelInt(int(total_nanos / _NANOS_PER_HOUR))  # Ensure int for Python 2/3 compat if total_nanos could be float


def get_duration_minutes(dur_cel: CelDuration) -> CelInt:
    """Gets the minute component of the duration (0-59, adjusted for sign)."""
    total_nanos = _get_total_nanos_from_cel_duration(dur_cel)
    minutes = int(total_nanos / _NANOS_PER_MINUTE)
    return CelInt(minutes)


def get_duration_seconds(dur_cel: CelDuration) -> CelInt:
    """Gets the second component of the duration (0-59, adjusted for sign)."""
    total_nanos = _get_total_nanos_from_cel_duration(dur_cel)
    seconds = int(total_nanos / _NANOS_PER_SECOND)
    return CelInt(seconds)


def get_duration_milliseconds(dur_cel: CelDuration) -> CelInt:
    """Gets the millisecond component of the duration (0-999, adjusted for sign)."""
    total_nanos = _get_total_nanos_from_cel_duration(dur_cel)
    milliseconds = int((total_nanos % _NANOS_PER_SECOND) / _NANOS_PER_MILLISECOND)
    return CelInt(milliseconds)

