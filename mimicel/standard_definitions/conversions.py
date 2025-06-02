# standard_definitions/conversions.py
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

import re2
from google.protobuf.timestamp_pb2 import Timestamp

from ..cel_values.cel_types import (
    CelFunctionDefinition, CelType,
    CEL_DYN, CEL_TIMESTAMP, CEL_DURATION, CEL_INT, CEL_STRING, CEL_BOOL, CEL_BYTES,
    CEL_TYPE, CEL_UINT, CEL_NULL, CEL_DOUBLE, CEL_INT32_WRAPPER, CelDynValue
)
from ..cel_values import (
    CelValue, CelInt, CelBool, CelString, CelNull, CelBytes, CelDouble,
    CelTimestamp, CelDuration, CelUInt,
    CelProtobufInt32Value
)
from ..cel_values.constants import UINT64_MAX, INT64_MIN, INT64_MAX
from ..cel_values.base import _check_uint64_range, _check_int64_range
# standard_definitions.functions モジュールから STANDARD_LIBRARY と必要なヘルパーをインポート
# (循環参照を避けるため、ヘルパーは helpers.py から、STANDARD_LIBRARY は functions.py から)
from .helpers import _parse_string_to_int, _parse_string_to_uint
from ..cel_values.well_known_types import CelProtobufDuration, CelProtobufTimestamp, CelProtobufBytesValue, \
    CelProtobufStringValue, CelProtobufBoolValue, CelProtobufDoubleValue, CelProtobufUInt64Value, CelProtobufInt64Value, \
    CelProtobufUInt32Value
from ..context import EvalContext
from ..duration import parse_duration


# CEL Timestamp limits (inclusive)
# Min: 0001-01-01T00:00:00Z -> seconds: -62135596800, nanos: 0
# Max: 9999-12-31T23:59:59.999999999Z -> seconds: 253402300799, nanos: 999999999
CEL_MIN_TIMESTAMP_SECONDS = -62135596800
CEL_MAX_TIMESTAMP_SECONDS = 253402300799 # Corresponds to 9999-12-31T23:59:59

def cel_type_of_impl(arg: CelValue, context: Optional[EvalContext] = None) -> CelType:
    if not isinstance(arg, CelValue):
        raise TypeError(f"type() function expects a CelValue argument, got {type(arg)}")

    if isinstance(arg, CelDynValue):
        arg = arg.value

    # CelInt/CelUIntがEnum情報を保持し、.cel_typeがそれを返すように修正済み
    # ここでセマンティクスモードに応じて分岐する
    base_cel_type = arg.cel_type  # これはCelInt/UIntの場合、Enum型名を持つCelTypeを返す可能性がある

    if context and context.env and \
            isinstance(arg, (CelInt, CelUInt)) and \
            hasattr(arg, '_enum_type_name') and arg._enum_type_name:  # 引数がEnum値から作られたCelInt/CelUIntか

        enum_semantics = getattr(context.env, 'enum_semantics', 'integer')  # CELEnvからモード取得

        if enum_semantics == "integer":
            # "legacy" モード: Enum値の型は基底の整数型
            if isinstance(arg, CelInt):
                return CEL_INT
            elif isinstance(arg, CelUInt):  # CelUIntも同様
                return CEL_UINT
        elif enum_semantics == "typename":
            # "strong" モード: Enum値の型はそのEnum型名
            # base_cel_type (arg.cel_type) が既にEnum型名を指すCelTypeを返しているので、それをそのまま使う
            return base_cel_type

            # Enum値でない場合、またはenum_semanticsが設定されていない場合は、通常のcel_typeを返す
    return base_cel_type

# ディスパッチャ関数 (CelFunctionDefinitionのimplementationになる)
def cel_type_of_dispatcher(arg: CelValue, _context: Optional[EvalContext] = None) -> CelType:
    # _dispatch_and_execute_function から _context (EvalContextインスタンス) が渡される
    # print("[CONTEXT:" + repr(_context) + f", {_context.env.enum_semantics}]")
    return cel_type_of_impl(arg, _context)


# --- Type Conversion Function Implementations ---

