from datetime import timedelta  # timedelta は最終的な timedelta 変換では不要になるが、参照として残す
import math
from decimal import Decimal, ROUND_HALF_EVEN, Context, InvalidOperation

from antlr4 import ParserRuleContext
# ANTLR生成モジュールからのインポートパスは実際のプロジェクト構造に合わせてください
from mimicel.duration.CelDurationVisitor import CelDurationVisitor  # 変更なし
from mimicel.duration.CelDurationParser import CelDurationParser  # 変更なし

# google.protobuf.Duration をインポート
from google.protobuf.duration_pb2 import Duration as PbDuration

# ナノ秒換算係数 (変更なし)
UNIT_TO_NANOS: dict[str, int] = {
    "h": 3600 * 1_000_000_000,
    "m": 60 * 1_000_000_000,
    "s": 1_000_000_000,
    "ms": 1_000_000,
    "us": 1_000,
    "µs": 1_000,
    "ns": 1,
}
# Decimalの丸め設定 (変更なし)
decimal_context = Context(rounding=ROUND_HALF_EVEN)


class DurationVisitor(CelDurationVisitor):
    def visitParse(self, ctx: CelDurationParser.ParseContext) -> PbDuration:  # 返り値を PbDuration に変更
        if ctx.duration_input():
            return self.visit(ctx.duration_input())
        raise ValueError("Invalid or empty duration string provided to parser.")

    def visitDuration_input(self, ctx: CelDurationParser.Duration_inputContext) -> PbDuration:  # 返り値を PbDuration に変更
        sign_val: int = 1
        if ctx.sign() and ctx.sign().MINUS():
            sign_val = -1

        total_nanos_decimal = Decimal("0")

        components = ctx.component()
        if components:
            visited_units = set()
            for comp_ctx in components:
                value_decimal, unit_str = self.visit(comp_ctx)
                if unit_str in visited_units:
                    raise ValueError(f"Duration unit '{unit_str}' appears more than once.")
                visited_units.add(unit_str)
                total_nanos_decimal += value_decimal * Decimal(UNIT_TO_NANOS[unit_str])
        elif ctx.zero_value_with_optional_s():
            amount_str, has_seconds_unit = self.visit(ctx.zero_value_with_optional_s())
            try:
                val_decimal = Decimal(amount_str)
            except InvalidOperation:
                raise ValueError(f"Invalid number format '{amount_str}' from zero_value_with_optional_s rule.")
            if val_decimal != Decimal("0") and not has_seconds_unit:
                raise ValueError(f"Unit 's' is required for non-zero duration value: '{amount_str}'")
            if has_seconds_unit or val_decimal == Decimal("0"):
                total_nanos_decimal = val_decimal * Decimal(UNIT_TO_NANOS["s"])
        else:
            raise ValueError("Invalid duration string: structure did not match expected patterns in duration_input.")

        total_nanos_signed_decimal: Decimal = total_nanos_decimal * sign_val

        # google.protobuf.Duration の秒とナノ秒の最大・最小値は int64 と int32 の範囲だが、
        # CELの Duration の仕様上の範囲 (約+/-10000年) も考慮する必要がある。
        # ここではまず、Decimal から int への変換時のオーバーフローを防ぐ。
        # PbDuration の seconds は int64、nanos は int32。
        # total_nanos_signed_decimal が巨大な場合、int() での変換が失敗する可能性がある。
        # Protobuf の Duration の seconds は +/- 315,576,000,000 (約1万年) 程度が限界。
        # total_nanos は +/- (315,576,000,000 * 1e9) 程度になる。これは Python の int で扱える。

        try:
            total_nanos_int = int(total_nanos_signed_decimal)
        except (OverflowError, TypeError, InvalidOperation) as e:  # TypeError/InvalidOpはDecimal->intで巨大すぎると発生
            raise ValueError(
                f"Duration value {total_nanos_signed_decimal} is too large to represent as integer nanos. Error: {e}")

        # total_nanos_int から PbDuration の seconds と nanos を計算
        seconds_val = total_nanos_int // 1_000_000_000
        nanos_val = total_nanos_int % 1_000_000_000  # Python 3 の % は除数と同じ符号

        # google.protobuf.Duration の仕様に合わせる正規化:
        # 1. nanos は [-999,999,999, +999,999,999] の範囲
        # 2. seconds と nanos は同じ符号を持つ（seconds が 0 でない場合）
        if seconds_val > 0 and nanos_val < 0:
            seconds_val -= 1
            nanos_val += 1_000_000_000
        elif seconds_val < 0 and nanos_val > 0:
            seconds_val += 1
            nanos_val -= 1_000_000_000

        # CELのDurationの範囲チェック（google.protobuf.Durationの範囲とほぼ同等か、より狭い場合がある）
        # ここではPbDuration自体の構成要素の範囲を主眼とする
        # PbDurationのsecondsフィールドはint64、nanosフィールドはint32の範囲
        if not (-315_576_000_000 <= seconds_val <= 315_576_000_000):  # 約1万年
            raise ValueError(
                f"Duration seconds component {seconds_val}s is out of representable range for google.protobuf.Duration.")
        if not (-999_999_999 <= nanos_val <= 999_999_999):
            raise ValueError(f"Duration nanos component {nanos_val}ns is out of valid range [-999999999, 999999999].")

        return PbDuration(seconds=seconds_val, nanos=nanos_val)

    # visitComponent, visitAmount, visitUnit, visitZero_value_with_optional_s は変更なし
    def visitComponent(self, ctx: CelDurationParser.ComponentContext) -> tuple[Decimal, str]:
        if not ctx.amount() or not ctx.unit():
            raise ValueError("Internal parser error: component rule is missing amount or unit.")
        value_str = self.visit(ctx.amount())
        if value_str.endswith('.') and len(value_str) > 1 and value_str[:-1].isdigit():
            raise ValueError(
                f"Numeric value '{value_str}' in component must not end with a decimal point without fractional digits.")
        try:
            value_decimal = Decimal(value_str)
        except InvalidOperation:
            raise ValueError(f"Invalid numeric string '{value_str}' in duration component.")
        unit_str = self.visit(ctx.unit())
        return value_decimal, unit_str

    def visitAmount(self, ctx: CelDurationParser.AmountContext) -> str:
        if ctx.DECIMAL(): return ctx.DECIMAL().getText()
        if ctx.INT(): return ctx.INT().getText()
        raise ValueError("Internal parser error: Amount rule did not produce DECIMAL or INT.")

    def visitUnit(self, ctx: CelDurationParser.UnitContext) -> str:
        unit_text = ctx.getText()
        if unit_text not in UNIT_TO_NANOS:
            raise ValueError(f"Internal error or invalid g4: Unknown duration unit parsed: '{unit_text}'")
        return unit_text

    def visitZero_value_with_optional_s(self, ctx: CelDurationParser.Zero_value_with_optional_sContext) -> tuple[
        str, bool]:
        if not ctx.amount():
            raise ValueError("Internal parser error: zero_value_with_optional_s rule missing amount.")
        num_str = self.visit(ctx.amount())
        has_seconds_unit = ctx.SECONDS() is not None
        return num_str, has_seconds_unit