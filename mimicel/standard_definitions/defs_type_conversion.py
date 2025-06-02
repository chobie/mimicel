# standard_definitions/__init__.py
from . import STANDARD_LIBRARY
from ..cel_values.cel_types import (
    CelFunctionDefinition,
    CEL_DYN, CEL_TIMESTAMP, CEL_DURATION, CEL_INT, CEL_STRING, CEL_BOOL, CEL_BYTES,
    CEL_TYPE, CEL_UINT, CEL_DOUBLE,
    CEL_INT32_WRAPPER, CEL_UINT32_WRAPPER, CEL_INT64_WRAPPER, CEL_UINT64_WRAPPER,
    CEL_BOOL_WRAPPER, CEL_DOUBLE_WRAPPER, CEL_STRING_WRAPPER, CEL_BYTES_WRAPPER,
    CEL_VALUE_WRAPPER,
)

# Implementation functions from other modules
from .conversions import (
    cel_convert_bool_impl, cel_convert_bytes_impl, cel_convert_double_impl,
    cel_convert_duration_impl, cel_convert_int_dispatcher, cel_convert_string_dispatcher,
    cel_convert_timestamp_dispatcher, cel_convert_uint_dispatcher,
    cel_type_of, cel_convert_dyn,
    # WKT Constructors (assuming these are defined in conversions.py or similar)
    cel_global_int32_value_constructor, cel_global_uint32_value_constructor, cel_global_int64_value_constructor,
    cel_global_uint64_value_constructor, cel_global_double_value_constructor, cel_global_bool_value_constructor,
    cel_global_string_value_constructor, cel_global_bytes_value_constructor,cel_type_of_dispatcher,
)

# --- bool (Conversion to CEL_BOOL) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="bool", arg_types=[CEL_BOOL], result_type=CEL_BOOL, implementation=cel_convert_bool_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="bool", arg_types=[CEL_STRING], result_type=CEL_BOOL, implementation=cel_convert_bool_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="bool", arg_types=[CEL_INT], result_type=CEL_BOOL, implementation=cel_convert_bool_impl, expects_cel_values=True)) # int(0)!=false, int(!0)!=true
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="bool", arg_types=[CEL_UINT], result_type=CEL_BOOL, implementation=cel_convert_bool_impl, expects_cel_values=True)) # uint(0u)!=false, uint(!0u)!=true
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="bool", arg_types=[CEL_DOUBLE], result_type=CEL_BOOL, implementation=cel_convert_bool_impl, expects_cel_values=True)) # double(0.0)!=false, double(!0.0)!=true
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="bool", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_BOOL, implementation=cel_convert_bool_impl, expects_cel_values=True)) # Value to Bool

# --- bytes (Conversion to CEL_BYTES) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="bytes", arg_types=[CEL_BYTES], result_type=CEL_BYTES, implementation=cel_convert_bytes_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="bytes", arg_types=[CEL_STRING], result_type=CEL_BYTES, implementation=cel_convert_bytes_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="bytes", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_BYTES, implementation=cel_convert_bytes_impl, expects_cel_values=True)) # Value to Bytes

# --- double (Conversion to CEL_DOUBLE) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="double", arg_types=[CEL_DOUBLE], result_type=CEL_DOUBLE, implementation=cel_convert_double_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="double", arg_types=[CEL_INT], result_type=CEL_DOUBLE, implementation=cel_convert_double_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="double", arg_types=[CEL_UINT], result_type=CEL_DOUBLE, implementation=cel_convert_double_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="double", arg_types=[CEL_STRING], result_type=CEL_DOUBLE, implementation=cel_convert_double_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="double", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_DOUBLE, implementation=cel_convert_double_impl, expects_cel_values=True)) # Value to Double

# --- duration (Conversion to CEL_DURATION) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="duration", arg_types=[CEL_DURATION], result_type=CEL_DURATION, implementation=cel_convert_duration_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="duration", arg_types=[CEL_STRING], result_type=CEL_DURATION, implementation=cel_convert_duration_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="duration", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_DURATION, implementation=cel_convert_duration_impl, expects_cel_values=True)) # Value to Duration

