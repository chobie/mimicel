from . import STANDARD_LIBRARY, TYPE_LIST_OF_VALUES, TYPE_STRUCT_AS_MAP
from ..cel_values.cel_types import (
    CelFunctionDefinition,
    CEL_DYN, CEL_INT, CEL_STRING, CEL_BOOL,
    CEL_LIST, CEL_MAP, CEL_UINT,
    CEL_VALUE_WRAPPER,      # For google.protobuf.Value
    CEL_STRUCT_WRAPPER,     # For google.protobuf.Struct
    CEL_LIST_WRAPPER        # For google.protobuf.ListValue
)

from .operators import (
    cel_operator_in_wrapper,
    cel_operator_ternary_wrapper, cel_operator_is_wrapper,
)

# (Many already listed in user's provided file, ensure WKT coverage)
# DYN in list<DYN>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_DYN, CEL_LIST], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
# Value in list<Value>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_VALUE_WRAPPER, TYPE_LIST_OF_VALUES], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
# DYN in list<Value>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_DYN, TYPE_LIST_OF_VALUES], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
# Value in ListValue (message type)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_VALUE_WRAPPER, CEL_LIST_WRAPPER], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
# DYN in ListValue (message type)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_DYN, CEL_LIST_WRAPPER], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
# string in map<string, Value> (Struct)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_STRING, TYPE_STRUCT_AS_MAP], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
# string in Struct (message type)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_STRING, CEL_STRUCT_WRAPPER], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
# DYN in Value (Value containing list or struct)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_DYN, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
# DYN in DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
# Key in Map for standard key types
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_STRING, CEL_MAP], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_INT, CEL_MAP], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_UINT, CEL_MAP], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_in_", arg_types=[CEL_BOOL, CEL_MAP], result_type=CEL_BOOL, implementation=cel_operator_in_wrapper, expects_cel_values=True))

# --- Conditional Operator (_?_:_) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_?_:_", arg_types=[CEL_BOOL, CEL_DYN, CEL_DYN], result_type=CEL_DYN, implementation=cel_operator_ternary_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_?_:_", arg_types=[CEL_DYN, CEL_DYN, CEL_DYN], result_type=CEL_DYN, implementation=cel_operator_ternary_wrapper, expects_cel_values=True))
# (Optionally add specific overloads like (bool, int, int) -> int if _determine_common_type is sophisticated)


# --- Type Checking Operator (_is_) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(
    name="_is_",
    arg_types=[CEL_DYN, CEL_STRING], # ★ 第2引数を CEL_TYPE から CEL_STRING に変更
    result_type=CEL_BOOL,
    implementation=cel_operator_is_wrapper, # この実装が文字列から型への比較を行う
    expects_cel_values=True
))
