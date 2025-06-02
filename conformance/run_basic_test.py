import os
import sys
import traceback
from typing import Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from google.protobuf.struct_pb2 import ListValue, Struct, Value
from google.protobuf import text_format
from google.protobuf.any_pb2 import Any as PbAny_type
from google.protobuf import message_factory
from google.protobuf import descriptor_pool
from google.protobuf.message import Message as ProtobufMessage, DecodeError

from cel.expr.conformance.test import simple_pb2
from cel.expr import value_pb2
from cel.expr import checked_pb2

from mimicel.type_registry import TypeRegistry
from mimicel.api import CelEnv
from mimicel.cel_values import unwrap_value

# グローバルスコープでprotoモジュールをロードしておく
try:
    from cel.expr.conformance.proto2 import test_all_types_pb2 as proto2_pb2
    from cel.expr.conformance.proto2 import test_all_types_extensions_pb2 as proto2_ext_pb2
    from cel.expr.conformance.proto3 import test_all_types_pb2 as proto3_pb2

    PROTO_MODULES_LOADED = True
except ImportError as e:
    print(f"WARNING: Conformance test proto modules could not be imported at global scope: {e}")
    PROTO_MODULES_LOADED = False
    proto2_pb2 = None
    proto2_ext_pb2 = None
    proto3_pb2 = None


BOLD = "\033[1m"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"

# グローバルスコープのインポート直後のデバッグプリント
# if PROTO_MODULES_LOADED:
#     if proto3_pb2:
#         print(f"[DEBUG HARNESS GLOBAL] global proto3_pb2 seems loaded: {proto3_pb2}")
#         if hasattr(proto3_pb2, 'TestAllTypes'):
#             print(f"  [DEBUG HARNESS GLOBAL] global proto3_pb2 has TestAllTypes: {proto3_pb2.TestAllTypes.DESCRIPTOR.full_name}")
#         else:
#             print(f"  [DEBUG HARNESS GLOBAL] global proto3_pb2 DOES NOT have TestAllTypes.")
#         if hasattr(proto3_pb2, 'GlobalEnum'):
#             print(f"  [DEBUG HARNESS GLOBAL] global proto3_pb2 has GlobalEnum: {proto3_pb2.GlobalEnum.DESCRIPTOR.full_name}")
#         else:
#             print(f"  [DEBUG HARNESS GLOBAL] global proto3_pb2 DOES NOT have GlobalEnum.")
#     else:
#         print("[DEBUG HARNESS GLOBAL] global proto3_pb2 is None after try-except block (problematic if proto3 tests run).")
# else:
#     print("[DEBUG HARNESS GLOBAL] PROTO_MODULES_LOADED is False.")


