from . import STANDARD_LIBRARY, TYPE_LIST_OF_VALUES, TYPE_STRUCT_AS_MAP
from ..cel_values.cel_types import (
    CelFunctionDefinition,
    CEL_DYN, CEL_TIMESTAMP, CEL_DURATION, CEL_INT, CEL_STRING, CEL_BOOL, CEL_BYTES,
    CEL_LIST, CEL_MAP, CEL_TYPE, CEL_UINT, CEL_NULL, CEL_DOUBLE,
    make_list_type, make_map_type,
    CEL_VALUE_WRAPPER,  # For google.protobuf.Value
    CEL_STRUCT_WRAPPER,  # For google.protobuf.Struct
    CEL_LIST_WRAPPER, CEL_BYTES_WRAPPER, CEL_ERROR  # For google.protobuf.ListValue
)

from .operators import (
    cel_operator_negate_wrapper,
    cel_operator_equals_wrapper, cel_operator_not_equals_wrapper,
    cel_operator_less_than_wrapper, cel_operator_less_than_equals_wrapper,
    cel_operator_greater_than_wrapper, cel_operator_greater_than_equals_wrapper,
    cel_operator_logical_not_wrapper, cel_operator_index_wrapper,
)


# --- Logical NOT (_!_) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_!_", arg_types=[CEL_BOOL], result_type=CEL_BOOL, implementation=cel_operator_logical_not_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_!_", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=cel_operator_logical_not_wrapper, expects_cel_values=True)) # !Value


# --- Negation (_-_ unary) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_-_", arg_types=[CEL_INT], result_type=CEL_INT, implementation=cel_operator_negate_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_-_", arg_types=[CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=cel_operator_negate_wrapper, expects_cel_values=True))
#STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_-_", arg_types=[CEL_UINT], result_type=CEL_INT, implementation=cel_operator_negate_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_-_", arg_types=[CEL_DURATION], result_type=CEL_DURATION, implementation=cel_operator_negate_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_-_", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=cel_operator_negate_wrapper, expects_cel_values=True)) # -Value -> DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_-_", arg_types=[CEL_DYN], result_type=CEL_DYN, implementation=cel_operator_negate_wrapper, expects_cel_values=True))


# --- Index Operator (_[_]) ---
# List indexing
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[CEL_LIST, CEL_INT], result_type=CEL_DYN, implementation=cel_operator_index_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[make_list_type(CEL_DYN), CEL_INT], result_type=CEL_DYN, implementation=cel_operator_index_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[TYPE_LIST_OF_VALUES, CEL_INT], result_type=CEL_VALUE_WRAPPER, implementation=cel_operator_index_wrapper, expects_cel_values=True)) # list<Value>[int] -> Value
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[CEL_LIST_WRAPPER, CEL_INT], result_type=CEL_VALUE_WRAPPER, implementation=cel_operator_index_wrapper, expects_cel_values=True)) # ListValue[int] -> Value
# Map/Struct indexing (key type string)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[CEL_MAP, CEL_STRING], result_type=CEL_DYN, implementation=cel_operator_index_wrapper, expects_cel_values=True)) # map<dyn,dyn>['str']
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[make_map_type(CEL_STRING, CEL_DYN), CEL_STRING], result_type=CEL_DYN, implementation=cel_operator_index_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[TYPE_STRUCT_AS_MAP, CEL_STRING], result_type=CEL_VALUE_WRAPPER, implementation=cel_operator_index_wrapper, expects_cel_values=True)) # map<string,Value>['str'] -> Value
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[CEL_STRUCT_WRAPPER, CEL_STRING], result_type=CEL_VALUE_WRAPPER, implementation=cel_operator_index_wrapper, expects_cel_values=True)) # Struct['str'] -> Value
# Map indexing (other key types)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[make_map_type(CEL_INT, CEL_DYN), CEL_INT], result_type=CEL_DYN, implementation=cel_operator_index_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[make_map_type(CEL_UINT, CEL_DYN), CEL_UINT], result_type=CEL_DYN, implementation=cel_operator_index_wrapper, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[make_map_type(CEL_BOOL, CEL_DYN), CEL_BOOL], result_type=CEL_DYN, implementation=cel_operator_index_wrapper, expects_cel_values=True))
# Value indexing (Value containing list or struct)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[CEL_VALUE_WRAPPER, CEL_INT], result_type=CEL_VALUE_WRAPPER, implementation=cel_operator_index_wrapper, expects_cel_values=True))    # Value[int] -> Value
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[CEL_VALUE_WRAPPER, CEL_STRING], result_type=CEL_VALUE_WRAPPER, implementation=cel_operator_index_wrapper, expects_cel_values=True)) # Value['str'] -> Value
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[CEL_VALUE_WRAPPER, CEL_DYN], result_type=CEL_VALUE_WRAPPER, implementation=cel_operator_index_wrapper, expects_cel_values=True))   # Fallback for Value index
# DYN fallback
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_[_]", arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_DYN, implementation=cel_operator_index_wrapper, expects_cel_values=True))