def cel_convert_bool_impl(arg: CelValue) -> CelBool:
    if isinstance(arg, CelBool):  # bool(bool) -> bool (identity)
        return arg

    if isinstance(arg, CelString):
        s_val = arg.value  # 元の文字列値

        # --- 許可する文字列パターンの定義 ---
        # True と評価される文字列
        if s_val in ("true", "TRUE", "True", "1", "t", "T"):
            return CelBool(True)

        # False と評価される文字列
        if s_val in ("false", "FALSE", "False", "0", "f", "F"):
            return CelBool(False)

        # 上記のいずれの有効なパターンにも一致しない場合
        raise ValueError(f"Type conversion error: Invalid string '{arg.value}' for bool conversion.")

    # 数値型から bool への変換 (変更なし)
    if isinstance(arg, (CelInt, CelUInt)):
        return CelBool(arg.value != 0)

    if isinstance(arg, CelDouble):
        if math.isnan(arg.value) or math.isinf(arg.value):
            return CelBool(True)
        return CelBool(arg.value != 0.0)

    # 適切なオーバーロードが見つからない場合のエラーメッセージも調整
    type_name_to_display = arg.cel_type.name if hasattr(arg, 'cel_type') and hasattr(arg.cel_type, 'name') else type(
        arg).__name__
    raise TypeError(f"Type conversion error: No matching overload for bool conversion from {type_name_to_display}")

def cel_convert_bytes_impl(arg: CelValue) -> CelBytes: # 元の cel_convert_bytes
    if isinstance(arg, CelBytes): return arg
    if isinstance(arg, CelString):
        try:
            return CelBytes(arg.value.encode('utf-8'))
        except UnicodeEncodeError as e:
            raise ValueError(f"String to bytes conversion error: invalid UTF-8 sequence near position {e.start}") from e
    raise TypeError(f"No matching overload for bytes({arg.cel_type.name})")

def cel_convert_double_impl(arg: CelValue) -> CelDouble: # 元の cel_convert_double
    if isinstance(arg, CelDouble): return arg
    if isinstance(arg, CelInt): return CelDouble(float(arg.value))
    if isinstance(arg, CelUInt): return CelDouble(float(arg.value))
    if isinstance(arg, CelString):
        try:
            return CelDouble(float(arg.value))
        except ValueError:
            raise ValueError(f"Invalid string for double conversion: '{arg.value}'")
    raise TypeError(f"No matching overload for double({arg.cel_type.name})")


# duration(string) と duration(duration)

def cel_convert_duration_impl(arg: CelValue) -> CelProtobufDuration:
    if isinstance(arg, CelProtobufDuration): # duration(duration) -> identity
        return arg
    if isinstance(arg, CelString):
        s = arg.value.strip()
        if not s:
            raise ValueError("Duration string cannot be empty")
        try:
            # parse_duration は PbDuration を返すように修正された
            pb_duration_val = parse_duration(s)

            # CelProtobufDuration のコンストラクタに PbDuration インスタンスを渡す
            return CelProtobufDuration(pb_duration_val)
        except ValueError as e: # parse_duration からの ValueError
            raise ValueError(f"Invalid duration string format: '{s}'. Details: {e}") from e
        except Exception as e: # 予期せぬエラー
            raise RuntimeError(f"Unexpected error parsing duration string '{s}': {e}") from e
    # arg.cel_type.name の部分は実際のCelValueのAPIに合わせてください
    raise TypeError(f"No matching overload for duration({type(arg).__name__})") # または arg.cel_type.name


