from . import STANDARD_LIBRARY, TYPE_LIST_OF_VALUES
from ..cel_values.cel_types import (
    CelFunctionDefinition,
    CEL_DYN,
    CEL_TIMESTAMP,
    CEL_DURATION,
    CEL_INT,
    CEL_STRING,
    CEL_BYTES,
    CEL_LIST,
    CEL_UINT,
    CEL_DOUBLE,
    make_list_type,
    CEL_VALUE_WRAPPER,      # For google.protobuf.Value
    CEL_LIST_WRAPPER        # For google.protobuf.ListValue
)

from .operators import (
    cel_operator_add_wrapper, cel_operator_subtract_wrapper, cel_operator_multiply_wrapper,
    cel_operator_divide_wrapper, cel_operator_modulo_wrapper,
)


op_add = "_+_"
impl_add = cel_operator_add_wrapper

# DYN (Catch-all, DYN + DYN -> DYN)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))

# Numeric Addition
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_INT, CEL_INT], result_type=CEL_INT, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_UINT, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_add, expects_cel_values=True))
# Cross-Numeric (as per _check_addition_operator logic)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_INT, implementation=impl_add, expects_cel_values=True)) # Or DYN if prefered
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_INT, implementation=impl_add, expects_cel_values=True)) # Or DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_DOUBLE, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_DOUBLE, implementation=impl_add, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(
    name="_+_",
    arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER],
    result_type=CEL_DYN,
    implementation=cel_operator_add_wrapper,
    expects_cel_values=True
))

# Value + Int -> DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(
    name="_+_",
    arg_types=[CEL_VALUE_WRAPPER, CEL_INT],
    result_type=CEL_DYN,
    implementation=cel_operator_add_wrapper,
    expects_cel_values=True
))
# Int + Value -> DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(
    name="_+_",
    arg_types=[CEL_INT, CEL_VALUE_WRAPPER],
    result_type=CEL_DYN,
    implementation=cel_operator_add_wrapper,
    expects_cel_values=True
))


# String Concatenation
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_STRING, CEL_STRING], result_type=CEL_STRING, implementation=impl_add, expects_cel_values=True))

# Bytes Concatenation
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_BYTES, CEL_BYTES], result_type=CEL_BYTES, implementation=impl_add, expects_cel_values=True))

# List Concatenation
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_LIST, CEL_LIST], result_type=CEL_LIST, implementation=impl_add, expects_cel_values=True)) # list<dyn> + list<dyn> -> list<dyn>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[make_list_type(CEL_DYN), make_list_type(CEL_DYN)], result_type=make_list_type(CEL_DYN), implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[TYPE_LIST_OF_VALUES, TYPE_LIST_OF_VALUES], result_type=TYPE_LIST_OF_VALUES, implementation=impl_add, expects_cel_values=True)) # list<Value> + list<Value> -> list<Value>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_LIST_WRAPPER, CEL_LIST_WRAPPER], result_type=TYPE_LIST_OF_VALUES, implementation=impl_add, expects_cel_values=True)) # ListValue + ListValue -> list<Value>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_LIST_WRAPPER, CEL_LIST], result_type=make_list_type(CEL_DYN), implementation=impl_add, expects_cel_values=True)) # ListValue + list<dyn> -> list<dyn>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_LIST, CEL_LIST_WRAPPER], result_type=make_list_type(CEL_DYN), implementation=impl_add, expects_cel_values=True)) # list<dyn> + ListValue -> list<dyn>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[TYPE_LIST_OF_VALUES, CEL_LIST], result_type=make_list_type(CEL_DYN), implementation=impl_add, expects_cel_values=True)) # list<Value> + list<dyn> -> list<dyn>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_LIST, TYPE_LIST_OF_VALUES], result_type=make_list_type(CEL_DYN), implementation=impl_add, expects_cel_values=True)) # list<dyn> + list<Value> -> list<dyn>

# Timestamp and Duration Addition
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_DURATION, CEL_DURATION], result_type=CEL_DURATION, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_TIMESTAMP, CEL_DURATION], result_type=CEL_TIMESTAMP, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_DURATION, CEL_TIMESTAMP], result_type=CEL_TIMESTAMP, implementation=impl_add, expects_cel_values=True))

# google.protobuf.Value with other types (generally results in DYN for type checker, runtime handles specifics)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_INT], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_INT, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_UINT], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_UINT, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_DOUBLE], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_DOUBLE, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_STRING], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_STRING, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_BYTES], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_BYTES, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_LIST], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True)) # Value + list<dyn>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_LIST, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True)) # list<dyn> + Value
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_LIST_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True)) # Value + ListValue
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_LIST_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True)) # ListValue + Value
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_DURATION], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_DURATION, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_VALUE_WRAPPER, CEL_TIMESTAMP], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_add, arg_types=[CEL_TIMESTAMP, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_add, expects_cel_values=True))


