# cel_types.py
from datetime import timedelta
# import re2 # 標準の re を使用する想定
import re
from typing import Dict, Optional, List, Callable, Any, Tuple, Type  # Type をインポート

from google.protobuf.struct_pb2 import NullValue, ListValue, Value, Struct
from google.protobuf.wrappers_pb2 import (
    Int32Value,
    UInt32Value,
    Int64Value,
    UInt64Value,
    BoolValue,
    DoubleValue,
    StringValue,
    BytesValue,
    FloatValue)

from google.protobuf.duration_pb2 import Duration as ProtobufDuration
from google.protobuf.timestamp_pb2 import Timestamp as ProtobufTimestamp
from google.protobuf.any_pb2 import Any

from mimicel.cel_values import CelValue

_THE_CEL_TYPE_INSTANCE: Optional['CelType'] = None


# --- CEL 型定義 --- #
class CelType(CelValue):  # ★ CelValue を継承
    _registry: Dict[str, 'CelType'] = {}
    _next_id_counter = 0

    # クラス変数として、型「type」を表すCelTypeインスタンスを保持
    # この変数は、CEL_TYPE定数が定義された後に設定される
    _the_type_of_types: Optional['CelType'] = None

    @classmethod
    def _generate_id(cls) -> int:
        # より衝突しにくいID生成方法を検討 (例: UUIDや登録順の連番)
        # ここではシンプルなカウンターを維持
        current_id = cls._next_id_counter
        cls._next_id_counter += 1
        return current_id

    def __init__(self, name: str, id_: int):
        self.name = name
        self.id = id_

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.name}')"

    def __eq__(self, other: Any) -> bool:

        if not isinstance(other, CelType):
            return False

        # ParameterizedCelType は独自の __eq__ を持つべき
        if isinstance(self, ParameterizedCelType) and isinstance(other, ParameterizedCelType):
            return self.name == other.name and self.base_type == other.base_type and self.params == other.params
        if isinstance(self, ParameterizedCelType) or isinstance(other, ParameterizedCelType):
            return False # Parameterized と 非Parameterized は異なる

        return self.name == other.name # 基本型やメッセージ型は名前で比較


    def __hash__(self):
        # ParameterizedCelType は独自の __hash__ を持つべき
        if isinstance(self, ParameterizedCelType):
            return hash((self.name, self.base_type, self.params, self.__class__.__name__))
        return hash((self.name, self.__class__.__name__)) # IDではなくクラス名を含めることで型の一意性を高める

    @property
    def cel_type(self) -> 'CelType':  # 型ヒントは前方参照として 'CelType'
        """型を表す値 (例: int型) の型は、グローバルな「type」型です。"""
        if CelType._the_type_of_types is None:
            # このエラーは、モジュールの初期化が完全に終わる前にアクセスされたか、
            # _the_type_of_types の設定が適切に行われなかったことを示す。
            # CEL_TYPE自身の.cel_type呼び出しは、下のCEL_TYPE定義後の代入で解決される。
            # ただし、万が一、CEL_TYPEが自身のcel_typeを解決しようとする非常に初期の段階では、
            # selfがCEL_TYPE自身である場合の特別扱いが必要かもしれない。
            if self.name == "type":  # もしselfがまさにCEL_TYPEオブジェクト自身なら
                return self  # typeの型はtype
            raise RuntimeError(
                "The _the_type_of_types (representing CEL_TYPE) has not been initialized in CelType."
            )
        return CelType._the_type_of_types

    def __lt__(self, other: Any) -> bool:
        other_display_name = getattr(other, 'name', type(other).__name__)
        if isinstance(other, CelValue) and hasattr(other, 'cel_type'):
            cel_type_prop = getattr(other, 'cel_type')
            if isinstance(cel_type_prop, CelType):  # cel_typeプロパティがCelTypeインスタンスを返す場合
                other_display_name = cel_type_prop.name
        raise TypeError(f"Operator '<' not supported between type value '{self.name}' and '{other_display_name}'")

    @classmethod
    def _register_instance(cls, instance: 'CelType'):
        if instance.name in cls._registry and cls._registry[instance.name].id != instance.id:
            raise ValueError(f"CelType name '{instance.name}' already registered with a different ID.")
        cls._registry[instance.name] = instance

    @classmethod
    def get_by_name(cls, name: str) -> Optional['CelType']:
        return cls._registry.get(name)

    @classmethod
    def get_or_register_type_instance(cls, name: str, type_class: Type['CelType'], *args, **kwargs) -> 'CelType':
        existing_instance = cls.get_by_name(name)
        if existing_instance:
            # 既に登録されているインスタンスの型が要求された型と一致するか確認
            if not isinstance(existing_instance, type_class):
                # 特に ParameterizedCelType と CelType の間で衝突が起きないように
                if not (issubclass(type(existing_instance), type_class) or issubclass(type_class,
                                                                                      type(existing_instance))):
                    raise TypeError(
                        f"Type name '{name}' already registered with a different incompatible class "
                        f"({type(existing_instance).__name__} vs {type_class.__name__}).")
            # ParameterizedCelType の場合、パラメータも一致するか確認 (これは make_... 関数で行う)
            return existing_instance

        # 新しいIDを生成 (既存のIDと衝突しないように)
        new_id = cls._generate_id()
        while any(t.id == new_id for t in cls._registry.values()):
            new_id = cls._generate_id()

        instance = type_class(name, new_id, *args, **kwargs)
        cls._register_instance(instance)
        return instance


