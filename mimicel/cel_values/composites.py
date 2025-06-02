import math
from typing import Dict, Any, Optional, List

from .cel_types import CelType, CEL_STRUCT, CelDynValue
from mimicel.cel_values import CelValue, CelNull, CelString, CelInt, CelUInt, CelBool, CelDouble


class CelStruct(CelValue):  # (変更なし)
    def __init__(self, type_name: str, fields: Dict[str, CelValue]):
        self.type_name: str = type_name
        self.fields: Dict[str, CelValue] = fields

    @property
    def cel_type(self) -> CelType:  # TypeRegistryから具体的なCelMessageTypeを取得するのが理想
        # from .cel_types import CelType.get_by_name # 循環を避けるためTypeRegistry経由
        # cel_msg_type = CelType.get_by_name(self.type_name)
        # return cel_msg_type if cel_msg_type else CEL_STRUCT # フォールバック
        return CEL_STRUCT  # 簡単のため

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CelStruct) and self.type_name == other.type_name and self.fields == other.fields

    def __lt__(self, other: Any) -> bool: raise TypeError(f"Operator '<' not supported on {self.cel_type.name}")

    def has_field(self, name: str) -> bool: return name in self.fields

    def get_field(self, name: str) -> CelValue: return self.fields.get(name, CelNull())  # 存在しないフィールドはCelNull

    def __contains__(self, key: str) -> bool: return key in self.fields  # for has(struct.field)

    def __getitem__(self, key: str) -> CelValue:
        if key not in self.fields: raise RuntimeError(
            f"Field '{key}' not found in struct '{self.type_name}'.")  # CEL: no_such_field
        return self.fields[key]

    def __repr__(self): return f"CelStruct(type='{self.type_name}', fields={self.fields!r})"

    def __hash__(self): return hash((self.type_name, tuple(sorted(self.fields.items()))))


class CelMap(CelValue):  # (変更なし、__len__, __getitem__, __contains__はsize(), index[], inで利用)
    def _normalize_key(self, key: Any) -> CelValue:  # key は __getitem__ などから CelValue として渡される想定
        if isinstance(key, (CelString, CelInt, CelUInt, CelBool)):
            return key
        # --- ▼▼▼ 修正箇所: CelDouble の扱い変更 ▼▼▼ ---
        if isinstance(key, CelDouble):
            double_val = key.value
            if double_val == math.trunc(double_val):  # 整数値の Double
                return CelInt(int(double_val))  # CelInt に正規化
            else:
                # 整数でない Double はそのまま CelDouble として返す
                # (マップ検索時に一致するキーがなければ KeyError となる)
                return key
                # --- ▲▲▲ 修正箇所 ▲▲▲ ---

        # Python ネイティブ型からの変換 (通常は wrap_value で処理されるが、念のため)
        if isinstance(key, str): return CelString(key)
        if isinstance(key, bool): return CelBool(key)
        if isinstance(key, int): return CelInt(key)
        if isinstance(key, float):
            if key == math.trunc(key):
                return CelInt(int(key))
            else:
                return CelDouble(key)  # 小数を持つfloatはCelDoubleとして返す

        raise TypeError(
            f"Invalid map key type for normalization: {type(key).__name__}. Must be String, Int, UInt, Bool, or convertible Double/Float.")

    def __init__(self, value: Dict[Any, Any]):
        from mimicel.cel_values import wrap_value

        self.value: Dict[CelValue, CelValue] = {}
        if not isinstance(value, dict): raise TypeError(f"CelMap input must be a dict, got {type(value).__name__}")
        for k_raw, v_raw in value.items():
            try:
                # キーはCelValueインスタンスであることを期待。そうでなければラップ。
                normalized_key = k_raw if isinstance(k_raw,
                                                     (CelString, CelInt, CelUInt, CelBool)) else self._normalize_key(
                    k_raw)
            except TypeError as e:
                raise TypeError(f"Error normalizing key '{k_raw!r}': {e}") from e
            normalized_value = v_raw if isinstance(v_raw, CelValue) else wrap_value(v_raw)
            self.value[normalized_key] = normalized_value

    @property
    def cel_type(self) -> 'CelType':
        from ..cel_values.cel_types import make_map_type, CEL_DYN  # 循環参照回避
        return make_map_type(CEL_DYN, CEL_DYN)  # 簡単のため

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CelMap) and self.value == other.value

    def __lt__(self, other: Any) -> bool:
        raise TypeError(f"Operator '<' not supported on {self.cel_type.name}")

    def get(self, key: Any, default: Optional[CelValue] = None) -> Optional[CelValue]:
        try:
            normalized_key = self._normalize_key(key);
            return self.value.get(normalized_key, default)
        except TypeError:
            return default  # 不正なキー型ならdefault

    def __contains__(self, key: Any) -> bool:
        try:
            normalized_key = self._normalize_key(key);
            return normalized_key in self.value
        except TypeError:
            return False

    def __getitem__(self, key: Any) -> CelValue: # key は評価器から CelValue として渡される
        normalized_key: CelValue
        try:
            normalized_key = self._normalize_key(key)
        except TypeError as e: # _normalize_key が型エラーを出した場合
             # Conformance test は "no such key" を期待している場合があるので、
             # ここで KeyError に近いエラーを出すか、あるいは _normalize_key で
             # 不正な型でもエラーにせず、検索で見つからないようにする。
             # 今回は、_normalize_key が不正な型をそのまま返すように変更したので、
             # ここでは KeyError を期待する。
             # ただし、メッセージはテストの期待に合わせる必要がある。
            key_repr = key.value if hasattr(key, 'value') else repr(key)
            raise RuntimeError(f"no such key: '{key_repr}' (due to invalid key type after normalization: {e})") from e

        try:
            return self.value[normalized_key]
        except KeyError:
            # --- ▼▼▼ 修正箇所: エラーメッセージ変更 ▼▼▼ ---
            key_repr = normalized_key.value if hasattr(normalized_key, 'value') else repr(normalized_key)
            raise RuntimeError(f"no such key: '{key_repr}'") from None # "no such key" パターンに合わせる
            # --- ▲▲▲ 修正箇所 ▲▲▲ ---

    def __len__(self) -> int:
        return len(self.value)

    def __iter__(self):
        return iter(self.value)  # keys iterator

    def items(self):
        return self.value.items()

    def keys(self):
        return self.value.keys()

    def values(self):
        return self.value.values()

    def __repr__(self):
        item_reprs = [f"{k!r}: {v!r}" for k, v in self.value.items()];
        return f"CelMap({{{', '.join(item_reprs)}}})"

    def __hash__(self):  # CelMapは通常ミュータブルなのでハッシュ不可だが、もしイミュータブルなら
        try:
            return hash(tuple(sorted(self.value.items())))
        except TypeError:
            raise TypeError("CelMap is unhashable if it contains unhashable values or if keys are unhashable")