def cel_convert_int_impl(arg: CelValue, arg_type_name_for_error: str) -> CelInt:
    if isinstance(arg, CelInt): return arg
    if isinstance(arg, CelUInt):
        if arg.value > INT64_MAX:  # INT64_MAX (2^63 - 1) を超えるuint値はintに変換できない
            # ★★★ エラーメッセージを修正 ★★★
            raise ValueError(
                f"range error: uint value {arg.value} cannot be converted to int as it is out of int64 range")
        return CelInt(arg.value)
    if isinstance(arg, CelDouble):
        d_val = arg.value
        if math.isnan(d_val) or math.isinf(d_val):
            # NaN や Infinity からの変換はエラー
            raise ValueError(f"int conversion range error: cannot convert {d_val} to int")

        # 0への丸め
        truncated_val_float = math.trunc(d_val)

        # Pythonのintに変換 (非常に大きなfloatも扱える)
        try:
            int_value_from_double = int(truncated_val_float)
        except (OverflowError, ValueError):  # floatがintに変換できない場合 (通常は発生しにくいが念のため)
            raise ValueError(
                f"int conversion range error: double value {d_val} could not be converted to a finite integer.")

        # ★★★ CEL仕様の「(minInt, maxInt) 非包含」ルールを適用 ★★★
        # つまり、結果は INT64_MIN より大きく、かつ INT64_MAX より小さくなければならない
        if not (INT64_MIN < int_value_from_double < INT64_MAX):
            # この条件は int_value_from_double <= INT64_MIN または int_value_from_double >= INT64_MAX と同等
            raise ValueError(
                f"int conversion range error: double value {d_val} (truncated to {int_value_from_double}) "
                f"is not strictly within the int64 range ({INT64_MIN} < value < {INT64_MAX})."
            )

        return CelInt(int_value_from_double)  # CelInt のコンストラクタはint64範囲内を期待

    if isinstance(arg, CelString):
        try:
            val = _parse_string_to_int(arg.value, "int")  # _parse_string_to_int は基数も考慮
            # _check_int64_range で範囲チェック
            return CelInt(_check_int64_range(val, "String to int conversion"))
        except ValueError as e:  # _parse_string_to_int や _check_int64_range からのエラー
            # ★ メッセージに "range error" を含めることを検討
            raise ValueError(
                f"int conversion range error: invalid string format or value out of range for int conversion: '{arg.value}'. Details: {e}") from e

    # timestamp(int) の逆、int(timestamp)
    if isinstance(arg, CelProtobufTimestamp):  # Timestampラッパー型
        if arg.value is None:
            # ★ null timestamp から int への変換エラーメッセージ
            raise TypeError(f"type conversion error: cannot convert null {arg.cel_type.name} to int")
        epoch_seconds = math.trunc(arg.value.timestamp())
        return CelInt(_check_int64_range(epoch_seconds, "Timestamp to int conversion"))

    # int(wrapper type)
    if isinstance(arg, (CelProtobufInt32Value, CelProtobufInt64Value)):
        if arg.value is None: raise TypeError(f"type conversion error: cannot convert null {arg.cel_type.name} to int")
        return CelInt(arg.value)  # CelIntのコンストラクタで範囲チェックされると仮定
    if isinstance(arg, (CelProtobufUInt32Value,
                        CelProtobufUInt64Value)):  # from ..cel_values.well_known_types import CelProtobufUInt32Value, CelProtobufUInt64Value
        if arg.value is None: raise TypeError(f"type conversion error: cannot convert null {arg.cel_type.name} to int")
        if arg.value > INT64_MAX:
            raise ValueError(
                f"range error: uint value {arg.value} from {arg.cel_type.name} cannot be converted to int as it is out of int64 range")
        return CelInt(arg.value)
    if isinstance(arg, CelProtobufDoubleValue):  # from ..cel_values.well_known_types import CelProtobufDoubleValue
        if arg.value is None: raise TypeError(f"type conversion error: cannot convert null {arg.cel_type.name} to int")
        # CelDouble と同様のロジックで変換
        d_val = arg.value
        if math.isnan(d_val) or math.isinf(d_val):
            raise ValueError(f"conversion range error: cannot convert {d_val} from {arg.cel_type.name} to int")
        truncated_val = math.trunc(d_val)
        try:
            return CelInt(_check_int64_range(int(truncated_val), f"{arg.cel_type.name} to int conversion"))
        except ValueError as e:
            raise ValueError(
                f"int conversion range error: double value {d_val} from {arg.cel_type.name} is out of int64 range. Details: {e}") from e

    raise TypeError(f"No matching overload for int({arg_type_name_for_error})")


def cel_convert_int_dispatcher(arg: CelValue) -> CelInt:
    return cel_convert_int_impl(arg, arg.cel_type.name)