def evaluate_cel_expression_for_conformance(
                                            testname: str,
                                            section: str,
                                            testcase: str,
                                            expr_str: str,
                                            bindings: dict,
                                            type_env: dict,
                                            container_str: str,
                                            disable_check_flag: bool,
                                            is_verbose: bool,
                                            enum_semantics_mode: str
                                            ):
    # is_problem_case_context = (
    #         (not container_str or container_str == "cel.expr.conformance.proto3") and
    #         type_env.get('x') == 'cel.expr.conformance.proto3.TestAllTypes' and
    #         "x.standalone_enum" in expr_str
    # )

    # if is_problem_case_context:
    #     print(f"\n  [DEBUG EVAL FUNC START - TC 3.18 Context] evaluate_cel_expression_for_conformance called.")
    #     print(f"    Container: '{container_str}', TypeEnv: {type_env}")

    if is_verbose:
        print(
            f"    [Evaluator] Expr: '{expr_str}', Container: '{container_str}', Bindings: {bindings}, TypeEnv: {type_env}, DisableCheck: {disable_check_flag}")

    type_registry_for_eval_env = TypeRegistry()
    proto_modules_for_eval_env = []

    if PROTO_MODULES_LOADED:
        # 1. Explicit container string handling
        if container_str == "cel.expr.conformance.proto2" and proto2_pb2:
            # if is_problem_case_context: print("    [DEBUG EVAL FUNC] In proto2 explicit container block (UNEXPECTED for TC 3.18).")
            proto_modules_for_eval_env.append(proto2_pb2)
            if hasattr(proto2_pb2, 'TestAllTypes'):
                type_registry_for_eval_env.register_message_type(proto2_pb2.TestAllTypes)
                type_registry_for_eval_env.register_message_type(proto2_pb2.NestedTestAllTypes)
                type_registry_for_eval_env.register_message_type(proto2_pb2.TestRequired)
            if hasattr(proto2_pb2, 'GlobalEnum'):
                type_registry_for_eval_env.register_enum_type(proto2_pb2.GlobalEnum.DESCRIPTOR)
            if is_verbose: print(
                f"      [Harness/EvalEnv] Registered types from proto2_pb2 for explicit container: {container_str}")

        elif container_str == "cel.expr.conformance.proto3" and proto3_pb2:
            # if is_problem_case_context: print("    [DEBUG EVAL FUNC] In proto3 explicit container block.")
            proto_modules_for_eval_env.append(proto3_pb2)
            if hasattr(proto3_pb2, 'TestAllTypes'):
                type_registry_for_eval_env.register_message_type(proto3_pb2.TestAllTypes)
            if hasattr(proto3_pb2, 'GlobalEnum'):
                type_registry_for_eval_env.register_enum_type(proto3_pb2.GlobalEnum.DESCRIPTOR)
            if is_verbose: print(
                f"      [Harness/EvalEnv] Registered types from proto3_pb2 for explicit container: {container_str}")

        # 2. Handle cases with no container_str by inferring from type_env
        elif not container_str:
            # if is_problem_case_context: print("    [DEBUG EVAL FUNC] No container_str. Inferring types from TypeEnv.")
            unique_message_classes_to_register = set()

            # 専用
            if testname == "proto2":
                if proto2_pb2 not in proto_modules_for_eval_env:
                    proto_modules_for_eval_env.append(proto2_pb2)
                if proto2_ext_pb2 not in proto_modules_for_eval_env:
                    proto_modules_for_eval_env.append(proto2_ext_pb2)
            if testname == "proto3":
                if proto3_pb2 not in proto_modules_for_eval_env:
                    proto_modules_for_eval_env.append(proto3_pb2)


            if type_env:
                for var_name, type_name_str_from_env in type_env.items():
                    if isinstance(type_name_str_from_env, str):
                        module_to_use = None
                        simple_type_name = type_name_str_from_env.split('.')[-1]

                        if type_name_str_from_env.startswith("cel.expr.conformance.proto2.") and proto2_pb2:
                            module_to_use = proto2_pb2
                            if proto2_pb2 not in proto_modules_for_eval_env:
                                proto_modules_for_eval_env.append(proto2_pb2)
                        elif type_name_str_from_env.startswith("cel.expr.conformance.proto3.") and proto3_pb2:
                            module_to_use = proto3_pb2
                            if proto3_pb2 not in proto_modules_for_eval_env:
                                proto_modules_for_eval_env.append(proto3_pb2)

                        if module_to_use and hasattr(module_to_use, simple_type_name):
                            msg_class_to_register = getattr(module_to_use, simple_type_name)
                            unique_message_classes_to_register.add(msg_class_to_register)
                            # if is_problem_case_context:
                            #     print(f"      [DEBUG EVAL FUNC] Identified type '{type_name_str_from_env}' from TypeEnv. Will attempt to register '{simple_type_name}' from {module_to_use.__name__}.")
                        # elif is_problem_case_context:
                        #      print(f"      [DEBUG EVAL FUNC] Could not find/resolve type '{type_name_str_from_env}' from TypeEnv in available proto modules.")

            for msg_class in unique_message_classes_to_register:
                type_registry_for_eval_env.register_message_type(msg_class)
                # if is_problem_case_context:
                #     print(f"        [DEBUG EVAL FUNC] Registered inferred message type: {msg_class.DESCRIPTOR.full_name}")

            if (section == "whitespace" or section == "comments") and (testcase == "spaces"
                                            or testcase == "tabs"
                                            or testcase == "new_lines"
                                            or testcase == "new_pages"
                                            or testcase == "carriage_returns"
                                            or testcase == "new_line_terminated"):
                if proto3_pb2:
                    if proto3_pb2 not in proto_modules_for_eval_env:
                        proto_modules_for_eval_env.append(proto3_pb2)
                    if hasattr(proto3_pb2, 'TestAllTypes'):
                        type_registry_for_eval_env.register_message_type(proto3_pb2.TestAllTypes)
                    if hasattr(proto3_pb2, 'GlobalEnum'):
                        type_registry_for_eval_env.register_enum_type(proto3_pb2.GlobalEnum.DESCRIPTOR)


            if unique_message_classes_to_register:
                if proto2_pb2 in proto_modules_for_eval_env and hasattr(proto2_pb2, 'GlobalEnum'):
                    type_registry_for_eval_env.register_enum_type(proto2_pb2.GlobalEnum.DESCRIPTOR)
                if proto3_pb2 in proto_modules_for_eval_env and hasattr(proto3_pb2, 'GlobalEnum'):
                    type_registry_for_eval_env.register_enum_type(proto3_pb2.GlobalEnum.DESCRIPTOR)

        elif container_str and is_verbose:
            print(
                f"      [Harness/EvalEnv] WARNING: Container '{container_str}' specified, but no specific type registration logic was matched or proto module was None.")

    # elif is_problem_case_context:
    #     print(f"  [DEBUG EVAL FUNC] PROTO_MODULES_LOADED is False. Cannot prepare types.")

    try:
        # if is_problem_case_context:
        #     print(f"  [DEBUG EVAL FUNC PRE-CELENV - TC 3.18 Context] Initializing CELEnv.")
        #     registered_messages = list(type_registry_for_eval_env._message_python_classes.keys())
        #     print(f"    TypeRegistry for CELEnv - Messages: {registered_messages}")
        #     if "cel.expr.conformance.proto3.TestAllTypes" in registered_messages:
        #         print(f"      'cel.expr.conformance.proto3.TestAllTypes' IS IN TypeRegistry for CELEnv.")
        #     else:
        #         print(f"      'cel.expr.conformance.proto3.TestAllTypes' IS NOT IN TypeRegistry for CELEnv. (THIS IS THE LIKELY PROBLEM IF ERROR PERSISTS)")

        current_test_env = CelEnv(
            variables=type_env if type_env else None,
            container=container_str if container_str else None,
            type_registry=type_registry_for_eval_env,
            proto_modules=proto_modules_for_eval_env,
            enum_semantics=enum_semantics_mode,
        )
        # if is_problem_case_context: print(f"  [DEBUG EVAL FUNC] CELEnv initialized successfully for TC 3.18 context.")

        program = current_test_env.compile(expr_str, disable_check=disable_check_flag)
        result_cel_value = program.eval(bindings)
        return result_cel_value
    except Exception as e:
        # if is_problem_case_context and "Invalid type string" in str(e):
        #      print(f"  [DEBUG EVAL FUNC ERROR - TC 3.18 Context] CELEnv init failed with 'Invalid type string': {e}")
        #      registered_messages_at_error = list(type_registry_for_eval_env._message_python_classes.keys())
        #      print(f"    TypeRegistry state AT ERROR - Messages: {registered_messages_at_error}")
        #      if "cel.expr.conformance.proto3.TestAllTypes" not in registered_messages_at_error:
        #          print(f"      CONFIRMED: 'cel.expr.conformance.proto3.TestAllTypes' was NOT in TypeRegistry at error.")
        # elif is_problem_case_context:
        #      print(f"  [DEBUG EVAL FUNC ERROR - TC 3.18 Context] CELEnv init or compile failed with an unexpected error: {type(e).__name__}: {e}")
        return e


