# parse_duration 関数の定義場所 (例: mimicel/duration.py)
from datetime import timedelta
from typing import Union  # 必要であれば

from antlr4 import InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener
from google.protobuf.duration_pb2 import Duration

# 生成されたLexer, Parser, Visitorをインポート
from mimicel.duration.CelDurationLexer import CelDurationLexer
from mimicel.duration.CelDurationParser import CelDurationParser
from mimicel.duration.duration_visitor import DurationVisitor  # 上記で定義したVisitor


class ThrowingErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line: int, column: int, msg: str, e):
        # ANTLRのエラーメッセージをそのまま使うか、ここでカスタムメッセージに変換する
        # 例: "Syntax error at 1:2 - token recognition error at: '.'"
        raise ValueError(f"Syntax error in duration string at {line}:{column} - {msg}")



def parse_duration(input_text: str) -> Duration: # 返り値を PbDuration に変更
    if not isinstance(input_text, str):
        raise TypeError("Input to parse_duration must be a string.")

    trimmed_input = input_text.strip()
    if not trimmed_input:
        raise ValueError("Duration string cannot be empty or just whitespace.")

    input_stream = InputStream(trimmed_input)
    lexer = CelDurationLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CelDurationParser(stream)

    # エラーリスナーの設定 (既存のものを想定)
    # parser.removeErrorListeners()
    # lexer.removeErrorListeners()
    # error_listener = ThrowingErrorListener()
    # parser.addErrorListener(error_listener)
    # lexer.addErrorListener(error_listener)

    try:
        tree = parser.parse()
    except Exception as ve_antlr: # ANTLR 자체에서 발생하는 오류 (RuntimeRecognitionError 등)
        raise ValueError(f"Invalid duration string format: '{input_text}'. ANTLR Details: {ve_antlr}") from ve_antlr

    visitor = DurationVisitor() # 修正された DurationVisitor を使用

    try:
        result_pb_duration = visitor.visit(tree) # visitor が PbDuration を返す
    except ValueError as ve_visitor: # Visitor内での独自バリデーションエラー
        raise ValueError(f"Invalid duration string content: '{input_text}'. Details: {ve_visitor}") from ve_visitor
    except Exception as e_generic_visitor:
        raise RuntimeError(
            f"Unexpected error visiting duration parse tree for '{input_text}': {e_generic_visitor}") from e_generic_visitor

    # isinstance チェックは PbDuration に対して行う
    if not isinstance(result_pb_duration, Duration):
        raise TypeError(f"Internal parser error: parsing duration did not result in PbDuration. Got {type(result_pb_duration)}")

    return result_pb_duration