def cel_convert_string_impl(arg: CelValue, arg_type_name_for_error: str) -> CelString:
    if isinstance(arg, CelString): return CelString(arg.value)
    if isinstance(arg, CelBool): return CelString("true" if arg.value else "false")
    if isinstance(arg, CelInt): return CelString(str(arg.value))
    if isinstance(arg, CelUInt):
        return CelString(str(arg.value)) # 末尾の "u" を削除
    if isinstance(arg, CelDouble):
        if math.isinf(arg.value): return CelString("Infinity" if arg.value > 0 else "-Infinity")
        if math.isnan(arg.value): return CelString("NaN")
        # Python's str() for float is generally good. Avoid trailing .0 for whole numbers.
        s = str(arg.value)
        if s.endswith(".0"): s = s[:-2]
        return CelString(s)
    if isinstance(arg, CelBytes):
        try:
            return CelString(arg.value.decode('utf-8'))
        except UnicodeDecodeError as e:
            raise ValueError(f"Bytes to string conversion error: invalid UTF-8 sequence near position {e.start}") from e
    if isinstance(arg, CelProtobufTimestamp):  # ★ 修正
        if arg.value is None: raise TypeError(f"Cannot convert null {arg.cel_type.name} to string")
        dt_utc = arg.value  # .value is already UTC aware datetime
        base_iso = dt_utc.strftime('%Y-%m-%dT%H:%M:%S')
        micros = dt_utc.microsecond
        nanos_from_micros = micros * 1000  # Convert micros to nanos for consistency with PbTimestamp

        # PbTimestamp might have more precise nanos than what datetime.microsecond holds
        # It's better to use the nanos from the original _pb_value if available and precise
        actual_nanos = 0
        if arg._pb_value is not None:  # Access internal PbTimestamp for precise nanos
            actual_nanos = arg._pb_value.nanos

        if actual_nanos == 0:
            return CelString(f"{base_iso}Z")
        else:
            # Format up to 9 decimal places for nanoseconds, stripping trailing zeros.
            # Ensure seconds part from strftime is consistent with actual_nanos's second.
            # Example: 0.999999999s -> .999999999. 0.1s -> .1
            frac_str_full = f"{actual_nanos:09d}".rstrip('0')
            if not frac_str_full:  # e.g. if actual_nanos was 0 after rstrip (should not happen if actual_nanos !=0)
                return CelString(f"{base_iso}Z")
            return CelString(f"{base_iso}.{frac_str_full}Z")

    if isinstance(arg, CelProtobufDuration):  # ★ 修正
        if arg.value is None: raise TypeError(f"Cannot convert null {arg.cel_type.name} to string")
        td = arg.value  # .value is timedelta
        total_seconds = td.total_seconds()

        if total_seconds == 0: return CelString("0s")

        sign_str = "-" if total_seconds < 0 else ""
        abs_total_seconds_float = abs(total_seconds)

        secs_part = math.trunc(abs_total_seconds_float)
        # Use nanos from original _pb_value for precision if available
        nanos_part = 0
        if arg._pb_value is not None:
            # PbDuration nanos are signed with seconds or 0. We need absolute fractional part.
            nanos_part = abs(arg._pb_value.nanos)  # Use the stored nanos
        else:  # Fallback if _pb_value not directly available (e.g. constructed purely from timedelta)
            nanos_part = int(round((abs_total_seconds_float - secs_part) * 1_000_000_000))

        if nanos_part == 0:
            return CelString(f"{sign_str}{int(secs_part)}s")
        else:
            frac_str_full = f"{nanos_part:09d}".rstrip('0')
            if not frac_str_full:  # Should not happen if nanos_part != 0
                return CelString(f"{sign_str}{int(secs_part)}s")
            return CelString(f"{sign_str}{int(secs_part)}.{frac_str_full}s")

    raise TypeError(f"No matching overload for string({arg_type_name_for_error})")


def cel_convert_string_dispatcher(arg: CelValue) -> CelString:
    return cel_convert_string_impl(arg, arg.cel_type.name)


# mimicel/standard_definitions/conversions.py (または該当ファイル)

from datetime import datetime, timezone, timedelta
# import re # 標準ライブラリのreの代わりにre2を使用 (ユーザーの指示に従う)
import re2  # re2ライブラリをインポート
from typing import Optional  # CelValue, CelProtobufTimestamp などの型ヒントのため

# google.protobuf.timestamp_pb2.Timestamp を PbTimestamp (または単にTimestamp)としてインポート
# 実際のインポートパスはプロジェクト構成に合わせてください。
from google.protobuf.timestamp_pb2 import Timestamp as PbTimestamp

# CelValue, CelProtobufTimestamp, CelString, CelInt などの型は
# 既存のコードベースで定義されていると仮定します。
# from ..cel_types import CelValue, CelString, CelInt # 仮のインポートパス
# from ..cel_types import CelProtobufTimestamp # CelProtobufTimestamp の定義もここにあると仮定

# CEL Timestamp limits (inclusive)
CEL_MIN_TIMESTAMP_SECONDS = -62135596800
CEL_MAX_TIMESTAMP_SECONDS = 253402300799


# Placeholder for CelProtobufTimestamp and other CEL types if not fully defined in this snippet's scope
# class CelValue: ...
# class CelString(CelValue): ...
# class CelInt(CelValue): ...
# class CelProtobufTimestamp(CelValue):
#     def __init__(self, pb_instance: Optional[PbTimestamp]):
#         self._pb_value = pb_instance # Assuming this structure
#         # ...