# --- Relational and Equality Operators ---
# Explicitly define each pair for _==_, _!=_, _<_, _<=_, _>=_, _>_
# This will be very verbose. Below is a pattern for _==_ and _<_.

op_ne = "_!=_"
impl_ne = cel_operator_not_equals_wrapper # from .operators import cel_operator_not_equals_wrapper

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
# Homogeneous primitives
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_INT, CEL_INT], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_STRING, CEL_STRING], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_BYTES, CEL_BYTES], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_BOOL, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_NULL, CEL_NULL], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True)) # null != null is false
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_TIMESTAMP, CEL_TIMESTAMP], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_DURATION, CEL_DURATION], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_TYPE, CEL_TYPE], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_LIST, CEL_LIST], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_MAP, CEL_MAP], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[TYPE_LIST_OF_VALUES, TYPE_LIST_OF_VALUES], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[TYPE_STRUCT_AS_MAP, TYPE_STRUCT_AS_MAP], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_LIST_WRAPPER, CEL_LIST_WRAPPER], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_STRUCT_WRAPPER, CEL_STRUCT_WRAPPER], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
# Cross-numeric
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
# Value vs Primitives/Null (for equality/inequality)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_VALUE_WRAPPER, CEL_NULL], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ne, arg_types=[CEL_NULL, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ne, expects_cel_values=True))
# ... (Value vs INT, UINT, DOUBLE, STRING, BYTES, BOOL, TIMESTAMP, DURATION, etc. for _!=_)


# _==_ (Equality)
op_eq = "_==_"
impl_eq = cel_operator_equals_wrapper
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
# Homogeneous
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_INT, CEL_INT], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_STRING, CEL_STRING], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_BYTES, CEL_BYTES], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_BOOL, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_NULL, CEL_NULL], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_TIMESTAMP, CEL_TIMESTAMP], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_DURATION, CEL_DURATION], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_TYPE, CEL_TYPE], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_LIST, CEL_LIST], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True)) # list<dyn> == list<dyn>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_MAP, CEL_MAP], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True)) # map<dyn,dyn> == map<dyn,dyn>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[TYPE_LIST_OF_VALUES, TYPE_LIST_OF_VALUES], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True)) # list<V> == list<V>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[TYPE_STRUCT_AS_MAP, TYPE_STRUCT_AS_MAP], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True)) # map<S,V> == map<S,V>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_LIST_WRAPPER, CEL_LIST_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True)) # ListValue == ListValue
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_STRUCT_WRAPPER, CEL_STRUCT_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True)) # Struct == Struct
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True)) # Value == Value
# Cross-numeric
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
# Value vs Primitives/Null (for equality)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_NULL], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_NULL, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_BOOL, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_INT], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_INT, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_UINT], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_UINT, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_DOUBLE, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_STRING], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_STRING, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_BYTES], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_BYTES, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
# Value vs WKTs (equality)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_TIMESTAMP], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_TIMESTAMP, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, CEL_DURATION], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_DURATION, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, TYPE_STRUCT_AS_MAP], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True)) # Value == map<string,Value>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[TYPE_STRUCT_AS_MAP, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[CEL_VALUE_WRAPPER, TYPE_LIST_OF_VALUES], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True)) # Value == list<Value>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_eq, arg_types=[TYPE_LIST_OF_VALUES, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_eq, expects_cel_values=True))


