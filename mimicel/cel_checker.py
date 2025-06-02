# cel_checker.py
# CELの型チェック関連のロジックを格納するモジュール

from typing import Dict, Any, Optional, List, TYPE_CHECKING

from google.protobuf.descriptor import FieldDescriptor, Descriptor

from cel.expr import syntax_pb2, checked_pb2
from google.protobuf import empty_pb2, descriptor_pool

# cel_types から必要な型定義をインポート
from .cel_values.cel_types import (
    CelType, ParameterizedCelType,
    CEL_INT, CEL_UINT, CEL_BOOL, CEL_STRING, CEL_DOUBLE, CEL_BYTES,
    CEL_NULL, CEL_DYN, CEL_TYPE, _LIST_BASE_TYPE, _MAP_BASE_TYPE,
    make_list_type, make_map_type,
    CEL_DURATION, CEL_TIMESTAMP, CEL_UNKNOWN, CEL_LIST, CEL_INT32_WRAPPER, CEL_VALUE_WRAPPER, CEL_STRUCT_WRAPPER,
    CEL_LIST_WRAPPER, CEL_BOOL_WRAPPER, CEL_INT64_WRAPPER, CEL_UINT64_WRAPPER, CEL_UINT32_WRAPPER, CEL_DOUBLE_WRAPPER,
    CEL_STRING_WRAPPER, CEL_BYTES_WRAPPER, CEL_FLOAT_WRAPPER, CEL_FLOAT, CEL_ANY, CEL_MAP, CEL_ERROR, CelMessageType
)

if TYPE_CHECKING:
    from .api import CelEnv  # 型ヒントのための循環参照回避

# --- checked_pb2.Type 定数 ---
TYPE_INT64_PB = checked_pb2.Type(primitive=checked_pb2.Type.PrimitiveType.INT64)
TYPE_UINT64_PB = checked_pb2.Type(primitive=checked_pb2.Type.PrimitiveType.UINT64)
TYPE_BOOL_PB = checked_pb2.Type(primitive=checked_pb2.Type.PrimitiveType.BOOL)
TYPE_STRING_PB = checked_pb2.Type(primitive=checked_pb2.Type.PrimitiveType.STRING)
TYPE_DOUBLE_PB = checked_pb2.Type(primitive=checked_pb2.Type.PrimitiveType.DOUBLE)
TYPE_BYTES_PB = checked_pb2.Type(primitive=checked_pb2.Type.PrimitiveType.BYTES)
TYPE_NULL_PB = checked_pb2.Type(null=0)
TYPE_DYN_PB = checked_pb2.Type(abstract_type=checked_pb2.Type.AbstractType(name="DYN"))
TYPE_TYPE_PB = checked_pb2.Type(abstract_type=checked_pb2.Type.AbstractType(name="TYPE"))
TYPE_ERROR_PB = checked_pb2.Type(error=empty_pb2.Empty())
TYPE_DURATION_PB = checked_pb2.Type(well_known=checked_pb2.Type.WellKnownType.DURATION)
TYPE_TIMESTAMP_PB = checked_pb2.Type(well_known=checked_pb2.Type.WellKnownType.TIMESTAMP)


_CEL_TYPE_TO_CHECKED_PB_BASE: Dict[CelType, checked_pb2.Type] = {
    CEL_INT: TYPE_INT64_PB,
    CEL_UINT: TYPE_UINT64_PB,
    CEL_BOOL: TYPE_BOOL_PB,
    CEL_STRING: TYPE_STRING_PB,
    CEL_DOUBLE: TYPE_DOUBLE_PB,
    CEL_FLOAT: TYPE_DOUBLE_PB,
    CEL_BYTES: TYPE_BYTES_PB,
    CEL_NULL: TYPE_NULL_PB,
    CEL_DYN: TYPE_DYN_PB,
    CEL_TYPE: TYPE_TYPE_PB,
    CEL_ERROR: TYPE_ERROR_PB,
    CEL_DURATION: TYPE_DURATION_PB,
    CEL_TIMESTAMP: TYPE_TIMESTAMP_PB,
    CEL_ANY: checked_pb2.Type(well_known=checked_pb2.Type.WellKnownType.ANY),
    CEL_BOOL_WRAPPER: checked_pb2.Type(message_type="google.protobuf.BoolValue"),
    CEL_BYTES_WRAPPER: checked_pb2.Type(message_type="google.protobuf.BytesValue"),
    CEL_DOUBLE_WRAPPER: checked_pb2.Type(message_type="google.protobuf.DoubleValue"),
    CEL_FLOAT_WRAPPER: checked_pb2.Type(message_type="google.protobuf.FloatValue"),
    CEL_INT32_WRAPPER: checked_pb2.Type(message_type="google.protobuf.Int32Value"),
    CEL_INT64_WRAPPER: checked_pb2.Type(message_type="google.protobuf.Int64Value"),
    CEL_STRING_WRAPPER: checked_pb2.Type(message_type="google.protobuf.StringValue"),
    CEL_UINT32_WRAPPER: checked_pb2.Type(message_type="google.protobuf.UInt32Value"),
    CEL_UINT64_WRAPPER: checked_pb2.Type(message_type="google.protobuf.UInt64Value"),
    CEL_VALUE_WRAPPER: checked_pb2.Type(message_type="google.protobuf.Value"),
    CEL_STRUCT_WRAPPER: checked_pb2.Type(message_type="google.protobuf.Struct"),
    CEL_LIST_WRAPPER: checked_pb2.Type(message_type="google.protobuf.ListValue"),
}
TYPE_STRUCT_AS_MAP = make_map_type(CEL_STRING, CEL_VALUE_WRAPPER)
TYPE_PROTO_LIST_AS_LIST = make_list_type(CEL_VALUE_WRAPPER)