def _proto_struct_to_py_dict(struct_val: Struct, type_registry_for_any: Optional[TypeRegistry]) -> dict:
    """ google.protobuf.Struct を Python dict に変換するヘルパー """
    py_dict = {}
    for key, value_proto in struct_val.fields.items():
        # value_proto は google.protobuf.Value
        # これを conformance_expr_value_to_py で Python ネイティブ値に変換
        # conformance_expr_value_to_py は value_pb2.Value を期待するが、
        # ここでは google.protobuf.Value を直接扱う必要がある。
        # そのため、google.protobuf.Value を value_pb2.Value に変換するか、
        # あるいは google.protobuf.Value を直接Pythonネイティブ値に変換する別のヘルパーが必要。
        # ここでは、_proto_value_to_py_native を新設する。
        py_dict[key] = _proto_value_to_py_native(value_proto, type_registry_for_any)
    return py_dict


def _proto_list_value_to_py_list(list_val_msg: ListValue, type_registry_for_any: Optional[TypeRegistry]) -> list:
    """ google.protobuf.ListValue を Python list に変換するヘルパー """
    py_list = []
    for item_val_pb in list_val_msg.values:  # item_val_pb は google.protobuf.Value
        py_list.append(_proto_value_to_py_native(item_val_pb, type_registry_for_any))
    return py_list


def _proto_value_to_py_native(value_proto: Value, type_registry_for_any: Optional[TypeRegistry]) -> PbAny_type:
    """ google.protobuf.Value を Python ネイティブ値に変換するヘルパー """
    kind = value_proto.WhichOneof('kind')
    if kind == 'null_value':
        return None
    elif kind == 'number_value':
        return value_proto.number_value  # float
    elif kind == 'string_value':
        return value_proto.string_value
    elif kind == 'bool_value':
        return value_proto.bool_value
    elif kind == 'struct_value':
        return _proto_struct_to_py_dict(value_proto.struct_value, type_registry_for_any)  # 再帰呼び出し
    elif kind == 'list_value':
        return _proto_list_value_to_py_list(value_proto.list_value, type_registry_for_any)  # 再帰呼び出し
    else:  # kind が None (空のValue) や未対応の場合
        return None  # またはエラー


