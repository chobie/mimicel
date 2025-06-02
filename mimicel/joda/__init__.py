from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener

from datetime import datetime # datetime.datetime をインポート
from .JodaLexer import JodaLexer
from .JodaParser import JodaParser
from .joda_visitor import MyJodaVisitor, ZONEINFO_AVAILABLE # カスタムビジターをインポート

class MyErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.has_error = False
        self.error_messages = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.has_error = True
        self.error_messages.append(f"Syntax Error: line {line}:{column} {msg}")

def parse_timezone(input_string: str):
    """
    Joda-Time形式のタイムゾーン文字列をビジターを使ってパースし、
    (Python timezone object | None, list_of_error_messages | None) のタプルを返す。
    """
    input_stream = InputStream(input_string)
    lexer = JodaLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = JodaParser(token_stream)

    parser.removeErrorListeners()
    error_listener = MyErrorListener()
    parser.addErrorListener(error_listener)

    tree = parser.timeZone()

    if error_listener.has_error:
        return (None, error_listener.error_messages)

    visitor = MyJodaVisitor()
    tz_object, visitor_errors = visitor.visit(tree)

    if visitor_errors: # ビジター内でエラーが検出された場合
        return (tz_object, visitor_errors) # tz_objectはNoneかもしれない

    return tz_object, None # エラーなし

if __name__ == '__main__':
    test_strings = [
        "UTC",
        "Europe/Berlin",        # zoneinfoが必要
        "America/New_York",     # zoneinfoが必要
        "Asia/Tokyo",           # zoneinfoが必要
        "Invalid/Zone",         # zoneinfoでエラーになる想定
        "+09:00",
        "-05:30",
        "+00:00",
        "-00:00",
        "+14:00",               # 有効なオフセット
        "-10:45",               # 有効なオフセット
        "Etc/GMT-10",           # zoneinfoが必要
        "GMT+5",                # zoneinfoでは "Etc/GMT+5" などが正しい
        "+25:00",               # FixedTZとして範囲外エラーになる想定
        "-99:00",               # FixedTZとして範囲外エラーになる想定
        "+0900",                # 構文エラー
        "InvalidTZ",            # 構文エラー
        "random_garbage!",      # 構文エラー
        "",                     # 構文エラー
    ]

    # zoneinfoが利用可能かどうかのメッセージ
    if ZONEINFO_AVAILABLE:
        print("zoneinfo module is available. Named timezones (e.g., Area/City) will be parsed.")
    else:
        print("zoneinfo module is NOT available (requires Python 3.9+). Named timezones will result in an error.")
        print("Consider installing 'tzdata' backport (`pip install tzdata`) or using 'pytz' for older Python versions if named timezones are needed.")
    
    print("\n--- Parsing Joda-Time like timezone strings to Python timezone objects ---")
    for tz_string in test_strings:
        tz_obj, errors = parse_timezone(tz_string)
        print(f"\nInput: '{tz_string}'")
        if errors:
            print(f"  Error(s):")
            for err in errors:
                print(f"    - {err}")
            if tz_obj is not None: # エラーがあってもオブジェクトが返る場合（現在は設計上ないが）
                 print(f"  Parsed Object (despite errors): {tz_obj}")
        elif tz_obj is not None:
            print(f"  Parsed Object: {tz_obj}")
            # タイムゾーンオブジェクトを使って現在時刻を表示 (例)
            try:
                now_in_tz = datetime.now(tz_obj)
                # %Z%z は zoneinfo や一部の timezone オブジェクトで有用
                print(f"  Current time in this TZ: {now_in_tz.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
            except Exception as e:
                print(f"  Could not get current time with this TZ object: {e}")
        else:
            # このケースは通常、エラーメッセージがあるはず
            print(f"  Failed to parse and no specific errors returned (unexpected).")