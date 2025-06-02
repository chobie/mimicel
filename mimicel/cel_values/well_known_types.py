import math
import traceback
from datetime import timedelta, datetime, timezone
from typing import Optional, Any, Callable, List, Iterable, Iterator, Tuple

from google.protobuf import descriptor_pool, message_factory
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message, DecodeError
from google.protobuf.wrappers_pb2 import Int32Value as PbInt32Value, FloatValue
from google.protobuf.wrappers_pb2 import UInt32Value as PbUInt32Value
from google.protobuf.wrappers_pb2 import Int64Value as PbInt64Value
from google.protobuf.wrappers_pb2 import UInt64Value as PbUInt64Value
from google.protobuf.wrappers_pb2 import DoubleValue as PbDoubleValue
from google.protobuf.wrappers_pb2 import BoolValue as PbBoolValue
from google.protobuf.wrappers_pb2 import StringValue as PbStringValue
from google.protobuf.wrappers_pb2 import BytesValue as PbBytesValue
from google.protobuf.struct_pb2 import NullValue as PbNullValue, Value
from google.protobuf.struct_pb2 import ListValue as PbListValue
from google.protobuf.struct_pb2 import Value as PbValue
from google.protobuf.struct_pb2 import Struct as PbStruct
from google.protobuf.duration_pb2 import Duration as PbDuration
from google.protobuf.timestamp_pb2 import Timestamp as PbTimestamp
from google.protobuf.any_pb2 import Any as PbAny

from mimicel.cel_checker import TYPE_STRUCT_AS_MAP, TYPE_PROTO_LIST_AS_LIST
from .cel_types import CelType, CEL_INT32_WRAPPER, CEL_DURATION, CEL_TIMESTAMP, CEL_INT64_WRAPPER, \
    CEL_UINT32_WRAPPER, CEL_UINT64_WRAPPER, CEL_BOOL_WRAPPER, CEL_DOUBLE_WRAPPER, CEL_STRING_WRAPPER, CEL_BYTES_WRAPPER, \
    CEL_NULL_WRAPPER, CEL_VALUE_WRAPPER, CEL_STRUCT_WRAPPER, make_map_type, CEL_STRING, CEL_DYN, CEL_FLOAT_WRAPPER, \
    CEL_ANY, CelDynValue
from mimicel.cel_values import CelValue, CelNull, CelInt, CelDouble, CelUInt, CelBool, CelString, CelBytes, CelList, \
    CelMap
from mimicel.cel_values.base import _check_timestamp_range, _check_int64_range, _check_duration_operation_result

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    class ZoneInfoNotFoundError(Exception): pass # type: ignore
    class ZoneInfo: # type: ignore
        def __init__(self, key: str):
            if key is None or key.upper() != "UTC":
                raise ZoneInfoNotFoundError(f"Timezone '{key}' not found (zoneinfo module not available or key unsupported by mock).")
            self._offset = timedelta(0)
            self._name = "UTC"
        def utcoffset(self, dt: Optional[datetime]) -> Optional[timedelta]: return self._offset
        def tzname(self, dt: Optional[datetime]) -> Optional[str]: return self._name
        def dst(self, dt: Optional[datetime]) -> Optional[timedelta]: return None


class CelProtobufValue(CelValue):
    _pb_value: PbValue

    def __init__(self, pb_value_instance: PbValue):
        if not isinstance(pb_value_instance, PbValue):
            raise TypeError(
                f"CelProtobufValue expects a google.protobuf.Value instance, "
                f"got {type(pb_value_instance)}"
            )
        self._pb_value = pb_value_instance

    @classmethod
    def from_native(cls, native_value: any) -> 'CelProtobufValue':
        pb_val = PbValue()
        if native_value is None:
            pb_val.null_value = PbNullValue.NULL_VALUE
        elif isinstance(native_value, bool):
            pb_val.bool_value = native_value
        elif isinstance(native_value, (int, float)):
            pb_val.number_value = float(native_value)
        elif isinstance(native_value, str):
            pb_val.string_value = native_value
        elif isinstance(native_value, list):  # ★ list から ListValue への変換
            list_val = PbListValue()
            for item in native_value:
                # 各要素も再帰的にValueに変換する必要がある
                # ここでは CelProtobufValue.from_native を再帰的に呼び出すか、
                # PbValue を直接構築するヘルパーが必要。
                # 簡単のため、Valueコンストラクタに直接設定できる型のみを要素として許容する。
                # (より堅牢な実装では、ネストしたdict/listもPbValueに変換する)
                item_pb_value = Value()  # 新しいValueメッセージ
                if item is None:
                    item_pb_value.null_value = PbNullValue.NULL_VALUE
                elif isinstance(item, bool):
                    item_pb_value.bool_value = item
                elif isinstance(item, (int, float)):
                    item_pb_value.number_value = float(item)
                elif isinstance(item, str):
                    item_pb_value.string_value = item
                # ネストしたlist/dictは、このfrom_nativeのスコープでは未サポートとするか、再帰呼び出し
                else:
                    # このレベルのfrom_nativeでは複雑なネストは扱わない方針もアリ
                    raise TypeError(f"Unsupported item type in list for Value conversion: {type(item)}")
                list_val.values.append(item_pb_value)
            pb_val.list_value.CopyFrom(list_val)
        elif isinstance(native_value, dict):  # ★ dict から Struct への変換
            struct_val = PbStruct()
            for k, v_item in native_value.items():
                if not isinstance(k, str):
                    raise TypeError("bad key type: Struct keys must be strings for Value conversion.")
                # 値も再帰的にValueに変換
                item_pb_value = Value()
                if v_item is None:
                    item_pb_value.null_value = PbNullValue.NULL_VALUE
                elif isinstance(v_item, bool):
                    item_pb_value.bool_value = v_item
                elif isinstance(v_item, (int, float)):
                    item_pb_value.number_value = float(v_item)
                elif isinstance(v_item, str):
                    item_pb_value.string_value = v_item
                else:
                    raise TypeError(f"Unsupported value type in dict for Value conversion: {type(v_item)}")
                struct_val.fields[k].CopyFrom(item_pb_value)
            pb_val.struct_value.CopyFrom(struct_val)
        else:
            raise TypeError(f"Unsupported native type for Value conversion: {type(native_value)}")
        return cls(pb_val)

    @property
    def cel_type(self) -> CelType:
        return CEL_VALUE_WRAPPER  # "google.protobuf.Value" 型

    def get_kind(self) -> str | None:
        return self._pb_value.WhichOneof('kind')

    def _dynamic_convert(self) -> CelValue:
        """
        内包する値の型に応じて、対応するCELの値インスタンスに変換します。
        struct_value -> CelProtobufStruct
        list_value -> CelProtobufListValue
        """
        kind = self.get_kind()

        if kind == "null_value":
            return CelNull()
        elif kind == "number_value":
            return CelDouble(self._pb_value.number_value)
        elif kind == "string_value":
            return CelString(self._pb_value.string_value)
        elif kind == "bool_value":
            return CelBool(self._pb_value.bool_value)
        elif kind == "struct_value":
            # PbStruct を CelProtobufStruct でラップして返す
            return CelProtobufStruct(self._pb_value.struct_value)
        elif kind == "list_value":
            # PbListValue を CelProtobufListValue でラップして返す
            return CelProtobufListValue(self._pb_value.list_value)
        elif kind is None:
            return CelNull()
        else:
            raise TypeError(f"Unknown or unsupported Value kind for dynamic conversion: {kind}")

    @property
    def value(self) -> Any:
        """
        内包する値をPythonネイティブ型で返します。
        StructValue -> Python dict (再帰的にアンラップ)
        ListValue -> Python list (再帰的にアンラップ)
        """
        kind = self.get_kind()
        if kind == "null_value" or kind is None:
            return None
        elif kind == "number_value":
            return self._pb_value.number_value
        elif kind == "string_value":
            return self._pb_value.string_value
        elif kind == "bool_value":
            return self._pb_value.bool_value
        elif kind == "struct_value":
            # PbStruct を Python dict に変換 (要素も再帰的にアンラップ)
            # ここで unwrap_value を使うと循環参照になるため、専用のヘルパーか手動で実装
            py_dict = {}
            for k, v_pb_val in self._pb_value.struct_value.fields.items():
                # 各PbValueをCelProtobufValueでラップし、その.valueを呼ぶか、
                # 直接PbValueの中身に応じてPythonネイティブ型に変換する。
                # ここではCelProtobufValue(v_pb_val).valueを使うのが一貫性がある。
                py_dict[k] = CelProtobufValue(v_pb_val).value  # 再帰的に .value を呼び出す
            return py_dict
        elif kind == "list_value":
            # PbListValue を Python list に変換 (要素も再帰的にアンラップ)
            py_list = []
            for v_pb_val in self._pb_value.list_value.values:
                py_list.append(CelProtobufValue(v_pb_val).value)  # 再帰的に .value を呼び出す
            return py_list
        else:
            raise TypeError(f"Unknown or unsupported Value kind for Python native unwrapping: {kind}")

    def __eq__(self, other: Any) -> bool:
        # 比較は _dynamic_convert() 後の具体的なCEL型で行うのが基本方針
        try:
            self_converted = self._dynamic_convert()
        except NotImplementedError:  # まだ Struct/List の変換が未実装の場合
            # この段階では NotImplementedError は発生しないはず (上記で対応済みのため)
            # 万が一発生した場合は、比較不能として False を返すかエラー
            return False

        if isinstance(other, CelProtobufValue):
            try:
                other_converted = other._dynamic_convert()
                return self_converted == other_converted
            except NotImplementedError:
                return False
        # other が既に具体的なCEL型である場合
        elif isinstance(other,
                        (CelNull, CelBool, CelDouble, CelString, CelProtobufStruct, CelProtobufListValue, CelList,
                         CelMap)):
            return self_converted == other

        return False

    def __lt__(self, other: Any) -> bool:
        # 大小比較も同様に、具体的な型に変換してから行う
        try:
            self_converted = self._dynamic_convert()
            if isinstance(other, CelProtobufValue):
                other_converted = other._dynamic_convert()
                return self_converted < other_converted
            else:
                return self_converted < other  # 相手が既に具体的な型であると期待
        except NotImplementedError:
            raise TypeError(
                f"Ordering not supported for Value containing struct/list (conversion not fully implemented).")
        except TypeError as e:
            other_type_name = type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name
            self_type_name_for_error = self_converted.cel_type.name if hasattr(self_converted, 'cel_type') else type(
                self_converted).__name__
            raise TypeError(f"Cannot compare {self_type_name_for_error} with {other_type_name}: {e}")

    def __hash__(self):
        # ハッシュも _dynamic_convert() 後の型に委ねる
        try:
            return hash(self._dynamic_convert())
        except NotImplementedError:
            raise TypeError(
                f"Object of type {self.cel_type.name} (containing struct/list) is not hashable (conversion not fully implemented).")
        except TypeError:  # 変換後の型がハッシュ化不能な場合 (例: CelProtobufStruct, CelProtobufListValue)
            raise TypeError(f"Value containing unhashable type (e.g., struct or list) is not hashable.")

    def __repr__(self) -> str:
        # ... (前回提示の __repr__ 実装、必要に応じて struct_value や list_value の簡易表示を追加) ...
        kind = self.get_kind()
        val_repr = "unspecified_kind"
        if kind == "null_value" or kind is None:
            val_repr = "null_value"
        elif kind == "number_value":
            val_repr = f"number_value: {self._pb_value.number_value}"
        elif kind == "string_value":
            val_repr = f"string_value: {self._pb_value.string_value!r}"
        elif kind == "bool_value":
            val_repr = f"bool_value: {str(self._pb_value.bool_value).lower()}"
        elif kind == "struct_value":
            val_repr = f"struct_value: (fields: {len(self._pb_value.struct_value.fields)})"
        elif kind == "list_value":
            val_repr = f"list_value: (elements: {len(self._pb_value.list_value.values)})"
        else:
            val_repr = f"unknown_kind: {self._pb_value}"
        return f"CelProtobufValue({val_repr})"



