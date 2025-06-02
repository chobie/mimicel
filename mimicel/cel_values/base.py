from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .cel_types import CelType

from mimicel.cel_values.constants import TIMESTAMP_MAX_DATETIME, TIMESTAMP_MIN_DATETIME, UINT64_MAX, INT64_MIN, \
    INT64_MAX


class CelValue(ABC):
    @abstractmethod
    def __eq__(self, other: Any) -> bool: pass

    def __ne__(self, other: Any) -> bool: return not self.__eq__(other)

    @abstractmethod

    def __lt__(self, other: Any) -> bool: pass

    def __le__(self, other: Any) -> bool:
        from .primitives import CelDouble
        # NaN safe: a <= b is (a < b) or (a == b)
        # If either is NaN, both < and == should be false.
        if isinstance(self, CelDouble) and self.value != self.value: return False # self is NaN
        if isinstance(other, CelDouble) and other.value != other.value: return False # other is NaN
        try:
            return self.__lt__(other) or self.__eq__(other)
        except TypeError: # If comparison not supported (e.g. different non-numeric types)
            raise

    def __gt__(self, other: Any) -> bool:
        from .primitives import CelDouble

        if isinstance(self, CelDouble) and self.value != self.value: return False
        if isinstance(other, CelDouble) and other.value != other.value: return False
        try:
            # a > b is !(a <= b)
            return not self.__le__(other)
        except TypeError:
            raise

    def __ge__(self, other: Any) -> bool:
        from .primitives import CelDouble

        if isinstance(self, CelDouble) and self.value != self.value: return False
        if isinstance(other, CelDouble) and other.value != other.value: return False
        try:
            # a >= b is !(a < b)
            return not self.__lt__(other)
        except TypeError:
            raise
    @property
    @abstractmethod
    def cel_type(self) -> 'CelType': pass

    def __add__(self, other: Any) -> 'CelValue':
        raise TypeError(
            f"Operator '+' not supported between {self.cel_type.name} and {type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name}")

    def __sub__(self, other: Any) -> 'CelValue':
        raise TypeError(
            f"Operator '-' not supported between {self.cel_type.name} and {type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name}")

    def __mul__(self, other: Any) -> 'CelValue':
        raise TypeError(
            f"Operator '*' not supported between {self.cel_type.name} and {type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name}")

    def __truediv__(self, other: Any) -> 'CelValue':
        raise TypeError(
            f"Operator '/' not supported between {self.cel_type.name} and {type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name}")

    def __mod__(self, other: Any) -> 'CelValue':
        raise TypeError(
            f"found no matching overload for '_%_' applied to '({self.cel_type.name}, {type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name})': no_such_overload")

    def __neg__(self) -> 'CelValue':
        raise TypeError(f"Operator unary '-' not supported for {self.cel_type.name}")



def _check_duration_operation_result(ts: datetime, op_desc: str) -> datetime:
    """Durationとの演算結果のTimestampが範囲内かチェックする"""
    # この関数はTimestampとDurationの演算結果のTimestampに対して使う
    return _check_timestamp_range(ts, op_desc)


def _check_timestamp_range(value: datetime, operation: str = "Timestamp operation") -> datetime:
    """CEL Timestampの範囲内かチェックし、範囲外ならValueErrorを送出"""
    # 比較のためにaware datetimeに正規化 (入力がnaiveならUTCとみなす)
    aware_value = value
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:  # naive
        aware_value = value.replace(tzinfo=timezone.utc)

    # タイムゾーンをUTCに変換して比較
    utc_value = aware_value.astimezone(timezone.utc)

    if not (TIMESTAMP_MIN_DATETIME <= utc_value <= TIMESTAMP_MAX_DATETIME):
        raise ValueError(f"{operation} resulted in out of range timestamp: {value.isoformat()}")
    return value  # 元のタイムゾーン情報を保持したまま返す（ただし内部ではUTC換算でチェック）


def _check_uint64_range(value: int, operation: str = "Unsigned integer operation") -> int:
    """uint64の範囲内かチェックし、範囲外ならValueErrorを送出"""
    if not (0 <= value <= UINT64_MAX):
        raise ValueError("return error for overflow")
        #raise ValueError(f"{operation} resulted in overflow: {value} is out of uint64 range (0 to {UINT64_MAX}).")
    return value


def _check_int64_range(value: int, operation: str = "Integer operation") -> int:
    """int64の範囲内かチェックし、範囲外ならValueErrorを送出"""
    if not (INT64_MIN <= value <= INT64_MAX):
        raise ValueError('return error for overflow')
        #raise ValueError(
        #    f"{operation} resulted in overflow/underflow: {value} is out of int64 range ({INT64_MIN} to {INT64_MAX}).")
    return value