def cel_convert_timestamp_impl(arg: 'CelValue', arg_type_name_for_error: str) -> 'CelProtobufTimestamp':
    if isinstance(arg, CelProtobufTimestamp):  # timestamp(timestamp) -> identity
        return arg

    if isinstance(arg, CelString):
        ts_str = arg.value.strip()
        if not ts_str:
            raise ValueError("Timestamp string for conversion cannot be empty.")

        # 正規表現の修正: タイムゾーン部分全体をオプションにする (?: ... )?
        # G8: 'Z' (もしZがマッチした場合)
        # G9: 符号 (+ または -) (もしオフセットがマッチした場合)
        # G10: オフセット時 (HH) (もしオフセットがマッチした場合)
        # G11: オフセット分 (MM) (もしオフセットがマッチした場合)
        pattern = re2.compile(
            r"(\d{4})-(\d{2})-(\d{2})"  # G1,G2,G3: Date (YYYY-MM-DD)
            r"[T ]"  # Separator 'T' or space
            r"(\d{2}):(\d{2}):(\d{2})"  # G4,G5,G6: Time (HH:MM:SS)
            r"(\.\d{1,9})?"  # G7: Optional Fractional seconds (.N to .NNNNNNNNN)
            r"(?:(Z)|(?:([+-])(\d{2}):(\d{2})))?$"  # G8(Z) または G9(sign)G10(HH)G11(MM) がオプションで末尾にマッチ
        )
        match = pattern.fullmatch(ts_str)
        if not match:
            # エラーメッセージを parse_timestamp_pb と同様に調整
            raise ValueError(
                f"Invalid RFC3339 string format for timestamp conversion: '{arg.value}' (timezone may be optional and defaulted to UTC, or format incorrect)")

        try:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            second = int(match.group(6))
        except ValueError as e:
            raise ValueError(f"Invalid integer component in date/time part of '{arg.value}': {e}") from e

        fractional_str = match.group(7)
        nanos = 0
        if fractional_str:
            frac_digits_str = fractional_str[1:]
            if not frac_digits_str.isdigit():
                raise ValueError(f"Invalid fractional second part: '{fractional_str}' in '{arg.value}'")

            nanos_str_padded = frac_digits_str.ljust(9, '0')
            nanos = int(nanos_str_padded)
            if not (0 <= nanos <= 999999999):
                raise ValueError(f"Nanos part '{nanos}' out of range [0, 999999999] in '{arg.value}'")

        # タイムゾーン情報の抽出 (parse_timestamp_pb と同様のロジック)
        z_indicator = match.group(8)  # 'Z' または None
        offset_sign_char = match.group(9)  # '+', '-' または None
        offset_hour_str = match.group(10)  # 'HH' または None
        offset_min_str = match.group(11)  # 'MM' または None

        tz_offset_from_utc = timedelta(0)  # デフォルトはUTCオフセットなし

        if z_indicator == 'Z':
            # tz_offset_from_utc は timedelta(0) のまま
            pass
        elif offset_sign_char and offset_hour_str and offset_min_str:  # オフセットが指定されている場合
            try:
                offset_hours = int(offset_hour_str)
                offset_minutes = int(offset_min_str)
            except ValueError as e:
                raise ValueError(f"Invalid integer in timezone offset of '{arg.value}': {e}") from e

            if not (0 <= offset_hours <= 23 and 0 <= offset_minutes <= 59):
                raise ValueError(f"Invalid timezone offset value in '{arg.value}'")

            offset_total_seconds_val = (offset_hours * 3600 + offset_minutes * 60)
            if offset_sign_char == '-':
                offset_total_seconds_val *= -1
            tz_offset_from_utc = timedelta(seconds=offset_total_seconds_val)
        # else: タイムゾーン指定が全くない場合、tz_offset_from_utc は timedelta(0) のまま (UTC扱い)

        # エポック秒計算ロジック (parse_timestamp_pb と同様)
        try:
            local_dt_naive_integral_seconds = datetime(year, month, day, hour, minute, second)
        except ValueError as e:
            raise ValueError(f"Invalid date/time components in '{arg.value}': {e}") from e

        utc_dt_integral_seconds = local_dt_naive_integral_seconds - tz_offset_from_utc
        epoch_ref_naive = datetime(1970, 1, 1)
        calculated_seconds = int((utc_dt_integral_seconds - epoch_ref_naive).total_seconds())

        # 範囲検証ロジック (parse_timestamp_pb と同様)
        is_valid_range = False
        if calculated_seconds < CEL_MIN_TIMESTAMP_SECONDS:
            is_valid_range = False
        elif calculated_seconds == CEL_MIN_TIMESTAMP_SECONDS:
            is_valid_range = (nanos >= 0)
        elif calculated_seconds > CEL_MAX_TIMESTAMP_SECONDS:
            is_valid_range = False
        elif calculated_seconds == CEL_MAX_TIMESTAMP_SECONDS:
            is_valid_range = (nanos <= 999999999)
        else:
            is_valid_range = (0 <= nanos <= 999999999)

        if not is_valid_range:
            min_repr = "0001-01-01T00:00:00Z"
            max_repr = "9999-12-31T23:59:59.999999999Z"
            raise ValueError(  # エラーメッセージに "range:" を含めるかはテストハーネスの期待による
                f"Timestamp string '{arg.value}' (parsed as {calculated_seconds}s, {nanos}ns) "
                f"is outside the valid CEL range [{min_repr}, {max_repr}]."
            )

        # PbTimestamp (google.protobuf.Timestamp) インスタンスを生成
        pb_timestamp = PbTimestamp()  # google.protobuf.Timestamp を使用
        pb_timestamp.seconds = calculated_seconds
        pb_timestamp.nanos = nanos

        return CelProtobufTimestamp(pb_timestamp)

    if isinstance(arg, CelInt):
        epoch_seconds_arg = arg.value
        try:
            if not (CEL_MIN_TIMESTAMP_SECONDS <= epoch_seconds_arg <= CEL_MAX_TIMESTAMP_SECONDS):
                min_dt_obj = datetime.fromtimestamp(CEL_MIN_TIMESTAMP_SECONDS, tz=timezone.utc)
                max_dt_obj = datetime.fromtimestamp(CEL_MAX_TIMESTAMP_SECONDS, tz=timezone.utc)
                raise ValueError(
                    f"Integer epoch seconds value {epoch_seconds_arg} for timestamp conversion is out of "
                    f"representable CEL range [{min_dt_obj.isoformat()} to {max_dt_obj.isoformat()} approx]."
                )

            pb_timestamp = PbTimestamp()  # google.protobuf.Timestamp を使用
            pb_timestamp.seconds = epoch_seconds_arg
            pb_timestamp.nanos = 0

            return CelProtobufTimestamp(pb_timestamp)
        except (OverflowError, OSError, ValueError) as e:
            raise ValueError(
                f"Error converting integer epoch seconds {epoch_seconds_arg} to timestamp. Details: {e}"
            ) from e

    raise TypeError(f"No matching overload for timestamp({arg_type_name_for_error})")


