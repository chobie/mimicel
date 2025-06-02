from datetime import datetime, timezone, timedelta

import re2

from cel.expr import syntax_pb2
from mimicel.duration import parse_duration

# CEL Timestamp limits (inclusive)
# Min: 0001-01-01T00:00:00Z -> seconds: -62135596800, nanos: 0
# Max: 9999-12-31T23:59:59.999999999Z -> seconds: 253402300799, nanos: 999999999
CEL_MIN_TIMESTAMP_SECONDS = -62135596800  # (datetime(1, 1, 1, tzinfo=timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()
CEL_MAX_TIMESTAMP_SECONDS = 253402300799  # (datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()

# mimicel/literal_registry_pb.py (または parse_timestamp_pb が定義されているファイル)

from datetime import datetime, timezone, timedelta
# import re # 標準ライブラリのreの代わりにre2を使用 (ユーザーの指示に従う)
import re2  # re2ライブラリをインポート
from typing import Optional  # Optional をインポート

# --- CEL Timestamp の範囲定数 (既存のものを想定) ---
CEL_MIN_TIMESTAMP_SECONDS = -62135596800
CEL_MAX_TIMESTAMP_SECONDS = 253402300799


def parse_timestamp_pb(text: str) -> datetime:
    """
    RFC3339形式に近いタイムスタンプ文字列リテラルをパースし、バリデーションを行う。
    ナノ秒精度（最大9桁）の小数部を処理する。
    タイムゾーン指定はオプションであり、省略された場合はUTCとして扱われる。
    返り値のdatetimeオブジェクトはマイクロ秒精度に丸められるが、
    バリデーションは元のナノ秒精度に基づいて行われる。
    """
    stripped_text = text.strip()
    if not stripped_text:
        raise ValueError("Timestamp string literal cannot be empty.")

    # 正規表現の修正: タイムゾーン部分全体をオプションにする (?: ... )?
    # G8: 'Z' (もしZがマッチした場合)
    # G9: 符号 (+ または -) (もしオフセットがマッチした場合)
    # G10: オフセット時 (HH) (もしオフセットがマッチした場合)
    # G11: オフセット分 (MM) (もしオフセットがマッチした場合)
    # これらのグループのうち、実際にマッチした部分のみが値を持つ。全体がマッチしなければ全てNone。
    pattern = re2.compile(
        r"(\d{4,5})-(\d{2})-(\d{2})"  # G1,G2,G3: Date (YYYY-MM-DD)
        r"[T ]"  # Separator 'T' or space
        r"(\d{2}):(\d{2}):(\d{2})"  # G4,G5,G6: Time (HH:MM:SS)
        r"(\.\d{1,9})?"  # G7: Optional Fractional seconds (.N to .NNNNNNNNN)
        r"(?:(Z)|(?:([+-])(\d{2}):(\d{2})))?$"  # G8(Z) または G9(sign)G10(HH)G11(MM) がオプションで末尾にマッチ
    )
    match = pattern.fullmatch(stripped_text)
    if not match:
        # フォーマットエラーの場合、"range:" プレフィックスは通常付けない
        raise ValueError(f"Invalid timestamp string format: '{text}'")

    try:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        second = int(match.group(6))
    except ValueError as e:  # 通常は正規表現で捕捉されるが念のため
        raise ValueError(f"Invalid integer component in date/time part of '{text}': {e}") from e

    fractional_str = match.group(7)  # 小数秒部分 (例: ".123456789")
    nanos = 0
    micros_for_datetime_constructor = 0
    if fractional_str:
        frac_digits_str = fractional_str[1:]  # ドットを除去
        if not frac_digits_str.isdigit():  # ここも正規表現でカバーされるはず
            raise ValueError(f"Invalid fractional second part: '{fractional_str}' in '{text}'")

        nanos_str_padded = frac_digits_str.ljust(9, '0')
        nanos = int(nanos_str_padded)
        if not (0 <= nanos <= 999999999):
            raise ValueError(f"Nanos part '{nanos}' out of range [0, 999999999] in '{text}'")

        micros_str_for_dt = frac_digits_str[:6].ljust(6, '0')
        micros_for_datetime_constructor = int(micros_str_for_dt)

    # タイムゾーン情報の抽出
    z_indicator = match.group(8)  # 'Z' または None
    offset_sign_char = match.group(9)  # '+', '-' または None
    offset_hour_str = match.group(10)  # 'HH' または None
    offset_min_str = match.group(11)  # 'MM' または None

    py_tzinfo: Optional[timezone]
    tz_offset_from_utc = timedelta(0)  # UTCからのオフセット (timedelta)

    if z_indicator == 'Z':
        py_tzinfo = timezone.utc
        # tz_offset_from_utc は timedelta(0) のまま
    elif offset_sign_char and offset_hour_str and offset_min_str:  # オフセットが指定されている場合
        try:
            offset_hours = int(offset_hour_str)
            offset_minutes = int(offset_min_str)
        except ValueError as e:  # 通常は正規表現で捕捉されるはず
            raise ValueError(f"Invalid integer in timezone offset of '{text}': {e}") from e

        if not (0 <= offset_hours <= 23 and 0 <= offset_minutes <= 59):
            raise ValueError(f"Invalid timezone offset value in '{text}'")

        offset_total_seconds_val = (offset_hours * 3600 + offset_minutes * 60)
        if offset_sign_char == '-':
            offset_total_seconds_val *= -1

        py_tzinfo = timezone(timedelta(seconds=offset_total_seconds_val))
        tz_offset_from_utc = timedelta(seconds=offset_total_seconds_val)
    else:
        # タイムゾーン指定が全くない場合 (Z もオフセットもない) はUTCとみなす
        py_tzinfo = timezone.utc
        tz_offset_from_utc = timedelta(0)

    # Pythonのdatetimeオブジェクトを（マイクロ秒精度で）構築
    try:
        dt_object_for_return = datetime(year, month, day, hour, minute, second,
                                        micros_for_datetime_constructor, tzinfo=py_tzinfo)
    except ValueError as e:
        raise ValueError(f"Invalid date/time components in '{text}': {e}") from e

    # --- CELの範囲検証のためのエポック秒計算 (ここは変更なし) ---
    try:
        naive_dt_integral_seconds = datetime(year, month, day, hour, minute, second)
    except ValueError as e:
        raise ValueError(
            f"Date/time components form an invalid date: {year}-{month}-{day} {hour}:{minute}:{second}. Error: {e}")
    utc_dt_integral_seconds = naive_dt_integral_seconds - tz_offset_from_utc
    epoch_ref_naive = datetime(1970, 1, 1)
    calculated_seconds = int((utc_dt_integral_seconds - epoch_ref_naive).total_seconds())

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
        # エラーメッセージに "range:" プレフィックスを付加 (テストハーネスの期待に合わせる場合)
        raise ValueError(
            f"range: Timestamp literal '{text}' (parsed as {calculated_seconds}s, {nanos}ns) "
            f"is outside the valid CEL range [{min_repr}, {max_repr}]."
        )

    return dt_object_for_return