class CelProtobufInt32Value(CelValue):
    _pb_value: Optional[PbInt32Value] # google.protobuf.Int32ValueインスタンスまたはNoneを保持

    def __init__(self, pb_value_instance: Optional[PbInt32Value]):
        """
        コンストラクタ。google.protobuf.Int32Valueのインスタンス、またはNone（null状態を表す）を受け取ります。
        """
        if pb_value_instance is not None and not isinstance(pb_value_instance, PbInt32Value):
            raise TypeError(
                f"CelProtobufInt32Value expects a google.protobuf.Int32Value instance or None, "
                f"got {type(pb_value_instance)}"
            )
        self._pb_value = pb_value_instance

    @classmethod
    def from_int(cls, value: Optional[int]) -> 'CelProtobufInt32Value':
        """PythonのintまたはNoneからCelProtobufInt32Valueを生成するファクトリメソッド"""
        if value is None:
            return cls(None) # null状態のラッパー
        # int32の範囲チェック: Pythonのintは任意精度なので、ProtobufのInt32Valueに収まるか確認
        if not (-(2**31) <= value < 2**31):
             raise ValueError(f"Integer value {value} is out of Int32 range for Int32Value.")
        return cls(PbInt32Value(value=value))

    @property
    def value(self) -> Optional[int]:
        """ラップされたPythonのint値、または値がない場合はNoneを返します。"""
        if self._pb_value is not None:
            return self._pb_value.value
        return None

    @property
    def cel_type(self) -> CelType:
        return CEL_INT32_WRAPPER # cel_types.py で定義した型を返す

    def __hash__(self):
        # null状態と値を持つ状態を区別してハッシュ化
        return hash(self.value if self._pb_value is not None else None)

    def __eq__(self, other: Any) -> bool:
        # print(f"DEBUG: CelProtobufInt32Value.__eq__ called. self.value={self.value}, other type={type(other)}")
        if self is other:
            return True

        # Step 1: 比較対象 `other` が CelDynValue ならアンラップする
        other_to_compare = other
        if isinstance(other, CelDynValue):  # 新設した CelDynValue かチェック
            other_to_compare = other.wrapped_value  # ラップされた実際の CelValue を取得

        # Step 2: self の Python プリミティブ値を取得
        self_py_val = self.value  # self.value は int または None

        # Step 3: self が null (Int32Valueが値をラップしていない) 場合の処理
        if self_py_val is None:
            # other_to_compare が CelNull か、または null をラップした数値ラッパーか
            if isinstance(other_to_compare, CelNull):
                return True
            # other_to_compare も value プロパティを持ち、それが None かチェック
            if hasattr(other_to_compare, 'value') and other_to_compare.value is None:
                # より厳密には、other_to_compare が数値ラッパー型であることも確認する
                if isinstance(other_to_compare, (
                        CelProtobufInt32Value, CelProtobufUInt32Value, CelProtobufInt64Value, CelProtobufUInt64Value,
                        CelProtobufFloatValue, CelProtobufDoubleValue, CelInt, CelUInt, CelDouble
                )):
                    return True
            return False

        # Step 4: self が値を持つ場合 (self_py_val は int)
        #          other_to_compare と比較する

        # other_to_compare から比較可能な Python 数値を取得試行
        other_py_numeric_val: Any = None
        is_other_numeric = False

        if isinstance(other_to_compare, (CelInt, CelUInt)):  # CelUint との比較
            other_py_numeric_val = other_to_compare.value
            is_other_numeric = True if other_py_numeric_val is not None else False
        elif isinstance(other_to_compare, CelDouble):
            other_py_numeric_val = other_to_compare.value
            is_other_numeric = True if other_py_numeric_val is not None else False
        elif isinstance(other_to_compare, (CelProtobufInt32Value, CelProtobufUInt32Value,
                                           CelProtobufInt64Value, CelProtobufUInt64Value,  # ★テストケースの型
                                           CelProtobufFloatValue, CelProtobufDoubleValue)):
            other_py_numeric_val = other_to_compare.value  # .value は Python プリミティブ値
            is_other_numeric = True if other_py_numeric_val is not None else False
        # else: other_to_compare は数値型ではない、または CelNull (CelNull は is_other_numeric = False)

        if is_other_numeric:
            # self_py_val (int) と other_py_numeric_val (int or float) の数値比較
            if isinstance(other_py_numeric_val, float) and math.isnan(other_py_numeric_val):
                return False  # int == NaN は False
            try:
                return self_py_val == other_py_numeric_val
            except TypeError:  # 万が一、互換性のない数値型同士の比較になった場合
                return False

        # self は数値 (int)、other_to_compare は数値として解釈できなかった場合、
        # または CelNull だった場合は False (self_py_val is None の分岐で処理済みのため CelNull はここに来ないはず)
        return False

    def __lt__(self, other: Any) -> bool:
        if self.value is None: # nullは比較不可
            raise TypeError(f"Cannot compare null {self.cel_type.name} using '<'")

        other_py_value: Any = None
        if isinstance(other, (CelProtobufInt32Value, CelInt)):
            other_py_value = other.value
            if other_py_value is None: # 相手もnullなら比較不可
                 raise TypeError(f"Cannot compare {self.cel_type.name} with null {other.cel_type.name} using '<'")
            return self.value < other_py_value # type: ignore
        elif isinstance(other, CelDouble):
            if math.isnan(other.value): # NaNとの比較は常にfalse (CEL仕様に準拠)
                return False
            return float(self.value) < other.value # type: ignore
        elif isinstance(other, CelUInt): # int32 vs uint64
            if self.value < 0: return True # 負のint32は常に正のuint64より小さい
            return self.value < other.value # type: ignore

        raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name}")

    # --- 算術演算子 ---
    # ラッパー型同士、またはラッパー型と対応するプリミティブ型 (CelInt) との演算を定義
    # 結果は、CELのセマンティクスに従い、通常はプリミティブ型 (CelInt) を返すか、
    # もしラッパー型を維持するなら CelProtobufInt32Value を返す。
    # ここでは、演算結果は CelInt を返すようにし、オーバーフローはint64の範囲でチェック。
    # nullとの演算はエラー。

    def _op_with_int_check_null(self, other: Any, op: Callable[[int, int], int], op_name: str) -> CelInt:
        if self.value is None:
            raise TypeError(f"Cannot perform {op_name} on null {self.cel_type.name}")

        other_int_val: Optional[int] = None
        if isinstance(other, CelProtobufInt32Value):
            other_int_val = other.value
        elif isinstance(other, CelInt):
            other_int_val = other.value
        elif isinstance(other, CelUInt): # uintも考慮
             other_int_val = other.value


        if other_int_val is None: # 相手がnullの場合
            raise TypeError(f"Cannot perform {op_name} with null {type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name}")

        # Pythonのintで演算し、結果をCelIntとして返す (int64範囲チェックはCelIntコンストラクタや_check_int64_rangeで行う想定)
        try:
            result_val = op(self.value, other_int_val)
            return CelInt(_check_int64_range(result_val, f"{self.cel_type.name} {op_name}"))
        except TypeError: # 互換性のない型との演算
            raise TypeError(f"Operator '{op_name}' not supported between {self.cel_type.name} and {type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name}")


    def __add__(self, other: Any) -> CelInt:
        return self._op_with_int_check_null(other, lambda a, b: a + b, "+")

    def __sub__(self, other: Any) -> CelInt:
        return self._op_with_int_check_null(other, lambda a, b: a - b, "-")

    def __mul__(self, other: Any) -> CelInt:
        return self._op_with_int_check_null(other, lambda a, b: a * b, "*")

    def __truediv__(self, other: Any) -> CelInt: # CELの整数除算は0への切り捨て
        if isinstance(other, (CelProtobufInt32Value, CelInt, CelUInt)):
            if other.value == 0: # type: ignore
                raise ValueError("division by zero")
        return self._op_with_int_check_null(other, lambda a, b: a // b, "/") # Pythonの // を使用

    def __mod__(self, other: Any) -> CelInt:
        if isinstance(other, (CelProtobufInt32Value, CelInt, CelUInt)):
            if other.value == 0: # type: ignore
                raise ValueError("Modulo by zero")
        return self._op_with_int_check_null(other, lambda a, b: a % b, "%")

    def __neg__(self) -> CelInt:
        if self.value is None:
            raise TypeError(f"Cannot negate null {self.cel_type.name}")
        # -(INT32_MIN) がINT64の範囲を超えることはない
        return CelInt(_check_int64_range(-self.value, f"Negation of {self.cel_type.name}"))


    def __repr__(self):
        # google.protobuf.Int32Value{value: 123} のような表現を目指す
        if self._pb_value is None:
            return f"{self.cel_type.name}{{}}" # または f"{self.cel_type.name}(null)"
        return f"{self.cel_type.name}{{value: {self.value}}}"


class CelProtobufUInt32Value(CelValue):
    _pb_value: Optional[PbUInt32Value]

    def __init__(self, pb_value_instance: Optional[PbUInt32Value]):
        if pb_value_instance is not None and not isinstance(pb_value_instance, PbUInt32Value):
            raise TypeError(f"CelProtobufUInt32Value expects UInt32Value or None, got {type(pb_value_instance)}")
        self._pb_value = pb_value_instance

    @classmethod
    def from_int(cls, value: Optional[int]) -> 'CelProtobufUInt32Value':
        if value is None:
            return cls(None)
        if not (0 <= value < 2**32):
            raise ValueError(f"Value {value} out of range for UInt32Value.")
        return cls(PbUInt32Value(value=value))

    @property
    def value(self) -> Optional[int]:
        return self._pb_value.value if self._pb_value is not None else None

    @property
    def cel_type(self) -> CelType:
        return CEL_UINT32_WRAPPER

    def __eq__(self, other: Any) -> bool:
        # print(f"DEBUG: CelProtobufUInt32Value.__eq__ called. self.value={self.value}, other type={type(other)}")
        if self is other:
            return True

        # Step 1: 比較対象 `other` が CelDynValue ならアンラップする
        other_for_comparison = other
        if isinstance(other, CelDynValue):  # CelDynValue は新設したクラス
            other_for_comparison = other.wrapped_value  # ラップされた実際の CelValue を取得

        # Step 2: self の Python プリミティブ値を取得
        self_py_val = self.value  # self.value は int (uintを表す) または None

        # Step 3: self が null (UInt32Valueが値をラップしていない) 場合の処理
        if self_py_val is None:
            if isinstance(other_for_comparison, CelNull):
                return True
            if hasattr(other_for_comparison, 'value') and other_for_comparison.value is None:
                if isinstance(other_for_comparison, (
                        CelProtobufInt32Value, CelProtobufUInt32Value, CelProtobufInt64Value, CelProtobufUInt64Value,
                        CelProtobufFloatValue, CelProtobufDoubleValue,
                        CelInt, CelUInt, CelDouble
                )):
                    return True
            return False

        # Step 4: Self が値を持つ場合 (self_py_val は非負の int)。 other_for_comparison と比較。
        other_py_val: Any = None
        is_other_numeric = False

        if isinstance(other_for_comparison, (CelInt, CelUInt)):
            other_py_val = other_for_comparison.value
            is_other_numeric = True if other_py_val is not None else False
        elif isinstance(other_for_comparison, CelDouble):
            other_py_val = other_for_comparison.value
            is_other_numeric = True if other_py_val is not None else False
        elif isinstance(other_for_comparison, (
                CelProtobufInt32Value, CelProtobufUInt32Value,
                CelProtobufInt64Value, CelProtobufUInt64Value,  # ★テストケースの型(Int64Value)
                CelProtobufFloatValue, CelProtobufDoubleValue
        )):
            other_py_val = other_for_comparison.value  # .value は Python プリミティブ値
            is_other_numeric = True if other_py_val is not None else False
        # else: other_for_comparison は CelNull か、または数値型ではない

        if is_other_numeric:
            if other_py_val is None:  # self は非null、other は数値ラッパーだが実質null
                return False

            # self_py_val (uint由来のint) と other_py_val (int or float) の数値比較
            if isinstance(other_py_val, float) and math.isnan(other_py_val):
                return False  # uint == NaN は False

            # CELのuintは非負。比較相手のintも非負でないと数値的に等価にはなりにくい
            # (ただし、-0.0 == 0u のようなケースはありうるが、int(-0)は0)
            # Pythonの == は型が異なっても数値として比較する
            # 例: 34 (uint由来のint) == 34 (int64由来のint) -> True
            # 例: 34 (uint由来のint) == 34.0 (double由来のfloat) -> True
            try:
                # print(f"DEBUG: Numeric comparison (UInt32Value): {self_py_val} ({type(self_py_val)}) == {other_py_val} ({type(other_py_val)})")
                return self_py_val == other_py_val
            except TypeError:
                return False  # 互換性のない型との比較エラー (通常はPythonが処理)

        # other_for_comparison が数値として解釈できなかった場合 (CelNull は is_other_numeric = False)
        # self は数値なので、CelNull や他の非数値型とは等しくない
        return False

    def __lt__(self, other: Any) -> bool:
        if self.value is None:
            raise TypeError(f"Cannot compare null {self.cel_type.name}")
        if isinstance(other, (CelProtobufUInt32Value, CelUInt)):
            return self.value < other.value
        if isinstance(other, CelInt):
            return other.value > 0 and self.value < other.value
        if isinstance(other, CelDouble):
            return not math.isnan(other.value) and float(self.value) < other.value
        raise TypeError(f"Unsupported comparison with {type(other)}")

    def _op_with_int_check_null(self, other: Any, op: Callable[[int, int], int], op_name: str) -> CelUInt:
        if self.value is None:
            raise TypeError(f"Cannot perform {op_name} on null {self.cel_type.name}")
        other_val = None
        if isinstance(other, (CelUInt, CelInt, CelProtobufUInt32Value)):
            other_val = other.value
        if other_val is None:
            raise TypeError(f"Cannot perform {op_name} with null {type(other).__name__}")
        return CelUInt(op(self.value, other_val))

    def __add__(self, other: Any) -> CelUInt:
        return self._op_with_int_check_null(other, lambda a, b: a + b, "+")

    def __sub__(self, other: Any) -> CelUInt:
        return self._op_with_int_check_null(other, lambda a, b: a - b, "-")

    def __mul__(self, other: Any) -> CelUInt:
        return self._op_with_int_check_null(other, lambda a, b: a * b, "*")

    def __truediv__(self, other: Any) -> CelUInt:
        if other.value == 0:
            raise ValueError("division by zero")
        return self._op_with_int_check_null(other, lambda a, b: a // b, "/")

    def __mod__(self, other: Any) -> CelUInt:
        if other.value == 0:
            raise ValueError("Modulo by zero")
        return self._op_with_int_check_null(other, lambda a, b: a % b, "%")

    def __repr__(self):
        return f"{self.cel_type.name}{{value: {self.value}}}" if self._pb_value else f"{self.cel_type.name}{{}}"

class CelProtobufInt64Value(CelValue):
    _pb_value: Optional[PbInt64Value]

    def __init__(self, pb_value_instance: Optional[PbInt64Value]):
        if pb_value_instance is not None and not isinstance(pb_value_instance, PbInt64Value):
            raise TypeError(f"CelProtobufInt64Value expects Int64Value or None, got {type(pb_value_instance)}")
        self._pb_value = pb_value_instance

    @classmethod
    def from_int(cls, value: Optional[int]) -> 'CelProtobufInt64Value':
        if value is None:
            return cls(None)
        # Python int は任意精度だが、Protobuf Int64 に収まる必要がある
        if not (-(2**63) <= value < 2**63):
            raise ValueError(f"Value {value} out of range for Int64Value.")
        return cls(PbInt64Value(value=value))

    @property
    def value(self) -> Optional[int]:
        return self._pb_value.value if self._pb_value is not None else None

    @property
    def cel_type(self) -> CelType:
        return CEL_INT64_WRAPPER

    def __eq__(self, other: Any) -> bool:
        if self.value is None:
            return isinstance(other, (CelProtobufInt64Value, CelNull)) and other.value is None
        if isinstance(other, (CelProtobufInt64Value, CelInt)):
            return self.value == other.value
        if isinstance(other, CelDouble):
            return not math.isnan(other.value) and float(self.value) == other.value
        return False

    def __lt__(self, other: Any) -> bool:
        if self.value is None:
            raise TypeError(f"Cannot compare null {self.cel_type.name} using '<'")
        if isinstance(other, (CelProtobufInt64Value, CelInt)):
            if other.value is None:
                raise TypeError(f"Cannot compare with null {other.cel_type.name}")
            return self.value < other.value
        if isinstance(other, CelDouble):
            return not math.isnan(other.value) and float(self.value) < other.value
        if isinstance(other, CelUInt):
            if self.value < 0:
                return True
            return self.value < other.value
        raise TypeError(f"Unsupported comparison with {type(other)}")

    def _op_with_int_check_null(self, other: Any, op: Callable[[int, int], int], op_name: str) -> CelInt:
        if self.value is None:
            raise TypeError(f"Cannot perform {op_name} on null {self.cel_type.name}")
        other_val = other.value if isinstance(other, (CelInt, CelUInt, CelProtobufInt64Value)) else None
        if other_val is None:
            raise TypeError(f"Cannot perform {op_name} with null {type(other).__name__}")
        return CelInt(_check_int64_range(op(self.value, other_val), f"{self.cel_type.name} {op_name}"))

    def __add__(self, other: Any) -> CelInt:
        return self._op_with_int_check_null(other, lambda a, b: a + b, "+")

    def __sub__(self, other: Any) -> CelInt:
        return self._op_with_int_check_null(other, lambda a, b: a - b, "-")

    def __mul__(self, other: Any) -> CelInt:
        return self._op_with_int_check_null(other, lambda a, b: a * b, "*")

    def __truediv__(self, other: Any) -> CelInt:
        if other.value == 0:
            raise ValueError("division by zero")
        return self._op_with_int_check_null(other, lambda a, b: a // b, "/")

    def __mod__(self, other: Any) -> CelInt:
        if other.value == 0:
            raise ValueError("Modulo by zero")
        return self._op_with_int_check_null(other, lambda a, b: a % b, "%")

    def __neg__(self) -> CelInt:
        if self.value is None:
            raise TypeError(f"Cannot negate null {self.cel_type.name}")
        return CelInt(_check_int64_range(-self.value, f"Negation of {self.cel_type.name}"))

    def __repr__(self):
        return f"{self.cel_type.name}{{value: {self.value}}}" if self._pb_value else f"{self.cel_type.name}{{}}"


class CelProtobufUInt64Value(CelValue):
    _pb_value: Optional[PbUInt64Value]

    def __init__(self, pb_value_instance: Optional[PbUInt64Value]):
        if pb_value_instance is not None and not isinstance(pb_value_instance, PbUInt64Value):
            raise TypeError(f"CelProtobufUInt64Value expects UInt64Value or None, got {type(pb_value_instance)}")
        self._pb_value = pb_value_instance

    @classmethod
    def from_int(cls, value: Optional[int]) -> 'CelProtobufUInt64Value':
        if value is None:
            return cls(None)
        if not (0 <= value < 2**64):
            raise ValueError(f"Value {value} out of range for UInt64Value.")
        return cls(PbUInt64Value(value=value))

    @property
    def value(self) -> Optional[int]:
        return self._pb_value.value if self._pb_value is not None else None

    @property
    def cel_type(self) -> CelType:
        return CEL_UINT64_WRAPPER

    def __eq__(self, other: Any) -> bool:
        if self.value is None:
            return isinstance(other, (CelProtobufUInt64Value, CelNull)) and other.value is None
        if isinstance(other, (CelProtobufUInt64Value, CelUInt)):
            return self.value == other.value
        if isinstance(other, CelDouble):
            return not math.isnan(other.value) and float(self.value) == other.value
        return False

    def __lt__(self, other: Any) -> bool:
        if self.value is None:
            raise TypeError(f"Cannot compare null {self.cel_type.name}")
        if isinstance(other, (CelProtobufUInt64Value, CelUInt)):
            return self.value < other.value
        if isinstance(other, CelInt):
            return other.value is not None and other.value > 0 and self.value < other.value
        if isinstance(other, CelDouble):
            return not math.isnan(other.value) and float(self.value) < other.value
        raise TypeError(f"Unsupported comparison with {type(other)}")

    def _op_with_int_check_null(self, other: Any, op: Callable[[int, int], int], op_name: str) -> CelUInt:
        if self.value is None:
            raise TypeError(f"Cannot perform {op_name} on null {self.cel_type.name}")
        other_val = other.value if isinstance(other, (CelUInt, CelInt, CelProtobufUInt64Value)) else None
        if other_val is None:
            raise TypeError(f"Cannot perform {op_name} with null {type(other).__name__}")
        return CelUInt(op(self.value, other_val))  # CELでは UInt64 の範囲制限は基本しない実装が多い

    def __add__(self, other: Any) -> CelUInt:
        return self._op_with_int_check_null(other, lambda a, b: a + b, "+")

    def __sub__(self, other: Any) -> CelUInt:
        return self._op_with_int_check_null(other, lambda a, b: a - b, "-")

    def __mul__(self, other: Any) -> CelUInt:
        return self._op_with_int_check_null(other, lambda a, b: a * b, "*")

    def __truediv__(self, other: Any) -> CelUInt:
        if other.value == 0:
            raise ValueError("division by zero")
        return self._op_with_int_check_null(other, lambda a, b: a // b, "/")

    def __mod__(self, other: Any) -> CelUInt:
        if other.value == 0:
            raise ValueError("Modulo by zero")
        return self._op_with_int_check_null(other, lambda a, b: a % b, "%")

    def __repr__(self):
        return f"{self.cel_type.name}{{value: {self.value}}}" if self._pb_value else f"{self.cel_type.name}{{}}"

class CelDuration(CelValue):
    def __init__(self, value: timedelta):
        # Durationの範囲チェックはここで明示的に行うか、演算時か、
        # duration(string)のようなコンストラクタ関数で行う。
        # ここではPythonのtimedeltaの範囲を受け入れる。
        # CEL仕様の「roughly +-290 years」は文字列からのパース時や、
        # Timestampとの演算結果で考慮される。
        self.value: timedelta = value  # _check_duration_range(value)

    def __hash__(self):
        return hash(self.value)

    @property
    def cel_type(self) -> CelType:
        return CEL_DURATION

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CelDuration) and self.value == other.value

    def __lt__(self, other: Any) -> bool:
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        if not isinstance(other, CelDuration):
            raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {other_type_name}")
        return self.value < other.value

    def __add__(self, other: Any) -> CelValue:  # Duration or Timestamp を返す
        if isinstance(other, CelDuration):
            # Duration + Duration -> Duration
            return CelDuration(self.value + other.value)  # 結果のDurationも範囲チェックが必要なら行う
        if isinstance(other, CelTimestamp):  # Duration + Timestamp -> Timestamp
            result_ts = other.value + self.value  # 順序入れ替え
            return CelTimestamp(_check_timestamp_range(result_ts, "Duration + Timestamp"))
        return super().__add__(other)

    def __sub__(self, other: Any) -> 'CelDuration':
        if isinstance(other, CelDuration):
            # Duration - Duration -> Duration
            return CelDuration(self.value - other.value)
        return super().__sub__(other)

    def __repr__(self):
        # CEL仕様の string(duration) は "seconds and fractional seconds with an 's' suffix"
        # ここではPythonのtimedeltaの標準reprを使うが、string()変換で仕様に合わせる
        return f"CelDuration(total_seconds={self.value.total_seconds()})"


class CelTimestamp(CelValue):
    def __init__(self, value: datetime):
        # 入力値がnaiveならUTCとして扱う (CELのTimestampは実質UTC)
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            aware_value = value.replace(tzinfo=timezone.utc)
        else:
            aware_value = value
        # 初期化時に範囲チェック
        self.value: datetime = _check_timestamp_range(aware_value, "CelTimestamp initialization")

    def __hash__(self):
        return hash(self.value)

    @property
    def cel_type(self) -> CelType:
        return CEL_TIMESTAMP

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CelTimestamp) and self.value == other.value

    def __lt__(self, other: Any) -> bool:
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        if not isinstance(other, CelTimestamp):
            raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {other_type_name}")
        return self.value < other.value

    def __add__(self, other: Any) -> 'CelTimestamp':
        if isinstance(other, CelDuration):
            result_ts = self.value + other.value
            return CelTimestamp(_check_timestamp_range(result_ts, "Timestamp + Duration"))
        return super().__add__(other)

    def __sub__(self, other: Any) -> CelValue:  # Timestamp or Duration を返す
        if isinstance(other, CelTimestamp):
            # Timestamp - Timestamp -> Duration
            # この差分がCELのDurationの範囲を超えることは通常考えにくいが、
            # CelDurationコンストラクタでチェックされる
            return CelDuration(self.value - other.value)
        if isinstance(other, CelDuration):
            # Timestamp - Duration -> Timestamp
            result_ts = self.value - other.value
            return CelTimestamp(_check_timestamp_range(result_ts, "Timestamp - Duration"))
        return super().__sub__(other)

    def __repr__(self):
        return f"CelTimestamp({self.value.isoformat()})"

class CelProtobufBoolValue(CelValue):
    _pb_value: Optional[PbBoolValue]

    def __init__(self, pb_value_instance: Optional[PbBoolValue]):
        if pb_value_instance is not None and not isinstance(pb_value_instance, PbBoolValue):
            raise TypeError(f"CelProtobufBoolValue expects BoolValue or None, got {type(pb_value_instance)}")
        self._pb_value = pb_value_instance

    @classmethod
    def from_bool(cls, value: Optional[bool]) -> 'CelProtobufBoolValue':
        if value is None:
            return cls(None)
        return cls(PbBoolValue(value=value))

    @property
    def value(self) -> Optional[bool]:
        return self._pb_value.value if self._pb_value is not None else None

    @property
    def cel_type(self) -> CelType:
        return CEL_BOOL_WRAPPER

    def __eq__(self, other: Any) -> bool:
        if self.value is None:
            return isinstance(other, (CelProtobufBoolValue, CelNull)) and other.value is None
        if isinstance(other, CelProtobufBoolValue):
            return self.value == other.value
        if isinstance(other, CelBool):
            return self.value == other.value
        return False

    def __lt__(self, other: Any) -> bool:
        if self.value is None:
            raise TypeError(f"Cannot compare null {self.cel_type.name}")
        if isinstance(other, CelProtobufBoolValue):
            if other.value is None:
                raise TypeError(f"Cannot compare with null {other.cel_type.name}")
            return self.value < other.value
        if isinstance(other, CelBool):
            return self.value < other.value
        raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {type(other).__name__}")

    def __invert__(self) -> 'CelBool':
        if self.value is None:
            raise TypeError(f"Cannot negate null {self.cel_type.name}")
        return CelBool(not self.value)

    def __hash__(self):
        return hash(self.value if self._pb_value is not None else None)

    def __repr__(self):
        return f"{self.cel_type.name}{{value: {self.value}}}" if self._pb_value else f"{self.cel_type.name}{{}}"


class CelProtobufDoubleValue(CelValue):
    _pb_value: Optional[PbDoubleValue]

    def __init__(self, pb_value_instance: Optional[PbDoubleValue]):
        if pb_value_instance is not None and not isinstance(pb_value_instance, PbDoubleValue):
            raise TypeError(f"CelProtobufDoubleValue expects a DoubleValue or None, got {type(pb_value_instance)}")
        self._pb_value = pb_value_instance

    @classmethod
    def from_float(cls, value: Optional[float]) -> 'CelProtobufDoubleValue':
        if value is None:
            return cls(None)
        return cls(PbDoubleValue(value=value))

    @property
    def value(self) -> Optional[float]:
        return self._pb_value.value if self._pb_value is not None else None

    @property
    def cel_type(self) -> CelType:
        return CEL_DOUBLE_WRAPPER

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other: Any) -> bool:
        v = self.value
        if v is None:
            return isinstance(other, (CelProtobufDoubleValue, CelNull)) and other.value is None
        if v != v:  # NaN
            return False
        if isinstance(other, CelProtobufDoubleValue):
            return other.value is not None and other.value == other.value and v == other.value
        if isinstance(other, CelDouble):
            return other.value == other.value and v == other.value
        if isinstance(other, (CelInt, CelUInt)):
            return v == float(other.value)
        return False

    def __ne__(self, other: Any) -> bool:
        v = self.value
        if v is None:
            return not (isinstance(other, (CelProtobufDoubleValue, CelNull)) and other.value is None)
        if v != v:
            return True
        if isinstance(other, CelProtobufDoubleValue) and other.value is not None and other.value != other.value:
            return True
        if isinstance(other, CelDouble) and other.value != other.value:
            return True
        return not self.__eq__(other)

    def __lt__(self, other: Any) -> bool:
        v = self.value
        if v is None:
            raise TypeError("Cannot compare null DoubleValue")
        if v != v:
            return False  # self is NaN

        if isinstance(other, CelProtobufDoubleValue):
            if other.value is None or other.value != other.value:
                return False
            return v < other.value
        if isinstance(other, CelDouble):
            return other.value == other.value and v < other.value
        if isinstance(other, (CelInt, CelUInt)):
            return v < float(other.value)
        raise TypeError(f"Unsupported comparison with {type(other)}")

    def __add__(self, other: Any) -> CelDouble:
        v = self.value
        if v is None:
            raise TypeError("Cannot add null DoubleValue")
        if isinstance(other, CelProtobufDoubleValue):
            if other.value is None:
                raise TypeError("Cannot add null DoubleValue")
            return CelDouble(v + other.value)
        if isinstance(other, CelDouble):
            return CelDouble(v + other.value)
        if isinstance(other, (CelInt, CelUInt)):
            return CelDouble(v + float(other.value))
        return super().__add__(other)

    def __sub__(self, other: Any) -> CelDouble:
        v = self.value
        if v is None:
            raise TypeError("Cannot subtract null DoubleValue")
        if isinstance(other, CelProtobufDoubleValue):
            if other.value is None:
                raise TypeError("Cannot subtract null DoubleValue")
            return CelDouble(v - other.value)
        if isinstance(other, CelDouble):
            return CelDouble(v - other.value)
        if isinstance(other, (CelInt, CelUInt)):
            return CelDouble(v - float(other.value))
        return super().__sub__(other)

    def __mul__(self, other: Any) -> CelDouble:
        v = self.value
        if v is None:
            raise TypeError("Cannot multiply null DoubleValue")
        if isinstance(other, CelProtobufDoubleValue):
            if other.value is None:
                raise TypeError("Cannot multiply null DoubleValue")
            return CelDouble(v * other.value)
        if isinstance(other, CelDouble):
            return CelDouble(v * other.value)
        if isinstance(other, (CelInt, CelUInt)):
            return CelDouble(v * float(other.value))
        return super().__mul__(other)

    def __truediv__(self, other: Any) -> CelDouble:
        v = self.value
        if v is None:
            raise TypeError("Cannot divide null DoubleValue")
        divisor: Optional[float] = None

        if isinstance(other, CelProtobufDoubleValue):
            divisor = other.value
        elif isinstance(other, CelDouble):
            divisor = other.value
        elif isinstance(other, (CelInt, CelUInt)):
            divisor = float(other.value)

        if divisor is None:
            raise TypeError("Cannot divide by null")
        if divisor == 0:
            raise ValueError("division by zero")
        return CelDouble(v / divisor)

    def __neg__(self) -> CelDouble:
        if self.value is None:
            raise TypeError("Cannot negate null DoubleValue")
        return CelDouble(-self.value)

    def __repr__(self):
        return f"{self.cel_type.name}{{value: {self.value}}}" if self._pb_value else f"{self.cel_type.name}{{}}"


class CelProtobufStringValue(CelValue):
    _pb_value: Optional[PbStringValue]

    def __init__(self, pb_value_instance: Optional[PbStringValue]):
        if pb_value_instance is not None and not isinstance(pb_value_instance, PbStringValue):
            raise TypeError(f"CelProtobufStringValue expects StringValue or None, got {type(pb_value_instance)}")
        self._pb_value = pb_value_instance

    @classmethod
    def from_str(cls, value: Optional[str]) -> 'CelProtobufStringValue':
        if value is None:
            return cls(None)
        return cls(PbStringValue(value=value))

    @property
    def value(self) -> Optional[str]:
        return self._pb_value.value if self._pb_value is not None else None

    @property
    def cel_type(self) -> CelType:
        return CEL_STRING_WRAPPER

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other: Any) -> bool:
        if self.value is None:
            return isinstance(other, (CelProtobufStringValue, CelNull)) and other.value is None
        if isinstance(other, CelProtobufStringValue):
            return self.value == other.value
        if isinstance(other, CelString):
            return self.value == other.value
        return False

    def __lt__(self, other: Any) -> bool:
        if self.value is None:
            raise TypeError("Cannot compare null StringValue")
        if isinstance(other, CelProtobufStringValue):
            if other.value is None:
                raise TypeError("Cannot compare with null StringValue")
            return self.value < other.value
        if isinstance(other, CelString):
            return self.value < other.value
        raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {type(other).__name__}")

    def __add__(self, other: Any) -> CelString:
        if self.value is None:
            raise TypeError("Cannot concatenate null StringValue")
        if isinstance(other, CelProtobufStringValue):
            if other.value is None:
                raise TypeError("Cannot concatenate with null StringValue")
            return CelString(self.value + other.value)
        if isinstance(other, CelString):
            return CelString(self.value + other.value)
        return super().__add__(other)

    def __len__(self):
        if self.value is None:
            raise TypeError("Cannot get length of null StringValue")
        return len(self.value)

    def __repr__(self):
        return f"{self.cel_type.name}{{value: {self.value!r}}}" if self._pb_value else f"{self.cel_type.name}{{}}"


