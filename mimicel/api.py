# api.py

from typing import Dict, Any, Optional, Union, Callable, List

from antlr4 import InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener
from google.protobuf import json_format
from google.protobuf.message import Message
from google.protobuf.struct_pb2 import NullValue, Value, Struct, ListValue

from cel.expr import syntax_pb2, checked_pb2

from .cel_ast_builder import CelASTBuilder
from .cel_values.cel_types import (
    CelType, CelFunctionRegistry, CelFunctionDefinition,
    CEL_INT, CEL_UINT, CEL_BOOL, CEL_STRING, CEL_DOUBLE, CEL_BYTES,
    CEL_NULL, CEL_DYN, CEL_TYPE,
    make_list_type, make_map_type,
    CEL_DURATION, CEL_TIMESTAMP, CEL_UNKNOWN, CEL_LIST, CEL_MAP, CEL_LIST_WRAPPER, CEL_STRUCT_WRAPPER,
    CEL_VALUE_WRAPPER, CEL_UINT32_WRAPPER, CEL_UINT64_WRAPPER, CEL_STRING_WRAPPER, CEL_INT64_WRAPPER, CEL_INT32_WRAPPER,
    CEL_FLOAT_WRAPPER, CEL_DOUBLE_WRAPPER, CEL_BYTES_WRAPPER, CEL_BOOL_WRAPPER, CEL_ANY, CEL_ERROR, CEL_FLOAT,
    CelMessageType
)
from .cel_values import unwrap_value
from .context import EvalContext
from .eval_pb import _dynamic_convert_if_value, eval_expr_pb
from .standard_definitions import STANDARD_LIBRARY
from .cel_library import CelLibrary
from .CELParser import CELParser
from .CELLexer import CELLexer
from .type_registry import TypeRegistry
from .cel_checker import CelChecker, TYPE_ERROR_PB

from google.protobuf.wrappers_pb2 import Int32Value, UInt32Value, Int64Value, UInt64Value, \
    BoolValue, BytesValue, StringValue, DoubleValue, FloatValue
from google.protobuf.duration_pb2 import Duration as ProtobufDuration
from google.protobuf.timestamp_pb2 import Timestamp as ProtobufTimestamp
from google.protobuf.any_pb2 import Any as PbAny


class CELCompileError(Exception):
    """CEL式のコンパイル時に発生するエラー。"""

    def __init__(self, message: str, line: int = None, column: int = None, source_text: str = None):
        location = f" at line {line}, column {column}" if line is not None and column is not None else ""
        super().__init__(f"{message}{location}")
        self.line = line
        self.column = column
        self.source_text = source_text


class ThrowingErrorListener(ErrorListener):
    """パースエラーを CELCompileError として送出するリスナー。"""

    def syntaxError(self, recognizer, offending_symbol, line, column, msg, e):
        raise CELCompileError(f"Syntax error: {msg}", line, column)


class CelProgram:
    """
    コンパイル済みのCEL式を表し、評価機能を提供します。
    型チェック済みの情報 (checked_pb2.CheckedExpr) を保持します。
    """

    def __init__(self,
                 checked_expr_pb: checked_pb2.CheckedExpr,
                 env: 'CelEnv'
    ):
        if not isinstance(checked_expr_pb, checked_pb2.CheckedExpr):
            raise TypeError(f"CelProgram expects a checked_pb2.CheckedExpr, got {type(checked_expr_pb)}")

        if not isinstance(env, CelEnv):
            raise TypeError(f"CelProgram expects a CELEnv, got {type(env)}")

        self.checked_expr_pb = checked_expr_pb
        self.expr_pb = checked_expr_pb.expr
        self.env = env

    def eval(self, input_vars: Optional[Dict[str, Any]] = None) -> Any:
        actual_input_vars = input_vars or {}
        ctx = EvalContext(
            base=actual_input_vars,
            env=self.env,
            checked_expr=self.checked_expr_pb
        )
        result_cel_value = eval_expr_pb(self.expr_pb, ctx)
        final_cel_value_for_unwrap = _dynamic_convert_if_value(result_cel_value, ctx)

        return unwrap_value(final_cel_value_for_unwrap)

    def to_json(self, indent: Optional[int] = None, preserving_proto_field_name: bool = True) -> str:
        return json_format.MessageToJson(
            self.checked_expr_pb,
            indent=indent,
            preserving_proto_field_name=preserving_proto_field_name
        )