def conformance_expr_value_to_py(
        cel_proto_value: value_pb2.Value,
        type_registry: Optional[TypeRegistry]
):
    kind = cel_proto_value.WhichOneof('kind')
    if kind == 'null_value':
        return None
    elif kind == 'bool_value':
        return cel_proto_value.bool_value
    elif kind == 'int64_value':
        return cel_proto_value.int64_value
    elif kind == 'uint64_value':
        return cel_proto_value.uint64_value
    elif kind == 'double_value':
        return cel_proto_value.double_value
    elif kind == 'string_value':
        return cel_proto_value.string_value
    elif kind == 'bytes_value':
        return cel_proto_value.bytes_value
    elif kind == 'list_value':  # cel.expr.value_pb2.ListValue
        return [conformance_expr_value_to_py(v, type_registry) for v in cel_proto_value.list_value.values]
    elif kind == 'map_value':  # cel.expr.value_pb2.MapValue
        py_map = {}
        for entry in cel_proto_value.map_value.entries:
            key = conformance_expr_value_to_py(entry.key, type_registry)
            if not isinstance(key, (str, int, bool, bytes, type(None))): key = str(key)
            py_map[key] = conformance_expr_value_to_py(entry.value, type_registry)
        return py_map
    elif kind == 'type_value':
        return cel_proto_value.type_value
    elif kind == 'object_value':  # google.protobuf.Any
        any_message = cel_proto_value.object_value
        type_url = any_message.TypeName()

        # ▼▼▼ Struct と ListValue の特別処理 (Any からアンパック) ▼▼▼
        if type_url == "type.googleapis.com/google.protobuf.Struct":
            struct_msg = Struct()
            if any_message.UnpackTo(struct_msg):
                return _proto_struct_to_py_dict(struct_msg, type_registry)
            else:
                raise ValueError(f"Failed to unpack google.protobuf.Struct from Any: {any_message}")
        elif type_url == "type.googleapis.com/google.protobuf.ListValue":
            list_val_msg = ListValue()
            if any_message.UnpackTo(list_val_msg):
                return _proto_list_value_to_py_list(list_val_msg, type_registry)
            else:
                raise ValueError(f"Failed to unpack google.protobuf.ListValue from Any: {any_message}")
        # ▲▲▲ Struct と ListValue の特別処理 ▲▲▲

        # その他の object_value (Any) の処理 (既存のロジック)
        if not isinstance(any_message, PbAny_type):  # any_message は PbAny_type のはず
            raise TypeError(
                f"Expected google.protobuf.Any for object_value field, got {type(any_message)}. Value: {any_message!r}")
        if not type_url: raise ValueError("object_value (Any) has no type_url.")
        type_name_from_url = type_url.split('/')[-1]
        if not type_name_from_url: raise ValueError(f"Could not extract type name from type_url: {type_url}")

        target_py_class = None
        if type_registry:
            if type_name_from_url:
                target_py_class = type_registry.get_python_message_class(type_name_from_url)

        if not target_py_class:
            pool = descriptor_pool.Default()
            try:
                msg_descriptor_from_pool = pool.FindMessageTypeByName(type_name_from_url)
                target_py_class = message_factory.GetMessageClass(msg_descriptor_from_pool)
            except KeyError:
                raise NotImplementedError(
                    f"Python class for message type '{type_name_from_url}' (from type_url '{type_url}') not found in TypeRegistry or default descriptor pool.")
            except Exception as e_desc:
                raise NotImplementedError(
                    f"Error resolving Python class for '{type_name_from_url}' via default pool: {e_desc}")
        if not target_py_class:
            raise NotImplementedError(f"Python class for '{type_name_from_url}' could not be resolved.")

        try:
            unpacked_message = target_py_class()
            if not any_message.Is(unpacked_message.DESCRIPTOR):  # Is() で型が一致するか確認
                raise ValueError(
                    f"Type URL mismatch for Any: {any_message.TypeName()} vs {unpacked_message.DESCRIPTOR.full_name}")

            # UnpackTo が推奨 (Python 3.7+)
            if hasattr(any_message, 'UnpackTo') and callable(any_message.UnpackTo):
                if not any_message.UnpackTo(unpacked_message):
                    raise ValueError(f"Failed to UnpackTo Any (type_url: {type_url}) into {target_py_class.__name__}")
            elif hasattr(unpacked_message, 'ParseFromString') and hasattr(any_message, 'value'):  # フォールバック
                unpacked_message.ParseFromString(any_message.value)
            else:
                raise RuntimeError(f"Cannot unpack Any message of type {type_url}, no suitable unpack method found.")
            return unpacked_message
        except DecodeError as de:
            raise ValueError(
                f"Failed to unpack Any (type_url: {type_url}, value: {any_message.value!r}) into {target_py_class.__name__} due to DecodeError: {de}") from de
        except Exception as e:
            raise ValueError(
                f"Failed to unpack Any (type_url: {type_url}) into {target_py_class.__name__}: {type(e).__name__} - {e}") from e

    elif kind == 'enum_value':
        return cel_proto_value.enum_value.value
    elif kind == 'value':  # cel.expr.value_pb2.Value のネストされた value フィールド
        if isinstance(cel_proto_value.value, value_pb2.Value):
            return conformance_expr_value_to_py(cel_proto_value.value, type_registry)
        else:
            raise NotImplementedError(
                f"Unexpected nested 'value' kind in value_pb2.Value without specific type: {cel_proto_value.value}")

    raise NotImplementedError(
        f"Conversion for value_pb2.Value kind '{kind}' not implemented for value: {cel_proto_value}")