def cel_convert_timestamp_dispatcher(arg: CelValue) -> CelProtobufTimestamp:
    return cel_convert_timestamp_impl(arg, arg.cel_type.name)


def cel_convert_uint_impl(arg: CelValue, arg_type_name_for_error: str) -> CelUInt:
    if isinstance(arg, CelUInt): return arg
    if isinstance(arg, CelInt):
        if arg.value < 0:
            # ★★★ エラーメッセージを修正 ★★★
            raise ValueError(f"uint conversion range error: cannot convert negative int {arg.value} to uint")
        # _check_uint64_range は非負の数を期待するが、ここでは既に arg.value >= 0
        return CelUInt(_check_uint64_range(arg.value, "Int to uint conversion"))

    if isinstance(arg, CelDouble):
        d_val = arg.value
        if math.isnan(d_val) or math.isinf(d_val) or d_val < 0:
            # ★ メッセージに "range error" を含めることを検討
            raise ValueError(f"uint conversion range error: cannot convert double {d_val} to uint")

        truncated_val = math.trunc(d_val)
        # _check_uint64_range で0からUINT64_MAXの範囲か確認
        try:
            # int() への変換で非常に大きなfloatがエラーになる可能性は低い (Pythonのintは任意精度)
            # _check_uint64_range が最終的なCELのuint64範囲をチェックする
            return CelUInt(_check_uint64_range(int(truncated_val), "Double to uint conversion"))
        except ValueError as e:  # _check_uint64_range からの ValueError
            raise ValueError(
                f"uint conversion range error: double value {d_val} (truncated to {int(truncated_val)}) is out of uint64 range. Details: {e}") from e

    if isinstance(arg, CelString):
        try:
            val = _parse_string_to_uint(arg.value, "uint")  # _parse_string_to_uint は非負整数を返す
            return CelUInt(_check_uint64_range(val, "String to uint conversion"))
        except ValueError as e:  # _parse_string_to_uint や _check_uint64_range からのエラー
            # ★ メッセージに "range error" を含めることを検討
            raise ValueError(
                f"uint conversion range error: invalid string format or value out of range for uint conversion: '{arg.value}'. Details: {e}") from e

    # uint(wrapper type)
    if isinstance(arg, (CelProtobufUInt32Value, CelProtobufUInt64Value)):
        if arg.value is None: raise TypeError(f"type conversion error: cannot convert null {arg.cel_type.name} to uint")
        # .value は既にuint互換のはず。CelUIntでラップする際に範囲チェックが行われる。
        return CelUInt(arg.value)
    if isinstance(arg, CelProtobufInt32Value) or isinstance(arg,
                                                            CelProtobufInt64Value):  # from ..cel_values.well_known_types import ...
        if arg.value is None: raise TypeError(f"type conversion error: cannot convert null {arg.cel_type.name} to uint")
        if arg.value < 0:
            raise ValueError(
                f"uint conversion range error: cannot convert negative int {arg.value} from {arg.cel_type.name} to uint")
        return CelUInt(_check_uint64_range(arg.value, f"{arg.cel_type.name} to uint conversion"))

    raise TypeError(f"No matching overload for uint({arg_type_name_for_error})")