# --- int (Conversion to CEL_INT) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_INT], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_UINT], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_DOUBLE], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_STRING], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_TIMESTAMP], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True)) # Timestamp to epoch seconds
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True)) # Value to Int
# Wrapper conversions to int
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_INT32_WRAPPER], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_INT64_WRAPPER], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_UINT32_WRAPPER], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_UINT64_WRAPPER], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="int", arg_types=[CEL_DOUBLE_WRAPPER], result_type=CEL_INT, implementation=cel_convert_int_dispatcher, expects_cel_values=True))
# Note: bool to int is not standard CEL, string to int is.

# --- string (Conversion to CEL_STRING) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_STRING], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_BOOL], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_INT], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_UINT], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_DOUBLE], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_BYTES], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True)) # UTF-8 decode
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_TIMESTAMP], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True)) # RFC3339
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_DURATION], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True)) # seconds.fractional's'
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True)) # Value to String
# Wrapper conversions to string
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="string", arg_types=[CEL_STRING_WRAPPER], result_type=CEL_STRING, implementation=cel_convert_string_dispatcher, expects_cel_values=True))
# ... (other wrappers like Int32Value to string if needed, usually via their primitive)

# --- timestamp (Conversion to CEL_TIMESTAMP) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="timestamp", arg_types=[CEL_TIMESTAMP], result_type=CEL_TIMESTAMP, implementation=cel_convert_timestamp_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="timestamp", arg_types=[CEL_STRING], result_type=CEL_TIMESTAMP, implementation=cel_convert_timestamp_dispatcher, expects_cel_values=True)) # RFC3339
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="timestamp", arg_types=[CEL_INT], result_type=CEL_TIMESTAMP, implementation=cel_convert_timestamp_dispatcher, expects_cel_values=True)) # Epoch seconds
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="timestamp", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_TIMESTAMP, implementation=cel_convert_timestamp_dispatcher, expects_cel_values=True)) # Value to Timestamp

# --- uint (Conversion to CEL_UINT) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="uint", arg_types=[CEL_UINT], result_type=CEL_UINT, implementation=cel_convert_uint_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="uint", arg_types=[CEL_INT], result_type=CEL_UINT, implementation=cel_convert_uint_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="uint", arg_types=[CEL_DOUBLE], result_type=CEL_UINT, implementation=cel_convert_uint_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="uint", arg_types=[CEL_STRING], result_type=CEL_UINT, implementation=cel_convert_uint_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="uint", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_UINT, implementation=cel_convert_uint_dispatcher, expects_cel_values=True)) # Value to Uint
# Wrapper conversions to uint
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="uint", arg_types=[CEL_UINT32_WRAPPER], result_type=CEL_UINT, implementation=cel_convert_uint_dispatcher, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="uint", arg_types=[CEL_UINT64_WRAPPER], result_type=CEL_UINT, implementation=cel_convert_uint_dispatcher, expects_cel_values=True))


# --- type (Get type of value) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(
    name="type",
    arg_types=[CEL_DYN],
    result_type=CEL_TYPE,
    implementation=cel_type_of_dispatcher, # ★ ディスパッチャを使用
    expects_cel_values=True,
    takes_eval_context=True # ★ EvalContextを要求するフラグを追加
))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(
    name="type",
    arg_types=[CEL_VALUE_WRAPPER], # type(Value) も考慮
    result_type=CEL_TYPE,
    implementation=cel_type_of_dispatcher,
    expects_cel_values=True,
    takes_eval_context=True
))

# --- dyn (Identity function, type hint for checker) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="dyn", arg_types=[CEL_DYN], result_type=CEL_DYN, implementation=cel_convert_dyn, expects_cel_values=True))
# dyn(Value) is still dyn, but explicitly
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="dyn", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_DYN, implementation=cel_convert_dyn, expects_cel_values=True))