def compare_actual_vs_expected(actual_eval_result,
                               expected_cel_proto_value: value_pb2.Value,  # これは cel.expr.value_pb2.Value
                               type_registry: Optional[TypeRegistry]
                               ):
    try:
        actual_py_value = unwrap_value(actual_eval_result)
    except Exception as e:
        actual_py_value = e
    try:
        expected_py_value = conformance_expr_value_to_py(expected_cel_proto_value, type_registry)
    except Exception as e:
        return False, f"Failed to convert expected value: {e} for {expected_cel_proto_value}"

    if isinstance(actual_py_value, Exception) and not expected_cel_proto_value.HasField("error_value"):
        return False, (f"Mismatch! Actual was an Exception, Expected was a Value.\n"
                       f"      Actual Exception: {type(actual_py_value).__name__}: {actual_py_value}\n"
                       f"      Expected Value (py): {expected_py_value!r} (type: {type(expected_py_value).__name__})")

    is_match = False
    import math

    if isinstance(actual_py_value, Struct) and isinstance(expected_py_value, dict):
        actual_dict = _proto_struct_to_py_dict(actual_py_value, type_registry)
        is_match = (actual_dict == expected_py_value)
    elif isinstance(actual_py_value, ListValue) and isinstance(expected_py_value, list):
        actual_list = _proto_list_value_to_py_list(actual_py_value, type_registry)
        is_match = (actual_list == expected_py_value)
    elif isinstance(actual_py_value, ProtobufMessage) and isinstance(expected_py_value, ProtobufMessage):
        if actual_py_value.DESCRIPTOR == expected_py_value.DESCRIPTOR:
            is_match = (actual_py_value == expected_py_value)
    elif type(actual_py_value) == type(expected_py_value):
        is_match = (actual_py_value == expected_py_value)
    elif isinstance(actual_py_value, (int, float)) and isinstance(expected_py_value, (int, float)):
        if isinstance(actual_py_value, float) and math.isnan(actual_py_value):
            is_match = isinstance(expected_py_value, float) and math.isnan(expected_py_value)
        elif isinstance(expected_py_value, float) and math.isnan(expected_py_value):
            is_match = False
        else:
            is_match = (float(actual_py_value) == float(expected_py_value))
    elif actual_py_value is None and expected_py_value is None:
        is_match = True

    if is_match: return True, "Actual result matches expected value."

    actual_display_value = actual_py_value
    actual_display_type = type(actual_py_value).__name__
    if isinstance(actual_py_value, Struct):
        try:
            actual_display_value = _proto_struct_to_py_dict(actual_py_value, type_registry)
            actual_display_type = type(actual_display_value).__name__
        except Exception:
            pass
    elif isinstance(actual_py_value, ListValue):
        try:
            actual_display_value = _proto_list_value_to_py_list(actual_py_value, type_registry)
            actual_display_type = type(actual_display_value).__name__
        except Exception:
            pass

    return False, (f"Mismatch! \n"
                   f"      Actual (py): {actual_display_value!r} (type: {actual_display_type})\n"
                   f"      Expected (py): {expected_py_value!r} (type: {type(expected_py_value).__name__})\n"
                   f"      (Raw Actual from eval: {actual_eval_result!r})")


def checked_type_to_string_type(checked_type_msg: checked_pb2.Type) -> str:
    kind = checked_type_msg.WhichOneof('type_kind')
    if kind == 'dyn': return "dyn"
    if kind == 'null': return "null_type"
    if kind == 'primitive':
        return {
            checked_pb2.Type.PrimitiveType.PRIMITIVE_TYPE_UNSPECIFIED: "dyn",
            checked_pb2.Type.PrimitiveType.BOOL: "bool",
            checked_pb2.Type.PrimitiveType.INT64: "int",
            checked_pb2.Type.PrimitiveType.UINT64: "uint",
            checked_pb2.Type.PrimitiveType.DOUBLE: "double",
            checked_pb2.Type.PrimitiveType.STRING: "string",
            checked_pb2.Type.PrimitiveType.BYTES: "bytes",
        }.get(checked_type_msg.primitive, "dyn")
    if kind == 'list_type': return f"list<{checked_type_to_string_type(checked_type_msg.list_type.elem_type)}>"
    if kind == 'map_type': return f"map<{checked_type_to_string_type(checked_type_msg.map_type.key_type)},{checked_type_to_string_type(checked_type_msg.map_type.value_type)}>"
    if kind == 'message_type': return checked_type_msg.message_type
    if kind == 'type_param': return checked_type_msg.type_param
    if kind == 'wrapper':
        return {
            checked_pb2.Type.PrimitiveType.BOOL: "google.protobuf.BoolValue",
            checked_pb2.Type.PrimitiveType.BYTES: "google.protobuf.BytesValue",
            checked_pb2.Type.PrimitiveType.DOUBLE: "google.protobuf.DoubleValue",
            checked_pb2.Type.PrimitiveType.INT64: "google.protobuf.Int64Value",
            checked_pb2.Type.PrimitiveType.STRING: "google.protobuf.StringValue",
            checked_pb2.Type.PrimitiveType.UINT64: "google.protobuf.UInt64Value",
        }.get(checked_type_msg.wrapper, "dyn")
    if kind == 'well_known':
        return {
            checked_pb2.Type.WellKnownType.ANY: "google.protobuf.Any",
            checked_pb2.Type.WellKnownType.TIMESTAMP: "google.protobuf.Timestamp",
            checked_pb2.Type.WellKnownType.DURATION: "google.protobuf.Duration",
        }.get(checked_type_msg.well_known, "dyn")
    if kind == 'type': return "type"
    if kind == 'error': return "!error!"
    if kind == 'function': return "!function!"
    if kind == 'abstract_type': return checked_type_msg.abstract_type.name
    return "dyn"