def cel_convert_uint_dispatcher(arg: CelValue) -> CelUInt:
    return cel_convert_uint_impl(arg, arg.cel_type.name)


def cel_type_of(arg: CelValue) -> CelType:  # 返り値型をCelTypeに
    if not isinstance(arg, CelValue):
        raise TypeError(f"type() function expects a CelValue argument, got {type(arg)}")
    return arg.cel_type  # .cel_type がEnum型名を持つCelTypeを返すように修正済み

def cel_convert_dyn(arg: CelValue) -> CelValue:
    return CelDynValue(arg)


def cel_global_int32_value_constructor(arg_value: Optional[CelValue] = None) -> CelProtobufInt32Value:
    if arg_value is None: # Int32Value()
        return CelProtobufInt32Value.from_int(None)
    if isinstance(arg_value, CelInt): # Int32Value(10)
        return CelProtobufInt32Value.from_int(arg_value.value)
    if isinstance(arg_value, CelNull): # Int32Value(null)
        return CelProtobufInt32Value.from_int(None)
    raise TypeError(f"Invalid argument for Int32Value(): expected int or null, got {arg_value.cel_type.name}")

# --- Int32Valueからの型変換 ---
def cel_convert_int32wrapper_to_int(arg: CelProtobufInt32Value) -> CelInt:
    if arg.value is None:
        raise TypeError("Cannot convert null google.protobuf.Int32Value to int")
    # CelIntコンストラクタでint64範囲チェックが行われる
    return CelInt(arg.value)

def cel_convert_int32wrapper_to_string(arg: CelProtobufInt32Value) -> CelString:
    if arg.value is None:
        # nullの文字列表現は "null" ではない (CELのstring(null)はエラーになるか、特定の表現になるか確認)
        # ここでは、もしstring(Int32Value(null)) がエラーなら、ここで例外を送出
        raise TypeError("Cannot convert null google.protobuf.Int32Value to string directly. Use 'has' or ternary operator.")
        # もし "null" という文字列を返すなら return CelString("null")
    return CelString(str(arg.value))


def cel_global_uint32_value_constructor(arg_value: Optional[CelValue] = None) -> CelProtobufUInt32Value:
    if arg_value is None:
        return CelProtobufUInt32Value.from_uint(None) # CelProtobufUInt32Value に from_uint を想定
    if isinstance(arg_value, CelUInt):
        return CelProtobufUInt32Value.from_uint(arg_value.value)
    if isinstance(arg_value, CelNull):
        return CelProtobufUInt32Value.from_uint(None)
    # CELでは uint(int_val) が可能なので、intからの変換も考慮する価値がある (仕様確認)
    # if isinstance(arg_value, CelInt):
    #     if arg_value.value < 0:
    #         raise ValueError("Cannot construct UInt32Value from negative int")
    #     return CelProtobufUInt32Value.from_uint(arg_value.value)
    raise TypeError(f"Invalid argument for google.protobuf.UInt32Value(): expected uint or null, got {arg_value.cel_type.name if isinstance(arg_value, CelValue) else type(arg_value).__name__}")