class CelList(CelValue):  # (変更なし、__len__と__getitem__はsize()とindex[]で利用)
    def __init__(self, elements: List[CelValue]):
        self.elements: List[CelValue] = elements

    @property
    def cel_type(self) -> 'CelType':
        from ..cel_values.cel_types import make_list_type, CEL_DYN  # 循環参照回避
        # TODO: より正確な型パラメータを推論する (型チェック時に行うべき)
        # 実行時は list<dyn> とするのが安全か、要素から推論するか。
        # Language Def: "at runtime, lists and maps can have heterogeneous types."
        #             "The type checker also introduces the dyn type... list(dyn)"
        # なので、実行時の .cel_type は list<dyn> が妥当。
        # より具体的な型は型チェック時に type_map に記録される。
        if not self.elements: return make_list_type(CEL_DYN)
        # 全要素が同じ型ならその型を、そうでなければdynを要素型とするリスト型を返すのが理想だが、
        # 実行時の型表現としてはこれで十分か。
        return make_list_type(CEL_DYN)  # 簡単のため

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CelList) and self.elements == other.elements

    def __lt__(self, other: Any) -> bool:
        raise TypeError(f"Operator '<' not supported on {self.cel_type.name}")

    def __add__(self, other: Any) -> 'CelList':
        if isinstance(other, CelList): return CelList(self.elements + other.elements)
        return super().__add__(other)

    def __contains__(self, item: CelValue) -> bool:
        return item in self.elements

    def __len__(self) -> int:
        return len(self.elements)

    def __getitem__(self, index: Any) -> CelValue:
        py_index: int

        if isinstance(index, CelDynValue):
            index = index.value

        # --- ▼▼▼ 修正箇所: CelUInt の処理を追加 ▼▼▼ ---
        if isinstance(index, CelInt):
            py_index = index.value
        elif isinstance(index, CelUInt):  # ★ CelUInt を許容
            py_index = index.value  # uint の値はそのまま整数インデックスとして使える
        elif isinstance(index, CelDouble):
            double_val = index.value
            if double_val == math.trunc(double_val):
                py_index = int(double_val)
            else:
                raise TypeError(
                    f"invalid_argument:  for list index: must be integer or whole number double, got CelDouble with value {double_val}"
                )
        elif isinstance(index, int):
            py_index = index
        else:
            index_type_name = index.cel_type.name if hasattr(index, 'cel_type') and hasattr(index.cel_type,
                                                                                            'name') else type(
                index).__name__
            raise TypeError(f"invalid_argument: List indices must be integers, not {index_type_name}")
        # --- ▲▲▲ 修正箇所 ▲▲▲ ---

        try:
            list_len = len(self.elements)
            if not (-list_len <= py_index < list_len):
                raise IndexError(f"List index {py_index} out of range for list of size {list_len}")
            return self.elements[py_index]
        except IndexError as e:
            raise RuntimeError(f"invalid_argument: IndexError during list access for index {py_index} (original message: {e})") from e

    def __iter__(self):
        return iter(self.elements)

    def __repr__(self):
        return f"CelList({self.elements!r})"