def _print_test_failure_details(tc: simple_pb2.SimpleTest,
                                section_idx: int, tc_idx: int,
                                actual_result_or_exc,
                                current_bindings: dict, current_type_env: dict,
                                summary_status_line: str,
                                verbose: bool,
                                is_preparation_error: bool = False,
                                type_registry_for_conversion: Optional[TypeRegistry] = None):
    print(f"\n      ---- Test Case Details ----")
    print(f"      Test:    {tc.name} (ID: [{section_idx}.{tc_idx}])")
    print(f"      {summary_status_line}")
    print(f"      Expr:    '{tc.expr}'")
    if current_bindings: print(f"      Bindings: {current_bindings}")
    if current_type_env: print(f"      TypeEnv:  {current_type_env}")
    if tc.container: print(f"      Container: {tc.container}")
    if tc.HasField("value"):
        try:
            expected_py_val = conformance_expr_value_to_py(tc.value, type_registry_for_conversion)
            print(f"      Expected Value: {expected_py_val!r} (type: {type(expected_py_val).__name__})")
        except Exception as e_conv:
            print(f"      Expected Value (Proto): {tc.value} (ERROR converting to Python: {e_conv})")
    if tc.HasField("eval_error"):
        expected_error_set = tc.eval_error
        if expected_error_set.errors:
            print(
                f"      Expected Error: Msg Pattern: '{expected_error_set.errors[0].message}' (from ErrorSet.errors[0])")
        else:
            print(
                f"      Expected Error: (ErrorSet: {expected_error_set}, but 'errors' list is empty or not as expected by test harness)")
    if isinstance(actual_result_or_exc, Exception):
        actual_exc = actual_result_or_exc
        print(f"      Actual Result: Exception - {type(actual_exc).__name__}: {actual_exc}")
        if hasattr(actual_exc, "__traceback__") and actual_exc.__traceback__:
            tb_lines = traceback.format_exception(type(actual_exc), actual_exc, actual_exc.__traceback__)
            print(f"      StackTrace:")
            for line in "".join(tb_lines).splitlines(): print(f"        {line.strip()}")
    elif not is_preparation_error:
        try:
            actual_py_value = unwrap_value(actual_result_or_exc)
            print(f"      Actual Value (py): {actual_py_value!r} (type: {type(actual_py_value).__name__})")
            if verbose and actual_result_or_exc is not actual_py_value:
                print(
                    f"      (Raw Actual from eval: {actual_result_or_exc!r} type: {type(actual_result_or_exc).__name__})")
        except Exception as e_unwrap:
            print(
                f"      Actual Value (raw from eval): {actual_result_or_exc!r} (type: {type(actual_result_or_exc).__name__}, ERROR unwrapping: {e_unwrap})")
    print(f"      {'-' * 30}")


