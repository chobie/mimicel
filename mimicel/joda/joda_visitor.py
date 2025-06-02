from antlr4 import *
from datetime import timezone, timedelta, datetime # datetime.datetime もインポート（テスト用）

# Python 3.9+ の zoneinfo を試みる
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    ZONEINFO_AVAILABLE = True
except ImportError:
    ZONEINFO_AVAILABLE = False
    # ダミーのクラス/例外を定義して、コードの構造を保つ
    class ZoneInfo: # type: ignore
        def __init__(self, key):
            raise NotImplementedError("zoneinfo module is not available. Use Python 3.9+ or install a backport/alternative like 'tzdata' or 'pytz'.")
    class ZoneInfoNotFoundError(Exception): # type: ignore
        pass

from .JodaParser import JodaParser
from .JodaVisitor import JodaVisitor

class MyJodaVisitor(JodaVisitor):
    """
    Joda-Time形式のタイムゾーン文字列をパースし、Pythonのタイムゾーンオブジェクトを返すカスタムビジター。
    返り値: (timezone_object | None, list_of_error_messages | None)
    """

    def visitTimeZone(self, ctx:JodaParser.TimeZoneContext):
        if ctx.UTC_KEYWORD():
            # datetime.timezone.utc は UTC を表すシングルトンインスタンス
            return (timezone.utc, None)
        elif ctx.longTZ():
            return self.visit(ctx.longTZ())
        elif ctx.fixedTZ():
            return self.visit(ctx.fixedTZ())
        
        return (None, ["Unknown or empty timezone format in visitTimeZone"])

    def visitLongTZ(self, ctx:JodaParser.LongTZContext):
        if ctx.LONG_TZ_IDENTIFIER():
            identifier = ctx.LONG_TZ_IDENTIFIER().getText()
            if ZONEINFO_AVAILABLE:
                try:
                    tz_object = ZoneInfo(identifier)
                    return (tz_object, None)
                except ZoneInfoNotFoundError:
                    return (None, [f"Invalid IANA timezone identifier: '{identifier}'"])
                except Exception as e: # ZoneInfoの初期化で他のエラーも起こりうる
                    return (None, [f"Error creating ZoneInfo for '{identifier}': {str(e)}"])
            else:
                return (None, [f"Cannot parse '{identifier}': zoneinfo module (Python 3.9+) is required for named timezones. Consider using 'pytz' for older Python versions."])
        
        return (None, ["Invalid LongTZ format (missing identifier)"])

    def visitFixedTZ(self, ctx:JodaParser.FixedTZContext):
        sign_node = ctx.PLUS() or ctx.MINUS()
        
        if not sign_node or len(ctx.DIGIT()) != 4 or not ctx.COLON():
            return (None, ["Invalid FixedTZ format (structure mismatch)"])

        sign_text = sign_node.getText()
        
        try:
            # DIGITトークンから整数値を抽出
            h1 = int(ctx.DIGIT(0).getText())
            h2 = int(ctx.DIGIT(1).getText())
            m1 = int(ctx.DIGIT(2).getText())
            m2 = int(ctx.DIGIT(3).getText())

            hours = h1 * 10 + h2
            minutes = m1 * 10 + m2

            # 時と分の基本的な範囲チェック
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                 # Joda-Timeはより広い範囲を許容する可能性があるが、datetime.timezoneはUTCからのオフセットが
                 # -23:59 から +23:59 の範囲を想定しているため、このチェックは妥当。
                 # Joda-TimeのFixedDateTimeZoneは±99:59までサポートするが、Pythonのdatetime.timezoneはtimedeltaの範囲に依存
                return (None, [f"Invalid time value in FixedTZ offset: HH={hours:02d}, MM={minutes:02d}"])

            # オフセットを秒で計算
            offset_seconds = (hours * 3600) + (minutes * 60)
            if sign_text == '-':
                offset_seconds *= -1
            
            # timedeltaオブジェクトを作成
            # datetime.timezoneはtimedeltaの範囲 (-1 day < offset < 1 day) を要求
            if abs(offset_seconds) >= 24 * 3600:
                return (None, [f"FixedTZ offset out of range for datetime.timezone: {sign_text}{hours:02d}:{minutes:02d}"])

            offset = timedelta(seconds=offset_seconds)
            
            # datetime.timezone オブジェクトを作成
            tz_object = timezone(offset, name=f"{sign_text}{hours:02d}:{minutes:02d}") # nameはオプションだが分かりやすい
            return (tz_object, None)
        except ValueError: # int()変換失敗など
            return (None, [f"Invalid numeric value in FixedTZ offset: '{ctx.getText()}'"])
        except Exception as e:
            return (None, [f"Error processing FixedTZ offset for '{ctx.getText()}': {str(e)}"])