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

    if visitor_errors:
        return (tz_object, visitor_errors)

    return tz_object, None