class CelChecker:
    def __init__(self, env: 'CelEnv'):
        self.env = env
        # self.container_name は self.env.container_name でアクセス
        self._descriptor_pool = getattr(self.env, 'descriptor_pool', descriptor_pool.Default())

    def _try_resolve_as_extension_field(self,
                                        message_cel_type: CelType,
                                        extension_fqn: str) -> Optional[CelType]:
        """
        指定された message_cel_type (の名前) に対して、extension_fqn (拡張フィールドの完全修飾名) を
        拡張フィールドとして解決しようと試みる。
        見つかればその CelType を、見つからなければ None を返す。
        """
        if not (isinstance(message_cel_type, CelMessageType) and hasattr(message_cel_type, 'name')):
            return None

        # TypeRegistry から親メッセージの MessageDescriptor を取得
        # (TypeRegistry に get_message_descriptor メソッドが必要になる)
        message_descriptor: Optional[Descriptor] = \
            self.env.type_registry.get_message_descriptor(message_cel_type.name)  # 仮のメソッド名

        if not message_descriptor:
            print(f"DEBUG: No descriptor found for message type {message_cel_type.name}")
            return None

        extension_field_descriptor: Optional[FieldDescriptor] = None
        try:
            # DescriptorPool を使って拡張フィールド名で検索
            ext_desc = self._descriptor_pool.FindExtensionByName(extension_fqn)
            # 見つかった拡張が、現在のメッセージ型を拡張しているか確認
            if ext_desc and ext_desc.containing_type == message_descriptor:
                extension_field_descriptor = ext_desc
        except KeyError:
            print(f"DEBUG: Extension '{extension_fqn}' not found in descriptor pool.")
            return None  # 拡張が見つからない
        except Exception as e:
            print(f"DEBUG: Error during FindExtensionByName for '{extension_fqn}': {e}")
            return None  # その他のエラー

        if extension_field_descriptor:
            # 見つかった拡張フィールドの FieldDescriptor を CelType に変換
            # TypeRegistry の既存のロジックを利用する
            return self.env.type_registry._protobuf_field_type_to_cel_type(extension_field_descriptor)

        return None

    def _record_type_error(self, node_id: int, message: str, expr_pb_for_context: Optional[syntax_pb2.Expr] = None):
        error_message = message
        if self.env and self.env.container_name:
            error_message = f"{message} (in container '{self.env.container_name}')"
        self.env._record_type_error(node_id, error_message, expr_pb_for_context)

    def _cel_type_to_checked_pb(self, cel_type: CelType) -> checked_pb2.Type:
        if cel_type is None:
            self._record_type_error(0, "Internal checker error: _cel_type_to_checked_pb received None CelType.")
            return TYPE_ERROR_PB

        if cel_type == CEL_DURATION:  # cel_types.py で CEL_DURATION が CelMessageType インスタンスになっている前提
            return TYPE_DURATION_PB
        if cel_type == CEL_TIMESTAMP:  # 同上
            return TYPE_TIMESTAMP_PB

        if cel_type == CEL_LIST_WRAPPER:
            return checked_pb2.Type(message_type="google.protobuf.ListValue")

        if cel_type == CEL_STRUCT_WRAPPER:
            return checked_pb2.Type(message_type="google.protobuf.Struct")

        if cel_type == CEL_VALUE_WRAPPER:
            return checked_pb2.Type(message_type="google.protobuf.Value")

        if cel_type == CEL_INT32_WRAPPER:
            # CEL仕様ではWKTは通常 message_type として表現される
            return checked_pb2.Type(message_type="google.protobuf.Int32Value")
        if isinstance(cel_type, ParameterizedCelType):
            if cel_type.base_type == _LIST_BASE_TYPE and len(cel_type.params) == 1:
                elem_pb_type = self._cel_type_to_checked_pb(cel_type.params[0])
                if elem_pb_type == TYPE_ERROR_PB: return TYPE_ERROR_PB
                return checked_pb2.Type(list_type=checked_pb2.Type.ListType(elem_type=elem_pb_type))
            elif cel_type.base_type == _MAP_BASE_TYPE and len(cel_type.params) == 2:
                key_pb_type = self._cel_type_to_checked_pb(cel_type.params[0])
                val_pb_type = self._cel_type_to_checked_pb(cel_type.params[1])
                if key_pb_type == TYPE_ERROR_PB or val_pb_type == TYPE_ERROR_PB: return TYPE_ERROR_PB
                return checked_pb2.Type(map_type=checked_pb2.Type.MapType(key_type=key_pb_type, value_type=val_pb_type))
            else:
                self._record_type_error(0,
                                        f"Cannot convert unknown parameterized CelType '{cel_type.name}' to protobuf Type.")
                return TYPE_ERROR_PB
        if cel_type == CEL_LIST:  # Generic list is list<dyn>
            elem_pb_type = self._cel_type_to_checked_pb(CEL_DYN)
            return checked_pb2.Type(list_type=checked_pb2.Type.ListType(elem_type=elem_pb_type))
        if cel_type in _CEL_TYPE_TO_CHECKED_PB_BASE:
            return _CEL_TYPE_TO_CHECKED_PB_BASE[cel_type]
        if self.env.type_registry.is_message_type(
                cel_type.name):  # Relies on type_registry having fully qualified names
            return checked_pb2.Type(message_type=cel_type.name)
        # If it's a message type known within a container, CELEnv._parse_cel_type_from_string should have resolved it.
        # If it reaches here and is_message_type is false, it's likely an unknown simple type or an error.
        self._record_type_error(0,
                                f"Cannot convert CelType '{cel_type.name}' to protobuf Type. It's not a basic type, parameterized type, or registered message type.")
        return TYPE_ERROR_PB

    def _checked_pb_to_cel_type(self, checked_type: checked_pb2.Type) -> CelType:
        kind = checked_type.WhichOneof('type_kind')

        if kind == 'abstract_type':
            if checked_type.abstract_type.name == "DYN": return CEL_DYN
            if checked_type.abstract_type.name == "TYPE": return CEL_TYPE
            return CEL_UNKNOWN  # Or a more specific abstract type if you add them

        # Fallback for direct 'dyn' or 'type' fields if abstract_type is not used
        if kind == 'dyn': return CEL_DYN
        if kind == 'type': return CEL_TYPE  # This refers to the 'type' type itself

        if kind == 'null': return CEL_NULL
        if kind == 'error': return CEL_UNKNOWN

        if kind == 'primitive':
            for ct, ctp_proto in _CEL_TYPE_TO_CHECKED_PB_BASE.items():
                if ctp_proto.WhichOneof('type_kind') == 'primitive' and ctp_proto.primitive == checked_type.primitive:
                    return ct
            return CEL_UNKNOWN
        elif kind == 'list_type':
            elem_cel_type = self._checked_pb_to_cel_type(checked_type.list_type.elem_type)
            return make_list_type(elem_cel_type if elem_cel_type != CEL_UNKNOWN else CEL_DYN)
        elif kind == 'map_type':
            key_cel_type = self._checked_pb_to_cel_type(checked_type.map_type.key_type)
            val_cel_type = self._checked_pb_to_cel_type(checked_type.map_type.value_type)
            return make_map_type(
                key_cel_type if key_cel_type != CEL_UNKNOWN else CEL_DYN,
                val_cel_type if val_cel_type != CEL_UNKNOWN else CEL_DYN
            )
        elif kind == 'message_type':
            msg_name = checked_type.message_type
            # Use CELEnv's parsing logic which should handle container resolution
            cel_msg_type = self.env._parse_cel_type_from_string(msg_name)
            return cel_msg_type if cel_msg_type and cel_msg_type != CEL_UNKNOWN else CEL_UNKNOWN
        elif kind == 'well_known':
            if checked_type.well_known == checked_pb2.Type.WellKnownType.DURATION: return CEL_DURATION
            if checked_type.well_known == checked_pb2.Type.WellKnownType.TIMESTAMP: return CEL_TIMESTAMP
            # Add other well-known types like ANY if supported
            return CEL_DYN

        return CEL_UNKNOWN

    def _determine_common_type(self, types: List[CelType]) -> CelType:
        # (元のコードのまま)
        if not types: return CEL_DYN
        if any(t == CEL_DYN for t in types): return CEL_DYN
        if any(t == CEL_UNKNOWN for t in types): return CEL_UNKNOWN
        non_null_types = [t for t in types if t != CEL_NULL]
        if not non_null_types: return CEL_NULL
        first_type = non_null_types[0]
        all_match_or_null = True
        for t in non_null_types:
            if t != first_type:
                all_match_or_null = False
                break
        if all_match_or_null: return first_type
        has_int = any(t == CEL_INT for t in non_null_types)
        has_uint = any(t == CEL_UINT for t in non_null_types)
        has_double = any(t == CEL_DOUBLE for t in non_null_types)
        if has_double and (has_int or has_uint):
            if all(self._is_assignable(t, CEL_DOUBLE) for t in non_null_types if t != CEL_DOUBLE):
                return CEL_DOUBLE
        elif has_int and has_uint and not has_double:
            return CEL_DYN
        elif (has_int and not has_uint and not has_double):
            if all(t == CEL_INT for t in non_null_types): return CEL_INT
        elif (has_uint and not has_int and not has_double):
            if all(t == CEL_UINT for t in non_null_types): return CEL_UINT
        return CEL_DYN

    def _is_assignable(self, from_type: CelType, to_type: CelType) -> bool:
        if to_type == CEL_DYN: return True
        if from_type == CEL_DYN: return True
        if from_type == to_type: return True
        if from_type == CEL_ERROR: return True
        if to_type == CEL_ERROR: return False

        if to_type == CEL_ANY:
            # 1. Any message type can be packed into google.protobuf.Any.
            if isinstance(from_type, CelMessageType):
                return True
            # 2. Primitives, lists, and maps can be packed into Any (usually via google.protobuf.Value first)
            if from_type in [CEL_NULL, CEL_BOOL, CEL_INT, CEL_UINT, CEL_DOUBLE, CEL_FLOAT, CEL_STRING, CEL_BYTES]:
                return True
            # list<T> or list<dyn>
            if (isinstance(from_type, ParameterizedCelType) and from_type.base_type == _LIST_BASE_TYPE) or \
                    from_type == CEL_LIST:
                # For list<T> to be assignable to Any, T must be packable into Value, or the list itself is Value-packable.
                # This is generally true for lists of primitives, messages, other lists/maps.
                return True
            # map<K,V> or map<dyn,dyn>
            if (isinstance(from_type, ParameterizedCelType) and from_type.base_type == _MAP_BASE_TYPE and
                self._is_assignable(from_type.params[0], CEL_STRING)) or \
                    from_type == CEL_MAP:
                # For map<K,V> to be assignable to Any, K must be string, and V must be packable into Value.
                # map<dyn,dyn> is also allowed, with runtime checks.
                return True
            # If from_type is already a WKT that can be packed (e.g. Struct, ListValue, Value itself)
            if from_type in [CEL_STRUCT_WRAPPER, CEL_LIST_WRAPPER, CEL_VALUE_WRAPPER]:
                return True
            # Fall through if not directly assignable, other rules might apply or return False

        # Assigning to google.protobuf.ListValue (CEL_LIST_WRAPPER)
        if to_type == CEL_LIST_WRAPPER:
            if (isinstance(from_type, ParameterizedCelType) and from_type.base_type == _LIST_BASE_TYPE) or \
                    from_type == CEL_LIST:
                if from_type == CEL_LIST: return True  # list<dyn> is assignable
                if isinstance(from_type, ParameterizedCelType):
                    element_type = from_type.params[0]
                    # Element type must be assignable to google.protobuf.Value
                    if self._is_assignable(element_type, CEL_VALUE_WRAPPER) or element_type == CEL_DYN:
                        return True

        # Assigning to google.protobuf.Struct (CEL_STRUCT_WRAPPER)
        if to_type == CEL_STRUCT_WRAPPER:
            if isinstance(from_type, ParameterizedCelType) and from_type.base_type == _MAP_BASE_TYPE:
                key_type = from_type.params[0]
                value_type = from_type.params[1]
                # Key must be string, value must be assignable to google.protobuf.Value
                if self._is_assignable(key_type, CEL_STRING) and \
                        (self._is_assignable(value_type, CEL_VALUE_WRAPPER) or value_type == CEL_DYN):
                    return True
            elif from_type == CEL_MAP:  # map<dyn,dyn> (e.g. empty map {})
                # An empty map (map<dyn,dyn>) is assignable to Struct
                # if its (non-existent) keys could be strings and values could be Value.
                # This is effectively true for an empty map.
                return True

        # Assigning to google.protobuf.Value (CEL_VALUE_WRAPPER)
        if to_type == CEL_VALUE_WRAPPER:
            if from_type in [CEL_NULL, CEL_BOOL, CEL_INT, CEL_UINT, CEL_DOUBLE, CEL_FLOAT, CEL_STRING, CEL_BYTES]:
                return True
            if (isinstance(from_type, ParameterizedCelType) and from_type.base_type == _LIST_BASE_TYPE) or \
                    from_type == CEL_LIST:
                return True
            if isinstance(from_type, ParameterizedCelType) and from_type.base_type == _MAP_BASE_TYPE:
                key_type = from_type.params[0]
                # For a map to be assignable to Value (which becomes a StructValue), keys must be strings.
                if self._is_assignable(key_type, CEL_STRING):
                    return True
            elif from_type == CEL_MAP:  # map<dyn,dyn> -> Value (becomes StructValue if keys are strings at runtime)
                return True

        # Assignability of primitives to their WKT wrappers
        if to_type == CEL_INT32_WRAPPER and from_type == CEL_INT: return True
        if to_type == CEL_INT64_WRAPPER and from_type == CEL_INT: return True
        if to_type == CEL_UINT32_WRAPPER and from_type == CEL_UINT: return True
        if to_type == CEL_UINT64_WRAPPER and from_type == CEL_UINT: return True
        if to_type == CEL_BOOL_WRAPPER and from_type == CEL_BOOL: return True
        if to_type == CEL_STRING_WRAPPER and from_type == CEL_STRING: return True
        if to_type == CEL_BYTES_WRAPPER and from_type == CEL_BYTES: return True
        if to_type == CEL_DOUBLE_WRAPPER and (
                from_type == CEL_DOUBLE or from_type == CEL_FLOAT or from_type == CEL_INT or from_type == CEL_UINT):
            return True
        if to_type == CEL_FLOAT_WRAPPER and (
                from_type == CEL_FLOAT or from_type == CEL_DOUBLE or from_type == CEL_INT or from_type == CEL_UINT):
            return True

        # Numeric promotion
        if to_type == CEL_DOUBLE and (from_type == CEL_INT or from_type == CEL_UINT or from_type == CEL_FLOAT):
            return True
        if to_type == CEL_FLOAT and (from_type == CEL_INT or from_type == CEL_UINT):
            return True

        # null assignability
        if from_type == CEL_NULL:
            if isinstance(to_type, CelMessageType) or \
                    to_type in [CEL_BOOL_WRAPPER, CEL_BYTES_WRAPPER, CEL_DOUBLE_WRAPPER, CEL_FLOAT_WRAPPER,
                                CEL_INT32_WRAPPER, CEL_INT64_WRAPPER, CEL_STRING_WRAPPER,
                                CEL_UINT32_WRAPPER, CEL_UINT64_WRAPPER, CEL_VALUE_WRAPPER,
                                CEL_ANY, CEL_NULL, CEL_DYN,
                                CEL_LIST_WRAPPER, CEL_STRUCT_WRAPPER]:
                return True

        # Enum type to int
        if to_type == CEL_INT and self.env and self.env.type_registry and \
                hasattr(from_type, 'name') and self.env.type_registry.is_enum_type(from_type.name):
            return True

        # Parameterized types (list to list, map to map)
        if isinstance(from_type, ParameterizedCelType) and isinstance(to_type, ParameterizedCelType):
            if from_type.base_type == to_type.base_type and len(from_type.params) == len(to_type.params):
                if from_type.base_type == _LIST_BASE_TYPE:
                    return self._is_assignable(from_type.params[0], to_type.params[0])

                if from_type.base_type == _MAP_BASE_TYPE:
                    from_key_type, from_value_type = from_type.params
                    to_key_type, to_value_type = to_type.params

                    # --- ▼▼▼ 修正: map<dyn,dyn> からの代入を特別扱い --- ▼▼▼
                    # If from_type is map<dyn,dyn> (e.g. empty map literal {}),
                    # it's assignable if the target map's key type is a valid map key type.
                    if from_key_type == CEL_DYN and from_value_type == CEL_DYN:
                        if to_key_type in [CEL_STRING, CEL_INT, CEL_UINT, CEL_BOOL, CEL_DYN]:
                            # And the target value type can accept DYN (which is true if _is_assignable(DYN, V) works)
                            return self._is_assignable(CEL_DYN, to_value_type)  # Effectively True
                        return False  # Target key type not compatible with a generic map
                    # --- ▲▲▲ 修正 ▲▲▲ ---

                    # General map assignability: keys usually invariant, values covariant.
                    # Allow DYN to match specific key types for flexibility.
                    key_match = (from_key_type == to_key_type) or \
                                (from_key_type == CEL_DYN and to_key_type in [CEL_STRING, CEL_INT, CEL_UINT,
                                                                              CEL_BOOL]) or \
                                (to_key_type == CEL_DYN and from_key_type in [CEL_STRING, CEL_INT, CEL_UINT, CEL_BOOL])

                    # If neither key is DYN, they must be identical.
                    if from_key_type != CEL_DYN and to_key_type != CEL_DYN and from_key_type != to_key_type:
                        key_match = False

                    value_match = self._is_assignable(from_value_type, to_value_type)
                    return key_match and value_match

        # list<T> to list<dyn>
        if isinstance(to_type, ParameterizedCelType) and to_type.base_type == _LIST_BASE_TYPE and to_type.params[
            0] == CEL_DYN:
            if isinstance(from_type, ParameterizedCelType) and from_type.base_type == _LIST_BASE_TYPE:
                return True
            if from_type == CEL_LIST:
                return True

        # map<K,V> to map<dyn,dyn>
        if isinstance(to_type, ParameterizedCelType) and to_type.base_type == _MAP_BASE_TYPE and \
                to_type.params[0] == CEL_DYN and to_type.params[1] == CEL_DYN:
            if isinstance(from_type, ParameterizedCelType) and from_type.base_type == _MAP_BASE_TYPE:
                return True
            if from_type == CEL_MAP:
                return True

        return False

    def _find_expr_by_id(self, expr_pb: syntax_pb2.Expr, target_id: int) -> Optional[syntax_pb2.Expr]:
        # (元のコードのまま)
        if expr_pb.id == target_id: return expr_pb
        kind = expr_pb.WhichOneof('expr_kind')
        if kind == 'const_expr' or kind == 'ident_expr': return None
        children_to_check = []
        if kind == 'select_expr':
            if expr_pb.select_expr.HasField("operand"): children_to_check.append(expr_pb.select_expr.operand)
        elif kind == 'call_expr':
            if expr_pb.call_expr.HasField("target"): children_to_check.append(expr_pb.call_expr.target)
            children_to_check.extend(expr_pb.call_expr.args)
        elif kind == 'list_expr':
            children_to_check.extend(expr_pb.list_expr.elements)
        elif kind == 'struct_expr':
            for entry in expr_pb.struct_expr.entries:
                if entry.HasField("map_key"): children_to_check.append(entry.map_key)
                if entry.HasField("value"): children_to_check.append(entry.value)
        elif kind == 'comprehension_expr':
            comp = expr_pb.comprehension_expr
            if comp.HasField("iter_range"): children_to_check.append(comp.iter_range)
            if comp.HasField("accu_init"): children_to_check.append(comp.accu_init)
            if comp.HasField("loop_condition"): children_to_check.append(comp.loop_condition)
            if comp.HasField("loop_step"): children_to_check.append(comp.loop_step)
            if comp.HasField("result"): children_to_check.append(comp.result)
        for child_expr in children_to_check:
            if child_expr:
                found = self._find_expr_by_id(child_expr, target_id)
                if found: return found
        return None

    def _handle_const_expr_check(self, node_pb: syntax_pb2.Expr,
                                 expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        # (元のコードのまま)
        const = node_pb.const_expr
        kind = const.WhichOneof('constant_kind')
        if kind == "null_value": return CEL_NULL
        if kind == "bool_value": return CEL_BOOL
        if kind == "int64_value": return CEL_INT
        if kind == "uint64_value": return CEL_UINT
        if kind == "double_value": return CEL_DOUBLE
        if kind == "string_value": return CEL_STRING
        if kind == "bytes_value": return CEL_BYTES
        self._record_type_error(node_pb.id, f"Unknown constant type: {kind}",
                                expr_pb_root_for_error_reporting)
        return CEL_UNKNOWN

    def _resolve_identifier_type_in_declarations(self, name: str, declarations: Dict[str, CelType]) -> Optional[
        CelType]:
        """
        与えられた名前を、まずそのままの形で指定された宣言セットから検索する。
        見つからなければ、コンテナ修飾名を試みる (nameが単純名の場合)。
        それでも見つからなければ、グローバル宣言 (self.env.declared_variables) も検索する。
        """

        # 1. name をそのまま現在のスコープ (declarations) で検索
        if name in declarations:
            return declarations[name]

        # 2. name をそのままグローバルスコープ (self.env.declared_variables) で検索
        if self.env and name in self.env.declared_variables:
            return self.env.declared_variables[name]

        # 3. name が単純名で、かつコンテナが指定されている場合、コンテナ修飾名を試す
        #    (このロジックは、主に name が select の field 部分から来た場合に有効)
        if self.env and self.env.container_name and '.' not in name:
            qualified_name = f"{self.env.container_name}.{name}"
            if qualified_name in declarations:  # ローカルスコープでの修飾名
                return declarations[qualified_name]
            if self.env and qualified_name in self.env.declared_variables:  # グローバルスコープでの修飾名
                return self.env.declared_variables[qualified_name]

        return None

    def _get_name_from_expr_node_for_checker(self, expr_node: syntax_pb2.Expr,
                                             ref_map: Dict[int, checked_pb2.Reference]) -> str:
        # (前回提案のものをベースに、ref_mapにない場合のASTからの再帰的名前構築を強化)
        q = []
        curr = expr_node
        while True:
            if curr.id in ref_map and ref_map[curr.id].name:
                # ref_mapに解決済みの名前があれば、それを先頭に追加して終了
                q.insert(0, ref_map[curr.id].name)
                break
            if curr.HasField("ident_expr"):
                q.insert(0, curr.ident_expr.name)
                break
            elif curr.HasField("select_expr"):
                q.insert(0, curr.select_expr.field)
                if curr.select_expr.HasField("operand"):
                    curr = curr.select_expr.operand
                else:
                    return ""  # 不正なAST
            else:
                return ""  # selectでもidentでもない
        return ".".join(q)

    def _resolve_ident_as_type_or_enum_value_or_package(
            self,
            name: str,
            node_id: int,
            ref_map_for_pb: Dict[int, checked_pb2.Reference]
    ) -> Optional[CelType]:
        names_to_try = []
        if '.' in name: names_to_try.append(name)  # 既にFQNの可能性

        # コンテナ名を考慮 (nameが単純名の場合)
        if self.env.container_name and '.' not in name:
            names_to_try.append(f"{self.env.container_name}.{name}")

        if name not in names_to_try: names_to_try.append(name)  # 元の名前も試す

        for name_attempt in names_to_try:
            # 1. Enum値か? (例: "pkg.MyEnum.VALUE")
            if name_attempt.count('.') >= 1:
                parts = name_attempt.rsplit('.', 1)
                if len(parts) == 2:
                    enum_type_cand, enum_val_cand = parts[0], parts[1]
                    if self.env.type_registry.is_enum_type(enum_type_cand):
                        val_num = self.env.type_registry.get_enum_value(enum_type_cand, enum_val_cand)
                        if val_num is not None:
                            if node_id != 0: ref_map_for_pb[node_id] = checked_pb2.Reference(name=name_attempt)
                            return CEL_INT

            # 2. 型リテラル (メッセージ型, Enum型名) またはパッケージ名か?
            type_as_val = self.env._parse_cel_type_from_string(name_attempt)
            if type_as_val and type_as_val != CEL_UNKNOWN:
                is_known_msg = self.env.type_registry.is_message_type(name_attempt)
                is_known_enum_t = self.env.type_registry.is_enum_type(name_attempt)
                is_known_pkg = self.env.type_registry.is_package(name_attempt)
                is_primitive_or_basic = name_attempt in [
                    "int", "uint", "bool", "string", "double", "bytes",
                    "null_type", "dyn", "type", "list", "map", "error",
                    # 主要なWKTもここに含めておく (ただし_parse_cel_type_from_stringが解決するはず)
                    "google.protobuf.Duration", "google.protobuf.Timestamp", "google.protobuf.Any",
                    "google.protobuf.BoolValue", "google.protobuf.BytesValue", "google.protobuf.DoubleValue",
                    "google.protobuf.FloatValue", "google.protobuf.Int32Value", "google.protobuf.Int64Value",
                    "google.protobuf.StringValue", "google.protobuf.UInt32Value", "google.protobuf.UInt64Value",
                    "google.protobuf.Value", "google.protobuf.Struct", "google.protobuf.ListValue"
                ]
                if is_known_msg or is_known_enum_t or is_known_pkg or is_primitive_or_basic:
                    if type_as_val.name == name_attempt:  # _parse_cel_type_from_stringが返した型名と一致
                        if node_id != 0: ref_map_for_pb[node_id] = checked_pb2.Reference(name=name_attempt)
                        return CEL_TYPE
        return None


    def _resolve_ident_as_type_or_enum_value(
            self,
            name: str,
            node_id: int,
            ref_map_for_pb: Dict[int, checked_pb2.Reference]
    ) -> Optional[CelType]:

        names_to_try = [name]
        # コンテナ名を考慮した名前解決 (単純名の場合)
        # TypeRegistry.is_enum_type や _parse_cel_type_from_string がコンテナ名を考慮するべき
        if self.env.container_name and '.' not in name:
            names_to_try.insert(0, f"{self.env.container_name}.{name}")

        for name_attempt in names_to_try:
            # 1a. Enum値か? (例: "pkg.MyEnum.VALUE")
            if '.' in name_attempt:
                parts = name_attempt.rsplit('.', 1)
                if len(parts) == 2:
                    enum_type_cand, enum_val_cand = parts[0], parts[1]
                    # TypeRegistry がコンテナ名を考慮して enum_type_cand を解決できる必要がある
                    if self.env.type_registry.is_enum_type(enum_type_cand):
                        val_num = self.env.type_registry.get_enum_value(enum_type_cand, enum_val_cand)
                        if val_num is not None:
                            if node_id != 0: ref_map_for_pb[node_id] = checked_pb2.Reference(name=name_attempt)
                            return CEL_INT

            # 1b. 型リテラル (メッセージ型 or Enum型名自体) か?
            # CELEnv._parse_cel_type_from_string はコンテナ名を考慮して型を解決する
            type_as_val = self.env._parse_cel_type_from_string(name_attempt)
            if type_as_val and type_as_val != CEL_UNKNOWN:
                # _parse_cel_type_from_string が返したものが実際に登録された型か確認
                if self.env.type_registry.is_message_type(name_attempt) or \
                        self.env.type_registry.is_enum_type(name_attempt):
                    if node_id != 0: ref_map_for_pb[node_id] = checked_pb2.Reference(name=name_attempt)
                    return CEL_TYPE
        return None

    def _handle_ident_expr_check(self, node_pb: syntax_pb2.Expr, current_declarations: Dict[str, CelType],
                                 ref_map_for_pb: Dict[int, checked_pb2.Reference],
                                 expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        name = node_pb.ident_expr.name

        # 優先順位1: 変数として解決 (ローカルおよびグローバル、コンテナ修飾も含む)
        resolved_var_type = self._resolve_identifier_type_in_declarations(name, current_declarations)
        # print("# resolved: ", resolved_var_type)
        if resolved_var_type:
            if node_pb.id != 0: ref_map_for_pb[node_pb.id] = checked_pb2.Reference(name=name)
            return resolved_var_type

        # 優先順位2: 型リテラル、Enum値、またはパッケージ名として解決
        # _resolve_ident_as_type_or_enum_value_or_package はコンテナ名を考慮する
        resolved_other = self._resolve_ident_as_type_or_enum_value_or_package(
            name, node_pb.id, ref_map_for_pb
        )
        if resolved_other:
            return resolved_other

        self._record_type_error(node_pb.id, f"Undeclared identifier '{name}'", expr_pb_root_for_error_reporting)
        return CEL_UNKNOWN

    def _handle_list_expr_check(self, node_pb: syntax_pb2.Expr, type_map_for_pb: Dict[int, checked_pb2.Type],
                                ref_map_for_pb: Dict[int, checked_pb2.Reference],
                                current_declarations: Dict[str, CelType],
                                expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        elements = node_pb.list_expr.elements
        if not elements:
            return make_list_type(CEL_DYN)

        elem_cel_types = [
            self._check_node(elem, type_map_for_pb, ref_map_for_pb, current_declarations,
                             expr_pb_root_for_error_reporting)
            for elem in elements
        ]

        if any(t == CEL_UNKNOWN for t in elem_cel_types):
            return CEL_UNKNOWN

        common_elem_type = self._determine_common_type(elem_cel_types)
        return make_list_type(common_elem_type)

    def _check_message_construction(self, node_id: int, struct_pb: syntax_pb2.Expr.CreateStruct,
                                    type_map_for_pb: Dict[int, checked_pb2.Type],
                                    ref_map_for_pb: Dict[int, checked_pb2.Reference],
                                    current_declarations: Dict[str, CelType],
                                    expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        message_name_from_expr = struct_pb.message_name
        msg_cel_type = self.env._parse_cel_type_from_string(message_name_from_expr)

        if not msg_cel_type or not self.env.type_registry.is_message_type(msg_cel_type.name):
            self._record_type_error(node_id, f"Unknown message type '{message_name_from_expr}' for construction.",
                                    # メッセージ構築用であることを明記
                                    expr_pb_root_for_error_reporting)
            return CEL_ERROR  # CEL_UNKNOWN から CEL_ERROR に変更

        actual_message_name = msg_cel_type.name

        if not self.env.type_registry.is_message_constructible(actual_message_name):
            self._record_type_error(node_id,
                                    f"Message type '{actual_message_name}' is not constructible "
                                    f"using message literal syntax '{{}}'. It may be an abstract type "
                                    f"like Duration or Timestamp which must be created via functions.",
                                    expr_pb_root_for_error_reporting)
            return CEL_ERROR  # CEL_UNKNOWN から CEL_ERROR に変更

        if actual_message_name == "google.protobuf.Any":
            has_type_url = False

            if not struct_pb.entries:  # Any{} の場合
                self._record_type_error(node_id,
                                        f"Invalid conversion to 'google.protobuf.Any': "
                                        f"message literal for 'google.protobuf.Any' must specify at least 'type_url' field.",
                                        expr_pb_root_for_error_reporting)
                return CEL_ERROR

            for entry in struct_pb.entries:
                if not entry.HasField("field_key"):
                    self._record_type_error(entry.id if entry.id != 0 else node_id,
                                            f"Message construction for '{actual_message_name}' expects 'field_key'.",
                                            expr_pb_root_for_error_reporting)
                    return CEL_ERROR

                if entry.field_key == "type_url":
                    has_type_url = True
                    type_url_value_type = self._check_node(entry.value, type_map_for_pb, ref_map_for_pb,
                                                           current_declarations, expr_pb_root_for_error_reporting)
                    if type_url_value_type == CEL_ERROR or type_url_value_type == CEL_UNKNOWN: return type_url_value_type
                    if not self._is_assignable(type_url_value_type, CEL_STRING):
                        self._record_type_error(entry.value.id if entry.value and entry.value.id != 0 else entry.id,
                                                "Field 'type_url' for 'google.protobuf.Any' must be a string.",
                                                expr_pb_root_for_error_reporting)
                        return CEL_ERROR
                elif entry.field_key == "value":
                    value_field_type = self._check_node(entry.value, type_map_for_pb, ref_map_for_pb,
                                                        current_declarations, expr_pb_root_for_error_reporting)
                    if value_field_type == CEL_ERROR or value_field_type == CEL_UNKNOWN: return value_field_type
                    if not self._is_assignable(value_field_type, CEL_BYTES):
                        self._record_type_error(entry.value.id if entry.value and entry.value.id != 0 else entry.id,
                                                "Field 'value' for 'google.protobuf.Any' must be bytes.",
                                                expr_pb_root_for_error_reporting)
                        return CEL_ERROR
                elif entry.field_key:
                    self._record_type_error(entry.id if entry.id != 0 else node_id,
                                            f"Unknown field '{entry.field_key}' for message type 'google.protobuf.Any'. Allowed fields are 'type_url' and 'value'.",
                                            expr_pb_root_for_error_reporting)
                    return CEL_ERROR

            if not has_type_url:
                self._record_type_error(node_id,
                                        f"Invalid conversion to 'google.protobuf.Any': "
                                        f"message literal for 'google.protobuf.Any' is missing required field 'type_url'.",
                                        expr_pb_root_for_error_reporting)
                return CEL_ERROR

            return msg_cel_type

        for entry in struct_pb.entries:
            entry_node_id_for_error = entry.id if entry.id != 0 else node_id
            if not entry.HasField("field_key"):
                self._record_type_error(entry_node_id_for_error,
                                        f"Message construction for '{actual_message_name}' expects 'field_key'.",
                                        expr_pb_root_for_error_reporting)
                return CEL_ERROR  # CEL_UNKNOWN から CEL_ERROR に変更
            field_name = entry.field_key
            field_def_type = self.env.type_registry.get_field_cel_type(actual_message_name, field_name)
            if not field_def_type:
                self._record_type_error(entry_node_id_for_error,
                                        f"Unknown field '{field_name}' for message type '{actual_message_name}'.",
                                        expr_pb_root_for_error_reporting)
                return CEL_ERROR  # CEL_UNKNOWN から CEL_ERROR に変更

            value_cel_type = self._check_node(entry.value, type_map_for_pb, ref_map_for_pb, current_declarations,
                                              expr_pb_root_for_error_reporting)

            if value_cel_type == CEL_ERROR or value_cel_type == CEL_UNKNOWN:  # エラーまたは不明型を伝播
                return value_cel_type

            if not self._is_assignable(value_cel_type, field_def_type):
                self._record_type_error(entry.value.id if entry.value.id != 0 else entry_node_id_for_error,
                                        f"Type mismatch for field '{field_name}'. Expected {field_def_type.name}, got {value_cel_type.name}.",
                                        expr_pb_root_for_error_reporting)
                return CEL_ERROR  # CEL_UNKNOWN から CEL_ERROR に変更
        return msg_cel_type

    def _check_map_construction(self, node_id: int, struct_pb: syntax_pb2.Expr.CreateStruct,
                                type_map_for_pb: Dict[int, checked_pb2.Type],
                                ref_map_for_pb: Dict[int, checked_pb2.Reference],
                                current_declarations: Dict[str, CelType],
                                expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        if not struct_pb.entries: return make_map_type(CEL_DYN, CEL_DYN)  # Empty map is map<dyn, dyn>
        key_cel_types: List[CelType] = []
        value_cel_types: List[CelType] = []
        has_error_in_entry = False
        for entry in struct_pb.entries:
            entry_node_id_for_error = entry.id if entry.id != 0 else node_id
            if not entry.HasField("map_key"):
                self._record_type_error(entry_node_id_for_error, "Map construction entry expects 'map_key'.",
                                        expr_pb_root_for_error_reporting)
                has_error_in_entry = True;
                break  # Stop processing on first error
            key_type = self._check_node(entry.map_key, type_map_for_pb, ref_map_for_pb, current_declarations,
                                        expr_pb_root_for_error_reporting)
            if key_type == CEL_UNKNOWN: has_error_in_entry = True; break
            allowed_key_types = [CEL_INT, CEL_UINT, CEL_BOOL, CEL_STRING, CEL_DYN]
            if key_type not in allowed_key_types:
                self._record_type_error(entry.map_key.id if entry.map_key.id != 0 else entry_node_id_for_error,
                                        f"Invalid map key type: {key_type.name}. Must be int, uint, bool, string, or dyn.",
                                        expr_pb_root_for_error_reporting)
                has_error_in_entry = True;
                break
            value_type = self._check_node(entry.value, type_map_for_pb, ref_map_for_pb, current_declarations,
                                          expr_pb_root_for_error_reporting)
            if value_type == CEL_UNKNOWN: has_error_in_entry = True; break
            key_cel_types.append(key_type)
            value_cel_types.append(value_type)

        if has_error_in_entry: return CEL_UNKNOWN  # Error already recorded

        common_key_type = self._determine_common_type(key_cel_types)
        common_value_type = self._determine_common_type(value_cel_types)
        # Validate derived common key type
        if common_key_type not in [CEL_INT, CEL_UINT, CEL_BOOL, CEL_STRING, CEL_DYN]:
            self._record_type_error(node_id,  # Error on the map construction node itself
                                    f"Derived map key type '{common_key_type.name}' is not one of int, uint, bool, string, or dyn.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN
        return make_map_type(common_key_type, common_value_type)

    def _handle_struct_expr_check(self, node_pb: syntax_pb2.Expr, type_map_for_pb: Dict[int, checked_pb2.Type],
                                  ref_map_for_pb: Dict[int, checked_pb2.Reference],
                                  current_declarations: Dict[str, CelType],
                                  expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        struct_pb = node_pb.struct_expr
        if struct_pb.message_name:
            return self._check_message_construction(node_pb.id, struct_pb, type_map_for_pb, ref_map_for_pb,
                                                    current_declarations, expr_pb_root_for_error_reporting)
        else:  # Map construction
            return self._check_map_construction(node_pb.id, struct_pb, type_map_for_pb, ref_map_for_pb,
                                                current_declarations, expr_pb_root_for_error_reporting)

    # --- _handle_select_expr_check の分割 ---
    def _check_select_test_only(self, node_id: int, op_type: CelType, field_name_str: str,
                                expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        if not field_name_str:  # has(ident)
            return CEL_BOOL

        if op_type == CEL_VALUE_WRAPPER:  # ★ has(Value.field)
            # Valueがstruct_valueを内包する場合、キーが存在するかのチェック。結果はbool。
            return CEL_BOOL

        if op_type == TYPE_STRUCT_AS_MAP:  # has(Struct.field)
            return CEL_BOOL

        # ... (既存の is_message_type や ParameterizedCelType (_MAP_BASE_TYPE) の処理 for has) ...
        # 通常のProtobufメッセージの has()
        if self.env.type_registry.is_message_type(op_type.name) and \
                not op_type == CEL_VALUE_WRAPPER:
            # type_registry.has_field がproto2/3のセマンティクスを考慮してboolを返すか、
            # あるいはここで詳細なロジックが必要。
            # 簡単には、フィールド定義があればtrueとみなす（実行時の値は問わない）。
            if self.env.type_registry.has_field(op_type.name, field_name_str):
                return CEL_BOOL
            else:
                if '.' in field_name_str:
                    if self._try_resolve_as_extension_field(op_type, field_name_str):

                        return CEL_BOOL

                # 厳密にはフィールドが存在しないエラーだが、has() の結果としてはfalseになるべき。
                # ただし、型チェックでエラーを出すならそれでも良い。
                # ここでは、フィールド定義がなければエラーとする。
                self._record_type_error(node_id,
                                        f"Unknown field '{field_name_str}' for message type '{op_type.name}' in 'has' macro.")
                return CEL_UNKNOWN  # または CEL_BOOL (falseの意味で)

        # 通常のCELマップの has()
        elif isinstance(op_type, ParameterizedCelType) and op_type.base_type == _MAP_BASE_TYPE:
            if self._is_assignable(CEL_STRING, op_type.params[0]) or op_type.params[0] == CEL_DYN:
                return CEL_BOOL
            else:
                self._record_type_error(node_id,
                                        f"'has(map.field)' on map expects string-compatible keys, but map has key type {op_type.params[0].name}.")
                return CEL_UNKNOWN
        elif isinstance(op_type, CelType) and op_type == CEL_DYN:
            return CEL_BOOL

        self._record_type_error(node_id, f"'has' macro with field selector unsupported on type '{op_type.name}'.")
        return CEL_UNKNOWN  # または CEL_BOOL (falseの意味で)

    # _handle_call_expr_check は、基本的には _resolve_and_check_function_call に委ねる。
    # _resolve_and_check_function_call が standard_definitions のオーバーロードを
    # 見つけられるように、standard_definitions 側を充実させる。

    def _check_select_field_access(self, node_id: int, op_type: CelType, field_name_str: str,
                                   expr_pb_root_for_error_reporting: syntax_pb2.Expr,
                                   operand_node: syntax_pb2.Expr,
                                   ref_map_for_pb: Dict[int, checked_pb2.Reference]
                                   ) -> CelType:
        if op_type == CEL_DYN: return CEL_DYN

        if op_type == CEL_TYPE:
            operand_actual_name = self._get_name_from_expr_node_for_checker(operand_node, ref_map_for_pb)
            if not operand_actual_name:
                self._record_type_error(node_id,
                                        f"Cannot determine base name for select of '{field_name_str}' on type literal/namespace.",
                                        expr_pb_root_for_error_reporting)
                return CEL_UNKNOWN

            potential_fq_name = f"{operand_actual_name}.{field_name_str}"

            # 1. potential_fq_name が Enum値か？
            if self.env.type_registry.is_enum_type(operand_actual_name):  # オペランドがEnum型名
                enum_val_num = self.env.type_registry.get_enum_value(operand_actual_name, field_name_str)
                if enum_val_num is not None:
                    if node_id != 0: ref_map_for_pb[node_id] = checked_pb2.Reference(name=potential_fq_name)
                    return CEL_INT

                    # 2. potential_fq_name が 型リテラル (メッセージ型, Enum型名) またはパッケージ名か？

            resolved_nested_type = self._resolve_ident_as_type_or_enum_value_or_package(
                potential_fq_name, node_id, ref_map_for_pb
            )
            if resolved_nested_type:  # これがCEL_TYPEまたはCEL_INTを返す
                return resolved_nested_type

            resolved_type_or_enum_val = self._resolve_ident_as_type_or_enum_value_or_package(
                potential_fq_name,
                node_id,
                ref_map_for_pb)
            if resolved_type_or_enum_val:
                return resolved_type_or_enum_val

            self._record_type_error(node_id,
                                    f"Name '{field_name_str}' cannot be resolved on type/namespace '{operand_actual_name}'.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN


        # ... (既存のメッセージ、マップなどのフィールドアクセス処理) ...
        if op_type == CEL_VALUE_WRAPPER: return CEL_VALUE_WRAPPER
        if hasattr(op_type, 'name') and op_type.name == TYPE_STRUCT_AS_MAP.name: return CEL_VALUE_WRAPPER
        if self.env.type_registry.is_message_type(op_type.name) and not op_type == CEL_VALUE_WRAPPER:
            field_type = self.env.type_registry.get_field_cel_type(op_type.name, field_name_str)
            if not field_type:
                field_type = self._try_resolve_as_extension_field(op_type, field_name_str)

            if field_type:
                if node_id != 0: ref_map_for_pb[node_id] = checked_pb2.Reference(name=field_name_str)
                return field_type
            else:
                self._record_type_error(node_id, f"Unknown field '{field_name_str}' for message type '{op_type.name}'.",
                                        expr_pb_root_for_error_reporting)
                return CEL_UNKNOWN
        elif isinstance(op_type, ParameterizedCelType) and op_type.base_type == _MAP_BASE_TYPE:
            allowed_map_key_types = [CEL_STRING, CEL_INT, CEL_UINT, CEL_BOOL, CEL_DYN]
            if op_type.params[0] in allowed_map_key_types or self._is_assignable(CEL_STRING, op_type.params[0]):
                if node_id != 0: ref_map_for_pb[node_id] = checked_pb2.Reference(name=field_name_str)
                return op_type.params[1]
            else:
                self._record_type_error(node_id,
                                        f"Map key type '{op_type.params[0].name}' is not valid for field-like access with '{field_name_str}'.",
                                        expr_pb_root_for_error_reporting)
                return CEL_UNKNOWN

        op_type_name_for_error = op_type.name if hasattr(op_type, 'name') else str(op_type)
        self._record_type_error(node_id,
                                f"Type '{op_type_name_for_error}' does not support field selection for '{field_name_str}'.",
                                expr_pb_root_for_error_reporting)
        return CEL_UNKNOWN

    def _handle_select_expr_check(self, node_pb: syntax_pb2.Expr, type_map_for_pb: Dict[int, checked_pb2.Type],
                                  ref_map_for_pb: Dict[int, checked_pb2.Reference],
                                  current_declarations: Dict[str, CelType],
                                  expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        select = node_pb.select_expr
        node_id = node_pb.id
        field_name_str = select.field

        # 1. select式全体が1つの修飾識別子として解決できるか試す
        full_name_attempt = self._get_name_from_expr_node_for_checker(node_pb, ref_map_for_pb)

        if full_name_attempt:
            # 1a. 完全修飾名が変数として宣言されているか
            resolved_as_var = self._resolve_identifier_type_in_declarations(full_name_attempt, current_declarations)
            if resolved_as_var:
                if node_id != 0:
                    ref_map_for_pb[node_id] = checked_pb2.Reference(name=full_name_attempt)

                return resolved_as_var

            # 1b. 完全修飾名が型リテラル、Enum値、またはパッケージ名か
            resolved_as_other = self._resolve_ident_as_type_or_enum_value_or_package(
                full_name_attempt, node_id, ref_map_for_pb
            )
            if resolved_as_other:
                return resolved_as_other

        # 2. 完全修飾名として解決できなかった場合、オペランドを評価し、フィールド選択を行う
        op_type = self._check_node(select.operand, type_map_for_pb, ref_map_for_pb, current_declarations,
                                   expr_pb_root_for_error_reporting)

        if op_type == CEL_ERROR or op_type == CEL_UNKNOWN:
            return op_type

        if select.test_only:
            return self._check_select_test_only(node_id, op_type, field_name_str, expr_pb_root_for_error_reporting)
        else:
            return self._check_select_field_access(node_id, op_type, field_name_str, expr_pb_root_for_error_reporting,
                                                   select.operand, ref_map_for_pb)

    # --- _handle_call_expr_check の分割 ---
    def _check_logical_operator(self, node_id: int, func_name: str, arg_cel_types: List[CelType],
                                call_args_expr: List[syntax_pb2.Expr],
                                expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        if len(arg_cel_types) != 2:
            self._record_type_error(node_id, f"Operator '{func_name}' expects 2 arguments.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN

        arg0_node_id = call_args_expr[0].id if call_args_expr and call_args_expr[0].id != 0 else node_id
        arg1_node_id = call_args_expr[1].id if len(call_args_expr) > 1 and call_args_expr[1].id != 0 else node_id

        if not self._is_assignable(arg_cel_types[0], CEL_BOOL):
            self._record_type_error(arg0_node_id,
                                    f"Left operand for '{func_name}' must be bool, got {arg_cel_types[0].name}.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN
        if not self._is_assignable(arg_cel_types[1], CEL_BOOL):
            self._record_type_error(arg1_node_id,
                                    f"Right operand for '{func_name}' must be bool, got {arg_cel_types[1].name}.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN
        return CEL_BOOL

    def _check_comparison_operator(self, node_id: int, func_name: str, arg_cel_types: List[CelType],
                                   expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        if len(arg_cel_types) != 2:
            self._record_type_error(node_id, f"Operator '{func_name}' expects 2 arguments.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN

        t1, t2 = arg_cel_types[0], arg_cel_types[1]

        if t1 == CEL_DYN or t2 == CEL_DYN:
            return CEL_BOOL

        is_equality_op = func_name in ["_==_", "_!=_"]

        # Value型が関与する場合、より寛容に (CELの動的型の性質を反映)
        # Valueは実行時にプリミティブに変換されるため、型チェッカーは比較を許可する
        if t1 == CEL_VALUE_WRAPPER or t2 == CEL_VALUE_WRAPPER:
            # 相手方が比較可能な型か (Value, DYN, Null, プリミティブ)
            # DYNは上で処理済み
            comparable_with_value_types = [
                CEL_NULL, CEL_BOOL, CEL_INT, CEL_UINT, CEL_DOUBLE,
                CEL_STRING, CEL_BYTES, CEL_TIMESTAMP, CEL_DURATION,
                CEL_VALUE_WRAPPER  # Value同士
            ]
            other_type = t2 if t1 == CEL_VALUE_WRAPPER else t1
            if other_type in comparable_with_value_types:
                return CEL_BOOL
            # Value とリスト/マップの直接比較は依然としてエラーが適切

        # 等価性演算子での NULL との比較
        if is_equality_op and (t1 == CEL_NULL or t2 == CEL_NULL):
            return CEL_BOOL

        if is_equality_op:
            wrapper_to_primitive_map = {
                CEL_BOOL_WRAPPER: CEL_BOOL,
                CEL_INT32_WRAPPER: CEL_INT,
                CEL_INT64_WRAPPER: CEL_INT,
                CEL_UINT32_WRAPPER: CEL_UINT,
                CEL_UINT64_WRAPPER: CEL_UINT,
                CEL_DOUBLE_WRAPPER: CEL_DOUBLE,
                CEL_FLOAT_WRAPPER: CEL_DOUBLE,
                CEL_STRING_WRAPPER: CEL_STRING,
                CEL_BYTES_WRAPPER: CEL_BYTES,
            }

            # t1がラッパー型で、t2がそのプリミティブ型であるか
            if t1 in wrapper_to_primitive_map and wrapper_to_primitive_map[t1] == t2:
                return CEL_BOOL
            # t2がラッパー型で、t1がそのプリミティブ型であるか
            if t2 in wrapper_to_primitive_map and wrapper_to_primitive_map[t2] == t1:
                return CEL_BOOL

        if is_equality_op and isinstance(t1, ParameterizedCelType) and isinstance(t2, ParameterizedCelType) and \
                t1.base_type == t2.base_type:  # 両方ともリスト型、または両方ともマップ型

            if t1.base_type == _LIST_BASE_TYPE:  # list<T1> vs list<T2>
                t1_elem_type = t1.params[0]
                t2_elem_type = t2.params[0]
                # 要素の型が一致するか、どちらかの要素型がDYNであれば比較を許可
                if t1_elem_type == t2_elem_type or \
                        t1_elem_type == CEL_DYN or t2_elem_type == CEL_DYN:
                    return CEL_BOOL

            elif t1.base_type == _MAP_BASE_TYPE:  # map<K1,V1> vs map<K2,V2>
                t1_key_type, t1_val_type = t1.params[0], t1.params[1]
                t2_key_type, t2_val_type = t2.params[0], t2.params[1]

                # キー型が互換 (一致またはDYN) かつ 値型が互換 (一致またはDYN) であれば比較を許可
                keys_compatible = (t1_key_type == t2_key_type or
                                   t1_key_type == CEL_DYN or t2_key_type == CEL_DYN)
                vals_compatible = (t1_val_type == t2_val_type or
                                   t1_val_type == CEL_DYN or t2_val_type == CEL_DYN)

                if keys_compatible and vals_compatible:
                    # マップキー型がCELで許可されている型であるかの追加チェックは
                    # 型システム(_parse_cel_type_from_string や make_map_type)側で行われている想定
                    return CEL_BOOL

        # 厳密な型同士の比較
        num_types = [CEL_INT, CEL_UINT, CEL_DOUBLE]
        if t1 in num_types and t2 in num_types: return CEL_BOOL
        if t1 == CEL_STRING and t2 == CEL_STRING: return CEL_BOOL
        if t1 == CEL_BYTES and t2 == CEL_BYTES: return CEL_BOOL
        if t1 == CEL_TIMESTAMP and t2 == CEL_TIMESTAMP: return CEL_BOOL
        if t1 == CEL_DURATION and t2 == CEL_DURATION: return CEL_BOOL
        if t1 == CEL_BOOL and t2 == CEL_BOOL: return CEL_BOOL  # bool同士は順序比較も可 (false < true)

        if is_equality_op and t1 == CEL_TYPE and t2 == CEL_TYPE: return CEL_BOOL

        # 型が完全に一致し、上記のいずれでもない場合 (例：list<int> == list<int>)
        # 等価性比較は許容されることが多い
        if is_equality_op and t1 == t2:
            return CEL_BOOL

        self._record_type_error(node_id, f"op '{func_name}' cannot compare '{t1.name}' and '{t2.name}'.",
                                expr_pb_root_for_error_reporting)
        return CEL_UNKNOWN

    def _check_ternary_operator(self, node_id: int, arg_cel_types: List[CelType],
                                call_args_expr: List[syntax_pb2.Expr],
                                expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        if len(arg_cel_types) != 3:
            self._record_type_error(node_id, f"Operator '_?_:_' expects 3 arguments.", expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN
        cond_type, true_type, false_type = arg_cel_types[0], arg_cel_types[1], arg_cel_types[2]
        cond_node_id = call_args_expr[0].id if call_args_expr and call_args_expr[0].id != 0 else node_id
        if not self._is_assignable(cond_type, CEL_BOOL):
            self._record_type_error(cond_node_id,
                                    f"Condition for '_?_:_' must be bool, got {cond_type.name}.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN
        return self._determine_common_type([true_type, false_type])

    def _check_arithmetic_operator(self, node_id: int, func_name: str, arg_cel_types: List[CelType],
                                   expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        # This is a simplified version for common arithmetic. Specific operators might need more detail.
        # Example: '+' handles strings, lists, numerics, time types.
        # Other operators like '-', '*', '/', '%' are typically numeric or DYN.
        if len(arg_cel_types) != 2 and not (func_name == "_-_" and len(arg_cel_types) == 1):  # Unary minus
            self._record_type_error(node_id, f"Operator '{func_name}' arity mismatch.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN

        if func_name == "_+_":  # Delegate to specific addition handler due to its complexity
            return self._check_addition_operator(node_id, arg_cel_types, expr_pb_root_for_error_reporting)

        # For other binary arithmetic ops (simplified):
        if len(arg_cel_types) == 2:
            t1, t2 = arg_cel_types[0], arg_cel_types[1]
            if t1 == CEL_DYN or t2 == CEL_DYN: return CEL_DYN
            num_types = [CEL_INT, CEL_UINT, CEL_DOUBLE]
            if t1 in num_types and t2 in num_types:
                if t1 == CEL_DOUBLE or t2 == CEL_DOUBLE: return CEL_DOUBLE
                if t1 == CEL_UINT and t2 == CEL_UINT and func_name not in ["_-_"]:  # uint - uint can be int if negative
                    return CEL_UINT
                return CEL_INT  # Default to INT for mixed int/uint or int/int
            # Specific WKT arithmetic (e.g., Timestamp - Duration) would be handled by function resolution.
            self._record_type_error(node_id,
                                    f"Operator '{func_name}' cannot be applied to '{t1.name}' and '{t2.name}'.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN
        # Unary minus
        elif func_name == "_-_" and len(arg_cel_types) == 1:
            t1 = arg_cel_types[0]
            if t1 == CEL_DYN: return CEL_DYN
            if t1 == CEL_INT: return CEL_INT
            if t1 == CEL_DOUBLE: return CEL_DOUBLE
            if t1 == CEL_UINT: return CEL_INT  # -uint -> int
            # WKTs like Duration might support unary minus.
            self._record_type_error(node_id, f"Operator unary '-' cannot be applied to '{t1.name}'.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN

        return CEL_UNKNOWN  # Should not reach here

    def _normalize_for_numeric_ops(self, type_val: CelType) -> CelType:
        """
        数値演算のために型を正規化します。
        例えば、Int32ValueラッパーはINTとして扱います。
        今後他の数値ラッパー型（BoolValueをBOOLとして扱うなど）を追加する場合もここに追記します。
        """
        if type_val == CEL_INT32_WRAPPER:
            return CEL_INT
        # 例: if type_val == CEL_DOUBLE_WRAPPER: return CEL_DOUBLE
        return type_val


    # 現状は+しかまともに型チェックはしていない。量産すると修正が困難になるので
    # additiveでいい感じの仕組みがつくれたら他に適用する
    def _check_addition_operator(self, node_id: int, arg_cel_types: List[CelType],
                                 expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        if len(arg_cel_types) != 2:
            self._record_type_error(node_id, f"Operator '_+_' expects 2 arguments.", expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN

        t1_orig, t2_orig = arg_cel_types[0], arg_cel_types[1]

        # 1. DYN の早期処理: いずれかが DYN なら結果も DYN (ただしリスト結合の場合は list<DYN>)
        if t1_orig == CEL_DYN or t2_orig == CEL_DYN:
            # もう片方がリスト系(CEL_LIST, ParameterizedList, CEL_LIST_WRAPPER, またはCEL_VALUE_WRAPPERがリストを内包しうる)
            # であれば list<DYN> を返す。そうでなければ CEL_DYN。
            # Valueがリストかは不明なので、Value+DynはDyn、ListWrapper+DynはList<Dyn>。
            t1_is_explicit_list = isinstance(t1_orig, ParameterizedCelType) and t1_orig.base_type == _LIST_BASE_TYPE or \
                                  t1_orig == CEL_LIST or t1_orig == CEL_LIST_WRAPPER
            t2_is_explicit_list = isinstance(t2_orig, ParameterizedCelType) and t2_orig.base_type == _LIST_BASE_TYPE or \
                                  t2_orig == CEL_LIST or t2_orig == CEL_LIST_WRAPPER
            if t1_is_explicit_list or t2_is_explicit_list:
                return make_list_type(CEL_DYN)
            return CEL_DYN

        # 2. CEL_VALUE_WRAPPER が関わる場合の処理 (DYN の後)
        #    Value + X  または X + Value の場合、結果は CEL_DYN とする (リスト結合を除く)
        #    実行時に Value の中身に応じて具体的な演算が行われる。
        if t1_orig == CEL_VALUE_WRAPPER or t2_orig == CEL_VALUE_WRAPPER:
            other_type = t2_orig if t1_orig == CEL_VALUE_WRAPPER else t1_orig
            # Value + List系 -> list<DYN>
            if isinstance(other_type, ParameterizedCelType) and other_type.base_type == _LIST_BASE_TYPE or \
                    other_type == CEL_LIST or other_type == CEL_LIST_WRAPPER:
                return make_list_type(CEL_DYN)
            # Value + Value -> list<DYN> (Valueが両方リストの場合) または DYN (それ以外)
            # 型チェッカーはValueの中身を知らないため、Value + Value は DYN が安全
            if t1_orig == CEL_VALUE_WRAPPER and t2_orig == CEL_VALUE_WRAPPER:  # Value + Value
                # 片方がリスト、もう片方が非リストならエラーだが、ここではDYN
                return CEL_DYN
            return CEL_DYN  # Value + (数値/文字列/boolなど) -> DYN

        # --- 以下は t1_orig と t2_orig が DYN でも VALUE_WRAPPER でもない場合 ---

        # 3. 数値型 (正規化後の型で判定)
        t1_norm, t2_norm = self._normalize_for_numeric_ops(t1_orig), self._normalize_for_numeric_ops(t2_orig)
        num_types = [CEL_INT, CEL_UINT, CEL_DOUBLE]
        if t1_norm in num_types and t2_norm in num_types:
            if t1_norm == CEL_DOUBLE or t2_norm == CEL_DOUBLE: return CEL_DOUBLE
            if t1_norm == CEL_UINT and t2_norm == CEL_UINT: return CEL_UINT
            return CEL_INT  # int + uint or uint + int -> int (CEL仕様確認要)

        # 4. 文字列結合
        if t1_orig == CEL_STRING and t2_orig == CEL_STRING: return CEL_STRING
        # 5. バイト列結合
        if t1_orig == CEL_BYTES and t2_orig == CEL_BYTES: return CEL_BYTES

        # 6. リスト結合 (CEL_LIST_WRAPPER と CEL_LIST を含む)
        #    (CEL_VALUE_WRAPPER が関わるケースは上記で処理済み)
        # CEL_LIST_WRAPPER (list<Value>) + CEL_LIST_WRAPPER (list<Value>) -> list<Value>
        if t1_orig == CEL_LIST_WRAPPER and t2_orig == CEL_LIST_WRAPPER:
            return make_list_type(CEL_VALUE_WRAPPER)
        # CEL_LIST_WRAPPER (list<Value>) + CEL_LIST (list<dyn>) -> list<dyn>
        if (t1_orig == CEL_LIST_WRAPPER and t2_orig == CEL_LIST) or \
                (t1_orig == CEL_LIST and t2_orig == CEL_LIST_WRAPPER):
            return make_list_type(CEL_DYN)
        # CEL_LIST_WRAPPER (list<Value>) + list<T> (T != Value, T != dyn) -> list<dyn>
        if (t1_orig == CEL_LIST_WRAPPER and isinstance(t2_orig,
                                                       ParameterizedCelType) and t2_orig.base_type == _LIST_BASE_TYPE) or \
                (isinstance(t1_orig,
                            ParameterizedCelType) and t1_orig.base_type == _LIST_BASE_TYPE and t2_orig == CEL_LIST_WRAPPER):
            # 要素型が Value と T (DYNでもValueでもない) なので、結果は list<dyn>
            return make_list_type(CEL_DYN)

        # 通常の ParameterizedList + ParameterizedList (例: list<int> + list<string> -> list<dyn>)
        if isinstance(t1_orig, ParameterizedCelType) and t1_orig.base_type == _LIST_BASE_TYPE and \
                isinstance(t2_orig, ParameterizedCelType) and t2_orig.base_type == _LIST_BASE_TYPE:
            return make_list_type(self._determine_common_type([t1_orig.params[0], t2_orig.params[0]]))
        # ParameterizedList + CEL_LIST (list<dyn>) -> list<dyn>
        if (isinstance(t1_orig,
                       ParameterizedCelType) and t1_orig.base_type == _LIST_BASE_TYPE and t2_orig == CEL_LIST) or \
                (t1_orig == CEL_LIST and isinstance(t2_orig,
                                                    ParameterizedCelType) and t2_orig.base_type == _LIST_BASE_TYPE):
            return make_list_type(CEL_DYN)
        # CEL_LIST (list<dyn>) + CEL_LIST (list<dyn>) -> list<dyn>
        if t1_orig == CEL_LIST and t2_orig == CEL_LIST:
            return make_list_type(CEL_DYN)

        # 7. Timestamp と Duration の加算
        if (t1_orig == CEL_TIMESTAMP and t2_orig == CEL_DURATION) or \
                (t1_orig == CEL_DURATION and t2_orig == CEL_TIMESTAMP):
            return CEL_TIMESTAMP
        if t1_orig == CEL_DURATION and t2_orig == CEL_DURATION:
            return CEL_DURATION

        # 上記のいずれにもマッチしない場合
        self._record_type_error(node_id,
                                f"Operator '_+_' cannot be applied to types '{t1_orig.name}' and '{t2_orig.name}'.",
                                expr_pb_root_for_error_reporting)
        return CEL_UNKNOWN

    def _resolve_and_check_function_call(self, node_id: int, func_name_from_ast: str,
                                         target_expr_for_call: Optional[syntax_pb2.Expr],
                                         target_type_of_operand: Optional[CelType],
                                         arg_cel_types: List[CelType],
                                         call_args_expr: List[syntax_pb2.Expr],
                                         ref_map_for_pb: Dict[int, checked_pb2.Reference],
                                         expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:

        # --- ▼▼▼ デバッグプリント追加 ▼▼▼ ---
        # print(
        #     f"\n[DEBUG CHECKER ENTRY] _resolve_and_check_function_call (for node_id: {node_id}, func_name_from_ast: '{func_name_from_ast}')")
        # if target_expr_for_call:
        #     print(
        #         f"  target_expr_for_call: id={target_expr_for_call.id}, kind={target_expr_for_call.WhichOneof('expr_kind')}")
        #     if target_expr_for_call.id in ref_map_for_pb:
        #         print(
        #             f"  ref_map entry for target_expr_for_call (id {target_expr_for_call.id}): {ref_map_for_pb[target_expr_for_call.id].name}")
        #     else:
        #         print(f"  No ref_map entry for target_expr_for_call (id {target_expr_for_call.id})")
        # else:
        #     print(f"  target_expr_for_call: None")

        if target_type_of_operand:
            is_cel_type_keyword = target_type_of_operand == CEL_TYPE
            # print(
            #     f"  target_type_of_operand: name='{target_type_of_operand.name if hasattr(target_type_of_operand, 'name') else str(target_type_of_operand)}', is_CEL_TYPE_keyword={is_cel_type_keyword}, type={type(target_type_of_operand)}")
        # else:
        #     print(f"  target_type_of_operand: None")

        arg_type_names = [t.name if hasattr(t, 'name') else str(t) for t in arg_cel_types]
        # print(f"  arg_cel_types: {arg_type_names}")
        # # --- ▲▲▲ デバッグプリント追加 ▲▲▲ ---

        enum_constructor_fq_name: Optional[str] = None

        # --- ▼▼▼ 条件分岐にもデバッグプリントを追加 ▼▼▼ ---
        if target_type_of_operand == CEL_TYPE and target_expr_for_call:
            # print(f"  [BRANCH 1] target_type_of_operand is CEL_TYPE and target_expr_for_call exists.")
            base_type_name = self._get_name_from_expr_node_for_checker(target_expr_for_call, ref_map_for_pb)
            # print(f"    _get_name_from_expr_node_for_checker returned: '{base_type_name}'")
            if base_type_name:
                prospective_enum_name = f"{base_type_name}.{func_name_from_ast}"
                # print(f"    Prospective enum name (Branch 1): '{prospective_enum_name}'")
                parsed_enum_type_candidate = self.env._parse_cel_type_from_string(prospective_enum_name)
                if parsed_enum_type_candidate and parsed_enum_type_candidate != CEL_UNKNOWN and \
                        self.env.type_registry.is_enum_type(parsed_enum_type_candidate.name):
                    enum_constructor_fq_name = parsed_enum_type_candidate.name
                    # print(f"    Enum constructor FQN (Branch 1): '{enum_constructor_fq_name}'")

        elif target_type_of_operand and target_type_of_operand != CEL_TYPE and \
                hasattr(target_type_of_operand, 'name'):
            # print(f"  [BRANCH 2] target_type_of_operand ('{target_type_of_operand.name}') is a concrete type.")
            prospective_enum_name = f"{target_type_of_operand.name}.{func_name_from_ast}"
            # print(f"    Prospective enum name (Branch 2): '{prospective_enum_name}'")
            # FQNが直接構成されるため、_parse_cel_type_from_string は不要かもしれないが、一貫性のため
            parsed_enum_type = self.env._parse_cel_type_from_string(prospective_enum_name)
            if parsed_enum_type and parsed_enum_type != CEL_UNKNOWN and \
                    self.env.type_registry.is_enum_type(parsed_enum_type.name):
                enum_constructor_fq_name = parsed_enum_type.name
                # print(f"    Enum constructor FQN (Branch 2): '{enum_constructor_fq_name}'")

        elif not target_type_of_operand:
            # print(f"  [BRANCH 3] No target_type_of_operand. func_name_from_ast: '{func_name_from_ast}'")
            parsed_enum_type = self.env._parse_cel_type_from_string(func_name_from_ast)
            if parsed_enum_type and parsed_enum_type != CEL_UNKNOWN:
                # print(
                #     f"    _parse_cel_type_from_string for '{func_name_from_ast}' -> '{parsed_enum_type.name}' (is_enum: {self.env.type_registry.is_enum_type(parsed_enum_type.name)})")
                if self.env.type_registry.is_enum_type(parsed_enum_type.name):
                    enum_constructor_fq_name = parsed_enum_type.name
                    # print(f"    Enum constructor FQN (Branch 3): '{enum_constructor_fq_name}'")
            # else:
            #     print(f"    _parse_cel_type_from_string for '{func_name_from_ast}' -> None or UNKNOWN")

        # --- ▲▲▲ 条件分岐のデバッグプリント追加 ▲▲▲ ---

        if enum_constructor_fq_name:
            # Enumコンストラクタ呼び出しとして処理
            if len(arg_cel_types) == 1:
                arg_type = arg_cel_types[0]
                arg_node_id_for_error = node_id
                if call_args_expr and call_args_expr[0] and call_args_expr[0].id != 0:
                    arg_node_id_for_error = call_args_expr[0].id

                # --- ▼▼▼ MODIFICATION: 引数型チェックに CEL_STRING を追加 ▼▼▼ ---
                is_valid_arg_type = False
                if self._is_assignable(arg_type, CEL_INT) or \
                        arg_type == CEL_UINT or \
                        arg_type == CEL_DYN:  # DYN は整数または文字列を表す可能性がある
                    is_valid_arg_type = True
                elif arg_type == CEL_STRING:  # 文字列引数も許可
                    is_valid_arg_type = True
                # --- ▲▲▲ MODIFICATION ▲▲▲ ---

                if is_valid_arg_type:
                    if node_id != 0:
                        ref_map_for_pb[node_id] = checked_pb2.Reference(name=enum_constructor_fq_name)
                    return CEL_INT  # Enum値の結果型は常に int
                else:
                    self._record_type_error(arg_node_id_for_error,
                                            f"Enum constructor for '{enum_constructor_fq_name}' expects an integer, string, or dyn argument, got {arg_type.name}.",
                                            expr_pb_root_for_error_reporting)
                    return CEL_UNKNOWN
            else:
                self._record_type_error(node_id,
                                        f"Enum constructor for '{enum_constructor_fq_name}' expects 1 argument, got {len(arg_cel_types)}.",
                                        expr_pb_root_for_error_reporting)
                return CEL_UNKNOWN

        # print(f"  Not an enum constructor. Proceeding to standard function resolution for '{func_name_from_ast}'.")
        # ... (通常の関数解決ロジックは同じ) ...

        # 2. Enumコンストラクタでなければ、通常の関数/メソッド解決
        resolved_func_def = self.env.builtins.resolve(func_name_from_ast, target_type_of_operand, arg_cel_types)
        if resolved_func_def:
            if node_id != 0:
                overload_id_str = resolved_func_def.name  # Fallback
                if hasattr(resolved_func_def, 'overload_id') and resolved_func_def.overload_id:  # type: ignore
                    overload_id_str = resolved_func_def.overload_id  # type: ignore
                elif resolved_func_def.is_method and target_type_of_operand and hasattr(target_type_of_operand, 'name'):
                    overload_id_str = f"{target_type_of_operand.name}.{resolved_func_def.name}({','.join(t.name for t in resolved_func_def.arg_types)})"
                else:
                    overload_id_str = f"{resolved_func_def.name}({','.join(t.name for t in resolved_func_def.arg_types)})"
                ref_map_for_pb[node_id] = checked_pb2.Reference(name=func_name_from_ast, overload_id=[overload_id_str])
            return resolved_func_def.result_type
        else:
            # エラーメッセージ生成
            t_repr = "global scope"
            if target_type_of_operand:
                t_repr = target_type_of_operand.name if hasattr(target_type_of_operand, 'name') else str(
                    target_type_of_operand)

            a_repr = ", ".join([t.name for t in arg_cel_types])

            # WKTコンストラクタ (例: Int32Value(10)) の場合、builtins.resolveで見つかるはず。
            # もし見つからなければ、それは未登録の関数。
            if not target_type_of_operand:  # グローバル関数コンテキスト
                parsed_as_msg_type = self.env._parse_cel_type_from_string(func_name_from_ast)
                # is_message_constructible は TypeRegistry にある。
                # ここでは、 func_name_from_ast が登録済みのメッセージ型で、かつ builtins.resolve で見つからなかった場合。
                if parsed_as_msg_type and self.env.type_registry.is_message_type(parsed_as_msg_type.name):
                    # is_message_constructible フラグはCELの {} 構文用。
                    # ここでは関数呼び出し形式のWKTコンストラクタを想定。
                    # これらは builtins にCelFunctionDefinitionとして登録されているべき。
                    self._record_type_error(node_id,
                                            f"No matching function overload found for constructor-like call to message type '{parsed_as_msg_type.name}' with arguments ({a_repr}). Ensure a CEL function (e.g. for WKT) is registered for it.",
                                            expr_pb_root_for_error_reporting)
                    return CEL_UNKNOWN

            self._record_type_error(node_id,
                                    f"No matching overload for function '{func_name_from_ast}' on target '{t_repr}' with arguments ({a_repr}).",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN

    def _handle_call_expr_check(self, node_pb: syntax_pb2.Expr, type_map_for_pb: Dict[int, checked_pb2.Type],
                                ref_map_for_pb: Dict[int, checked_pb2.Reference],
                                current_declarations: Dict[str, CelType],
                                expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        call = node_pb.call_expr
        node_id = node_pb.id
        func_name = call.function

        arg_cel_types: List[CelType] = []
        for arg_node in call.args:
            arg_type = self._check_node(arg_node, type_map_for_pb, ref_map_for_pb, current_declarations,
                                        expr_pb_root_for_error_reporting)
            if arg_type == CEL_UNKNOWN: return CEL_UNKNOWN
            arg_cel_types.append(arg_type)

        target_cel_type: Optional[CelType] = None
        target_expr_node: Optional[syntax_pb2.Expr] = None # Store the target expression node itself

        if call.HasField("target"):
            target_expr_node = call.target
            target_cel_type = self._check_node(call.target, type_map_for_pb, ref_map_for_pb, current_declarations,
                                               expr_pb_root_for_error_reporting)
            if target_cel_type == CEL_UNKNOWN: return CEL_UNKNOWN # Propagate error

        # Dispatch to specific handlers for built-in operators
        if func_name in ["_&&_", "_||_"]:
            return self._check_logical_operator(node_id, func_name, arg_cel_types, list(call.args),
                                                expr_pb_root_for_error_reporting)
        elif func_name in ["_<_", "_<=_", "_>_", "_>=_", "_==_", "_!=_"]:
            return self._check_comparison_operator(node_id, func_name, arg_cel_types, expr_pb_root_for_error_reporting)
        elif func_name == "_?_:_":
            return self._check_ternary_operator(node_id, arg_cel_types, list(call.args),
                                                expr_pb_root_for_error_reporting)
        elif func_name in ["_+_", "_-_", "_*_", "_/_", "_%_"]:  # Group arithmetic operators
            # Unary minus is also "_-_" but with 1 arg.
            if func_name == "_-_" and len(arg_cel_types) == 1:  # Unary minus
                # Pass to _check_arithmetic_operator which can handle unary based on arity
                pass  # Fall through to _resolve_and_check_function_call for unary '-'
            elif func_name == "_+_":
                return self._check_addition_operator(node_id, arg_cel_types, expr_pb_root_for_error_reporting)
            # Other binary arithmetic ops can be handled by a more generic arithmetic checker or by function resolution
            # This is a placeholder, specific WKT arithmetic should be resolved by function registry
            # return self._check_arithmetic_operator(node_id, func_name, arg_cel_types, expr_pb_root_for_error_reporting)
            # For now, let general resolution handle them, which is more flexible for WKTs.

        # For all other functions (including user-defined and remaining operators)
        return self._resolve_and_check_function_call(
            node_id,
            func_name,                  # The function name string from call.function
            target_expr_node,           # The AST node of the call's target (e.g., Ident("TestAllTypes"))
            target_cel_type,            # The resolved CelType of that target AST node
            arg_cel_types,
            list(call.args),            # Pass the original argument expressions for detailed error reporting
            ref_map_for_pb,
            expr_pb_root_for_error_reporting
        )

    def _handle_comprehension_expr_check(self, node_pb: syntax_pb2.Expr, type_map_for_pb: Dict[int, checked_pb2.Type],
                                         ref_map_for_pb: Dict[int, checked_pb2.Reference],
                                         current_declarations: Dict[str, CelType],
                                         expr_pb_root_for_error_reporting: syntax_pb2.Expr) -> CelType:
        comp = node_pb.comprehension_expr
        node_id = node_pb.id
        iter_range_type = self._check_node(comp.iter_range, type_map_for_pb, ref_map_for_pb, current_declarations,
                                           expr_pb_root_for_error_reporting)
        if iter_range_type == CEL_UNKNOWN: return CEL_UNKNOWN

        iter_elem_type = CEL_DYN
        is_range_valid = False
        if isinstance(iter_range_type, ParameterizedCelType):
            if iter_range_type.base_type == _LIST_BASE_TYPE:
                iter_elem_type, is_range_valid = iter_range_type.params[0], True
            elif iter_range_type.base_type == _MAP_BASE_TYPE:  # Comprehension over map iterates keys
                iter_elem_type, is_range_valid = iter_range_type.params[0], True  # iter_var gets key type
        elif iter_range_type == CEL_DYN or iter_range_type == CEL_LIST:  # list<dyn>
            iter_elem_type, is_range_valid = CEL_DYN, True
        # Add WKTs that are iterable, e.g. google.protobuf.ListValue
        # elif iter_range_type.name == "google.protobuf.ListValue": # Assuming ListValue is list<Value>
        #    iter_elem_type, is_range_valid = self.env._parse_cel_type_from_string("google.protobuf.Value"), True

        if not is_range_valid:
            self._record_type_error(comp.iter_range.id or node_id,
                                    f"Iteration range for comprehension must be a list, map, or dyn (or supported iterable WKT); found type '{iter_range_type.name}'.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN

        comprehension_scope = current_declarations.copy()
        comprehension_scope[comp.iter_var] = iter_elem_type

        accu_init_type = self._check_node(comp.accu_init, type_map_for_pb, ref_map_for_pb, comprehension_scope,
                                          expr_pb_root_for_error_reporting)
        if accu_init_type == CEL_UNKNOWN: return CEL_UNKNOWN

        comprehension_scope[comp.accu_var] = accu_init_type

        cond_type = self._check_node(comp.loop_condition, type_map_for_pb, ref_map_for_pb, comprehension_scope,
                                     expr_pb_root_for_error_reporting)
        if cond_type == CEL_UNKNOWN: return CEL_UNKNOWN
        if not self._is_assignable(cond_type, CEL_BOOL):
            self._record_type_error(comp.loop_condition.id or node_id,
                                    f"Loop condition in comprehension must be bool, got {cond_type.name}.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN

        step_type = self._check_node(comp.loop_step, type_map_for_pb, ref_map_for_pb, comprehension_scope,
                                     expr_pb_root_for_error_reporting)
        if step_type == CEL_UNKNOWN: return CEL_UNKNOWN

        if not self._is_assignable(step_type, accu_init_type):
            self._record_type_error(comp.loop_step.id or node_id,
                                    f"Loop step result type '{step_type.name}' is not assignable to accumulator type '{accu_init_type.name}'.",
                                    expr_pb_root_for_error_reporting)
            return CEL_UNKNOWN

        # Result expression is evaluated in a scope where accu_var has its final type (accu_init_type).
        # iter_var is out of scope for the result expression of a standard fold/comprehension.
        result_scope = current_declarations.copy()
        result_scope[comp.accu_var] = accu_init_type

        result_type = self._check_node(comp.result, type_map_for_pb, ref_map_for_pb, result_scope,
                                       expr_pb_root_for_error_reporting)
        return result_type

    def _check_node(self,
                    node_pb: syntax_pb2.Expr,
                    type_map_for_pb: Dict[int, checked_pb2.Type],
                    ref_map_for_pb: Dict[int, checked_pb2.Reference],
                    current_declarations: Dict[str, CelType],
                    expr_pb_root_for_error_reporting: syntax_pb2.Expr
                    # Root of the expression being checked, for context in errors
                    ) -> CelType:
        node_id = node_pb.id
        resulting_cel_type: CelType
        expr_kind = node_pb.WhichOneof('expr_kind')

        if expr_kind == "const_expr":
            resulting_cel_type = self._handle_const_expr_check(node_pb, expr_pb_root_for_error_reporting)
        elif expr_kind == "ident_expr":
            resulting_cel_type = self._handle_ident_expr_check(node_pb, current_declarations, ref_map_for_pb,
                                                               expr_pb_root_for_error_reporting)
        elif expr_kind == "select_expr":
            resulting_cel_type = self._handle_select_expr_check(node_pb, type_map_for_pb, ref_map_for_pb,
                                                                current_declarations, expr_pb_root_for_error_reporting)
        elif expr_kind == "call_expr":
            resulting_cel_type = self._handle_call_expr_check(node_pb, type_map_for_pb, ref_map_for_pb,
                                                              current_declarations, expr_pb_root_for_error_reporting)
        elif expr_kind == "list_expr":
            resulting_cel_type = self._handle_list_expr_check(node_pb, type_map_for_pb, ref_map_for_pb,
                                                              current_declarations, expr_pb_root_for_error_reporting)
        elif expr_kind == "struct_expr":
            resulting_cel_type = self._handle_struct_expr_check(node_pb, type_map_for_pb, ref_map_for_pb,
                                                                current_declarations, expr_pb_root_for_error_reporting)
        elif expr_kind == "comprehension_expr":
            resulting_cel_type = self._handle_comprehension_expr_check(node_pb, type_map_for_pb, ref_map_for_pb,
                                                                       current_declarations,
                                                                       expr_pb_root_for_error_reporting)
        else:
            # This case should ideally not be reached if the AST is valid and all expr_kind are handled.
            self._record_type_error(node_id, f"Unhandled expr_kind '{expr_kind}' during type checking.",
                                    expr_pb_root_for_error_reporting)
            resulting_cel_type = CEL_UNKNOWN

        # Store the determined type in the type_map for this node_id
        # This is done for all nodes, including those that might result in CEL_UNKNOWN or TYPE_ERROR_PB
        if node_id != 0:  # ID 0 is sometimes used for nodes not in the original source, or for global errors
            pb_type_to_store: Optional[checked_pb2.Type] = None
            if resulting_cel_type == CEL_UNKNOWN:
                # If an error was recorded for this node leading to UNKNOWN, mark as ERROR_PB
                # This check might need refinement: an error for a child node could make parent UNKNOWN
                # For now, if the node's processing directly results in UNKNOWN, it's an error type.
                pb_type_to_store = TYPE_ERROR_PB
            else:
                pb_type_to_store = self._cel_type_to_checked_pb(resulting_cel_type)
                # If _cel_type_to_checked_pb itself returns TYPE_ERROR_PB (e.g., for an unmappable CelType),
                # and resulting_cel_type was not CEL_UNKNOWN, it indicates an internal issue.
                if pb_type_to_store == TYPE_ERROR_PB and resulting_cel_type != CEL_UNKNOWN:
                    # This specific error implies a bug in _cel_type_to_checked_pb or an unregistered CelType.
                    self._record_type_error(
                        node_id,
                        f"Internal checker error: Failed to convert valid CelType '{resulting_cel_type.name}' to protobuf Type for type_map.",
                        expr_pb_root_for_error_reporting)

            if pb_type_to_store:  # Ensure we have a type to store
                type_map_for_pb[node_id] = pb_type_to_store
            # else:
            # This case (pb_type_to_store is None) should ideally not happen if logic is correct.
            # Log if it does for debugging.
            # print(f"Warning: No protobuf type determined for node {node_id} with CelType {resulting_cel_type}")

        return resulting_cel_type

    def perform_check(self,
                      expr_pb: syntax_pb2.Expr,
                      effective_declarations: Dict[str, CelType],
                      type_map_for_pb: Dict[int, checked_pb2.Type],
                      ref_map_for_pb: Dict[int, checked_pb2.Reference]
                      ) -> CelType:
        # The root of the expression is also passed as expr_pb_root_for_error_reporting
        # print(repr(expr_pb))
        return self._check_node(expr_pb, type_map_for_pb, ref_map_for_pb, effective_declarations, expr_pb)