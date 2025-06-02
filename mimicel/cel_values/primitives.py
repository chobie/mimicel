import math
import traceback
from typing import Optional, Any

from .cel_types import CelType, CEL_NULL, CEL_BOOL, CEL_BYTES, CEL_STRING, CEL_DOUBLE, CEL_UINT, CEL_INT
from mimicel.cel_values import CelValue
from mimicel.cel_values.constants import INT64_MIN, INT64_MAX
from mimicel.cel_values.base import _check_uint64_range, _check_int64_range
from .errors import CelErrorValue


class CelNull(CelValue):  # (変更なし)
    _instance: Optional['CelNull'] = None

    def __new__(cls):
        if cls._instance is None: cls._instance = super(CelNull, cls).__new__(cls)
        return cls._instance

    @property
    def value(self): return None

    def __hash__(self): return hash(None)

    @property
    def cel_type(self) -> CelType: return CEL_NULL

    def __eq__(self, other: Any) -> bool: return isinstance(other, CelNull)

    def __lt__(self, other: Any) -> bool:
        # null is not comparable with <, <=, >, >= with any type, including itself
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        raise TypeError(f"Operator '<' not supported between {self.cel_type.name} and {other_type_name}")

    def __repr__(self): return "CelNull()"


class CelBool(CelValue):  # (変更なし)
    def __init__(self, value: bool): self.value: bool = value

    def __hash__(self): return hash(self.value)

    @property
    def cel_type(self) -> CelType: return CEL_BOOL

    def __eq__(self, other: Any) -> bool: return isinstance(other, CelBool) and self.value == other.value

    def __lt__(self, other: Any) -> bool: # false < true
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        if not isinstance(other, CelBool):
            raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {other_type_name}")
        return self.value < other.value # Python bools (False < True)

    def __invert__(self) -> 'CelBool': return CelBool(not self.value)  # For logical NOT _!_

    def __repr__(self): return f"CelBool({self.value})"


class CelBytes(CelValue):  # (変更なし)
    def __init__(self, value: bytes):
        self.value: bytes = value

    def __hash__(self):
        return hash(self.value)

    @property
    def cel_type(self) -> CelType:
        return CEL_BYTES

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CelBytes) and self.value == other.value

    def __lt__(self, other: Any) -> bool:
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        if not isinstance(other, CelBytes):
            raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {other_type_name}")
        return self.value < other.value

    def __add__(self, other: Any) -> 'CelBytes':
        if isinstance(other, CelBytes): return CelBytes(self.value + other.value)
        return super().__add__(other)

    def __repr__(self):
        return f"CelBytes({self.value!r})"

    def __len__(self):
        return len(self.value)  # For size()


class CelString(CelValue):  # (変更なし)
    def __init__(self, value: str):
        self.value: str = value

    def __hash__(self):
        return hash(self.value)

    @property
    def cel_type(self) -> CelType:
        return CEL_STRING

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CelString) and self.value == other.value

    def __lt__(self, other: Any) -> bool:
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        if not isinstance(other, CelString):
            raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {other_type_name}")
        return self.value < other.value

    def __add__(self, other: Any) -> 'CelString':
        if isinstance(other, CelString): return CelString(self.value + other.value)
        return super().__add__(other)

    def __repr__(self):
        return f"CelString({self.value!r})"

    def __len__(self):
        return len(self.value)  # For size()