# _<_ (Less Than)
op_lt = "_<_"
impl_lt = cel_operator_less_than_wrapper
# Homogeneous primitives
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_INT, CEL_INT], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_STRING, CEL_STRING], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_BYTES, CEL_BYTES], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_BOOL, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True)) # false < true
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_TIMESTAMP, CEL_TIMESTAMP], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_DURATION, CEL_DURATION], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
# Cross-numeric
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
# Value comparisons (ordering primarily with self or DYN, or specific compatible primitives as per checker)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
# Based on updated _check_comparison_operator allowing Value vs Primitives for ordering:
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_VALUE_WRAPPER, CEL_INT], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_INT, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_VALUE_WRAPPER, CEL_UINT], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_UINT, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_VALUE_WRAPPER, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_DOUBLE, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_VALUE_WRAPPER, CEL_STRING], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_STRING, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_VALUE_WRAPPER, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_BOOL, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_lt, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_BOOL, implementation=impl_lt, expects_cel_values=True))
# Note: List, Map, Struct, Bytes, Null, Type are generally not orderable with Value unless Value contains that specific type.

# _<=_ (Less Than or Equal To)
op_le = "_<=_"
impl_le = cel_operator_less_than_equals_wrapper
# (Repeat all pairs as for _<_)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_INT, CEL_INT], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_STRING, CEL_STRING], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_BYTES, CEL_BYTES], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_BOOL, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_TIMESTAMP, CEL_TIMESTAMP], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_DURATION, CEL_DURATION], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_VALUE_WRAPPER, CEL_INT], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_INT, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_le, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_BOOL, implementation=impl_le, expects_cel_values=True))
# ... (Value vs other primitives for <=)

# _>_ (Greater Than)
op_gt = "_>_"
impl_gt = cel_operator_greater_than_wrapper
# Homogeneous primitives
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_INT, CEL_INT], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_STRING, CEL_STRING], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_BYTES, CEL_BYTES], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_BOOL, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_TIMESTAMP, CEL_TIMESTAMP], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_DURATION, CEL_DURATION], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
# Cross-numeric
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
# Value comparisons (ordering with self, DYN, or specific compatible primitives as per type checker)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_VALUE_WRAPPER, CEL_INT], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_INT, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_VALUE_WRAPPER, CEL_UINT], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_UINT, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_VALUE_WRAPPER, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_DOUBLE, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_VALUE_WRAPPER, CEL_STRING], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_STRING, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_VALUE_WRAPPER, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_BOOL, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_VALUE_WRAPPER, CEL_BYTES], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_BYTES, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_VALUE_WRAPPER, CEL_TIMESTAMP], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_TIMESTAMP, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_VALUE_WRAPPER, CEL_DURATION], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_DURATION, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_gt, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_BOOL, implementation=impl_gt, expects_cel_values=True))
# Note: NULL and TYPE are generally not orderable. List/Map are not orderable by these operators.

# _>=_ (Greater Than or Equal To)
op_ge = "_>=_"
impl_ge = cel_operator_greater_than_equals_wrapper
# Homogeneous primitives
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_INT, CEL_INT], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_STRING, CEL_STRING], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_BYTES, CEL_BYTES], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_BOOL, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_TIMESTAMP, CEL_TIMESTAMP], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_DURATION, CEL_DURATION], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
# Cross-numeric
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
# Value comparisons
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_VALUE_WRAPPER, CEL_INT], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_INT, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_VALUE_WRAPPER, CEL_UINT], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_UINT, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_VALUE_WRAPPER, CEL_DOUBLE], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_DOUBLE, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_VALUE_WRAPPER, CEL_STRING], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_STRING, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_VALUE_WRAPPER, CEL_BOOL], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_BOOL, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_VALUE_WRAPPER, CEL_BYTES], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_BYTES, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_VALUE_WRAPPER, CEL_TIMESTAMP], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_TIMESTAMP, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_VALUE_WRAPPER, CEL_DURATION], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_DURATION, CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_ge, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_BOOL, implementation=impl_ge, expects_cel_values=True))