def cel_global_int64_value_constructor(arg_value: Optional[CelValue] = None) -> CelProtobufInt64Value:
    if arg_value is None:
        return CelProtobufInt64Value.from_int(None) # CelProtobufInt64Value に from_int を想定
    if isinstance(arg_value, CelInt):
        return CelProtobufInt64Value.from_int(arg_value.value)
    if isinstance(arg_value, CelNull):
        return CelProtobufInt64Value.from_int(None)
    raise TypeError(f"Invalid argument for google.protobuf.Int64Value(): expected int or null, got {arg_value.cel_type.name if isinstance(arg_value, CelValue) else type(arg_value).__name__}")

def cel_global_uint64_value_constructor(arg_value: Optional[CelValue] = None) -> CelProtobufUInt64Value:
    if arg_value is None:
        return CelProtobufUInt64Value.from_uint(None) # CelProtobufUInt64Value に from_uint を想定
    if isinstance(arg_value, CelUInt):
        return CelProtobufUInt64Value.from_uint(arg_value.value)
    if isinstance(arg_value, CelNull):
        return CelProtobufUInt64Value.from_uint(None)
    # if isinstance(arg_value, CelInt):
    #     if arg_value.value < 0:
    #         raise ValueError("Cannot construct UInt64Value from negative int")
    #     return CelProtobufUInt64Value.from_uint(arg_value.value)
    raise TypeError(f"Invalid argument for google.protobuf.UInt64Value(): expected uint or null, got {arg_value.cel_type.name if isinstance(arg_value, CelValue) else type(arg_value).__name__}")

def cel_global_double_value_constructor(arg_value: Optional[CelValue] = None) -> CelProtobufDoubleValue:
    if arg_value is None:
        return CelProtobufDoubleValue.from_double(None) # CelProtobufDoubleValue に from_double を想定
    if isinstance(arg_value, CelDouble):
        return CelProtobufDoubleValue.from_double(arg_value.value)
    if isinstance(arg_value, CelInt): # double(int_val)
        return CelProtobufDoubleValue.from_double(float(arg_value.value))
    if isinstance(arg_value, CelUInt): # double(uint_val)
        return CelProtobufDoubleValue.from_double(float(arg_value.value))
    if isinstance(arg_value, CelNull):
        return CelProtobufDoubleValue.from_double(None)
    raise TypeError(f"Invalid argument for google.protobuf.DoubleValue(): expected double, int, uint, or null, got {arg_value.cel_type.name if isinstance(arg_value, CelValue) else type(arg_value).__name__}")

# FloatValue は DoubleValue と同様に扱うことが多いですが、専用の型とラッパーがあれば別途定義
# def cel_global_float_value_constructor(arg_value: Optional[CelValue] = None) -> CelProtobufFloatValue:
#     # ... CelProtobufDoubleValue と同様の実装 ...

def cel_global_bool_value_constructor(arg_value: Optional[CelValue] = None) -> CelProtobufBoolValue:
    if arg_value is None:
        return CelProtobufBoolValue.from_bool(None) # CelProtobufBoolValue に from_bool を想定
    if isinstance(arg_value, CelBool):
        return CelProtobufBoolValue.from_bool(arg_value.value)
    if isinstance(arg_value, CelNull):
        return CelProtobufBoolValue.from_bool(None)
    raise TypeError(f"Invalid argument for google.protobuf.BoolValue(): expected bool or null, got {arg_value.cel_type.name if isinstance(arg_value, CelValue) else type(arg_value).__name__}")

def cel_global_string_value_constructor(arg_value: Optional[CelValue] = None) -> CelProtobufStringValue:
    if arg_value is None:
        return CelProtobufStringValue.from_str(None) # CelProtobufStringValue に from_str を想定
    if isinstance(arg_value, CelString):
        return CelProtobufStringValue.from_str(arg_value.value)
    if isinstance(arg_value, CelNull):
        return CelProtobufStringValue.from_str(None)
    raise TypeError(f"Invalid argument for google.protobuf.StringValue(): expected string or null, got {arg_value.cel_type.name if isinstance(arg_value, CelValue) else type(arg_value).__name__}")

def cel_global_bytes_value_constructor(arg_value: Optional[CelValue] = None) -> CelProtobufBytesValue:
    if arg_value is None:
        return CelProtobufBytesValue.from_bytes(None) # CelProtobufBytesValue に from_bytes を想定
    if isinstance(arg_value, CelBytes):
        return CelProtobufBytesValue.from_bytes(arg_value.value)
    if isinstance(arg_value, CelNull):
        return CelProtobufBytesValue.from_bytes(None)
    raise TypeError(f"Invalid argument for google.protobuf.BytesValue(): expected bytes or null, got {arg_value.cel_type.name if isinstance(arg_value, CelValue) else type(arg_value).__name__}")
