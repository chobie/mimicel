# type_registry.py
import logging
from typing import Dict, Set, Type, Optional, Any, TYPE_CHECKING
from google.protobuf.message import Message as ProtobufMessage
from google.protobuf.descriptor import FieldDescriptor, EnumDescriptor, Descriptor

from .cel_values.cel_types import (
    CEL_INT, CEL_UINT, CEL_DOUBLE, CEL_STRING, CEL_BOOL, CEL_BYTES,
    CEL_TIMESTAMP, CEL_DURATION, CEL_DYN, CEL_UNKNOWN,
    CEL_INT32_WRAPPER, CEL_UINT32_WRAPPER, CEL_INT64_WRAPPER,
    CEL_UINT64_WRAPPER, CEL_BOOL_WRAPPER, CEL_DOUBLE_WRAPPER, CEL_STRING_WRAPPER, CEL_BYTES_WRAPPER,
    make_list_type, make_map_type, CelMessageType, CelType, CEL_STRUCT_WRAPPER, CEL_LIST_WRAPPER, CEL_VALUE_WRAPPER,
    CEL_FLOAT_WRAPPER, CEL_ANY
)


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class TypeRegistry:
    def __init__(self):
        # message_name (str) -> {field_name (str): CelType}
        self._message_fields: Dict[str, Dict[str, 'CelType']] = {}
        # message_name (str) -> Python Protobuf Message Class (Type[ProtobufMessage])
        self._message_python_classes: Dict[str, Type[ProtobufMessage]] = {}
        self._message_constructibility: Dict[str, bool] = {}
        #   enum_name (str) -> {value_name (str): value_number (int)}
        self._enum_values: Dict[str, Dict[str, int]] = {}
        #   enum_name (str) -> EnumDescriptor (オプション、詳細情報が必要な場合)
        self._enum_descriptors: Dict[str, EnumDescriptor] = {}
        self._known_packages: Set[str] = set() # ★ 登録されたパッケージ名を保持

    def get_message_descriptor(self, message_name_fqn: str) -> Optional[Descriptor]:
        py_class = self._message_python_classes.get(message_name_fqn)
        if py_class and hasattr(py_class, 'DESCRIPTOR'):
            if isinstance(py_class.DESCRIPTOR, Descriptor):
                return py_class.DESCRIPTOR
            else:
                # print(f"Warning: {message_name_fqn}.DESCRIPTOR is not a MessageDescriptor, but {type(py_class.DESCRIPTOR)}")
                pass
        return None

    def _add_package_prefixes(self, full_name: str):
        """完全修飾名からパッケージプレフィックスを抽出し、_known_packagesに追加"""
        if '.' in full_name:
            parts = full_name.split('.')
            for i in range(1, len(parts)): # 最後の要素（クラス名/Enum名）は除く
                self._known_packages.add(".".join(parts[:i]))

    def _map_protobuf_primitive_to_cel_type(self, field_type_enum: int) -> 'CelType':
        """ Protobuf FieldDescriptor.type (enum値) をプリミティブなCelTypeにマッピングするヘルパー """
        if field_type_enum == FieldDescriptor.TYPE_DOUBLE: return CEL_DOUBLE
        if field_type_enum == FieldDescriptor.TYPE_FLOAT: return CEL_DOUBLE
        if field_type_enum == FieldDescriptor.TYPE_INT64: return CEL_INT
        if field_type_enum == FieldDescriptor.TYPE_UINT64: return CEL_UINT
        if field_type_enum == FieldDescriptor.TYPE_INT32: return CEL_INT
        if field_type_enum == FieldDescriptor.TYPE_FIXED64: return CEL_UINT
        if field_type_enum == FieldDescriptor.TYPE_FIXED32: return CEL_UINT
        if field_type_enum == FieldDescriptor.TYPE_BOOL: return CEL_BOOL
        if field_type_enum == FieldDescriptor.TYPE_STRING: return CEL_STRING
        if field_type_enum == FieldDescriptor.TYPE_BYTES: return CEL_BYTES
        if field_type_enum == FieldDescriptor.TYPE_UINT32: return CEL_UINT
        if field_type_enum == FieldDescriptor.TYPE_SFIXED32: return CEL_INT
        if field_type_enum == FieldDescriptor.TYPE_SFIXED64: return CEL_INT
        if field_type_enum == FieldDescriptor.TYPE_SINT32: return CEL_INT
        if field_type_enum == FieldDescriptor.TYPE_SINT64: return CEL_INT
        if field_type_enum == FieldDescriptor.TYPE_ENUM: return CEL_INT  # Enum は int
        return CEL_UNKNOWN  # 不明なプリミティブ型

    def _protobuf_field_type_to_cel_type(self, field: FieldDescriptor) -> 'CelType':
        # --- ▼▼▼ 修正: MAP FIELD HANDLING を最優先に ▼▼▼ ---
        if field.type == FieldDescriptor.TYPE_MESSAGE and \
                field.message_type and \
                hasattr(field.message_type, 'GetOptions') and \
                callable(field.message_type.GetOptions) and \
                field.message_type.GetOptions().map_entry:

            key_field_desc = field.message_type.fields_by_name.get('key')
            value_field_desc = field.message_type.fields_by_name.get('value')

            if not key_field_desc or not value_field_desc:
                # print(f"Warning: Malformed map entry for field '{field.full_name}'. Missing key/value.")
                return CEL_UNKNOWN

            cel_key_type = self._protobuf_field_type_to_cel_type(key_field_desc)
            cel_value_type = self._protobuf_field_type_to_cel_type(value_field_desc)

            # map<K,V> のキー型がCELで許可されているか確認 (通常 string, int, uint, bool)
            # ここでは key_field_desc.type から直接CEL型に変換したものをそのまま使う
            # (例: string -> CEL_STRING, int32 -> CEL_INT)
            # Protobufのmapキーはスカラー型のみ許可される
            allowed_map_key_types = [CEL_STRING, CEL_INT, CEL_UINT, CEL_BOOL]
            if cel_key_type not in allowed_map_key_types:
                # print(f"Warning: Unsupported map key type '{cel_key_type.name}' for field '{field.full_name}'.")
                return CEL_UNKNOWN  # または map<dyn, V> のようなフォールバック

            return make_map_type(cel_key_type, cel_value_type)
        # --- ▲▲▲ MAP FIELD HANDLING --- ▲▲▲

        if field.label == FieldDescriptor.LABEL_REPEATED:  # マップでない場合の repeated
            element_cel_type: 'CelType'
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                element_cel_type = self._protobuf_field_type_to_cel_type_message_or_wellknown(field)
            elif field.type == FieldDescriptor.TYPE_ENUM:
                if field.enum_type: self.register_enum_type(field.enum_type)
                element_cel_type = CEL_INT
            else:
                element_cel_type = self._map_protobuf_primitive_to_cel_type(field.type)
            return make_list_type(element_cel_type)

        # 単一フィールド (repeatedでもmapでもない)
        if field.type == FieldDescriptor.TYPE_MESSAGE:
            return self._protobuf_field_type_to_cel_type_message_or_wellknown(field)

        if field.type == FieldDescriptor.TYPE_ENUM:
            if field.enum_type: self.register_enum_type(field.enum_type)
            return CEL_INT

        return self._map_protobuf_primitive_to_cel_type(field.type)

    def _protobuf_field_type_to_cel_type_message_or_wellknown(self, field: FieldDescriptor) -> 'CelType':
        """ TYPE_MESSAGE のフィールドを処理 (WellKnownTypeを含む) """
        if not field.message_type:  # ありえないはずだが念のため
            return CEL_UNKNOWN

        full_name = field.message_type.full_name
        if full_name == "google.protobuf.Duration": return CEL_DURATION
        if full_name == "google.protobuf.Timestamp": return CEL_TIMESTAMP
        if full_name == "google.protobuf.Int32Value": return CEL_INT32_WRAPPER
        if full_name == "google.protobuf.UInt32Value": return CEL_UINT32_WRAPPER
        if full_name == "google.protobuf.Int64Value": return CEL_INT64_WRAPPER
        if full_name == "google.protobuf.UInt64Value": return CEL_UINT64_WRAPPER
        if full_name == "google.protobuf.BoolValue": return CEL_BOOL_WRAPPER
        if full_name == "google.protobuf.FloatValue": return CEL_FLOAT_WRAPPER
        if full_name == "google.protobuf.DoubleValue": return CEL_DOUBLE_WRAPPER
        if full_name == "google.protobuf.FloatValue": return CEL_DOUBLE_WRAPPER # または専用のCEL_FLOAT32_WRAPPER
        if full_name == "google.protobuf.StringValue": return CEL_STRING_WRAPPER
        if full_name == "google.protobuf.BytesValue": return CEL_BYTES_WRAPPER
        if full_name == "google.protobuf.Value": return CEL_VALUE_WRAPPER
        if full_name == "google.protobuf.Struct": return CEL_STRUCT_WRAPPER
        if full_name == "google.protobuf.ListValue": return CEL_LIST_WRAPPER
        if full_name == "google.protobuf.Any": return CEL_ANY

        return CelType.get_or_register_type_instance(
            full_name,
            CelMessageType,
            python_type=self._message_python_classes.get(full_name)  # 登録済みのPythonクラスを渡す
        )

    def register_message_type(self,
                              message_class: Type[ProtobufMessage],
                              full_name_override: Optional[str] = None,
                              is_constructible: bool = True):
        if not isinstance(message_class, type) or not issubclass(message_class, ProtobufMessage):
            raise TypeError(f"{message_class} is not a valid Protobuf Message class.")

        descriptor = message_class.DESCRIPTOR
        message_name = full_name_override if full_name_override else descriptor.full_name

        self._add_package_prefixes(message_name)  # ★ パッケージ名を登録

        if message_name in self._message_python_classes and self._message_python_classes[message_name] == message_class:
            self._message_constructibility[message_name] = is_constructible
            for enum_desc in descriptor.enum_types:  # 既に登録済みでもネストEnumは再帰的に登録試行
                self.register_enum_type(enum_desc)
            # ネストされたメッセージも同様に登録を試みるか、呼び出し元に委ねる
            # for nested_type_desc in descriptor.nested_types:
            #     try:
            #         from google.protobuf import message_factory # 遅延インポート
            #         nested_py_class = message_factory.GetMessageClass(nested_type_desc)
            #         if nested_py_class: self.register_message_type(nested_py_class)
            #     except Exception: pass # クラス取得失敗は無視
            return
        elif message_name in self._message_python_classes:
            logger.warn(
                f"Warning: Message type '{message_name}' is being re-registered with a different class. This may be unintended.")

        self._message_python_classes[message_name] = message_class
        self._message_constructibility[message_name] = is_constructible

        # CelTypeのグローバルレジストリにもCelMessageTypeとして登録
        CelType.get_or_register_type_instance(
            message_name, CelMessageType, python_type=message_class
        )

        fields_info: Dict[str, 'CelType'] = {}
        for field_descriptor in descriptor.fields:
            fields_info[field_descriptor.name] = self._protobuf_field_type_to_cel_type(field_descriptor)
        self._message_fields[message_name] = fields_info

        for enum_desc in descriptor.enum_types:
            self.register_enum_type(enum_desc)

    def register_enum_type(self, enum_descriptor: EnumDescriptor, parent_message_name: Optional[str] = None):
        if not isinstance(enum_descriptor, EnumDescriptor):
            raise TypeError("Expected EnumDescriptor.")

        enum_full_name = enum_descriptor.full_name
        self._add_package_prefixes(enum_full_name) # ★ Enumのパッケージ名も登録

        if enum_full_name in self._enum_descriptors:
            return

        self._enum_descriptors[enum_full_name] = enum_descriptor
        self._enum_values[enum_full_name] = {
            val_desc.name: val_desc.number for val_desc in enum_descriptor.values
        }
        # Enum型名自体をCelTypeとしてグローバルレジストリに登録
        CelType.get_or_register_type_instance(enum_full_name, CelType)


    def is_package(self, name: str) -> bool: # ★ is_packageメソッドを追加
        """指定された名前が登録済みのパッケージ名（またはそのプレフィックス）であるか"""
        if name in self._known_packages:
            return True
        # name が登録済みパッケージのプレフィックスであるか (例: name="cel.expr", 登録済み="cel.expr.conformance")
        # より正確には、name + "." で始まるパッケージがあるか
        for pkg in self._known_packages:
            if pkg.startswith(name + "."):
                return True
        return False

    def is_enum_type(self, type_name: str) -> bool:
        """指定された名前が登録済みのEnum型か"""
        return type_name in self._enum_descriptors

    def get_enum_value(self, enum_name: str, value_name: str) -> Optional[int]:
        """指定されたEnum型の特定の値の数値を取得"""
        if enum_name in self._enum_values and value_name in self._enum_values[enum_name]:
            return self._enum_values[enum_name][value_name]
        return None

    def get_enum_descriptor(self, enum_name: str) -> Optional[EnumDescriptor]:
        return self._enum_descriptors.get(enum_name)

    def is_message_constructible(self, message_name: str) -> bool:
        """指定されたメッセージ型がCELのメッセージ構築式で構築可能か返す"""
        # 登録されていない型は構築不可として扱うか、エラーとするか。
        # ここでは登録されていればフラグ値を、なければFalseを返す。
        return self._message_constructibility.get(message_name, False)


    def is_message_type(self, type_name: str) -> bool:
        return type_name in self._message_python_classes  # Pythonクラスが登録されているかで判定

    def has_field(self, message_name: str, field_name: str) -> bool:
        return message_name in self._message_fields and field_name in self._message_fields[message_name]

    def get_message_cel_type(self, message_name: str) -> Optional['CelMessageType']:
        cel_type_instance = CelType.get_by_name(message_name)
        if isinstance(cel_type_instance, CelMessageType):
            # python_type がまだ設定されていなければ、ここで設定を試みる
            if cel_type_instance.python_type is None and message_name in self._message_python_classes:
                cel_type_instance.python_type = self._message_python_classes[message_name]
            return cel_type_instance

        # CelTypeレジストリにないが、Pythonクラスは登録されている場合 (依存関係で後から解決されるなど)
        if message_name in self._message_python_classes and not cel_type_instance:
            py_class = self._message_python_classes[message_name]
            # この呼び出しで CelType._registry にも登録される
            return CelType.get_or_register_type_instance(message_name, CelMessageType,
                                                         python_type=py_class)  # type: ignore
        return None

    def get_field_cel_type(self, message_name: str, field_name: str) -> Optional['CelType']:
        if self.has_field(message_name, field_name):
            return self._message_fields[message_name][field_name]
        return None

    def get_python_message_class(self, message_name: str) -> Optional[Type[ProtobufMessage]]:
        return self._message_python_classes.get(message_name)

    def register(self, py_type: Type, field_names: Set[str], is_message: Optional[bool] = None,
                 type_name_override: Optional[str] = None):
        # この汎用registerメソッドも is_constructible を考慮するように修正するか検討。
        # ただし、現状はProtobufMessageでない型は is_constructible=True 相当で登録されている。
        if issubclass(py_type, ProtobufMessage):
            # ProtobufMessageの場合、is_constructible はTrueがデフォルト
            self.register_message_type(py_type, full_name_override=type_name_override, is_constructible=True)
        else:
            type_name = type_name_override if type_name_override else py_type.__name__
            CelType.get_or_register_type_instance(type_name, CelType)
            self._message_fields[type_name] = {fname: CEL_DYN for fname in field_names}
            # Protobufでない型の場合、_message_constructibility にはどう記録するか？
            # CELのメッセージ構築構文はProtobufメッセージ用なので、非Protobuf型は構築不可(False)とするのが自然か。
            self._message_constructibility[type_name] = False

    def get_field_names(self, type_name: str) -> Optional[Set[str]]:
        if type_name in self._message_fields:
            return set(self._message_fields[type_name].keys())
        return None

    def has_type(self, type_name: str) -> bool:
        return type_name in self._message_fields

    def register_native_type(self, native_type: Type[Any]):
        """Register a native Python type with the CEL type system using reflection."""
        type_name = native_type.__name__
        
        # Add to known packages if it has a module
        if hasattr(native_type, '__module__') and native_type.__module__:
            module_parts = native_type.__module__.split('.')
            if module_parts[0] != '__main__':
                for i in range(1, len(module_parts) + 1):
                    self._known_packages.add('.'.join(module_parts[:i]))
        
        # Register in CelType registry as CelMessageType (like protobuf messages)
        CelType.get_or_register_type_instance(type_name, CelMessageType, python_type=native_type)
        
        # Extract fields using reflection
        fields_info: Dict[str, 'CelType'] = {}
        
        # Get fields from __init__ method signature
        if hasattr(native_type, '__init__'):
            import inspect
            sig = inspect.signature(native_type.__init__)
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                    
                # Try to map Python type hints to CEL types
                if param.annotation != inspect.Parameter.empty:
                    cel_type = self._python_type_to_cel_type(param.annotation)
                    fields_info[param_name] = cel_type
                else:
                    # Default to DYN if no type annotation
                    fields_info[param_name] = CEL_DYN
        
        # Also check instance attributes by creating a temporary instance if possible
        try:
            # Try to create an instance with dummy values to discover instance attributes
            sig = inspect.signature(native_type.__init__)
            dummy_args = {}
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                # Create dummy values based on type annotations
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == str:
                        dummy_args[param_name] = ""
                    elif param.annotation == int:
                        dummy_args[param_name] = 0
                    elif param.annotation == float:
                        dummy_args[param_name] = 0.0
                    elif param.annotation == bool:
                        dummy_args[param_name] = False
                    elif param.annotation == bytes:
                        dummy_args[param_name] = b""
                    elif hasattr(param.annotation, '__origin__') and param.annotation.__origin__ == list:
                        dummy_args[param_name] = []
                    else:
                        dummy_args[param_name] = None
                else:
                    dummy_args[param_name] = None
            
            # Create temporary instance
            temp_instance = native_type(**dummy_args)
            
            # Discover all instance attributes
            for attr_name in dir(temp_instance):
                if not attr_name.startswith('_') and attr_name not in fields_info:
                    # Try to determine the type of the attribute
                    attr_value = getattr(temp_instance, attr_name, None)
                    if attr_value is not None:
                        cel_type = self._python_value_to_cel_type(attr_value)
                        fields_info[attr_name] = cel_type
                    else:
                        fields_info[attr_name] = CEL_DYN
        except Exception:
            # If we can't create an instance, fall back to class attributes
            for attr_name in dir(native_type):
                if not attr_name.startswith('_') and attr_name not in fields_info:
                    fields_info[attr_name] = CEL_DYN
        
        self._message_fields[type_name] = fields_info
        # Native types are constructible
        self._message_constructibility[type_name] = True
        
        # Store the Python class - use the same dict as protobuf messages
        # This ensures is_message_type() will return True for native types
        self._message_python_classes[type_name] = native_type
    
    def _python_value_to_cel_type(self, value: Any) -> 'CelType':
        """Map Python values to CEL types based on their runtime type."""
        if isinstance(value, str):
            return CEL_STRING
        elif isinstance(value, int):
            return CEL_INT
        elif isinstance(value, float):
            return CEL_DOUBLE
        elif isinstance(value, bool):
            return CEL_BOOL
        elif isinstance(value, bytes):
            return CEL_BYTES
        elif isinstance(value, list):
            # Try to infer element type from first element
            if value and len(value) > 0:
                element_type = self._python_value_to_cel_type(value[0])
                return make_list_type(element_type)
            return make_list_type(CEL_DYN)
        elif isinstance(value, dict):
            # Try to infer key/value types from first item
            if value:
                first_key = next(iter(value))
                first_value = value[first_key]
                key_type = self._python_value_to_cel_type(first_key)
                value_type = self._python_value_to_cel_type(first_value)
                return make_map_type(key_type, value_type)
            return make_map_type(CEL_DYN, CEL_DYN)
        else:
            # For objects, check if it's a registered type
            type_name = type(value).__name__
            cel_type = CelType.get_by_name(type_name)
            if cel_type:
                return cel_type
        return CEL_DYN
    
    def _python_type_to_cel_type(self, python_type: Type) -> 'CelType':
        """Map Python types to CEL types."""
        if python_type == str:
            return CEL_STRING
        elif python_type == int:
            return CEL_INT
        elif python_type == float:
            return CEL_DOUBLE
        elif python_type == bool:
            return CEL_BOOL
        elif python_type == bytes:
            return CEL_BYTES
        elif hasattr(python_type, '__origin__'):
            # Handle generic types like List[str], Dict[str, int]
            origin = python_type.__origin__
            if origin == list:
                # Get the element type if available
                args = getattr(python_type, '__args__', ())
                if args:
                    element_type = self._python_type_to_cel_type(args[0])
                    return make_list_type(element_type)
                return make_list_type(CEL_DYN)
            elif origin == dict:
                # Get key and value types if available
                args = getattr(python_type, '__args__', ())
                if len(args) >= 2:
                    key_type = self._python_type_to_cel_type(args[0])
                    value_type = self._python_type_to_cel_type(args[1])
                    return make_map_type(key_type, value_type)
                return make_map_type(CEL_DYN, CEL_DYN)
        else:
            # For other types, check if it's a registered type
            type_name = getattr(python_type, '__name__', str(python_type))
            cel_type = CelType.get_by_name(type_name)
            if cel_type:
                return cel_type
                
        return CEL_DYN

    def get_field(self, obj: Any, field_name: str) -> Optional[Any]:
        type_name: Optional[str] = None
        is_proto_message = isinstance(obj, ProtobufMessage)
        if is_proto_message:
            type_name = obj.DESCRIPTOR.full_name
        else:
            type_name = type(obj).__name__

        if type_name and self.has_field(type_name, field_name):
            try:
                return getattr(obj, field_name)
            except AttributeError:
                return None

        if hasattr(obj, field_name):
            return getattr(obj, field_name)

        return None