# --- 既知の型登録 (get_or_register_type_instance を使用) ---
CEL_INT = CelType.get_or_register_type_instance("int", CelType)
CEL_UINT = CelType.get_or_register_type_instance("uint", CelType)
CEL_STRING = CelType.get_or_register_type_instance("string", CelType)
CEL_BOOL = CelType.get_or_register_type_instance("bool", CelType)
CEL_STRUCT = CelType.get_or_register_type_instance("struct", CelType)
CEL_NULL = CelType.get_or_register_type_instance("null_type", CelType)
CEL_FLOAT = CelType.get_or_register_type_instance("float", CelType)
CEL_DOUBLE = CelType.get_or_register_type_instance("double", CelType)
CEL_BYTES = CelType.get_or_register_type_instance("bytes", CelType)
CEL_TYPE = CelType.get_or_register_type_instance("type", CelType)
CEL_UNKNOWN = CelType.get_or_register_type_instance("unknown", CelType)
CEL_DYN = CelType.get_or_register_type_instance("dyn", CelType)

_LIST_BASE_TYPE = CelType.get_or_register_type_instance("list_base_internal", CelType)
_MAP_BASE_TYPE = CelType.get_or_register_type_instance("map_base_internal", CelType)

CEL_LIST = CelType.get_or_register_type_instance("list", CelType)  # パラメータなしlist
CEL_MAP = CelType.get_or_register_type_instance("map", CelType)  # パラメータなしmap

# CEL_TYPE (型自身の型) の定義
CEL_TYPE = CelType.get_or_register_type_instance("type", CelType)
# CelTypeクラスが持つ「型の型」の参照を、今定義したCEL_TYPEインスタンスに設定

CEL_ERROR = CelType.get_or_register_type_instance("error", CelType)

CelType._the_type_of_types = CEL_TYPE

class CelMessageType(CelType):
    """ Protobufメッセージ型を表すCEL型。 """

    def __init__(self, name: str, id_: int, python_type: Optional[Type] = None):
        super().__init__(name, id_)
        self.python_type = python_type  # 対応するPython Protobufクラス (オプショナル)

    # __eq__ と __hash__ は CelType のものを継承（名前とIDで比較）
    # メッセージ型は名前で実質的に一意なので、CelTypeの比較で十分。