class CelProtobufBytesValue(CelValue):
    _pb_value: Optional[PbBytesValue]

    def __init__(self, pb_value_instance: Optional[PbBytesValue]):
        if pb_value_instance is not None and not isinstance(pb_value_instance, PbBytesValue):
            raise TypeError(f"CelProtobufBytesValue expects BytesValue or None, got {type(pb_value_instance)}")
        self._pb_value = pb_value_instance

    @classmethod
    def from_bytes(cls, value: Optional[bytes]) -> 'CelProtobufBytesValue':
        if value is None:
            return cls(None)
        return cls(PbBytesValue(value=value))

    @property
    def value(self) -> Optional[bytes]:
        return self._pb_value.value if self._pb_value is not None else None

    @property
    def cel_type(self) -> CelType:
        return CEL_BYTES_WRAPPER

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other: Any) -> bool:
        # self.value は Python の bytes または None

        # Case 1: self が null 状態の BytesValue (例: from_bytes(None) で生成)
        if self.value is None:
            if isinstance(other, CelProtobufBytesValue):
                return other.value is None  # 相手も null 状態の BytesValue なら True
            elif isinstance(other, CelNull):
                return True  # null 状態の BytesValue は CEL の null と等価
            else:
                # null状態のBytesValueは、値を持つCelBytesや他の型とは等しくない
                return False

        # Case 2: self が値 (具体的なbytes) を持つ BytesValue
        # self.value は Python の bytes (例: b'set')

        if isinstance(other, CelProtobufBytesValue):
            # 相手も CelProtobufBytesValue の場合
            if other.value is None:  # 相手が null 状態の BytesValue なら False
                return False
            return self.value == other.value  # Python の bytes 値同士を比較

        elif isinstance(other, CelBytes):
            # 相手が CelBytes の場合
            # CelBytes は常に具体的な bytes 値を持つ (CelBytes.value は None にならない設計のはず)
            # これが今回のテストケース 'BytesValue{value:b"set"} == b"set"' (CelBytes(b"set")) に該当
            return self.value == other.value  # Python の bytes 値同士を比較 (例: b'set' == b'set')

        elif isinstance(other, CelNull):
            # 値を持つ BytesValue は CEL の null とは等しくない
            return False

        # (オプション) Pythonのbytes型と直接比較する場合。
        # CELの評価器内部では通常CelValue同士の比較になるが、テストなどで役立つ可能性はある。
        # elif isinstance(other, bytes):
        #     return self.value == other

        # 上記のいずれでもない場合は比較不可、または等しくない
        return False  # 他の型とは等しくないと判断

    def __lt__(self, other: Any) -> bool:
        if self.value is None:
            raise TypeError("Cannot compare null BytesValue")
        if isinstance(other, CelProtobufBytesValue):
            if other.value is None:
                raise TypeError("Cannot compare with null BytesValue")
            return self.value < other.value
        if isinstance(other, CelBytes):
            return self.value < other.value
        raise TypeError(f"Unsupported comparison between {self.cel_type.name} and {type(other).__name__}")

    def __add__(self, other: Any) -> CelBytes:
        if self.value is None:
            raise TypeError("Cannot concatenate null BytesValue")
        if isinstance(other, CelProtobufBytesValue):
            if other.value is None:
                raise TypeError("Cannot concatenate with null BytesValue")
            return CelBytes(self.value + other.value)
        if isinstance(other, CelBytes):
            return CelBytes(self.value + other.value)
        return super().__add__(other)

    def __len__(self):
        if self.value is None:
            raise TypeError("Cannot get length of null BytesValue")
        return len(self.value)

    def __repr__(self):
        return f"{self.cel_type.name}{{value: {self.value!r}}}" if self._pb_value else f"{self.cel_type.name}{{}}"