class CelDouble(CelValue):  # (変更なしのため主要部分のみ)
    def __init__(self, value: float):
        self.value: float = value

    def __hash__(self):
        return hash(self.value)  # NaNのハッシュは実装依存だがPythonでは同じ

    @property
    def cel_type(self) -> CelType:
        return CEL_DOUBLE

    def __eq__(self, other: Any) -> bool:
        # CEL Spec: NaN == NaN is false
        if self.value != self.value:  # self is NaN
            return False
        if isinstance(other, CelDouble):
            if other.value != other.value:  # other is NaN
                return False
            return self.value == other.value
        if isinstance(other, (CelInt, CelUInt)):
            return self.value == float(other.value)
        return False

    def __ne__(self, other: Any) -> bool:
        # CEL Spec: NaN != NaN is true
        if self.value != self.value or (
                isinstance(other, CelDouble) and other.value != other.value):  # one or both are NaN
            return True
        return not self.__eq__(other)

    def __lt__(self, other: Any) -> bool:
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        if self.value != self.value: return False # self is NaN
        if isinstance(other, CelDouble):
            if other.value != other.value: return False # other is NaN
            return self.value < other.value
        if isinstance(other, (CelInt, CelUInt)):
             # other is not NaN since it's int/uint
            return self.value < float(other.value)
        raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {other_type_name}")

    # __add__などの算術演算子は float の標準的な挙動 (inf, -inf, NaN がありうる)
    # CELのdouble演算でオーバーフローエラーが規定されているかは要確認。通常はIEEE754に従いinfになる。
    # ここではPythonのfloatの挙動に任せる。
    def __add__(self, other: Any) -> 'CelDouble':
        if isinstance(other, CelDouble): return CelDouble(self.value + other.value)
        if isinstance(other, (CelInt, CelUInt)): return CelDouble(self.value + float(other.value))
        return super().__add__(other)

    def __sub__(self, other: Any) -> 'CelDouble':
        if isinstance(other, CelDouble): return CelDouble(self.value - other.value)
        if isinstance(other, (CelInt, CelUInt)): return CelDouble(self.value - float(other.value))
        return super().__sub__(other)

    def __mul__(self, other: Any) -> 'CelDouble':
        if isinstance(other, CelDouble): return CelDouble(self.value * other.value)
        if isinstance(other, (CelInt, CelUInt)): return CelDouble(self.value * float(other.value))
        return super().__mul__(other)

    def __truediv__(self, other: Any) -> 'CelDouble':
        # まず相手の型を調べてfloat値を取得
        other_float_val: float
        if isinstance(other, CelDouble):
            other_float_val = other.value
        elif isinstance(other, (CelInt, CelUInt)):
            other_float_val = float(other.value)
        else:
            # サポート外の型との除算は基底クラスのメソッドに任せる (通常TypeErrorを送出)
            return super().__truediv__(other)

        # self.value (被除数) と other_float_val (除数) を用いて除算
        # 除数がゼロの場合の特別な処理
        if other_float_val == 0.0:
            if self.value == 0.0:
                # 0.0 / 0.0 -> NaN
                return CelDouble(float('nan'))
            elif self.value > 0.0:
                # 正の数 / 0.0 -> +Infinity
                return CelDouble(float('inf'))
            elif self.value < 0.0:
                # 負の数 / 0.0 -> -Infinity
                return CelDouble(float('-inf'))
            else:  # self.value is NaN
                # NaN / 0.0 -> NaN (Pythonの通常のfloat除算で処理される)
                # このケースは下の通常の除算パスでカバーされるが、明示しても良い
                return CelDouble(float('nan'))

        # 除数がゼロでない場合、または被除数か除数がNaN/Infinityの場合
        # Pythonのfloat除算はIEEE 754のルールに従う
        # (例: NaN / X -> NaN, X / NaN -> NaN, Inf / X -> Inf, X / Inf -> 0.0, Inf / Inf -> NaN)
        return CelDouble(self.value / other_float_val)

    def __neg__(self) -> 'CelDouble':
        return CelDouble(-self.value)

    def __repr__(self):
        return f"CelDouble({self.value})"