def make_literal_pb(name: str, value: str) -> syntax_pb2.Expr:  # value はPythonの文字列
    # この関数はASTビルダから呼び出され、リテラルを内部的な関数呼び出しに変換する
    if name == "duration":
        try:
            parse_duration(value)  # バリデーションのみ (parse_duration は成功時に timedelta を返す)
        except ValueError as e:
            # バリデーション失敗時はエラーメッセージを具体的にして再送出
            raise ValueError(f"Invalid duration literal string: '{value}'. Details: {e}") from e

        return syntax_pb2.Expr(
            call_expr=syntax_pb2.Expr.Call(
                function="_lit_duration_",  # 内部処理用の関数名
                args=[
                    syntax_pb2.Expr(
                        const_expr=syntax_pb2.Constant(string_value=value)
                    )
                ],
            )
        )
    elif name == "timestamp":
        try:
            parse_timestamp_pb(value)  # バリデーションのみ (parse_timestamp_pb は成功時に datetime を返す)
        except ValueError as e:
            # バリデーション失敗時はエラーメッセージを具体的にして再送出
            raise ValueError(f"Invalid timestamp literal string: '{value}'. Details: {e}") from e

        return syntax_pb2.Expr(
            call_expr=syntax_pb2.Expr.Call(
                function="_lit_timestamp_",  # 内部処理用の関数名
                args=[
                    syntax_pb2.Expr(
                        const_expr=syntax_pb2.Constant(string_value=value)
                    )
                ],
            )
        )
    raise ValueError(f"Unknown literal type constructor: {name}")


LITERAL_CONSTRUCTORS_PB = {
    "duration": make_literal_pb,
    "timestamp": make_literal_pb,
}