class CelProtobufNullValue(CelValue):
    _instance: Optional['CelProtobufNullValue'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CelProtobufNullValue, cls).__new__(cls)
        return cls._instance

    @classmethod
    def from_proto(cls, value: Optional[int] = None) -> 'CelProtobufNullValue':
        # NullValue は enum だが常に NULL_VALUE (= 0) 固定
        if value is not None and value != PbNullValue.NULL_VALUE:
            raise ValueError(f"Invalid NullValue enum: {value}")
        return cls()

    @property
    def value(self):
        return None  # CEL における null 値

    @property
    def cel_type(self) -> CelType:
        return CEL_NULL_WRAPPER

    def __hash__(self):
        return hash(None)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, (CelProtobufNullValue, CelNull))

    def __lt__(self, other: Any) -> bool:
        other_type = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        raise TypeError(f"Operator '<' not supported between {self.cel_type.name} and {other_type}")

    def __repr__(self):
        return f"{self.cel_type.name}{{}}"


def cel_value_from_json_value(value: Any, CEL_NULL=None) -> CelValue:
    from ..cel_values import (
        CelNull, CelBool, CelInt, CelUInt, CelDouble,
        CelString, CelBytes, CelList, CelStruct,
    )

    if value is None:
        return CelNull()
    elif isinstance(value, bool):
        return CelBool(value)
    elif isinstance(value, int):
        if value >= 0:
            return CelUInt(value)
        else:
            return CelInt(value)
    elif isinstance(value, float):
        return CelDouble(value)
    elif isinstance(value, str):
        return CelString(value)
    elif isinstance(value, bytes):
        return CelBytes(value)
    elif isinstance(value, list):
        return CelList([cel_value_from_json_value(v) for v in value])
    elif isinstance(value, dict):
        return CelStruct({k: cel_value_from_json_value(v) for k, v in value.items()})
    else:
        raise TypeError(f"Unsupported JSON-like value type: {type(value).__name__}")

def cel_value_to_json_value(cel_value: CelValue) -> Any:
    from ..cel_values import (
        CelNull, CelBool, CelInt, CelUInt, CelDouble,
        CelString, CelBytes, CelList, CelStruct
    )

    if isinstance(cel_value, CelNull):
        return None
    elif isinstance(cel_value, CelBool):
        return cel_value.value
    elif isinstance(cel_value, (CelInt, CelUInt)):
        return int(cel_value.value)
    elif isinstance(cel_value, CelDouble):
        return float(cel_value.value)
    elif isinstance(cel_value, CelString):
        return cel_value.value
    elif isinstance(cel_value, CelBytes):
        # CELではbase64表現を使うが、ここではbytesをそのまま返す（必要に応じて変更）
        return cel_value.value
    elif isinstance(cel_value, CelList):
        return [cel_value_to_json_value(el) for el in cel_value]
    elif isinstance(cel_value, CelStruct):
        return {k: cel_value_to_json_value(v) for k, v in cel_value.fields.items()}
    else:
        raise TypeError(f"Unsupported CelValue type: {type(cel_value).__name__}")


# --- CEL Timestamp/Duration の範囲定数 ---
_CEL_MIN_TIMESTAMP_SECONDS = -62135596800
_CEL_MAX_TIMESTAMP_SECONDS = 253402300799
_NANOS_PER_SECOND = 1_000_000_000
_NANOS_PER_MILLISECOND = 1_000_000
_NANOS_PER_MINUTE = 60 * _NANOS_PER_SECOND
_NANOS_PER_HOUR = 60 * _NANOS_PER_MINUTE


# --- タイムゾーン解析ヘルパー (前回の回答から、re を使用) ---
def _parse_timezone_string(tz_cel: Optional[CelString]) -> timezone:
    if tz_cel is None or not tz_cel.value: return timezone.utc
    tz_str = tz_cel.value.strip()
    if not tz_str: return timezone.utc
    try:
        return ZoneInfo(tz_str)
    except ZoneInfoNotFoundError:
        pass
    except Exception:
        pass

    offset_match = re.fullmatch(r"([+-])?(\d{2}):(\d{2})", tz_str)
    if offset_match:
        sign_char, hours_str, minutes_str = offset_match.groups()
        try:
            hours, minutes = int(hours_str), int(minutes_str)
            if not (0 <= hours <= 23 and 0 <= minutes <= 59): raise ValueError("Offset out of range.")
            offset_delta = timedelta(hours=hours, minutes=minutes)
            if sign_char == '-':
                offset_delta *= -1
            elif sign_char is None and tz_str != "00:00":  # 符号なしで "00:00" 以外なら正とみなす (例: "02:00")
                pass  # 正のオフセットとして offset_delta を使用
            return timezone(offset_delta)
        except ValueError:
            pass
    if tz_str.upper() == "UTC": return timezone.utc
    raise ValueError(f"Invalid or unsupported timezone string: '{tz_str}'")