class CelUInt(CelValue):
    def __init__(self, value: int, enum_type_name: Optional[str] = None):  # ★ enum_type_name を追加
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"CelUInt value must be a non-negative integer, got {value}")
        self.value: int = _check_uint64_range(value, "CelUInt initialization")
        self._enum_type_name: Optional[str] = enum_type_name  # ★ 保持

    def __hash__(self):
        return hash(self.value)

    @property
    def cel_type(self) -> CelType:
        if self._enum_type_name:
            resolved_enum_type = CelType.get_by_name(self._enum_type_name)
            if resolved_enum_type:
                return resolved_enum_type
        return CEL_UINT

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, CelUInt): return self.value == other.value
        if isinstance(other, CelInt): return other.value >= 0 and self.value == other.value
        if isinstance(other, CelDouble):
            return not (other.value != other.value) and float(self.value) == other.value
        return False

    def __lt__(self, other: Any) -> bool:
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        if isinstance(other, CelUInt): return self.value < other.value
        # Corrected logic for uint < int
        if isinstance(other, CelInt): return other.value > 0 and self.value < other.value
        if isinstance(other, CelDouble):
            if other.value != other.value: return False  # other is NaN
            return float(self.value) < other.value
        raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {other_type_name}")

    def __add__(self, other: Any) -> 'CelUInt':
        if isinstance(other, CelUInt):
            return CelUInt(_check_uint64_range(self.value + other.value, "Addition"))
        return super().__add__(other)

    def __sub__(self, other: Any) -> 'CelUInt':
        if isinstance(other, CelUInt):
            # 結果が負になる場合はuintの範囲外 (CELの仕様ではuint - uint -> uint)
            # uintの減算で結果が負になる場合はエラーとすべき (仕様確認要だが、通常そう)
            # あるいは、型チェッカーがこれを検出するか、uint(abs(res))のような形になるか。
            # ここでは結果が非負であることを期待。
            res = self.value - other.value
            if res < 0:
                raise ValueError("return error for overflow")
                #raise ValueError(f"Subtraction resulted in a negative value for uint: {res}")
            return CelUInt(_check_uint64_range(res, "Subtraction"))
        return super().__sub__(other)

    def __mul__(self, other: Any) -> 'CelUInt':
        if isinstance(other, CelUInt):
            res = self.value * other.value
            return CelUInt(_check_uint64_range(res, "Multiplication"))
        return super().__mul__(other)

    def __truediv__(self, other: Any) -> 'CelUInt':
        if isinstance(other, CelUInt):
            if other.value == 0:
                raise ValueError("divide by zero")
            return CelUInt(self.value // other.value)  # 結果は非負
        return super().__truediv__(other)

    def __mod__(self, other: Any) -> 'CelUInt':
        if isinstance(other, CelUInt):
            if other.value == 0:
                raise ValueError("modulus by zero")
            return CelUInt(self.value % other.value)
        return super().__mod__(other)

    def __neg__(self) -> 'CelInt':  # -uint は int になる (CELの型規則による)
        # uintをintに変換してマイナス。0は0。正のuintは負のintになる。
        # 結果がint64の範囲内である必要がある。
        # -(0u) -> 0
        # -(1u) -> -1
        # -(UINT64_MAX) は INT64_MIN より小さいのでエラー
        if self.value > INT64_MAX:  # 正確には -(2^63) はINT64_MINだが、それより大きいuintの負号は範囲外
            if self.value > abs(INT64_MIN):  # 例: -(2^63)u は -9223372036854775808 になるのでOK
                if ((-1) * self.value) < INT64_MIN:
                    raise ValueError(f"Negation of uint {self.value} overflows int64.")
        return CelInt(_check_int64_range(-self.value, "Negation of uint"))

    def __repr__(self):
        return f"CelUInt({self.value})"


class CelInt(CelValue):
    def __init__(self, value: int, enum_type_name: Optional[str] = None): # ★ enum_type_name を追加
        self.value: int = _check_int64_range(value, "CelInt initialization")
        self._enum_type_name: Optional[str] = enum_type_name # ★ 保持

    def __hash__(self):
        return hash(self.value)

    @property
    def cel_type(self) -> CelType:
        # ★★★ もし_enum_type_nameがあれば、それに対応するCelTypeを返す ★★★
        if self._enum_type_name:
            # CelType.get_by_name は、TypeRegistry.register_enum_type で
            # Enum型名がCelTypeとして登録されていることを期待する
            resolved_enum_type = CelType.get_by_name(self._enum_type_name)
            if resolved_enum_type:
                return resolved_enum_type
            # else:
                # フォールバックとして int を返すか、エラーを出すか。
                # print(f"Warning: Enum type '{self._enum_type_name}' not found in CelType registry for CelInt. Falling back to INT.")
        return CEL_INT

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, CelInt): return self.value == other.value
        if isinstance(other, CelUInt): return self.value >= 0 and self.value == other.value
        if isinstance(other, CelDouble):
            # CELでは数値は数直線上にあるものとして比較される。NaNとの比較は常にfalse。
            return not (other.value != other.value) and float(self.value) == other.value
        return False

    def __lt__(self, other: Any) -> bool:
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        if isinstance(other, CelInt): return self.value < other.value
        if isinstance(other, CelUInt): return self.value < 0 or self.value < other.value # Corrected logic for int < uint
        if isinstance(other, CelDouble):
            if other.value != other.value: return False # other is NaN
            return float(self.value) < other.value
        raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {other_type_name}")

    def __add__(self, other: Any) -> 'CelInt':
        from .well_known_types import CelProtobufInt32Value
        from .well_known_types import CelProtobufValue

        if isinstance(other, CelInt) or isinstance(other, CelProtobufInt32Value):
            return CelInt(_check_int64_range(self.value + other.value, "Addition"))

        # CelUIntとの加算は、型チェッカーレベルで禁止されるか、
        # 事前にint(uint_val)やuint(int_val)のように明示的な型変換が行われる想定。
        # ここでは、厳密にCelInt同士の演算のみを定義。
        return super().__add__(other)

    def __sub__(self, other: Any) -> 'CelInt':
        from .well_known_types import CelProtobufInt32Value
        if isinstance(other, CelInt) or isinstance(other, CelProtobufInt32Value):
            return CelInt(_check_int64_range(self.value - other.value, "Subtraction"))

        return super().__sub__(other)

    def __mul__(self, other: Any) -> 'CelInt':
        from .well_known_types import CelProtobufInt32Value
        if isinstance(other, CelInt) or isinstance(other, CelProtobufInt32Value):
            # Pythonのint同士の乗算はオーバーフローしないが、CELのint64の範囲に収める
            res = self.value * other.value
            return CelInt(_check_int64_range(res, "Multiplication"))

        return super().__mul__(other)

    def __truediv__(self, other: Any) -> CelValue: # 返り値型を CelValue に
        other_val: Any # 比較または演算に使用する値
        is_other_double_nature = False

        from .well_known_types import (CelProtobufInt32Value,
                                       CelProtobufInt64Value,
                                       CelProtobufUInt32Value,
                                       CelProtobufUInt64Value,
                                       CelProtobufDoubleValue,
                                       CelProtobufFloatValue)

        if isinstance(other, CelInt):
            other_val = other.value
        elif isinstance(other, CelDouble):
            other_val = other.value
            is_other_double_nature = True
        # ★★★ WKT数値ラッパー型の処理を追加 ★★★
        elif isinstance(other, (CelProtobufInt32Value, CelProtobufInt64Value,
                                CelProtobufUInt32Value, CelProtobufUInt64Value)):
            if other.value is None: # ラッパーがnull状態の場合
                raise TypeError(f"Cannot perform division with null wrapped value from {other.cel_type.name}")
            other_val = other.value # ラップされた数値 (int)
        elif isinstance(other, (CelProtobufDoubleValue, CelProtobufFloatValue)):
            if other.value is None:
                raise TypeError(f"Cannot perform division with null wrapped value from {other.cel_type.name}")
            other_val = other.value # ラップされた数値 (float)
            is_other_double_nature = True
        else:
            other_type_name = getattr(getattr(other, 'cel_type', None), 'name', type(other).__name__)
            raise TypeError(f"Operator '/' not supported between {self.cel_type.name} and {other_type_name}")

        # 実際の除算処理
        if is_other_double_nature or isinstance(other_val, float): # 相手がdouble naturezaを持つ場合
            if other_val == 0.0:
                if self.value == 0.0: return CelDouble(float('nan'))
                return CelDouble(float('inf') if self.value > 0 else float('-inf'))
            return CelDouble(float(self.value) / float(other_val))
        else: # 相手が整数 natureza を持つ場合 (other_val は int のはず)
            other_int_val = int(other_val) # floatからキャストされるケースも考慮
            if other_int_val == 0:
                return CelErrorValue("division by zero / divide by zero")
            return CelInt(self.value // other_int_val)

    def __mod__(self, other: Any) -> 'CelInt':
        other_val: Optional[int] = None
        other_cel_type = getattr(other, 'cel_type', None)

        if isinstance(other, CelInt) or (
                other_cel_type and other_cel_type.name in [CEL_INT.name, "google.protobuf.Int32Value",
                                                           "google.protobuf.Int64Value"]):
            other_val = other.value
        elif isinstance(other, CelUInt) or (
                other_cel_type and other_cel_type.name in [CEL_UINT.name, "google.protobuf.UInt32Value",
                                                           "google.protobuf.UInt64Value"]):
            # uint も整数として扱う
            other_val = other.value
        else:
            other_type_name = getattr(other_cel_type, 'name', type(other).__name__)
            raise TypeError(f"Operator '%' not supported between {self.cel_type.name} and {other_type_name}")

        if other_val is None and other_cel_type is not None and "Wrapper" in other_cel_type.name:
            raise TypeError(f"Cannot perform modulo with null wrapped value from {other_cel_type.name}")

        if other_val == 0:
            raise ValueError("modulus by zero")  # CEL spec: error

        # CELの剰余演算: result = dividend - truncate(dividend / divisor) * divisor
        # 結果の符号は被除数 (self.value) と同じ
        if self.value == 0:  # 0 % x = 0
            return CelInt(0)
        if other_val == 0:  # 上で処理済みだが念のため
            raise ValueError("modulus by zero")

        # math.trunc(x / y) を使う
        # 例: 43 % (-5) -> 43 - trunc(43 / -5) * (-5) = 43 - trunc(-8.6) * (-5) = 43 - (-8 * -5) = 43 - 40 = 3
        # 例: -43 % 5  -> -43 - trunc(-43 / 5) * 5  = -43 - trunc(-8.6) * 5  = -43 - (-8 * 5)  = -43 - (-40) = -3
        # 例: -43 % -5 -> -43 - trunc(-43 / -5) * (-5) = -43 - trunc(8.6) * (-5) = -43 - (8 * -5) = -43 - (-40) = -3

        # 整数除算の結果 (0方向への切り捨て)
        # Pythonの // は床除算なので、math.trunc を使う
        quotient = math.trunc(self.value / other_val)
        result = self.value - (quotient * other_val)

        return CelInt(result)

    def __neg__(self) -> 'CelInt':
        if self.value == INT64_MIN:  # -(-2^63) は 2^63 となり、int64の最大値(2^63-1)を超える
            raise ValueError("return error for overflow")
            #raise ValueError(f"Negation of {self.value} overflows int64.")
        return CelInt(-self.value)

    def __repr__(self):
        return f"CelInt({self.value})"