# --- Arithmetic Operator: _-_ (Subtraction) ---
op_sub = "_-_"
impl_sub = cel_operator_subtract_wrapper
# DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_DYN, implementation=impl_sub, expects_cel_values=True))
# Numeric (result types match _check_arithmetic_operator for subtraction)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_INT, CEL_INT], result_type=CEL_INT, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_INT, implementation=impl_sub, expects_cel_values=True)) # uint-uint -> int
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_sub, expects_cel_values=True))
# Cross-Numeric
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_INT, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_INT, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_DOUBLE, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_DOUBLE, implementation=impl_sub, expects_cel_values=True))
# Timestamp/Duration
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_TIMESTAMP, CEL_TIMESTAMP], result_type=CEL_DURATION, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_TIMESTAMP, CEL_DURATION], result_type=CEL_TIMESTAMP, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_DURATION, CEL_DURATION], result_type=CEL_DURATION, implementation=impl_sub, expects_cel_values=True))
# Value involvement -> DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_VALUE_WRAPPER, CEL_INT], result_type=CEL_DYN, implementation=impl_sub, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_sub, arg_types=[CEL_INT, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_sub, expects_cel_values=True))
# ... (Value vs other numeric/time types -> DYN)

# --- Arithmetic Operator: _*_ (Multiplication) ---
op_mul = "_*_"
impl_mul = cel_operator_multiply_wrapper
# DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_DYN, implementation=impl_mul, expects_cel_values=True))
# Numeric (result types match _check_arithmetic_operator for multiplication)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_INT, CEL_INT], result_type=CEL_INT, implementation=impl_mul, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_UINT, implementation=impl_mul, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_mul, expects_cel_values=True))
# Cross-Numeric
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_INT, implementation=impl_mul, expects_cel_values=True)) # Or DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_INT, implementation=impl_mul, expects_cel_values=True)) # Or DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_mul, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_DOUBLE, implementation=impl_mul, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_mul, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_DOUBLE, implementation=impl_mul, expects_cel_values=True))
# Value involvement -> DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mul, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_mul, expects_cel_values=True))
# ... (Value vs numeric -> DYN)


# --- Arithmetic Operator: _/_ (Division) ---
op_div = "_/_"
impl_div = cel_operator_divide_wrapper
# DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_DYN, implementation=impl_div, expects_cel_values=True))
# Numeric (result types based on CEL spec: int/int->int, uint/uint->uint, double/double->double)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_INT, CEL_INT], result_type=CEL_INT, implementation=impl_div, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_UINT, implementation=impl_div, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_DOUBLE, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_div, expects_cel_values=True))
# Cross-Numeric (result in wider type or DYN, here using double if involved, else int for int/uint mixes)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_INT, implementation=impl_div, expects_cel_values=True)) # int/uint -> int
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_INT, implementation=impl_div, expects_cel_values=True)) # uint/int -> int
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_INT, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_div, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_DOUBLE, CEL_INT], result_type=CEL_DOUBLE, implementation=impl_div, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_UINT, CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=impl_div, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_DOUBLE, CEL_UINT], result_type=CEL_DOUBLE, implementation=impl_div, expects_cel_values=True))
# Value involvement -> DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_div, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_div, expects_cel_values=True))
# ... (Value vs numeric -> DYN)

# --- Arithmetic Operator: _%_ (Modulo) ---
op_mod = "_%_"
impl_mod = cel_operator_modulo_wrapper
# DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mod, arg_types=[CEL_DYN, CEL_DYN], result_type=CEL_DYN, implementation=impl_mod, expects_cel_values=True))
# Numeric (int and uint only)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mod, arg_types=[CEL_INT, CEL_INT], result_type=CEL_INT, implementation=impl_mod, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mod, arg_types=[CEL_UINT, CEL_UINT], result_type=CEL_UINT, implementation=impl_mod, expects_cel_values=True))
# Cross int/uint (result type consistent with CEL spec or checker, e.g. int)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mod, arg_types=[CEL_INT, CEL_UINT], result_type=CEL_INT, implementation=impl_mod, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mod, arg_types=[CEL_UINT, CEL_INT], result_type=CEL_INT, implementation=impl_mod, expects_cel_values=True))
# Value involvement -> DYN
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=op_mod, arg_types=[CEL_VALUE_WRAPPER, CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=impl_mod, expects_cel_values=True))
# ... (Value vs int/uint -> DYN)