CEL_DURATION = CelType.get_or_register_type_instance(
    "google.protobuf.Duration",
    CelMessageType,
    python_type=ProtobufDuration
)
CEL_TIMESTAMP = CelType.get_or_register_type_instance(
    "google.protobuf.Timestamp",
    CelMessageType,
    python_type=ProtobufTimestamp
)


CEL_INT32_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.Int32Value",
    CelMessageType,
    python_type=Int32Value
)
CEL_UINT32_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.UInt32Value",
    CelMessageType,
    python_type=UInt32Value
)
CEL_INT64_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.Int64Value",
    CelMessageType,
    python_type=Int64Value
)
CEL_UINT64_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.UInt64Value",
    CelMessageType,
    python_type=UInt64Value
)
CEL_BOOL_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.BoolValue",
    CelMessageType,
    python_type=BoolValue
)
CEL_FLOAT_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.FloatValue",
    CelMessageType,
    python_type=FloatValue
)
CEL_DOUBLE_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.DoubleValue",
    CelMessageType,
    python_type=DoubleValue
)
CEL_STRING_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.StringValue",
    CelMessageType,
    python_type=StringValue
)
CEL_BYTES_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.BytesValue",
    CelMessageType,
    python_type=BytesValue
)
CEL_NULL_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.NullValue",
    CelMessageType,
    python_type=NullValue
)
CEL_LIST_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.ListValue",
    CelMessageType,
    python_type=ListValue
)
CEL_VALUE_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.Value",
    CelMessageType,
    python_type=Value
)

CEL_STRUCT_WRAPPER = CelType.get_or_register_type_instance(
    "google.protobuf.Struct",
    CelMessageType,
    python_type=Struct
)
CEL_ANY = CelType.get_or_register_type_instance(
    "google.protobuf.Any",
    CelMessageType,
    python_type=Any
)

class ParameterizedCelType(CelType):
    base_type: CelType
    params: Tuple[CelType, ...]

    def __init__(self, name: str, id_: int, base_type: CelType, params: List[CelType]):
        """
        コンストラクタ。CelType.get_or_register_type_instance から呼び出されることを想定。
        name と id_ は get_or_register_type_instance によって決定される。
        """
        super().__init__(name, id_)  # name と id_ をスーパークラスに渡す
        self.base_type = base_type
        self.params = tuple(params)  # パラメータはタプルとして保持


    def __eq__(self, other): # CelValue / CelType の __eq__ をオーバーライド
        if not isinstance(other, ParameterizedCelType):
            return False
        # 名前(list<dyn>など)とIDが同じかまずCelTypeの__eq__で確認できると良いが、
        # ParameterizedCelType同士ならbase_typeとparamsが重要
        return super().__eq__(other) and \
               self.base_type == other.base_type and \
               self.params == other.params

    def __hash__(self): # CelValue / CelType の __hash__ をオーバーライド
        return hash((super().__hash__(), self.base_type, self.params))


# --- ParameterizedCelType を生成するヘルパー関数 (修正箇所) ---
_parameterized_type_cache: Dict[str, ParameterizedCelType] = {}  # キャッシュのキーは型名(str)


def _generate_parameterized_name(base_type_for_name: CelType, params: Tuple[CelType, ...]) -> str:
    """パラメータ化された型の名前を生成します (例: list<int>, map<string,bool>)"""
    param_names = ", ".join(p.name for p in params)
    # base_type_for_name.name は "list_base_internal" などになっているため、表示用の名前に変換
    clean_base_name = "list" if base_type_for_name == _LIST_BASE_TYPE else \
        "map" if base_type_for_name == _MAP_BASE_TYPE else \
            base_type_for_name.name.replace("_base_internal", "")
    return f"{clean_base_name}<{param_names}>"


