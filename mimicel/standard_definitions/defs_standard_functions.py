from . import STANDARD_LIBRARY, TYPE_LIST_OF_VALUES, TYPE_STRUCT_AS_MAP, functions
from ..cel_values.cel_types import (
    CelFunctionDefinition,
    CEL_DYN, CEL_TIMESTAMP, CEL_DURATION, CEL_INT, CEL_STRING, CEL_BOOL, CEL_BYTES,
    CEL_LIST, CEL_MAP,
    make_list_type, make_map_type,
    CEL_VALUE_WRAPPER,  # For google.protobuf.Value
    CEL_STRUCT_WRAPPER,  # For google.protobuf.Struct
    CEL_LIST_WRAPPER, TYPE_LIST_OF_INTS, TYPE_LIST_OF_BOOLS, TYPE_LIST_OF_UINTS,
    TYPE_LIST_OF_DOUBLES, TYPE_LIST_OF_STRINGS, TYPE_LIST_OF_BYTES, TYPE_MAP_INT_STRING,
    TYPE_MAP_STRING_INT, TYPE_MAP_STRING_STRING, TYPE_MAP_STRING_DOUBLE  # For google.protobuf.ListValue
)

from .functions import (
    cel_len_impl,
    string_contains_impl, string_ends_with_impl, string_matches_impl, string_starts_with_impl,
)

# --- size() ---
# Global functions
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[CEL_STRING], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[CEL_BYTES], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[CEL_LIST], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True)) # list<dyn>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[make_list_type(CEL_DYN)], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_LIST_OF_INTS], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_LIST_OF_UINTS], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_LIST_OF_BOOLS], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_LIST_OF_STRINGS], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_LIST_OF_DOUBLES], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_LIST_OF_BYTES], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_LIST_OF_VALUES], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True)) # list<Value>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[CEL_LIST_WRAPPER], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True)) # ListValue message
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[CEL_MAP], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True)) # map<dyn,dyn>
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[make_map_type(CEL_DYN, CEL_DYN)], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_STRUCT_AS_MAP], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True)) # map<string,Value> (Struct)
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[CEL_STRUCT_WRAPPER], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True)) # Struct message
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[CEL_VALUE_WRAPPER], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True)) # Value (containing list/struct)

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_MAP_INT_STRING], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_MAP_STRING_INT], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_MAP_STRING_STRING], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[TYPE_MAP_STRING_DOUBLE], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", arg_types=[CEL_DYN], result_type=CEL_INT, implementation=cel_len_impl, expects_cel_values=True))

# Method-style
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=CEL_STRING, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=CEL_BYTES, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=CEL_LIST, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=make_list_type(CEL_DYN), arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_LIST_OF_VALUES, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=CEL_LIST_WRAPPER, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=CEL_MAP, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=make_map_type(CEL_DYN, CEL_DYN), arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_STRUCT_AS_MAP, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=CEL_STRUCT_WRAPPER, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=CEL_VALUE_WRAPPER, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_LIST_OF_INTS, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_LIST_OF_UINTS, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_LIST_OF_BOOLS, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_LIST_OF_STRINGS, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_LIST_OF_DOUBLES, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_LIST_OF_BYTES, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))

STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_MAP_INT_STRING, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_MAP_STRING_INT, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_MAP_STRING_STRING, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="size", receiver_type=TYPE_MAP_STRING_DOUBLE, arg_types=[], result_type=CEL_INT, implementation=cel_len_impl, is_method=True, expects_cel_values=True))



# --- String Functions (methods on CEL_STRING) ---
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="contains", receiver_type=CEL_STRING, arg_types=[CEL_STRING], result_type=CEL_BOOL, implementation=string_contains_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="endsWith", receiver_type=CEL_STRING, arg_types=[CEL_STRING], result_type=CEL_BOOL, implementation=string_ends_with_impl, is_method=True, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="startsWith", receiver_type=CEL_STRING, arg_types=[CEL_STRING], result_type=CEL_BOOL, implementation=string_starts_with_impl, is_method=True, expects_cel_values=True))

# Global 'matches'
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="matches", arg_types=[CEL_STRING, CEL_STRING], result_type=CEL_BOOL, implementation=lambda s, p: string_matches_impl(s,p), expects_cel_values=True))
# Method 'matches'
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="matches", receiver_type=CEL_STRING, arg_types=[CEL_STRING], result_type=CEL_BOOL, implementation=string_matches_impl, is_method=True, expects_cel_values=True))


# --- Date/Time Accessor Functions ---
# (Assuming get_timestamp_full_year, get_duration_hours etc. are defined in functions.py
#  and take CelProtobufTimestamp/CelProtobufDuration as first argument)
# Alternatively, direct lambda to methods if CelProtobufTimestamp/Duration have these as Python methods.
# For verbosity as requested, each is listed.

# Timestamp Accessors
ts_accessors = [
    ("getFullYear", "get_timestamp_full_year"), ("getMonth", "get_timestamp_month"),
    ("getDayOfMonth", "get_timestamp_day_of_month"), ("getDate", "get_timestamp_day_of_month_1_based"), # Assuming different impl for 1-based
    ("getDayOfYear", "get_timestamp_day_of_year"), ("getDayOfWeek", "get_timestamp_day_of_week"),
    ("getHours", "get_timestamp_hours"), ("getMinutes", "get_timestamp_minutes"),
    ("getSeconds", "get_timestamp_seconds"), ("getMilliseconds", "get_timestamp_milliseconds")
]
for cel_name, py_impl_name in ts_accessors:
    # Assuming py_impl_name is a function in .functions taking (CelProtobufTimestamp, Optional[CelString])
    # If they are methods of CelProtobufTimestamp: impl = lambda ts, tz=None, method_name=py_impl_name: getattr(ts, method_name)(tz)
    # For simplicity, assuming direct functions from .functions
    func_impl = getattr(functions, py_impl_name, None) # Get from .functions module
    if func_impl:
        STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=cel_name, receiver_type=CEL_TIMESTAMP, arg_types=[], result_type=CEL_INT, implementation=func_impl, is_method=True, expects_cel_values=True))
        STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=cel_name, receiver_type=CEL_TIMESTAMP, arg_types=[CEL_STRING], result_type=CEL_INT, implementation=func_impl, is_method=True, expects_cel_values=True))
    #else:
    #    print(f"Warning: Implementation for Timestamp accessor '{py_impl_name}' not found in .functions module.")


# Duration Accessors
dur_accessors = [
    ("getHours", "get_duration_hours"), ("getMinutes", "get_duration_minutes"),
    ("getSeconds", "get_duration_seconds"), ("getMilliseconds", "get_duration_milliseconds")
]
for cel_name, py_impl_name in dur_accessors:
    func_impl = getattr(functions, py_impl_name, None)
    if func_impl:
        STANDARD_LIBRARY.add_function(CelFunctionDefinition(name=cel_name, receiver_type=CEL_DURATION, arg_types=[], result_type=CEL_INT, implementation=func_impl, is_method=True, expects_cel_values=True))
    #else:
    #    print(f"Warning: Implementation for Duration accessor '{py_impl_name}' not found in .functions module.")