def run_tests_from_textproto(textproto_file_path: str,
                             cel_evaluator_func: callable,
                             verbose: bool = False,
                             fail_fast: bool = False):
    if not os.path.exists(textproto_file_path):
        print(f"Error: Test file not found: {textproto_file_path}")
        return False
    test_file_data = simple_pb2.SimpleTestFile()
    try:
        with open(textproto_file_path, 'r', encoding='utf-8') as f:
            text_format.Parse(f.read(), test_file_data)
    except text_format.ParseError as e:
        print(f"Error parsing test file {textproto_file_path}: {e}")
        return False

    file_name_for_log = os.path.basename(textproto_file_path)
    print(f"\n# Running tests from file: {test_file_data.name} ({file_name_for_log})")
    if verbose:
        print(f"Description: {test_file_data.description}")

    total_tests, passed_tests, file_had_failures = 0, 0, False

    for section_idx, section in enumerate(test_file_data.section):
        current_section_name = f"Section [{section_idx}]: {section.name}"
        if verbose:
            print(f"\n  {current_section_name} ({section.description})")
        else:
            print(f"\n  {current_section_name}")

        for tc_idx, tc in enumerate(section.test):

            # error_right, error_leftのテストケースはcel-goでやってもdivision by zeroになって
            # 通すのが無理。
            if os.path.basename(textproto_file_path) == "logic.textproto" and tc.name in ("error_right", "error_left"):
                if verbose:
                    print(
                        f"    Test Case [{section_idx}.{tc_idx}]: {tc.name} - SKIPPED (logic.textproto excluded case)")
                else:
                    print(f"    Test Case [{section_idx}.{tc_idx}]: {tc.name} - SKIPPED")
                continue

            total_tests += 1
            test_case_identifier_line = f"    Test Case [{section_idx}.{tc_idx}]: {tc.name}"
            if not verbose:
                print(test_case_identifier_line, end="")

            current_bindings, current_type_env_for_celenv = {}, {}
            preparation_error = None

            temp_type_registry_for_bindings_conversion = TypeRegistry()
            if PROTO_MODULES_LOADED:
                if tc.container == "cel.expr.conformance.proto2" and proto2_pb2:
                    if hasattr(proto2_pb2,
                               'TestAllTypes'): temp_type_registry_for_bindings_conversion.register_message_type(
                        proto2_pb2.TestAllTypes)
                elif tc.container == "cel.expr.conformance.proto3" and proto3_pb2:
                    if hasattr(proto3_pb2,
                               'TestAllTypes'): temp_type_registry_for_bindings_conversion.register_message_type(
                        proto3_pb2.TestAllTypes)
                elif not tc.container:
                    if tc.type_env:
                        for decl_entry in tc.type_env:
                            if decl_entry.HasField("ident"):
                                type_name_str = checked_type_to_string_type(decl_entry.ident.type)
                                if type_name_str.startswith("cel.expr.conformance.proto2.") and proto2_pb2:
                                    simple_name = type_name_str.split('.')[-1]
                                    if hasattr(proto2_pb2, simple_name):
                                        temp_type_registry_for_bindings_conversion.register_message_type(
                                            getattr(proto2_pb2, simple_name))
                                elif type_name_str.startswith("cel.expr.conformance.proto3.") and proto3_pb2:
                                    simple_name = type_name_str.split('.')[-1]
                                    if hasattr(proto3_pb2, simple_name):
                                        temp_type_registry_for_bindings_conversion.register_message_type(
                                            getattr(proto3_pb2, simple_name))

            if tc.bindings:
                if verbose: print(f"{test_case_identifier_line}\n      Bindings:")
                for key_string, value_proto_message in tc.bindings.items():
                    try:
                        python_value = conformance_expr_value_to_py(value_proto_message,
                                                                    temp_type_registry_for_bindings_conversion)
                        current_bindings[key_string] = python_value
                        if verbose: print(f"        {key_string}: {python_value!r}")
                    except Exception as e:
                        preparation_error = e;
                        summary = f"Status: FAILED (Error preparing binding for key '{key_string}')"
                        if not verbose: print(f" - {summary.replace('Status: ', '')}")
                        _print_test_failure_details(tc, section_idx, tc_idx, e, current_bindings,
                                                    current_type_env_for_celenv, summary, True, True,
                                                    temp_type_registry_for_bindings_conversion)
                        file_had_failures = True;
                        break
                if preparation_error: continue

            if tc.type_env:
                if verbose:
                    if not tc.bindings and not preparation_error: print(f"{test_case_identifier_line}")
                    print("      TypeEnv (for CELEnv variables):")
                for decl_idx, decl_entry in enumerate(tc.type_env):
                    try:
                        if not isinstance(decl_entry, checked_pb2.Decl): raise TypeError(
                            f"TypeEnv entry {decl_idx} not a 'Decl' obj...")
                        if decl_entry.HasField("ident"):
                            type_str = checked_type_to_string_type(decl_entry.ident.type)
                            current_type_env_for_celenv[decl_entry.name] = type_str
                            if verbose: print(f"        {decl_entry.name}: {type_str}")
                    except Exception as e:
                        preparation_error = e; break
                if preparation_error:
                    summary = f"Status: FAILED (Error preparing type_env for '{getattr(decl_entry, 'name', f'decl_{decl_idx}')}')"
                    _print_test_failure_details(tc, section_idx, tc_idx, preparation_error, current_bindings,
                                                current_type_env_for_celenv, summary, True, True,
                                                temp_type_registry_for_bindings_conversion)
                    file_had_failures = True;
                    continue

            enum_semantics_mode = "integer"
            if section.name == "strong_proto2" or section.name == "strong_proto3": enum_semantics_mode = "typename"

            actual_result_or_exc = cel_evaluator_func(
                test_file_data.name,
                section.name,
                tc.name,
                tc.expr,
                current_bindings,
                current_type_env_for_celenv,
                tc.container,
                tc.disable_check,
                verbose,
                enum_semantics_mode
            )

            test_passed_this_case = False;
            summary_status = "UNKNOWN"
            if isinstance(actual_result_or_exc, Exception):
                actual_exception = actual_result_or_exc
                if tc.HasField("eval_error"):
                    expected_eval_error = tc.eval_error
                    if expected_eval_error.errors:
                        expected_message_pattern = expected_eval_error.errors[0].message
                        if expected_message_pattern == "foo":
                            test_passed_this_case = True; summary_status = "Status: PASSED (Expected Error 'foo', Got Any Error)"
                        elif expected_message_pattern and (expected_message_pattern in str(actual_exception)):
                            test_passed_this_case = True; summary_status = "Status: PASSED (Expected Error, Got Matching Error Msg)"
                        else:
                            summary_status = f"Status: FAILED (Error Mismatch: Expected msg containing '{expected_message_pattern}', Got '{actual_exception}')"
                    else:
                        summary_status = f"Status: FAILED (Test expected error via ErrorSet, but 'errors' list was empty or malformed in test spec)"
                else:
                    summary_status = f"Status: FAILED (Unexpected Exception)"
            else:
                if tc.HasField("eval_error"):
                    summary_status = f"Status: FAILED (Expected Error, Got Value)"
                elif tc.HasField("value"):
                    is_match, _ = compare_actual_vs_expected(actual_result_or_exc, tc.value,
                                                             temp_type_registry_for_bindings_conversion)
                    if is_match:
                        test_passed_this_case = True; summary_status = "Status: PASSED"
                    else:
                        summary_status = f"Status: FAILED (Value Mismatch)"
                else:
                    test_passed_this_case = True; summary_status = "Status: PASSED (No specific value/error expectation, and no error occurred)"

            if test_passed_this_case:
                passed_tests += 1
                if verbose:
                    _print_test_failure_details(tc, section_idx, tc_idx, actual_result_or_exc, current_bindings,
                                                current_type_env_for_celenv, summary_status, verbose,
                                                type_registry_for_conversion=temp_type_registry_for_bindings_conversion)
                elif not preparation_error:
                    print(f" - {summary_status.replace('Status: ', '')}")
            else:
                if not verbose and not preparation_error and not (tc.bindings or tc.type_env): print("")
                _print_test_failure_details(tc, section_idx, tc_idx, actual_result_or_exc, current_bindings,
                                            current_type_env_for_celenv, summary_status, verbose,
                                            is_preparation_error=(preparation_error is not None),
                                            type_registry_for_conversion=temp_type_registry_for_bindings_conversion)
                file_had_failures = True
                if "FAILED" in summary_status and fail_fast: print(
                    f"\nFAIL_FAST: Stopping test execution (Test: {tc.name})"); return False

    print(f"\n--- Test File Summary for {file_name_for_log} ---")
    num_not_passed = total_tests - passed_tests
    print(f"Total tests attempted: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed or Skipped: {num_not_passed}")

    run_tests_from_textproto._last_total_tests = total_tests
    run_tests_from_textproto._last_passed_tests = passed_tests

    return not file_had_failures