def make_list_type(element_type: CelType) -> ParameterizedCelType:
    name = _generate_parameterized_name(_LIST_BASE_TYPE, (element_type,))

    # キャッシュから取得を試みる
    if name in _parameterized_type_cache:
        cached_instance = _parameterized_type_cache[name]
        # キャッシュされたインスタンスのパラメータが一致するか確認
        if cached_instance.base_type == _LIST_BASE_TYPE and cached_instance.params == (element_type,):
            return cached_instance
        # else: キャッシュミスまたは衝突、新しいインスタンスを作成（下で処理）

    instance = CelType.get_or_register_type_instance(
        name,
        ParameterizedCelType,
        base_type=_LIST_BASE_TYPE,
        params=[element_type]
    )
    if not isinstance(instance, ParameterizedCelType):
        raise TypeError(f"Expected ParameterizedCelType for '{name}', got {type(instance)}")
    _parameterized_type_cache[name] = instance  # キャッシュに保存
    return instance


def make_map_type(key_type: CelType, value_type: CelType) -> ParameterizedCelType:
    name = _generate_parameterized_name(_MAP_BASE_TYPE, (key_type, value_type))

    if name in _parameterized_type_cache:
        cached_instance = _parameterized_type_cache[name]
        if cached_instance.base_type == _MAP_BASE_TYPE and cached_instance.params == (key_type, value_type):
            return cached_instance

    instance = CelType.get_or_register_type_instance(
        name,
        ParameterizedCelType,
        base_type=_MAP_BASE_TYPE,
        params=[key_type, value_type]
    )
    if not isinstance(instance, ParameterizedCelType):
        raise TypeError(f"Expected ParameterizedCelType for '{name}', got {type(instance)}")
    _parameterized_type_cache[name] = instance
    return instance

TYPE_LIST_OF_INTS = make_list_type(CEL_INT)
TYPE_LIST_OF_UINTS = make_list_type(CEL_UINT)
TYPE_LIST_OF_BOOLS = make_list_type(CEL_BOOL)
TYPE_LIST_OF_STRINGS = make_list_type(CEL_STRING)
TYPE_LIST_OF_DOUBLES = make_list_type(CEL_DOUBLE) # float も double として扱う
TYPE_LIST_OF_BYTES = make_list_type(CEL_BYTES)

TYPE_MAP_INT_STRING = make_map_type(CEL_INT, CEL_STRING)
TYPE_MAP_STRING_INT = make_map_type(CEL_STRING, CEL_INT)
TYPE_MAP_STRING_STRING = make_map_type(CEL_STRING, CEL_STRING)
TYPE_MAP_STRING_DOUBLE = make_map_type(CEL_STRING, CEL_DOUBLE)


# --- CelFunctionDefinition と CelFunctionRegistry (変更なし) ---
class CelFunctionDefinition:
    def __init__(
            self,
            name: str,
            arg_types: List[CelType],
            result_type: CelType,
            implementation: Optional[Callable[..., Any]] = None,
            receiver_type: Optional[CelType] = None,
            is_method: bool = False,
            expects_cel_values: bool = False,
            takes_eval_context: bool = False # ★ 新しい引数をデフォルト値付きで追加
    ):
        self.name = name
        self.arg_types = arg_types
        self.result_type = result_type
        self.implementation = implementation
        self.receiver_type = receiver_type
        self.is_method = is_method if receiver_type else False # is_method は receiver_type があれば True
        self.expects_cel_values = expects_cel_values
        self.takes_eval_context = takes_eval_context # ★ インスタンス変数に保存


    def matches_arguments(self, call_arg_types: List[CelType]) -> bool:
        if len(call_arg_types) != len(self.arg_types): return False
        for def_type, call_type in zip(self.arg_types, call_arg_types):
            if def_type == call_type: continue
            if def_type == CEL_DYN or call_type == CEL_DYN: continue
            if def_type == CEL_UNKNOWN: continue
            return False
        return True

    def __repr__(self):
        receiver_repr = f"on {self.receiver_type.name} " if self.is_method and self.receiver_type else ""
        arg_repr = ", ".join(at.name for at in self.arg_types)
        return (f"CelFunctionDefinition(name='{self.name}' {receiver_repr}"
                f"({arg_repr}) -> {self.result_type.name})")