# --- Protobuf Timestamp から Python datetime への変換ヘルパー (UTC aware) ---
def _pb_timestamp_to_datetime_utc(pb_ts: PbTimestamp) -> datetime:
    if pb_ts is None: raise ValueError("Input protobuf timestamp is null")
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return epoch + timedelta(seconds=pb_ts.seconds, microseconds=pb_ts.nanos // 1000)


# --- CEL Timestamp Range Check (google.protobuf.Timestampに対して行う) ---
def _check_cel_timestamp_pb_range(pb_ts: PbTimestamp, operation_context: str):
    s, n = pb_ts.seconds, pb_ts.nanos
    is_valid = False
    if s < _CEL_MIN_TIMESTAMP_SECONDS or s > _CEL_MAX_TIMESTAMP_SECONDS:
        is_valid = False
    elif s == _CEL_MIN_TIMESTAMP_SECONDS:
        is_valid = (n >= 0)
    elif s == _CEL_MAX_TIMESTAMP_SECONDS:
        is_valid = (n <= 999_999_999)
    else:
        is_valid = (0 <= n <= 999_999_999)  # 通常の nanos 範囲

    if not (0 <= n <= 999_999_999):  # Protobuf Timestamp 自体の nanos 制約
        raise ValueError(
            f"Timestamp nanos ({n}) out of valid protobuf range [0, 999999999] during {operation_context}.")

    if not is_valid:
        min_repr, max_repr = "0001-01-01T00:00:00Z", "9999-12-31T23:59:59.999999999Z"
        raise ValueError(
            f"Timestamp result ({s}s, {n}ns) from {operation_context} "
            f"is outside the valid CEL range [{min_repr}, {max_repr}]."
        )


_INT64_MAX = (1 << 63) - 1
_INT64_MIN = -(1 << 63)

# --- CelProtobufDuration クラスの実装 ---
class CelProtobufDuration(CelValue):
    _pb_value: Optional[PbDuration]

    def __init__(self, pb_duration_instance: Optional[PbDuration]):
        if pb_duration_instance is not None:
            if not isinstance(pb_duration_instance, PbDuration):
                raise TypeError(
                    f"CelProtobufDuration expects a google.protobuf.Duration instance or None, "
                    f"got {type(pb_duration_instance)}"
                )

            s, n = pb_duration_instance.seconds, pb_duration_instance.nanos

            # # 1. google.protobuf.Duration 構造としてのバリデーション (nanos範囲と符号の一致)
            # if not (-999_999_999 <= n <= 999_999_999):
            #     raise ValueError(f"Duration nanos ({n}) out of protobuf spec range [-999999999, 999999999] "
            #                      f"for duration with seconds={s}.")
            # if s != 0 and n != 0 and (s < 0) != (n < 0):
            #     raise ValueError(f"Duration seconds ({s}) and nanos ({n}) must have the same sign "
            #                      f"if both are non-zero.")

            total_nanos = s * 1_000_000_000 + n
            if not (_INT64_MIN <= total_nanos <= _INT64_MAX):
                # エラーメッセージに "range" を含める
                raise ValueError(
                    f"Duration value (seconds={s}, nanos={n}; total_nanos={total_nanos}) "
                    f"is outside the allowed CEL operational range (total nanoseconds must fit in int64)."
                )

        self._pb_value = pb_duration_instance

    @classmethod
    def from_timedelta(cls, td: Optional[timedelta]) -> 'CelProtobufDuration':
        if td is None:
            return cls(None)  # コンストラクタが None を処理

        # timedelta.total_seconds() は float を返す。ナノ秒精度で扱うために注意。
        # より直接的な方法:
        total_nanos = (td.days * 86400 + td.seconds) * _NANOS_PER_SECOND + td.microseconds * 1000

        seconds = total_nanos // _NANOS_PER_SECOND
        nanos = total_nanos % _NANOS_PER_SECOND  # Python 3では剰余の符号は除数に一致 (結果は正か0)

        # total_nanos が負の場合、seconds と nanos が PbDuration の規則に合うように調整
        # PbDuration: sとnは同符号(s!=0)、またはn=0。nは[-1e9+1, 1e9-1]
        if total_nanos < 0 and nanos > 0:  # 例: total_nanos = -0.5s = -500e6 ns
            # seconds = -500e6 // 1e9 = -1
            # nanos   = -500e6 %  1e9 =  500e6 (Python)
            # この場合、seconds = -1, nanos = 500e6 は (-0.5s) を表す
            # PbDuration としては (seconds = 0, nanos = -500e6) or (seconds = -1, nanos = 500e6)
            # 後者は正規化されてない。 (seconds = -1, nanos = +500e6) -> -0.5s
            # 正常なPbDurationは secondsとnanosが同符号。
            seconds += 1
            nanos -= _NANOS_PER_SECOND

        # ここで pb_duration のバリデーションがコンストラクタで行われる
        pb_duration = PbDuration(seconds=seconds, nanos=nanos)
        return cls(pb_duration)

    @property
    def value(self) -> Optional[timedelta]:
        # このプロパティは精度が落ちることに注意
        # 具体的にはtimedeltaのハンドリングで999999999nsが-1 day, 23:59:59になったりする。
        if self._pb_value is None: return None
        return timedelta(seconds=self._pb_value.seconds, microseconds=self._pb_value.nanos // 1000)

    @property
    def cel_type(self) -> CelValue:
        return CEL_DURATION  # 実際のCelTypeオブジェクトを返す

    def __hash__(self):
        if self._pb_value is None: return hash(None)
        return hash((self._pb_value.seconds, self._pb_value.nanos))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, CelProtobufDuration):
            if self._pb_value is None: return other._pb_value is None
            if other._pb_value is None: return False
            return self._pb_value.seconds == other._pb_value.seconds and \
                self._pb_value.nanos == other._pb_value.nanos
        if self._pb_value is None and isinstance(other, CelNull): return True  # null == null
        return False

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, CelProtobufDuration):
            if isinstance(other, CelNull): raise TypeError(f"Unsupported < between Duration and Null")
            raise TypeError(f"Unsupported < between Duration and {type(other).__name__}")
        if self._pb_value is None or other._pb_value is None:
            raise TypeError("Cannot compare None Duration values using '<'")
        s1, n1, s2, n2 = self._pb_value.seconds, self._pb_value.nanos, other._pb_value.seconds, other._pb_value.nanos
        if s1 != s2: return s1 < s2
        return n1 < n2

    # (他の比較演算子 __gt__, __le__, __ge__ も同様に実装可能)

    def __repr__(self):
        if self._pb_value is None: return f"CelProtobufDuration(None)"
        return f"CelProtobufDuration(PbDuration(seconds={self._pb_value.seconds}, nanos={self._pb_value.nanos}))"

    def __add__(self, other: Any) -> CelValue:
        if self._pb_value is None: raise TypeError("Cannot perform arithmetic on null Duration")
        if isinstance(other, CelProtobufDuration):
            if other._pb_value is None: raise TypeError("Cannot perform arithmetic with null Duration")
            s1, n1 = self._pb_value.seconds, self._pb_value.nanos
            s2, n2 = other._pb_value.seconds, other._pb_value.nanos

            res_s = s1 + s2
            res_n = n1 + n2

            # PbDuration の nanos の正規化 (-1e9 < n < 1e9, s と n は同符号)
            if res_n <= -_NANOS_PER_SECOND or res_n >= _NANOS_PER_SECOND:
                res_s += res_n // _NANOS_PER_SECOND
                res_n %= _NANOS_PER_SECOND

            # sとnの符号を合わせる (sが0でない場合)
            if res_s > 0 and res_n < 0:
                res_s -= 1
                res_n += _NANOS_PER_SECOND
            elif res_s < 0 and res_n > 0:
                res_s += 1
                res_n -= _NANOS_PER_SECOND

            return CelProtobufDuration(PbDuration(seconds=res_s, nanos=res_n))

        if isinstance(other, CelProtobufTimestamp):  # Duration + Timestamp
            if other._pb_value is None: raise TypeError("Cannot perform arithmetic with null Timestamp")
            # Timestamp + Duration と同じロジックを呼び出す
            return cel_perform_timestamp_duration_add(other._pb_value, self._pb_value)

        return super().__add__(other)

    def __sub__(self, other: Any) -> 'CelProtobufDuration':
        if self._pb_value is None: raise TypeError("Cannot perform arithmetic on null Duration")
        if isinstance(other, CelProtobufDuration):
            if other._pb_value is None: raise TypeError("Cannot perform arithmetic with null Duration")
            # self + (-other) と同等
            neg_other_pb = PbDuration(seconds=-other._pb_value.seconds, nanos=-other._pb_value.nanos)
            # __add__ のロジックで Duration + Duration を処理
            temp_self_as_duration = CelProtobufDuration(self._pb_value)  # 一時オブジェクト
            temp_neg_other_as_duration = CelProtobufDuration(neg_other_pb)
            return temp_self_as_duration.__add__(temp_neg_other_as_duration)  # 正確にはPbレベルで計算すべき

        return super().__sub__(other)

    def __neg__(self) -> 'CelProtobufDuration':
        if self._pb_value is None: raise TypeError("Cannot negate null Duration")
        # PbDuration の seconds と nanos の両方の符号を反転させる
        neg_pb_duration = PbDuration(seconds=-self._pb_value.seconds, nanos=-self._pb_value.nanos)
        # コンストラクタでバリデーション（符号の一致など）が行われる
        return CelProtobufDuration(neg_pb_duration)

    # --- Duration アクセサメソッド (PbDuration から直接計算) ---
    def _get_total_nanos(self) -> int:
        if self._pb_value is None: raise TypeError("Cannot get total nanos from null Duration")
        # PbDuration は正規化されている前提 (sとnは同符号かn=0)
        return self._pb_value.seconds * _NANOS_PER_SECOND + self._pb_value.nanos

    def getHours(self) -> CelInt:
        return CelInt(self._get_total_nanos() // _NANOS_PER_HOUR)

    def getMinutes(self) -> CelInt:
        return CelInt((self._get_total_nanos() % _NANOS_PER_HOUR) // _NANOS_PER_MINUTE)

    def getSeconds(self) -> CelInt:
        return CelInt((self._get_total_nanos() % _NANOS_PER_MINUTE) // _NANOS_PER_SECOND)

    def getMilliseconds(self) -> CelInt:
        return CelInt((self._get_total_nanos() % _NANOS_PER_SECOND) // _NANOS_PER_MILLISECOND)


# --- Timestamp と Duration の加算ロジック (ヘルパー関数) ---
def cel_perform_timestamp_duration_add(
        ts_pb: PbTimestamp,
        dur_pb: PbDuration
) -> 'CelProtobufTimestamp':  # CelProtobufTimestamp を返すように変更
    """
    PbTimestamp と PbDuration をナノ秒精度で加算し、結果を新しい PbTimestamp として返す。
    結果はCELのタイムスタンプ範囲内でなければならない。
    """
    # Durationの正規化 (secondsとnanosが同符号、nanosが範囲内) はCelProtobufDurationコンストラクタで行われていると期待
    # ts_pbのnanosは [0, 999,999,999]

    res_s = ts_pb.seconds + dur_pb.seconds
    res_n = ts_pb.nanos + dur_pb.nanos

    # 結果のナノ秒を [0, 999,999,999] の範囲に正規化
    if res_n >= _NANOS_PER_SECOND:
        res_s += res_n // _NANOS_PER_SECOND
        res_n %= _NANOS_PER_SECOND
    elif res_n < 0:
        # 例: res_n = -1 => 1秒借りてきて res_n = 999,999,999 にする
        # borrow = math.floor(res_n / _NANOS_PER_SECOND) でも良いが、
        # res_n が (-1e9, 0) の場合、borrow = -1. res_s += -1. res_n -= -1 * 1e9.
        num_seconds_to_borrow = (-res_n + _NANOS_PER_SECOND - 1) // _NANOS_PER_SECOND  # 借りる秒数 (常に正)
        res_s -= num_seconds_to_borrow
        res_n += num_seconds_to_borrow * _NANOS_PER_SECOND

    result_pb_timestamp = PbTimestamp(seconds=res_s, nanos=res_n)
    _check_cel_timestamp_pb_range(result_pb_timestamp, "Timestamp + Duration operation")  # CEL範囲チェック

    return CelProtobufTimestamp(result_pb_timestamp)


# --- CelProtobufTimestamp クラスの実装 ---
class CelProtobufTimestamp(CelValue):
    _pb_value: Optional[PbTimestamp]

    def __init__(self, pb_timestamp_instance: Optional[PbTimestamp]):
        if pb_timestamp_instance is not None:
            if not isinstance(pb_timestamp_instance, PbTimestamp):
                raise TypeError(
                    f"CelProtobufTimestamp expects a google.protobuf.Timestamp instance or None, "
                    f"got {type(pb_timestamp_instance)}"
                )
            # コンストラクタでのCEL範囲チェックは _check_cel_timestamp_pb_range で行う
            _check_cel_timestamp_pb_range(pb_timestamp_instance, "CelProtobufTimestamp initialization")
        self._pb_value = pb_timestamp_instance

    @classmethod
    def from_datetime(cls, dt: Optional[datetime]) -> 'CelProtobufTimestamp':
        if dt is None: return cls(None)

        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            # Naive datetime はUTCとみなす (CELの一般的な慣習)
            dt = dt.replace(tzinfo=timezone.utc)

        aware_dt_utc = dt.astimezone(timezone.utc)  # 明示的にUTCに変換

        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        diff_from_epoch = aware_dt_utc - epoch

        # total_seconds() は float なので丸め誤差に注意が必要
        # より直接的な方法:
        seconds = diff_from_epoch.days * 86400 + diff_from_epoch.seconds
        nanos = diff_from_epoch.microseconds * 1000

        # PbTimestamp の nanos は [0, 999,999,999]
        # datetime からの変換では nanos は常に正。
        # diff_from_epoch.total_seconds() を使う場合はより慎重な丸めが必要。
        # total_seconds_float = diff_from_epoch.total_seconds()
        # seconds = math.floor(total_seconds_float)
        # nanos = int(round((total_seconds_float - seconds) * _NANOS_PER_SECOND))
        # if nanos == _NANOS_PER_SECOND: seconds += 1; nanos = 0
        # if nanos < 0: # Should not happen if total_seconds_float >=0 and datetime was after epoch
        #     # This indicates total_seconds_float was negative.
        #     # For negative timestamps from datetime, this logic needs to be more robust.
        #     # However, _check_cel_timestamp_pb_range will validate final PbTimestamp.
        #     pass # Should be handled by _check_cel_timestamp_pb_range on construction

        pb_timestamp = PbTimestamp(seconds=seconds, nanos=nanos)
        # コンストラクタで _check_cel_timestamp_pb_range が呼ばれる
        return cls(pb_timestamp)

    @property
    def value(self) -> Optional[datetime]:  # このプロパティは精度が落ちることに注意
        if self._pb_value is None: return None
        return _pb_timestamp_to_datetime_utc(self._pb_value)

    @property
    def cel_type(self) -> CelValue:
        return CEL_TIMESTAMP  # 実際のCelTypeオブジェクトを返す

    def __hash__(self):
        if self._pb_value is None: return hash(None)
        return hash((self._pb_value.seconds, self._pb_value.nanos))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, CelProtobufTimestamp):
            if self._pb_value is None: return other._pb_value is None
            if other._pb_value is None: return False
            return self._pb_value.seconds == other._pb_value.seconds and \
                self._pb_value.nanos == other._pb_value.nanos
        if self._pb_value is None and isinstance(other, CelNull): return True
        return False

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, CelProtobufTimestamp):
            if isinstance(other, CelNull): raise TypeError(f"Unsupported < between Timestamp and Null")
            raise TypeError(f"Unsupported < between Timestamp and {type(other).__name__}")
        if self._pb_value is None or other._pb_value is None:
            raise TypeError("Cannot compare None Timestamp values using '<'")
        s1, n1 = self._pb_value.seconds, self._pb_value.nanos
        s2, n2 = other._pb_value.seconds, other._pb_value.nanos
        if s1 != s2: return s1 < s2
        return n1 < n2

    def __repr__(self):
        if self._pb_value is None: return f"CelProtobufTimestamp(None)"
        return f"CelProtobufTimestamp(PbTimestamp(seconds={self._pb_value.seconds}, nanos={self._pb_value.nanos}))"

    # --- 算術演算子 (修正箇所) ---
    def __add__(self, other: Any) -> 'CelProtobufTimestamp':
        if self._pb_value is None: raise TypeError("Cannot perform arithmetic on null Timestamp")
        if isinstance(other, CelProtobufDuration):
            if other._pb_value is None: raise TypeError("Cannot perform arithmetic with null Duration")
            # ここで直接 PbTimestamp と PbDuration で計算するヘルパーを呼ぶ
            return cel_perform_timestamp_duration_add(self._pb_value, other._pb_value)
        return super().__add__(other)

    def __sub__(self, other: Any) -> CelValue:  # Timestamp または Duration を返す
        if self._pb_value is None: raise TypeError("Cannot perform arithmetic on null Timestamp")
        if isinstance(other, CelProtobufDuration):  # Timestamp - Duration => Timestamp
            if other._pb_value is None: raise TypeError("Cannot perform arithmetic with null Duration")
            # Timestamp + (-Duration) と同等
            neg_dur_pb = PbDuration(seconds=-other._pb_value.seconds, nanos=-other._pb_value.nanos)
            # CelProtobufDuration コンストラクタで Duration の正規化が行われると期待
            # ただし、PbDurationのnanosは負にもなりうるので、CelProtobufDurationのコンストラクタが
            # それを正しく処理するか、ここで正規化されたPbDurationを渡す必要がある。
            # ここでは単純に符号反転したものを渡す。
            return cel_perform_timestamp_duration_add(self._pb_value, neg_dur_pb)

        if isinstance(other, CelProtobufTimestamp):  # Timestamp - Timestamp => Duration
            if other._pb_value is None: raise TypeError("Cannot perform arithmetic with null Timestamp")

            s1, n1 = self._pb_value.seconds, self._pb_value.nanos
            s2, n2 = other._pb_value.seconds, other._pb_value.nanos

            res_s = s1 - s2
            res_n = n1 - n2

            # Duration の nanos の正規化 (-1e9 < n < 1e9, s と n は同符号)
            if res_n <= -_NANOS_PER_SECOND or res_n >= _NANOS_PER_SECOND:
                res_s += res_n // _NANOS_PER_SECOND
                res_n %= _NANOS_PER_SECOND

            if res_s > 0 and res_n < 0:
                res_s -= 1
                res_n += _NANOS_PER_SECOND
            elif res_s < 0 and res_n > 0:
                res_s += 1
                res_n -= _NANOS_PER_SECOND

            return CelProtobufDuration(PbDuration(seconds=res_s, nanos=res_n))
        return super().__sub__(other)

    # --- アクセサメソッド (タイムゾーン処理と精度) ---
    def _get_component(self, tz_cel: Optional[CelString], component_extractor: Callable[[datetime], int]) -> CelInt:
        if self._pb_value is None:
            raise TypeError("Cannot get component from null Timestamp")

        dt_obj_utc = _pb_timestamp_to_datetime_utc(self._pb_value)  # PbTimestampからdatetime(UTC)へ
        target_tz = _parse_timezone_string(tz_cel)
        dt_in_target_tz = dt_obj_utc.astimezone(target_tz)
        return CelInt(component_extractor(dt_in_target_tz))

    def getFullYear(self, tz_cel: Optional[CelString] = None) -> CelInt:
        return self._get_component(tz_cel, lambda dt: dt.year)

    def getMonth(self, tz_cel: Optional[CelString] = None) -> CelInt:  # CEL: 0 for January
        return self._get_component(tz_cel, lambda dt: dt.month - 1)

    def getDayOfMonth(self, tz_cel: Optional[CelString] = None) -> CelInt:  # CEL: 0-indexed
        return self._get_component(tz_cel, lambda dt: dt.day - 1)

    def getDate(self, tz_cel: Optional[CelString] = None) -> CelInt:  # おそらく1-indexed (ユーザー定義リストより)
        return self._get_component(tz_cel, lambda dt: dt.day)

    def getDayOfYear(self, tz_cel: Optional[CelString] = None) -> CelInt:  # CEL: 0-indexed
        return self._get_component(tz_cel, lambda dt: dt.timetuple().tm_yday - 1)

    def getDayOfWeek(self, tz_cel: Optional[CelString] = None) -> CelInt:  # CEL: 0 for Sunday
        return self._get_component(tz_cel, lambda dt: (dt.weekday() + 1) % 7)

    def getHours(self, tz_cel: Optional[CelString] = None) -> CelInt:
        return self._get_component(tz_cel, lambda dt: dt.hour)

    def getMinutes(self, tz_cel: Optional[CelString] = None) -> CelInt:
        return self._get_component(tz_cel, lambda dt: dt.minute)

    def getSeconds(self, tz_cel: Optional[CelString] = None) -> CelInt:
        return self._get_component(tz_cel, lambda dt: dt.second)

    def getMilliseconds(self, tz_cel: Optional[CelString] = None) -> CelInt:
        if self._pb_value is None: raise TypeError("Cannot get milliseconds from null Timestamp")
        # タイムゾーンに関わらず、Timestampのナノ秒部分からミリ秒を計算
        return CelInt(self._pb_value.nanos // _NANOS_PER_MILLISECOND)


class CelProtobufListValue(CelValue):
    """
    google.protobuf.ListValue をラップし、CELの list<Value> のように振る舞うクラス。
    各要素は google.protobuf.Value であり、CelProtobufValueでラップされて返される。
    """
    _pb_list_value: PbListValue
    _cached_cel_elements: Optional[List[CelProtobufValue]] = None  # キャッシュ用

    def __init__(self, pb_list_value_instance: PbListValue):
        if not isinstance(pb_list_value_instance, PbListValue):
            raise TypeError(
                f"CelProtobufListValue expects a google.protobuf.ListValue instance, "
                f"got {type(pb_list_value_instance)}"
            )
        self._pb_list_value = pb_list_value_instance

    def _get_elements_as_cel_values(self) -> List[CelProtobufValue]:
        """内部のPbValue要素をCelProtobufValueのリストとして取得（キャッシュ利用）"""
        if self._cached_cel_elements is None:
            # CelProtobufValue のインポートがここにあるのは循環参照を避けるための一時的な措置かもしれません。
            # 通常はモジュールトップレベルでインポートします。
            # from .well_known_types import CelProtobufValue # 必要に応じて調整
            self._cached_cel_elements = [CelProtobufValue(val) for val in self._pb_list_value.values]
        return self._cached_cel_elements

    @property
    def cel_type(self) -> CelType:
        """
        この値のCEL型 (list<google.protobuf.Value>) を返します。
        """
        return TYPE_PROTO_LIST_AS_LIST

    @property
    def value(self) -> PbListValue:
        """
        ラップしている google.protobuf.ListValue インスタンスを返します。
        主に unwrap_value で使用されます。
        """
        return self._pb_list_value

    def __getitem__(self, index: CelValue) -> CelValue:
        """
        リストのインデックスアクセス (list[index])。
        index は CelInt であることが期待されます。
        結果は CelProtobufValue (Valueのラッパー) として返されます。
        """
        if not isinstance(index, CelInt):
            raise TypeError(f"List index must be an integer, got {type(index).__name__}")

        py_index = index.value
        elements = self._get_elements_as_cel_values()
        try:
            return elements[py_index]
        except IndexError:
            raise RuntimeError(f"IndexError: list index {py_index} out of range for ListValue.")

    def __contains__(self, item: CelValue) -> bool:
        """
        要素の存在確認 (item in list)。
        item とリスト内の各要素 (CelProtobufValueから変換後) とを比較します。
        """
        # from ..eval_pb import _dynamic_convert_if_value # 評価器のヘルパーを使う場合
        # または、CelProtobufValueが比較演算子を適切に実装していることを期待する
        elements = self._get_elements_as_cel_values()
        for elem_pv in elements:
            # item は既に具体的な CelValue のはず。
            # elem_pv (CelProtobufValue) を具体的な型に変換してから比較
            # ここで _dynamic_convert_if_value を使うのは eval_pb への依存を生むため、
            # CelProtobufValue の __eq__ が CelValue との比較を正しく処理する前提とするか、
            # elem_pv を明示的に変換する。
            # ここでは、elem_pv を変換する。
            try:
                converted_elem = elem_pv._dynamic_convert()  # CelProtobufValue -> CelString, CelDouble etc.
                if item == converted_elem:
                    return True
            except NotImplementedError:  # struct/list はまだ変換できない
                pass  # 比較対象外としてスキップ
            except Exception:  # その他の変換エラー
                pass  # 比較対象外としてスキップ
        return False

    def __len__(self) -> int:
        """
        リストの要素数を返します (size(list) のため)。
        """
        return len(self._pb_list_value.values)

    def __add__(self, other: CelValue) -> CelList:
        """
        リストの結合 (list + other_list)。
        結果は新しい CelList (要素は CelProtobufValue)。
        """
        from .composites import CelList  # 循環参照回避

        elements = self._get_elements_as_cel_values()

        if isinstance(other, CelProtobufListValue):
            other_elements = other._get_elements_as_cel_values()
            return CelList(elements + other_elements)
        elif isinstance(other, CelList):
            # CelListの要素がCelProtobufValueであることを期待するか、型チェックが必要
            # ここでは、結合結果のリストはCelProtobufValueのリストとCelValueのリストの混合になるが、
            # CelListはCelValueを要素として許容するので問題ない。
            # 厳密には、CelListの要素もCelProtobufValueに変換すべきかもしれない。
            # 最小対応としては、CelList(elements + other.elements) とする。
            # ただし、CelListの要素は CelValue。
            # CelProtobufListValue の要素は CelProtobufValue なので、
            # 結合後のリストの要素型を list<Value> に保つなら、other.elements も Value にする必要がある。
            # ここでは、より一般的な CelList<Value | dyn> のようなイメージで結合する。
            # 仕様では list(A) + list(A) -> list(A) なので、要素型を合わせるのが理想。
            # ここでは、要素がCelValueであるCelListを返す。
            return CelList(elements + other.elements)

        raise TypeError(
            f"Operator '+' not supported between {self.cel_type.name} and {other.cel_type.name if isinstance(other, CelValue) else type(other).__name__}")

    def __eq__(self, other: Any) -> bool:
        """
        等価性比較。
        相手も CelProtobufListValue で、内部の PbListValue が等しいか (要素ごとに再帰的に比較)。
        または、CelList との比較も考慮。
        """
        if isinstance(other, CelProtobufListValue):
            # PbListValue 同士の比較は要素ごとのValue比較に依存
            # PbListValue には __eq__ があるのでそれに任せる
            return self._pb_list_value == other._pb_list_value
        elif isinstance(other, CelList):
            # CelProtobufListValue の各要素 (CelProtobufValue) を変換し、
            # CelList の各要素 (CelValue) と比較する
            if len(self) != len(other):
                return False

            self_elements_converted = []
            for pv_val in self._get_elements_as_cel_values():
                try:
                    self_elements_converted.append(pv_val._dynamic_convert())
                except NotImplementedError:
                    return False  # 変換できない要素があれば等しくない

            for i in range(len(self_elements_converted)):
                if self_elements_converted[i] != other.elements[i]:
                    return False
            return True

        return False

    def __lt__(self, other: Any) -> bool:
        # リストは通常、CELでは大小比較をサポートしません。
        raise TypeError(f"Operator '<' not supported on type {self.cel_type.name}")

    def __hash__(self):
        # google.protobuf.ListValue はミュータブルなコンテナなのでハッシュ化不可。
        raise TypeError(f"Object of type {self.cel_type.name} is not hashable.")

    def __repr__(self) -> str:
        return f"CelProtobufListValue(count={len(self._pb_list_value.values)}, pb_list_value={self._pb_list_value})"

    def __iter__(self) -> Iterator[CelProtobufValue]:
        """要素 (CelProtobufValue) のイテレータを返します。"""
        return iter(self._get_elements_as_cel_values())


class CelProtobufStruct(CelValue):
    """
    google.protobuf.Struct をラップし、CELの map<string, Value> のように振る舞うクラス。
    キーは文字列、値は google.protobuf.Value (CelProtobufValueでラップされる)。
    """
    _pb_struct: PbStruct

    def __init__(self, pb_struct_instance: PbStruct):
        if not isinstance(pb_struct_instance, PbStruct):
            raise TypeError(
                f"CelProtobufStruct expects a google.protobuf.Struct instance, "
                f"got {type(pb_struct_instance)}"
            )
        self._pb_struct = pb_struct_instance

    @property
    def cel_type(self) -> CelType:
        """
        この値のCEL型 (map<string, google.protobuf.Value>) を返します。
        """
        return TYPE_STRUCT_AS_MAP

    @property
    def value(self) -> PbStruct:
        """
        ラップしている google.protobuf.Struct インスタンスを返します。
        主に unwrap_value で使用されます。
        """
        return self._pb_struct

    def __getitem__(self, key: CelValue) -> CelValue:
        """
        マップのキーアクセス (struct['field_name'])。
        キーは CelString であることが期待されます。
        結果は CelProtobufValue (Valueのラッパー) として返されます。
        """
        if not isinstance(key, CelString):
            raise TypeError(f"Struct field access key must be a CelString, got {type(key).__name__}")

        field_name = key.value
        if field_name in self._pb_struct.fields:
            pb_value_field = self._pb_struct.fields[field_name]
            return CelProtobufValue(pb_value_field)  # PbValueをCelProtobufValueでラップ
        else:
            # CEL仕様: no_such_field エラーに相当する例外
            raise RuntimeError(f"KeyError: field '{field_name}' not found in struct.")

    def __contains__(self, key: CelValue) -> bool:
        """
        キーの存在確認 ('field_name' in struct)。
        キーは CelString であることが期待されます。
        """
        if not isinstance(key, CelString):
            # 不正なキー型の場合は False を返すのが、Pythonのdict.__contains__の挙動に近い
            return False
        return key.value in self._pb_struct.fields

    def __len__(self) -> int:
        """
        構造体のフィールド（キー）の数を返します (size(struct) のため)。
        """
        return len(self._pb_struct.fields)

    def __eq__(self, other: Any) -> bool:
        """
        等価性比較。
        相手も CelProtobufStruct で、内部の PbStruct が等しいかを見ます。
        """
        if not isinstance(other, CelProtobufStruct):
            # CELのマップとして比較する場合、相手がCelMapであるケースも将来的には考慮
            return False
        # google.protobuf.Struct 同士の比較は、Protobufライブラリの比較演算子に委ねる
        return self._pb_struct == other._pb_struct

    def __lt__(self, other: Any) -> bool:
        # マップや構造体は通常、CELでは大小比較をサポートしません。
        raise TypeError(f"Operator '<' not supported on type {self.cel_type.name}")

    def __hash__(self):
        # google.protobuf.Struct はミュータブルなフィールド (fields) を持つため、
        # Pythonのdictと同様に、通常はハッシュ化不可です。
        raise TypeError(f"Object of type {self.cel_type.name} is not hashable.")

    def __repr__(self) -> str:
        # フィールドが多いと長くなるため、フィールド数のみ表示するなどの簡略表現も可
        # ここでは PbStruct の標準 repr を利用
        return f"CelProtobufStruct(pb_struct={self._pb_struct})"

    # --- オプション: より完全なマップインターフェースのためのメソッド ---

    def get(self, key: CelValue, default: Optional[CelValue] = None) -> CelValue:
        """
        キーに対応する値 (CelProtobufValue) を取得します。
        キーが存在しない場合は default (指定がなければ CelNull()) を返します。
        キーは CelString であることが期待されます。
        """
        if not isinstance(key, CelString):
            return default if default is not None else CelNull()

        field_name = key.value
        if field_name in self._pb_struct.fields:
            pb_value_field = self._pb_struct.fields[field_name]
            return CelProtobufValue(pb_value_field)

        return default if default is not None else CelNull()

    def keys(self) -> CelList:
        """マップのキーのリスト (CelList of CelString) を返します。"""
        from .composites import CelList  # 循環参照を避けるため、使用箇所でインポート
        return CelList([CelString(key_str) for key_str in self._pb_struct.fields.keys()])

    def items(self) -> Iterator[Tuple[CelString, CelProtobufValue]]:
        """(キー, 値) のタプルのイテレータを返します。キーはCelString、値はCelProtobufValue。"""
        for key_str, pb_value in self._pb_struct.fields.items():
            yield (CelString(key_str), CelProtobufValue(pb_value))

    # values() メソッドも必要に応じて追加可能
    # def values(self) -> CelList:
    #     from .composites import CelList
    #     return CelList([CelProtobufValue(pb_value) for pb_value in self._pb_struct.fields.values()])


class CelWrappedProtoMessage(CelValue):
    # ... (__init__, cel_type, __lt__, __hash__, __repr__ は前回の提案通りと仮定) ...
    def __init__(self, pb_message: Message):
        if not isinstance(pb_message, Message):
            raise TypeError("CelWrappedProtoMessage expects a ProtobufMessage instance.")
        self.pb_message = pb_message
        self._cel_type_instance: Optional[CelType] = None
        # self._differencer = None # MessageDifferencer を使う場合

    @property
    def cel_type(self) -> CelType:
        if self._cel_type_instance is None:
            type_name = self.pb_message.DESCRIPTOR.full_name
            resolved_type = CelType.get_by_name(type_name)
            self._cel_type_instance = resolved_type if resolved_type else CEL_DYN
        return self._cel_type_instance

    def _unpack_any_for_comparison(self, any_msg_value: Message) -> tuple[Optional[Message], bool]:
        # 渡されたオブジェクトが本当に any_pb2.Any のインスタンスか、再度確認
        if not isinstance(any_msg_value, PbAny):
            #print(f"DEBUG UNPACK: _unpack_any_for_comparison received non-Any type: {type(any_msg_value)}")
            return None, False

            # ここでは any_msg_value は any_pb2.Any インスタンスであると期待される
        # any_pb2.Any 型のオブジェクトであることを確認するために、再度インポートした型と比較
        from google.protobuf.any_pb2 import Any as CanonicalAny
        if not isinstance(any_msg_value, CanonicalAny):
            #print(
            #    f"DEBUG UNPACK: any_msg_value (type: {type(any_msg_value)}) is not an instance of the directly imported CanonicalAny (type: {CanonicalAny}). Type identity issue?")
            return None, False

        type_url = any_msg_value.TypeName()
        # print(f"DEBUG UNPACK: Any type_url: '{type_url}'")
        if not type_url:
            # print("DEBUG UNPACK: Type URL is empty.")
            return None, False

        type_name_from_url = type_url.split('/')[-1]
        if not type_name_from_url:
            # print(f"DEBUG UNPACK: Could not extract type name from type_url: {type_url}")
            return None, False
        # print(f"DEBUG UNPACK: Resolved type_name_from_url: {type_name_from_url}")

        pool = descriptor_pool.Default()
        try:
            msg_descriptor = pool.FindMessageTypeByName(type_name_from_url)
            target_message_class = message_factory.GetMessageClass(msg_descriptor)
        except KeyError:
            # print(f"DEBUG UNPACK: KeyError: Message descriptor for '{type_name_from_url}' not found in default pool.")
            return None, False
        except Exception as e:
            # print(f"DEBUG UNPACK: Exception finding descriptor or class for '{type_name_from_url}': {type(e).__name__}: {e}")
            return None, False

        if not target_message_class:
            # print(f"DEBUG UNPACK: Target_message_class is None for {type_name_from_url}.")
            return None, False

        unpacked_msg = target_message_class()
        try:
            if not any_msg_value.Is(msg_descriptor):
                # print(f"DEBUG UNPACK: Any.Is({msg_descriptor.full_name}) returned False for type_url '{type_url}'. Type mismatch.")
                return None, False

            # UnpackInto の存在確認と呼び出し
            if not hasattr(any_msg_value, 'UnpackInto'):
                #print(f"CRITICAL DEBUG: any_msg_value (type: {type(any_msg_value)}) DOES NOT HAVE 'UnpackInto' method.")
                #print(f"DEBUG UNPACK: Attributes of any_msg_value: {dir(any_msg_value)}")
                # フォールバックとして ParseFromString を試みる (非推奨だが最終手段)
                #print(f"DEBUG UNPACK: Attempting fallback to ParseFromString for {type_name_from_url}")
                try:
                    unpacked_msg.ParseFromString(any_msg_value.value)  # .value でバイト列を取得
                    #print(f"DEBUG UNPACK: ParseFromString for {type_name_from_url} SUCCEEDED.")
                    return unpacked_msg, True
                except Exception as e_parse:
                    #print(
                    #    f"DEBUG UNPACK: Exception during ParseFromString fallback for '{type_name_from_url}': {type(e_parse).__name__}: {e_parse}")
                    return None, False

            # 通常の UnpackInto 呼び出し
            # print(f"DEBUG UNPACK: Attempting UnpackInto for {type_name_from_url} into instance of {type(unpacked_msg)}")
            any_msg_value.UnpackInto(unpacked_msg)
            # print(f"DEBUG UNPACK: UnpackInto for {type_name_from_url} SUCCEEDED.")
            return unpacked_msg, True

        except DecodeError as de:
            # print(f"DEBUG UNPACK: DecodeError during Any.UnpackInto for '{type_name_from_url}': {de}")
            # print(f"DEBUG UNPACK: Failing Any value bytes: {any_msg_value.value!r}")
            return None, False
        except AttributeError as ae:  # UnpackInto が存在しない場合 (上記 hasattr で捕捉されるはずだが念のため)
            #print(f"DEBUG UNPACK: AttributeError during Any.UnpackInto for '{type_name_from_url}': {ae}")
            #print(traceback.format_exc())
            return None, False
        except Exception as e:
            # print(f"DEBUG UNPACK: Generic exception during Any.UnpackInto for '{type_name_from_url}': {type(e).__name__}: {e}")
            # print(traceback.format_exc())
            return None, False

    def _compare_repeated_field_cel_semantics(self, field_desc: FieldDescriptor, list1, list2) -> bool:
        if len(list1) != len(list2): return False
        for item1, item2 in zip(list1, list2):
            if field_desc.type in [FieldDescriptor.TYPE_FLOAT, FieldDescriptor.TYPE_DOUBLE]:
                if math.isnan(item1) and math.isnan(item2): return False
                if math.isnan(item1) or math.isnan(item2): return False
                if item1 != item2: return False
            elif field_desc.type == FieldDescriptor.TYPE_MESSAGE:
                if field_desc.message_type.full_name == "google.protobuf.Any":
                    unpacked1, success1 = self._unpack_any_for_comparison(item1)  # self. を使用
                    unpacked2, success2 = self._unpack_any_for_comparison(item2)  # self. を使用
                    if success1 and success2:
                        if unpacked1 is None or unpacked2 is None: return False
                        if unpacked1.DESCRIPTOR != unpacked2.DESCRIPTOR: return False
                        if not self._compare_proto_messages_cel_semantics(unpacked1, unpacked2): return False
                    elif not success1 and not success2:
                        if item1.TypeName() != item2.TypeName() or item1.value != item2.value: return False
                    else:
                        return False
                elif not self._compare_proto_messages_cel_semantics(item1, item2):
                    return False
            else:
                if item1 != item2: return False
        return True

    def _compare_proto_messages_cel_semantics(self, msg1: Message, msg2: Message) -> bool:
        if msg1.DESCRIPTOR != msg2.DESCRIPTOR: return False

        for oneof_desc in msg1.DESCRIPTOR.oneofs:
            if msg1.WhichOneof(oneof_desc.name) != msg2.WhichOneof(oneof_desc.name):
                return False

        for field_desc in msg1.DESCRIPTOR.fields:
            name = field_desc.name
            is_present1 = msg1.HasField(name) if field_desc.has_presence else True
            is_present2 = msg2.HasField(name) if field_desc.has_presence else True

            if field_desc.label == FieldDescriptor.LABEL_REPEATED:
                if not self._compare_repeated_field_cel_semantics(field_desc, getattr(msg1, name), getattr(msg2, name)):
                    return False
                continue

            if is_present1 != is_present2: return False
            if is_present1:
                val1 = getattr(msg1, name)
                val2 = getattr(msg2, name)
                if field_desc.type in [FieldDescriptor.TYPE_FLOAT, FieldDescriptor.TYPE_DOUBLE]:
                    if math.isnan(val1) and math.isnan(val2): return False
                    if math.isnan(val1) or math.isnan(val2): return False
                    if val1 != val2: return False
                elif field_desc.type == FieldDescriptor.TYPE_MESSAGE:
                    if field_desc.message_type.full_name == "google.protobuf.Any":
                        unpacked1, success1 = self._unpack_any_for_comparison(val1)  # self. を使用
                        unpacked2, success2 = self._unpack_any_for_comparison(val2)  # self. を使用
                        if success1 and success2:
                            if unpacked1 is None or unpacked2 is None: return False
                            if unpacked1.DESCRIPTOR != unpacked2.DESCRIPTOR: return False
                            if not self._compare_proto_messages_cel_semantics(unpacked1, unpacked2): return False
                        elif not success1 and not success2:
                            if val1.TypeName() != val2.TypeName() or val1.value != val2.value: return False
                        else:
                            return False
                    elif not self._compare_proto_messages_cel_semantics(val1, val2):
                        return False
                elif val1 != val2:
                    return False
        return True

    def __eq__(self, other: Any) -> bool:
        if self is other: return True
        if not isinstance(other, CelWrappedProtoMessage):
            if isinstance(other, CelNull): return False
            if isinstance(other, Message) and \
                    hasattr(self.pb_message, 'DESCRIPTOR') and \
                    hasattr(other, 'DESCRIPTOR') and \
                    self.pb_message.DESCRIPTOR == other.DESCRIPTOR:
                return self._compare_proto_messages_cel_semantics(self.pb_message, other)
            return NotImplemented

        if self.pb_message.DESCRIPTOR != other.pb_message.DESCRIPTOR: return False
        return self._compare_proto_messages_cel_semantics(self.pb_message, other.pb_message)

    # ... (__lt__, __hash__, __repr__) ...
    def __lt__(self, other: Any) -> bool:
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        raise TypeError(f"Operator '<' not supported between {self.cel_type.name} and {other_type_name}")

    def __hash__(self):
        raise TypeError(f"Object of type {self.cel_type.name} is not hashable.")

    def __repr__(self):
        type_url_str = ""
        if isinstance(self.pb_message, PbAny):
            type_url_str = f", type_url='{self.pb_message.TypeName()}'"
        return f"CelWrappedProtoMessage({self.pb_message.DESCRIPTOR.name}{type_url_str})"


class CelProtobufFloatValue(CelValue):
    _pb_value: Optional[FloatValue]

    def __init__(self, pb_value_instance: Optional[FloatValue]):
        if pb_value_instance is not None and not isinstance(pb_value_instance, FloatValue):
            raise TypeError(
                f"CelProtobufFloatValue expects a google.protobuf.FloatValue instance or None, "
                f"got {type(pb_value_instance)}"
            )
        self._pb_value = pb_value_instance

    @classmethod
    def from_float(cls, value: Optional[float]) -> 'CelProtobufFloatValue':
        if value is None:
            return cls(None)
        # Pythonのfloatは通常double精度だが、FloatValueはfloat32を想定。
        # Protobufライブラリがよしなに変換してくれる。
        return cls(FloatValue(value=value))

    @property
    def value(self) -> Optional[float]:
        if self._pb_value is not None:
            return self._pb_value.value
        return None

    @property
    def cel_type(self) -> 'CelType':  # CelTypeは前方参照
        return CEL_FLOAT_WRAPPER

    def __eq__(self, other: Any) -> bool:
        # print(f"DEBUG: CelProtobufFloatValue.__eq__ called. self.value={self.value}, other type={type(other)}")
        if self is other:
            return True

        # Step 1: 比較対象 `other` が CelDynValue ならアンラップする
        other_for_comparison = other
        if isinstance(other, CelDynValue):  # CelDynValue は新設したクラス
            other_for_comparison = other.wrapped_value

        # Step 2: self の Python プリミティブ値を取得
        self_py_val = self.value  # self.value は float または None

        # Step 3: self が null または NaN の場合の処理
        if self_py_val is None:  # self (FloatValue) が null (値が設定されていない)
            if isinstance(other_for_comparison, CelNull):
                return True
            if hasattr(other_for_comparison, 'value') and other_for_comparison.value is None:
                if isinstance(other_for_comparison, (  # 数値型ラッパーのnull状態も考慮
                        CelProtobufInt32Value, CelProtobufUInt32Value, CelProtobufInt64Value, CelProtobufUInt64Value,
                        CelProtobufFloatValue, CelProtobufDoubleValue,
                        CelInt, CelUInt, CelDouble
                )):
                    return True
            return False

        if math.isnan(self_py_val):  # self が NaN の場合、何とも等しくない (CELの仕様)
            return False

        # Step 4: Self が有効な float 値を持つ場合。 other_for_comparison と比較。
        other_py_val: Any = None
        is_other_numeric = False

        if isinstance(other_for_comparison, (CelInt, CelUInt)):
            other_py_val = other_for_comparison.value  # int
            is_other_numeric = True if other_py_val is not None else False
        elif isinstance(other_for_comparison,
                        (CelDouble, CelProtobufFloatValue, CelProtobufDoubleValue)):  # CelProtobufFloatValue を追加
            other_py_val = other_for_comparison.value  # float
            is_other_numeric = True if other_py_val is not None else False
        elif isinstance(other_for_comparison, (  # 整数ラッパー型を追加
                CelProtobufInt32Value, CelProtobufUInt32Value,
                CelProtobufInt64Value, CelProtobufUInt64Value  # ★テストケースの型(Int64Value)
        )):
            other_py_val = other_for_comparison.value  # int
            is_other_numeric = True if other_py_val is not None else False
        # else: other_for_comparison は CelNull か、または数値型ではない

        if is_other_numeric:
            if other_py_val is None:  # self は非null/非NaN、other は数値ラッパーだが実質null
                return False

            if isinstance(other_py_val, float) and math.isnan(other_py_val):
                return False  # float == NaN は False

            # self_py_val (float) と other_py_val (int or float) の数値比較
            # Python の == は float と int を数値として正しく比較する (例: 3.0 == 3 は True)
            try:
                # print(f"DEBUG: Numeric comparison (FloatValue): {self_py_val} ({type(self_py_val)}) == {other_py_val} ({type(other_py_val)})")
                return self_py_val == other_py_val
            except TypeError:
                return False

                # other_for_comparison が数値として解釈できなかった場合 (CelNull は is_other_numeric = False)
        # self は数値なので、CelNull や他の非数値型とは等しくない
        return False

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        if self._pb_value is None:
            return f"{self.cel_type.name}(None)"
        return f"{self.cel_type.name}(value={self.value})"

    # 必要に応じて算術演算子も定義 (通常は CelDouble に昇格して演算)
    def __add__(self, other: Any) -> 'CelDouble':
        if self.value is None: raise TypeError("Cannot perform arithmetic on null FloatValue")
        # ... (CelProtobufDoubleValue の __add__ に似た実装) ...
        # 例:
        other_val_py = None
        if isinstance(other, (CelDouble, CelProtobufDoubleValue, CelProtobufFloatValue, CelInt, CelUInt)):
            other_val_py = getattr(other, 'value', None)

        if other_val_py is None and not isinstance(other, CelNull):  # CelNull以外でvalueが取れないケース
            raise TypeError(f"Unsupported operand type for + with {self.cel_type.name}: {type(other)}")
        if other_val_py is None and isinstance(other, CelNull):  # nullとの演算
            raise TypeError(f"Cannot add {self.cel_type.name} and null")

        return CelDouble(self.value + float(other_val_py))  # 結果はCelDouble

    # 他の算術演算子 (- * /) も同様に CelDouble を返すように実装可能
    def __lt__(self, other: Any) -> bool:  # 順序比較
        if self.value is None or math.isnan(self.value): return False  # nullやNaNは比較でエラーかfalse

        other_py_float_val: Optional[float] = None
        if isinstance(other, (CelDouble, CelProtobufDoubleValue, CelProtobufFloatValue)):
            other_py_float_val = other.value
            if other_py_float_val is None or math.isnan(other_py_float_val): return False
        elif isinstance(other, (CelInt, CelUInt)):
            other_py_float_val = float(other.value)
        elif isinstance(other, CelNull):
            raise TypeError(f"Cannot compare {self.cel_type.name} with null using '<'")
        else:
            raise TypeError(
                f"Unsupported comparison between {self.cel_type.name} and {type(other).__name__ if not isinstance(other, CelValue) else other.cel_type.name}")

        return self.value < other_py_float_val


class CelProtobufAny(CelValue):
    _pb_any: Any  # google.protobuf.Any のインスタンス

    # TypeRegistryへのアクセスが必要になるため、コンストラクタで受け取るか、
    # グローバルなものを使うか設計が必要。ここではグローバルプールを使うヘルパーを想定。

    def __init__(self, pb_any_instance: PbAny):
        if not isinstance(pb_any_instance, PbAny):
            raise TypeError("CelProtobufAny expects a google.protobuf.Any instance.")
        self._pb_any = pb_any_instance
        self._type_registry_accessor = None  # 遅延初期化または外部から設定

    # TypeRegistryへのアクセサを設定するメソッド (オプション)
    def set_type_registry_accessor(self, accessor: callable):
        # accessor は (type_name: str) -> Optional[Type[ProtobufMessage]] のような関数を期待
        self._type_registry_accessor = accessor

    @property
    def cel_type(self) -> 'CelType':
        return CEL_ANY

    def _unpack(self) -> tuple[Optional[Message], bool]:
        """
        Anyメッセージをアンパック試行。成功なら (unpacked_message, True)。
        TypeRegistryへのアクセス方法に依存する。
        """
        type_url = self._pb_any.TypeName()
        if not type_url: return None, False

        type_name = type_url.split('/')[-1]
        if not type_name: return None, False

        # TypeRegistry経由でのクラス取得を試みる (理想的だが依存関係が複雑になる)
        # if self._type_registry_accessor:
        #     target_message_class = self._type_registry_accessor(type_name)
        # else:
        #     # フォールバックとしてグローバルプールとファクトリを使用
        pool = descriptor_pool.Default()
        try:
            msg_descriptor = pool.FindMessageTypeByName(type_name)
            target_message_class = message_factory.GetMessageClass(msg_descriptor)
        except KeyError:
            # print(f"DEBUG: Descriptor for '{type_name}' not found in pool for Any unpacking.")
            return None, False
        except Exception:  # GetMessageClassが他のエラーを出す可能性
            return None, False

        if not target_message_class:
            return None, False

        try:
            unpacked_msg = target_message_class()
            if self._pb_any.UnpackTo(unpacked_msg):  # Python は UnpackInto
                return unpacked_msg, True
            else:
                return None, False
        except Exception:
            return None, False

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CelProtobufAny):
            if isinstance(other, CelNull): return False
            return NotImplemented

        # 両方とも CelProtobufAny の場合
        unpacked_self, success_self = self._unpack()
        unpacked_other, success_other = other._unpack()

        if success_self and success_other:  # 両方アンパック成功
            if unpacked_self is None or unpacked_other is None: return False  # defensive

            # アンパック後の型が同じか確認
            if unpacked_self.DESCRIPTOR != unpacked_other.DESCRIPTOR:
                return False

            # アンパックされたメッセージ同士を比較 (CelWrappedProtoMessageの比較ロジックを再利用または共通化)
            # ここで CelWrappedProtoMessage を使うと循環依存になる可能性があるため注意。
            # _compare_proto_messages_cel_semantics のような共通ヘルパーが必要になる。
            # 仮に、生のProtobufメッセージ比較関数 _compare_raw_protos を使うとする
            return _compare_raw_protos_cel_semantics(unpacked_self, unpacked_other)

        elif not success_self and not success_other:  # 両方アンパック失敗
            # Anyメッセージ自体をバイト比較 (type_url と value)
            return self._pb_any.TypeName() == other._pb_any.TypeName() and \
                self._pb_any.value == other._pb_any.value
        else:  # 片方だけアンパック成功
            return False

    def __lt__(self, other: Any) -> bool:
        # google.protobuf.Any はCELでは直接的な順序比較をサポートしない
        other_type_name = other.cel_type.name if isinstance(other, CelValue) else type(other).__name__
        raise TypeError(f"Operator '<' not supported between {self.cel_type.name} and {other_type_name}")


    def __hash__(self):
        # google.protobuf.Any はミュータブルであり、内容によって等価性が変わるため、
        # 通常はハッシュ化不可能とするのが安全。
        raise TypeError(f"Object of type {self.cel_type.name} is not hashable.")

    def __repr__(self):
        return f"CelProtobufAny(type_url='{self._pb_any.TypeName()}', has_value={self._pb_any.ByteSize() > len(self._pb_any.TypeName()) + 2})" # ByteSizeでvalueの存在を推測


    # ... 他のメソッド ...


# _compare_raw_protos_cel_semantics は CelWrappedProtoMessage._compare_proto_messages_cel_semantics
# と同様のロジックを持つヘルパー関数。Anyのアンパック部分を除いて共通化できる。
# この関数は CelProtobufAny の外部か、共通のユーティリティモジュールに配置する。
def _compare_raw_protos_cel_semantics(msg1: Message, msg2: Message,
                                      any_unpacker: Optional[callable] = None) -> bool:
    if msg1.DESCRIPTOR != msg2.DESCRIPTOR: return False  # 基本的な型チェック

    for field_desc in msg1.DESCRIPTOR.fields:
        name = field_desc.name
        is_present1 = msg1.HasField(name) if field_desc.has_presence else True
        is_present2 = msg2.HasField(name) if field_desc.has_presence else True

        if field_desc.label == FieldDescriptor.LABEL_REPEATED:
            # ... (繰り返しフィールドの比較、要素がAnyならany_unpackerで再帰) ...
            list1, list2 = getattr(msg1, name), getattr(msg2, name)
            if len(list1) != len(list2): return False
            for item1, item2 in zip(list1, list2):
                if field_desc.type == FieldDescriptor.TYPE_MESSAGE:
                    if field_desc.message_type.full_name == "google.protobuf.Any" and any_unpacker:
                        # any_unpacker は (AnyMsg) -> (UnpackedMsg | None, success: bool) を返す
                        u1, s1 = any_unpacker(item1)
                        u2, s2 = any_unpacker(item2)
                        if s1 and s2:
                            if not _compare_raw_protos_cel_semantics(u1, u2, any_unpacker): return False
                        elif not s1 and not s2:
                            if item1.TypeName() != item2.TypeName() or item1.value != item2.value: return False
                        else:
                            return False
                    elif not _compare_raw_protos_cel_semantics(item1, item2, any_unpacker):
                        return False
                elif field_desc.type in [FieldDescriptor.TYPE_FLOAT, FieldDescriptor.TYPE_DOUBLE]:
                    if math.isnan(item1) and math.isnan(item2): return False
                    if math.isnan(item1) or math.isnan(item2): return False
                    if item1 != item2: return False
                elif item1 != item2:
                    return False
            continue

        if is_present1 != is_present2: return False
        if is_present1:
            val1, val2 = getattr(msg1, name), getattr(msg2, name)
            if field_desc.type in [FieldDescriptor.TYPE_FLOAT, FieldDescriptor.TYPE_DOUBLE]:
                if math.isnan(val1) and math.isnan(val2): return False
                if math.isnan(val1) or math.isnan(val2): return False
                if val1 != val2: return False
            elif field_desc.type == FieldDescriptor.TYPE_MESSAGE:
                if field_desc.message_type.full_name == "google.protobuf.Any" and any_unpacker:
                    u1, s1 = any_unpacker(val1)
                    u2, s2 = any_unpacker(val2)
                    if s1 and s2:
                        if not _compare_raw_protos_cel_semantics(u1, u2, any_unpacker): return False
                    elif not s1 and not s2:
                        if val1.TypeName() != val2.TypeName() or val1.value != val2.value: return False
                    else:
                        return False
                elif not _compare_raw_protos_cel_semantics(val1, val2, any_unpacker):
                    return False
            elif val1 != val2:
                return False
    return True