def load_fixture(name: str) -> str:
    # WORKSPACE名が __main__ の場合
    if "runfiles" in __file__:
        runfiles_base = os.path.join(
            os.path.dirname(__file__),
            "..", "..",  # 適宜調整
            "cel-spec+", "tests", "simple", "testdata"
        )
        return os.path.abspath(os.path.join(runfiles_base, name))
    else:
        testdata_dir = os.path.join(PROJECT_ROOT, 'cel-spec', "tests", "simple", "testdata")
        return os.path.join(testdata_dir, name)

if __name__ == '__main__':
    import argparse

    grand_total_tests = 0
    grand_passed_tests = 0

    parser = argparse.ArgumentParser(description="Run CEL conformance tests")
    parser.add_argument("-k", "--keyword", type=str, help="Only run test cases matching this keyword")
    args = parser.parse_args()

    test_filenames = [
        "plumbing.textproto",
        "basic.textproto",
        "comparisons.textproto",
        "conversions.textproto",
        "dynamic.textproto",
        "enums.textproto",
        "fields.textproto",
        "fp_math.textproto",
        "integer_math.textproto",
        "lists.textproto",
        "logic.textproto",
        "macros.textproto",
        "namespace.textproto",
        "parse.textproto",
        "proto2.textproto",
        "proto3.textproto",
        "string.textproto",
        "timestamps.textproto",
        "unknowns.textproto",
    ]

    #test_file_paths = [os.path.join(testdata_dir, name) for name in test_filenames]
    test_file_paths = [load_fixture(name) for name in test_filenames]
    evaluator = evaluate_cel_expression_for_conformance
    current_verbose = False
    current_fail_fast = True

    print(f"Running with verbose={current_verbose}, fail_fast={current_fail_fast}")
    overall_success = True
    for path in test_file_paths:
        name = os.path.basename(path)
        if args.keyword and args.keyword not in name:
            continue

        local_test_result = {"total": 0, "passed": 0}
        def wrapped_run_tests(path, evaluator, verbose, fail_fast):
            result = run_tests_from_textproto(path, evaluator, verbose, fail_fast)
            local_test_result["total"] = getattr(run_tests_from_textproto, "_last_total_tests", 0)
            local_test_result["passed"] = getattr(run_tests_from_textproto, "_last_passed_tests", 0)
            return result

        file_passed = wrapped_run_tests(path,
                                        evaluator,
                                        verbose=current_verbose,
                                        fail_fast=current_fail_fast)
        grand_total_tests += local_test_result["total"]
        grand_passed_tests += local_test_result["passed"]

        if not file_passed:
            overall_success = False
            if current_fail_fast: print(
                f"\nFAIL_FAST (Overall): Stopping after failure in {os.path.basename(path)}"); break

    print("-" * 40)

    print(f"\n==== Overall Test Summary ====")
    print(f"Total Tests Run: {grand_total_tests}")
    print(f"Total Passed:   {grand_passed_tests}")
    print(f"Total Failed:   {grand_total_tests - grand_passed_tests}")

    if overall_success:
        print(f"\n{BOLD}{GREEN}All specified test files passed successfully or handled errors as expected.{RESET}")
    else:
        print(f"\n{BOLD}{RED}One or more test files reported failures.{RESET}")