class CelFunctionRegistry:
    def __init__(self):
        self._functions: Dict[str, List[CelFunctionDefinition]] = {}

    def register(self, fn_def: CelFunctionDefinition):
        self._functions.setdefault(fn_def.name, []).append(fn_def)

    def resolve(self,
                name: str,
                target_type: Optional[CelType],
                arg_types: List[CelType]) -> Optional[CelFunctionDefinition]:
        candidates = self._functions.get(name, [])
        matched_definitions: List[CelFunctionDefinition] = []

        for fn_def in candidates:
            if target_type is not None:
                if not fn_def.is_method or fn_def.receiver_type is None:
                    continue

                receiver_match = False

                if fn_def.receiver_type == target_type:
                    receiver_match = True
                elif fn_def.receiver_type == CEL_DYN or target_type == CEL_DYN:
                    receiver_match = True
                elif fn_def.receiver_type == CEL_UNKNOWN:
                    receiver_match = True
                if not receiver_match:
                    continue
            else:
                if fn_def.is_method:
                    continue

            if fn_def.matches_arguments(arg_types):
                matched_definitions.append(fn_def)

        if not matched_definitions: return None
        return matched_definitions[0]  # TODO: オーバーロード解決の優先順位付け

    def all(self) -> List[CelFunctionDefinition]:
        return [func_def for overloads_list in self._functions.values() for func_def in overloads_list]

    def copy(self) -> 'CelFunctionRegistry':
        new_registry = CelFunctionRegistry();
        new_registry._functions = {name: list(overloads) for name, overloads in self._functions.items()};
        return new_registry

    def is_function_defined(self, name: str) -> bool:
        """
        Checks if a function with the given name has any registered overloads.
        """
        return name in self._functions