class CelEnv:
    def __init__(
            self,
            variables: Optional[Dict[str, Union[str, CelType]]] = None,
            type_registry: Optional[TypeRegistry] = None,
            builtins: Optional[Union[Dict[str, Callable[..., Any]], CelFunctionRegistry]] = None,
            additional_libraries: Optional[List[CelLibrary]] = None,
            container: Optional[str] = None,
            proto_modules: Optional[List[Any]] = None,
            enum_semantics: str = "integer"
    ):
        self.container_name: Optional[str] = None
        if isinstance(container, str) and container.strip():
            self.container_name = container.strip()

        self.enum_semantics = enum_semantics

        self.declared_variables: Dict[str, CelType] = {}
        self.type_registry: TypeRegistry = type_registry if type_registry is not None else TypeRegistry()
        self.type_check_errors: List[str] = []

        try:
            # Standard WKT Wrappers
            self.type_registry.register_message_type(Int32Value, is_constructible=True)
            self.type_registry.register_message_type(UInt32Value, is_constructible=True)
            self.type_registry.register_message_type(Int64Value, is_constructible=True)
            self.type_registry.register_message_type(UInt64Value, is_constructible=True)
            self.type_registry.register_message_type(BoolValue, is_constructible=True)
            self.type_registry.register_message_type(StringValue, is_constructible=True)
            self.type_registry.register_message_type(BytesValue, is_constructible=True)
            self.type_registry.register_message_type(FloatValue, is_constructible=True)
            self.type_registry.register_message_type(DoubleValue, is_constructible=True)
            self.type_registry.register_message_type(Value, is_constructible=True)
            self.type_registry.register_message_type(Struct, is_constructible=True)
            self.type_registry.register_message_type(ListValue, is_constructible=True)
            self.type_registry.register_message_type(PbAny, is_constructible=True)

            # ★ google.protobuf.Duration と Timestamp を構築不可として登録
            self.type_registry.register_message_type(ProtobufDuration, is_constructible=False)
            self.type_registry.register_message_type(ProtobufTimestamp, is_constructible=False)

        except Exception as e:
            print(f"Warning: Failed to auto-register standard WKTs: {e}")

        if proto_modules:
            # 必要なインポート (重複を避けるため、既存のインポートと合わせて調整してください)
            from google.protobuf.descriptor import Descriptor as PbMessageDescriptor
            from google.protobuf.descriptor import EnumDescriptor as PbEnumDescriptor
            from google.protobuf.message import Message as PbMessage

            unique_message_classes_to_register = set()
            unique_enum_descriptors_to_register = set()

            def collect_types_recursively(item_to_scan):
                """
                モジュールまたはメッセージクラスから再帰的にメッセージクラスとEnumディスクリプタを収集する。
                """
                # ケース1: メッセージクラスの場合 (ネストされた型やEnumを探索)
                if isinstance(item_to_scan, type) and \
                        issubclass(item_to_scan, PbMessage) and \
                        hasattr(item_to_scan, 'DESCRIPTOR') and \
                        isinstance(item_to_scan.DESCRIPTOR, PbMessageDescriptor):

                    msg_class = item_to_scan
                    if msg_class in unique_message_classes_to_register:  # 既に処理済みならスキップ
                        return
                    unique_message_classes_to_register.add(msg_class)

                    # ネストされたEnumを収集
                    if hasattr(msg_class.DESCRIPTOR, 'enum_types'):
                        for enum_desc in msg_class.DESCRIPTOR.enum_types:
                            if enum_desc not in unique_enum_descriptors_to_register:
                                unique_enum_descriptors_to_register.add(enum_desc)

                    # ネストされたメッセージを収集し、再帰的に探索
                    if hasattr(msg_class.DESCRIPTOR, 'nested_types'):
                        for nested_type_desc in msg_class.DESCRIPTOR.nested_types:
                            nested_class_name = nested_type_desc.name
                            if hasattr(msg_class, nested_class_name):
                                nested_class = getattr(msg_class, nested_class_name)
                                collect_types_recursively(nested_class)  # 再帰呼び出し

                # ケース2: モジュールの場合 (トップレベルのアイテムを探索)
                elif hasattr(item_to_scan, '__dict__'):  # モジュールかどうかを簡易的に判定
                    for attr_name in dir(item_to_scan):
                        if attr_name.startswith('_'):  # プライベート/マジック属性はスキップ
                            continue

                        try:
                            attr_value = getattr(item_to_scan, attr_name)
                        except AttributeError:
                            continue  # 一部のモジュール属性は getattr でエラーになることがある

                        # トップレベルのメッセージクラスかEnumディスクリプタなら再帰処理
                        if isinstance(attr_value, type) and \
                                issubclass(attr_value, PbMessage) and \
                                hasattr(attr_value, 'DESCRIPTOR') and \
                                isinstance(attr_value.DESCRIPTOR, PbMessageDescriptor) and \
                                attr_value.DESCRIPTOR.file.name.endswith('.proto'):  # 元の条件を踏襲
                            collect_types_recursively(attr_value)
                        elif isinstance(attr_value, PbEnumDescriptor):
                            if attr_value not in unique_enum_descriptors_to_register:
                                unique_enum_descriptors_to_register.add(attr_value)

            # 提供された各モジュールに対して型収集を実行
            for module in proto_modules:
                if module is not None:
                    collect_types_recursively(module)

            # 収集した全てのユニークなメッセージクラスを登録
            for msg_class in unique_message_classes_to_register:
                # print(f"DEBUG CELEnv: Registering message type {msg_class.DESCRIPTOR.full_name}")
                self.type_registry.register_message_type(msg_class)  # is_constructible はデフォルト値を使用

            # 収集した全てのユニークなEnumディスクリプタを登録
            for enum_desc in unique_enum_descriptors_to_register:
                # print(f"DEBUG CELEnv: Registering enum type {enum_desc.full_name}")
                self.type_registry.register_enum_type(enum_desc)

        if variables:
            for name, type_input in variables.items():
                if isinstance(type_input, CelType):
                    self.declared_variables[name] = type_input
                elif isinstance(type_input, str):
                    parsed_cel_type = self._parse_cel_type_from_string(type_input)
                    if parsed_cel_type:
                        self.declared_variables[name] = parsed_cel_type
                    else:
                        container_info = f" in container '{self.container_name}'" if self.container_name else ""
                        raise CELCompileError(
                            f"Invalid type string '{type_input}' for variable '{name}'{container_info}.")
                else:
                    raise TypeError(f"Variable type for '{name}' must be str or CelType, got {type(type_input)}")

        self.builtins: CelFunctionRegistry = CelFunctionRegistry()

        if STANDARD_LIBRARY:
            STANDARD_LIBRARY.register_functions_to(self.builtins)
        else:
            print("Warning: STANDARD_LIBRARY not found or initialized. Standard functions may be missing.")

        if additional_libraries:
            for lib in additional_libraries:
                if isinstance(lib, CelLibrary):
                    lib.register_functions_to(self.builtins)
                else:
                    print(f"Warning: Ignoring an item in 'additional_libraries' "
                          f"that is not a CelLibrary instance: {type(lib)}")

        if isinstance(builtins, CelFunctionRegistry):
            for func_name_key in list(builtins._functions.keys()):
                overloads_list = builtins._functions[func_name_key]
                for fn_def in overloads_list:
                    self.builtins.register(fn_def)
        elif isinstance(builtins, dict):
            for func_name, func_impl in builtins.items():
                if callable(func_impl):
                    self.builtins.register(
                        CelFunctionDefinition(func_name, [CEL_DYN], CEL_DYN, func_impl)
                    )
                else:
                    print(f"Warning: Item '{func_name}' in 'builtins' dict is not callable and will be ignored.")
        elif builtins is not None:
            raise TypeError(
                f"Invalid type for 'builtins'. Expected Dict, CelFunctionRegistry, or None. Got: {type(builtins)}")

    def _clear_type_errors(self):
        self.type_check_errors = []

    def _record_type_error(self, node_id: int, message: str, expr_pb_for_context: Optional[syntax_pb2.Expr] = None):
        # エラーメッセージにコンテナ情報を追加することも検討できる
        # error_message = message
        # if self.container_name:
        #     error_message = f"{message} (context: {self.container_name})"
        # self.type_check_errors.append(f"Error at node {node_id}: {error_message}")
        self.type_check_errors.append(f"Error at node {node_id}: {message}")

    def _parse_cel_type_from_string(self, type_str: str) -> Optional[CelType]:
        # 0. CelTypeグローバルレジストリからの直接取得 (FQNやプリミティブ型名)
        type_str = type_str.lstrip(".")
        cached_type = CelType.get_by_name(type_str)
        if cached_type:
            # それが実際にTypeRegistryに認識されている型か、またはパッケージ名か確認
            is_known_msg = self.type_registry.is_message_type(type_str)
            is_known_enum = self.type_registry.is_enum_type(type_str)
            is_known_pkg = self.type_registry.is_package(type_str)
            is_basic_cel_type = type_str in [
                "int", "uint", "bool", "string", "double", "bytes", "null_type",
                "dyn", "type", "list", "map", "error",
                "google.protobuf.Duration", "google.protobuf.Timestamp", "google.protobuf.Any",
                "google.protobuf.BoolValue", "google.protobuf.BytesValue", "google.protobuf.DoubleValue",
                "google.protobuf.FloatValue", "google.protobuf.Int32Value", "google.protobuf.Int64Value",
                "google.protobuf.StringValue", "google.protobuf.UInt32Value", "google.protobuf.UInt64Value",
                "google.protobuf.Value", "google.protobuf.Struct", "google.protobuf.ListValue"
            ]
            if (is_known_msg and isinstance(cached_type, CelMessageType)) or \
                    (is_known_enum and not isinstance(cached_type, CelMessageType)) or \
                    (is_known_pkg and not isinstance(cached_type, CelMessageType)) or \
                    (is_basic_cel_type):  # 基本型はCelTypeインスタンス
                return cached_type

        # 1. 基本的な型名の直接的なマッチング (上記basic_cel_typeリストでカバーされるので、ここは冗長かもしれないが残す)
        basic_types = {
            "int": CEL_INT,
            "uint": CEL_UINT,
            "bool": CEL_BOOL,
            "string": CEL_STRING,
            "double": CEL_DOUBLE,
            "float": CEL_FLOAT,
            "bytes": CEL_BYTES,
            "null_type": CEL_NULL,
            "dyn": CEL_DYN,
            "type": CEL_TYPE,
            "list": CEL_LIST,
            "map": CEL_MAP,
            "error": CEL_ERROR,
            "google.protobuf.Duration": CEL_DURATION,
            "google.protobuf.Timestamp": CEL_TIMESTAMP,
            "google.protobuf.Any": CEL_ANY,  # 以下WKTラッパー
            "google.protobuf.BoolValue": CEL_BOOL_WRAPPER,
            "google.protobuf.BytesValue": CEL_BYTES_WRAPPER,
            "google.protobuf.DoubleValue": CEL_DOUBLE_WRAPPER,
            "google.protobuf.FloatValue": CEL_FLOAT_WRAPPER,
            "google.protobuf.Int32Value": CEL_INT32_WRAPPER,
            "google.protobuf.Int64Value": CEL_INT64_WRAPPER,
            "google.protobuf.StringValue": CEL_STRING_WRAPPER,
            "google.protobuf.UInt32Value": CEL_UINT32_WRAPPER,
            "google.protobuf.UInt64Value": CEL_UINT64_WRAPPER,
            "google.protobuf.Value": CEL_VALUE_WRAPPER,
            "google.protobuf.Struct": CEL_STRUCT_WRAPPER,
            "google.protobuf.ListValue": CEL_LIST_WRAPPER,
        }
        if type_str in basic_types:
            return basic_types[type_str]

        # 2. パラメータ化された型 (list<T>, map<K,V>) のパース
        import re
        list_match = re.fullmatch(r"list\s*<\s*(.+)\s*>", type_str)
        if list_match:
            elem_type_str = list_match.group(1).strip()
            elem_type = self._parse_cel_type_from_string(elem_type_str)
            return make_list_type(elem_type if elem_type and elem_type != CEL_UNKNOWN else CEL_DYN)

        map_match = re.fullmatch(r"map\s*<\s*(.+)\s*,\s*(.+)\s*>", type_str)
        if map_match:
            key_type_str, val_type_str = map_match.group(1).strip(), map_match.group(2).strip()
            key_type = self._parse_cel_type_from_string(key_type_str)
            val_type = self._parse_cel_type_from_string(val_type_str)
            allowed_key_types = [CEL_INT, CEL_UINT, CEL_BOOL, CEL_STRING, CEL_DYN]
            if not key_type or key_type == CEL_UNKNOWN or (key_type not in allowed_key_types): return None
            return make_map_type(key_type, val_type if val_type and val_type != CEL_UNKNOWN else CEL_DYN)

        # 3. TypeRegistryからメッセージ型、Enum型、またはパッケージ名を解決 (完全修飾名で試行)
        if self.type_registry.is_message_type(type_str):
            return self.type_registry.get_message_cel_type(type_str)
        if self.type_registry.is_enum_type(type_str):
            return CelType.get_by_name(type_str)
        if self.type_registry.is_package(type_str):
            return CelType.get_or_register_type_instance(type_str, CelType)

        # 4. container_name を考慮した解決
        if self.container_name:
            qualified_name = f"{self.container_name}.{type_str}"
            # コンテナ修飾名でCelTypeグローバルレジストリを再検索
            cached_qualified_type = CelType.get_by_name(qualified_name)
            if cached_qualified_type:
                if self.type_registry.is_message_type(qualified_name) and isinstance(cached_qualified_type,
                                                                                     CelMessageType): return cached_qualified_type
                if self.type_registry.is_enum_type(qualified_name) and not isinstance(cached_qualified_type,
                                                                                      CelMessageType): return cached_qualified_type
                if self.type_registry.is_package(qualified_name) and not isinstance(cached_qualified_type,
                                                                                    CelMessageType): return cached_qualified_type
            # TypeRegistryに直接問い合わせる
            if self.type_registry.is_message_type(qualified_name):
                return self.type_registry.get_message_cel_type(qualified_name)
            if self.type_registry.is_enum_type(qualified_name):
                return CelType.get_by_name(qualified_name)
            if self.type_registry.is_package(qualified_name):
                return CelType.get_or_register_type_instance(qualified_name, CelType)
        return None

    def parse(self, expression: str) -> syntax_pb2.Expr:
        input_stream = InputStream(expression)
        lexer = CELLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = CELParser(stream)
        parser.removeErrorListeners()
        parser.addErrorListener(ThrowingErrorListener())
        try:
            tree = parser.start()
            visitor = CelASTBuilder()
            parsed_expr = visitor.visit(tree)
            if not isinstance(parsed_expr, syntax_pb2.Expr):
                raise CELCompileError(
                    f"AST builder did not return a valid Expr protobuf. Got: {type(parsed_expr).__name__}")
            return parsed_expr
        except CELCompileError:
            raise
        except Exception as e:
            raise CELCompileError(f"Failed to parse expression: {e}") from e

    def check(self,
              expr_pb: syntax_pb2.Expr,
              additional_declarations: Optional[Dict[str, Union[str, CelType]]] = None,
              is_check_disabled: bool = False
    ) -> checked_pb2.CheckedExpr:
        if not isinstance(expr_pb, syntax_pb2.Expr):
            raise TypeError("Input to check must be a syntax_pb2.Expr protobuf message.")

        self._clear_type_errors()
        checked_expr_pb = checked_pb2.CheckedExpr()
        checked_expr_pb.expr.CopyFrom(expr_pb)
        type_map_for_pb: Dict[int, checked_pb2.Type] = {}
        ref_map_for_pb: Dict[int, checked_pb2.Reference] = {}

        effective_declarations: Dict[str, CelType] = self.declared_variables.copy()
        if additional_declarations:
            for name, type_input in additional_declarations.items():
                if isinstance(type_input, CelType):
                    effective_declarations[name] = type_input
                elif isinstance(type_input, str):
                    parsed_type = self._parse_cel_type_from_string(type_input)
                    if parsed_type:
                        effective_declarations[name] = parsed_type
                    else:
                        container_info = f" in container '{self.container_name}'" if self.container_name else ""
                        self._record_type_error(0,  # node_id 0 はグローバルな宣言エラーを示す
                                                f"Could not parse type string '{type_input}' for additional declaration '{name}'{container_info}. Defaulting to DYN.",
                                                expr_pb)
                        effective_declarations[name] = CEL_DYN
                else:
                    self._record_type_error(0,
                                            f"Invalid type input for additional declaration '{name}': {type(type_input)}. Defaulting to DYN.",
                                            expr_pb)
                    effective_declarations[name] = CEL_DYN

        checker = CelChecker(self)

        root_node_type = checker.perform_check(
            expr_pb,
            effective_declarations,
            type_map_for_pb,
            ref_map_for_pb
        )

        for node_id, node_type_pb_val in type_map_for_pb.items():
            checked_expr_pb.type_map[node_id].CopyFrom(node_type_pb_val)
        for node_id, node_ref_pb_val in ref_map_for_pb.items():
            checked_expr_pb.reference_map[node_id].CopyFrom(node_ref_pb_val)

        if not is_check_disabled:
            if self.type_check_errors:
                unique_error_messages = []
                seen_errors = set()
                for err_msg in self.type_check_errors:
                    if err_msg not in seen_errors:
                        unique_error_messages.append(err_msg)
                        seen_errors.add(err_msg)
                final_error_message = "Type checking failed with the following errors:\n" + "\n".join(
                    unique_error_messages)
                raise CELCompileError(final_error_message)

            if root_node_type == CEL_UNKNOWN and not self.type_check_errors:
                raise CELCompileError(
                    f"Type checking failed: Root expression type resolved to UNKNOWN (node id: {expr_pb.id}). "
                    "No specific error was recorded by the checker, indicating a potential internal issue or an unhandled type resolution path.")
            for node_id_key, type_val_pb_map in type_map_for_pb.items():
                if type_val_pb_map == TYPE_ERROR_PB and not any(
                        f"Error at node {node_id_key}" in e for e in self.type_check_errors):
                    raise CELCompileError(
                        f"Type checking failed: Node {node_id_key} type resolved to ERROR_PB without a specific error message in type_check_errors. "
                        "This may indicate an internal issue in the type checker.")
        return checked_expr_pb

    def compile(self,
                expression: str,
                type_declarations: Optional[Dict[str, Union[str, CelType]]] = None,
                disable_check: bool = False
    ) -> CelProgram:

        expr_pb = self.parse(expression)
        # print(expr_pb)
        checked_expr_pb = self.check(expr_pb,
                                     additional_declarations=type_declarations,
                                     is_check_disabled=disable_check)
        return CelProgram(checked_expr_pb, self)

    def program(self,
                expr_pb: syntax_pb2.Expr,
                type_declarations: Optional[Dict[str, Union[str, CelType]]] = None
    ) -> CelProgram:
        checked_expr_pb = self.check(expr_pb,
                                     additional_declarations=type_declarations)
        return CelProgram(checked_expr_pb, self)

    def program_from_checked_json(self, json_string: str) -> CelProgram:
        checked_expr_pb = checked_pb2.CheckedExpr()
        json_format.Parse(json_string, checked_expr_pb)
        return CelProgram(checked_expr_pb, self)