from typing import Optional, Any
from .base import CelValue
from .cel_types import CEL_ERROR, CelType # CEL_ERROR は cel_types.py で定義


class CelErrorValue(CelValue):
    def __init__(self, message: str):
        self.message = message
        # error_code や原因となった例外を保持することも可能

    @property
    def cel_type(self) -> CelType:
        return CEL_ERROR # error型を表すCelTypeインスタンス

    def __eq__(self, other: Any) -> bool:
        # エラー同士の比較は通常 false (エラーは状態であり、値として等価ではない)
        return False

    def __lt__(self, other: Any) -> bool:
        raise TypeError(f"Operator '<' not supported on error type")

    def __hash__(self):
        raise TypeError(f"Error value of type {self.cel_type.name} is not hashable")

    def __repr__(self):
        return f"CelErrorValue<{self.message}>"