class CelDynValue(CelValue):
    """
    CELのdyn()によって動的型付けされた値をラップするクラス。
    実際の値はスーパークラスの self.value (または self._internal_value) に保持される。
    """

    def __init__(self, wrapped_cel_value: CelValue):
        """
        コンストラクタ。
        :param wrapped_cel_value: dyn()によってラップされる実際のCelValueインスタンス。
        """
        if not isinstance(wrapped_cel_value, CelValue):
            raise TypeError(f"CelDynValue must wrap a CelValue instance. Got: {type(wrapped_cel_value)}")

        self.value = wrapped_cel_value

    @property
    def wrapped_value(self) -> CelValue:
        """ラップされている実際のCelValueインスタンスを返します。"""
        return self.value  # CelValue の value プロパティ経由でアクセス (コンストラクタで設定したため)

    @property
    def cel_type(self) -> CelType:
        """このCelDynValueインスタンスのCEL型は CEL_DYN です。"""
        global CEL_DYN  # グローバルなCEL_DYN型ディスクリプタを参照
        if CEL_DYN is None:
            raise RuntimeError("CEL_DYN type descriptor not initialized.")
        return CEL_DYN

    def __repr__(self) -> str:
        return f"CelDynValue(wrapped={self.value!r})"

    # --- 比較演算子 ---
    # CelDynValueの比較は、ラップされた値の比較に委譲する。
    # dyn(a) == b  -> a == b
    # a == dyn(b)  -> a == b
    # dyn(a) == dyn(b) -> a == b

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True

        other_unwrapped = other.wrapped_value if isinstance(other, CelDynValue) else other
        # self.wrapped_value と other_unwrapped を比較
        # (self.wrapped_value の __eq__ が呼び出される)
        return self.wrapped_value == other_unwrapped

    def __ne__(self, other: Any) -> bool:
        # not (a == b) の標準的な実装
        eq_result = self.__eq__(other)
        return NotImplemented if eq_result is NotImplemented else not eq_result

    def __lt__(self, other: Any) -> bool:
        other_unwrapped = other.wrapped_value if isinstance(other, CelDynValue) else other
        if hasattr(self.wrapped_value, '__lt__'):
            return self.wrapped_value < other_unwrapped  # type: ignore
        raise TypeError(
            f"Operator '<' not supported between dyn (wrapping {type(self.wrapped_value).__name__}) and {type(other_unwrapped).__name__}")

    def __le__(self, other: Any) -> bool:
        other_unwrapped = other.wrapped_value if isinstance(other, CelDynValue) else other
        if hasattr(self.wrapped_value, '__le__'):
            return self.wrapped_value <= other_unwrapped  # type: ignore
        raise TypeError(
            f"Operator '<=' not supported between dyn (wrapping {type(self.wrapped_value).__name__}) and {type(other_unwrapped).__name__}")

    def __gt__(self, other: Any) -> bool:
        other_unwrapped = other.wrapped_value if isinstance(other, CelDynValue) else other
        if hasattr(self.wrapped_value, '__gt__'):
            return self.wrapped_value > other_unwrapped  # type: ignore
        raise TypeError(
            f"Operator '>' not supported between dyn (wrapping {type(self.wrapped_value).__name__}) and {type(other_unwrapped).__name__}")

    def __ge__(self, other: Any) -> bool:
        other_unwrapped = other.wrapped_value if isinstance(other, CelDynValue) else other
        if hasattr(self.wrapped_value, '__ge__'):
            return self.wrapped_value >= other_unwrapped  # type: ignore
        raise TypeError(
            f"Operator '>=' not supported between dyn (wrapping {type(self.wrapped_value).__name__}) and {type(other_unwrapped).__name__}")

    def __hash__(self) -> int:
        # dynでラップされた値は、それ自体がハッシュ可能であればハッシュ可能とする。
        # CelDynValue(list) などはハッシュ不可になる。
        try:
            # クラスを含めることで CelDynValue(X) と X のハッシュ値が異なるようにする
            return hash((self.__class__, self.wrapped_value))
        except TypeError:  # wrapped_value がハッシュ不可能な場合
            raise TypeError(
                f"unhashable type: '{self.__class__.__name__}' wrapping an unhashable value of type '{type(self.wrapped_value).__name__}'")

    # --- 算術演算子 (ラップされた値に委譲) ---
    def _delegate_binary_op(self, other: Any, op_name: str) -> CelValue:
        other_unwrapped = other.wrapped_value if isinstance(other, CelDynValue) else other
        method = getattr(self.wrapped_value, op_name, None)
        if method:
            return method(other_unwrapped)
        raise TypeError(
            f"Operator '{op_name}' not supported for dyn (wrapping {type(self.wrapped_value).__name__}) and {type(other_unwrapped).__name__}")

    def __add__(self, other: Any) -> CelValue:
        return self._delegate_binary_op(other, "__add__")

    def __sub__(self, other: Any) -> CelValue:
        return self._delegate_binary_op(other, "__sub__")

    def __mul__(self, other: Any) -> CelValue:
        return self._delegate_binary_op(other, "__mul__")

    def __truediv__(self, other: Any) -> CelValue:
        return self._delegate_binary_op(other, "__truediv__")

    def __floordiv__(self, other: Any) -> CelValue:
        return self._delegate_binary_op(other, "__floordiv__")

    def __mod__(self, other: Any) -> CelValue:
        return self._delegate_binary_op(other, "__mod__")

    # __rtruediv__ など、右辺の演算子も必要に応じて実装

    def __neg__(self) -> CelValue:
        if hasattr(self.wrapped_value, '__neg__'):
            return -self.wrapped_value  # type: ignore
        raise TypeError(f"Operator '-' (unary) not supported for dyn (wrapping {type(self.wrapped_value).__name__})")

    # 必要に応じて他のマジックメソッドも同様に委譲 (例: __contains__, __getitem__, __len__)
    # 例えば、dyn(list)[0] のようなアクセスを可能にする場合:
    # def __getitem__(self, key: Any) -> CelValue:
    #     if hasattr(self.wrapped_value, '__getitem__'):
    #         return self.wrapped_value[key]
    #     raise TypeError(f"Dyn-wrapped type {type(self.wrapped_value).__name__} does not support indexing")