# --- Protobuf Well-Known Type Constructors ---
# Example: Int32Value() and Int32Value(int)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.Int32Value", arg_types=[], result_type=CEL_INT32_WRAPPER, implementation=lambda: cel_global_int32_value_constructor(None), expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.Int32Value", arg_types=[CEL_INT], result_type=CEL_INT32_WRAPPER, implementation=cel_global_int32_value_constructor, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.Int32Value", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_INT32_WRAPPER, implementation=cel_global_int32_value_constructor, expects_cel_values=True)) # Value(int) -> Int32Value

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.UInt32Value", arg_types=[], result_type=CEL_UINT32_WRAPPER, implementation=lambda: cel_global_uint32_value_constructor(None), expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.UInt32Value", arg_types=[CEL_UINT], result_type=CEL_UINT32_WRAPPER, implementation=cel_global_uint32_value_constructor, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.UInt32Value", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_UINT32_WRAPPER, implementation=cel_global_uint32_value_constructor, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.Int64Value", arg_types=[], result_type=CEL_INT64_WRAPPER, implementation=lambda: cel_global_int64_value_constructor(None), expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.Int64Value", arg_types=[CEL_INT], result_type=CEL_INT64_WRAPPER, implementation=cel_global_int64_value_constructor, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.Int64Value", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_INT64_WRAPPER, implementation=cel_global_int64_value_constructor, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.UInt64Value", arg_types=[], result_type=CEL_UINT64_WRAPPER, implementation=lambda: cel_global_uint64_value_constructor(None), expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.UInt64Value", arg_types=[CEL_UINT], result_type=CEL_UINT64_WRAPPER, implementation=cel_global_uint64_value_constructor, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.UInt64Value", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_UINT64_WRAPPER, implementation=cel_global_uint64_value_constructor, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.DoubleValue", arg_types=[], result_type=CEL_DOUBLE_WRAPPER, implementation=lambda: cel_global_double_value_constructor(None), expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.DoubleValue", arg_types=[CEL_DOUBLE], result_type=CEL_DOUBLE_WRAPPER, implementation=cel_global_double_value_constructor, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.DoubleValue", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_DOUBLE_WRAPPER, implementation=cel_global_double_value_constructor, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.BoolValue", arg_types=[], result_type=CEL_BOOL_WRAPPER, implementation=lambda: cel_global_bool_value_constructor(None), expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.BoolValue", arg_types=[CEL_BOOL], result_type=CEL_BOOL_WRAPPER, implementation=cel_global_bool_value_constructor, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.BoolValue", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_BOOL_WRAPPER, implementation=cel_global_bool_value_constructor, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.StringValue", arg_types=[], result_type=CEL_STRING_WRAPPER, implementation=lambda: cel_global_string_value_constructor(None), expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.StringValue", arg_types=[CEL_STRING], result_type=CEL_STRING_WRAPPER, implementation=cel_global_string_value_constructor, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.StringValue", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_STRING_WRAPPER, implementation=cel_global_string_value_constructor, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.BytesValue", arg_types=[], result_type=CEL_BYTES_WRAPPER, implementation=lambda: cel_global_bytes_value_constructor(None), expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.BytesValue", arg_types=[CEL_BYTES], result_type=CEL_BYTES_WRAPPER, implementation=cel_global_bytes_value_constructor, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.BytesValue", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_BYTES_WRAPPER, implementation=cel_global_bytes_value_constructor, expects_cel_values=True))

# Note: google.protobuf.Value, Struct, ListValue constructors are not typically exposed as global functions
# in this manner, as they are often constructed from literals or other data sources.
# If needed, they would be:
# STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.Value", arg_types=[CEL_DYN], result_type=CEL_VALUE_WRAPPER, ...))
# STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.Struct", arg_types=[make_map_type(CEL_STRING, CEL_VALUE_WRAPPER)], result_type=CEL_STRUCT_WRAPPER, ...))
# STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="google.protobuf.ListValue", arg_types=[make_list_type(CEL_VALUE_WRAPPER)], result_type=CEL_LIST_WRAPPER, ...))
