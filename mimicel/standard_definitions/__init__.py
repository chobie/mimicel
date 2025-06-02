# standard_definitions/__init__.py

from ..cel_library import CelLibrary
from ..cel_values.cel_types import (
    CEL_STRING,
    make_list_type, make_map_type,
    CEL_VALUE_WRAPPER,      # For google.protobuf.Value
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
    cel_global_string_value_constructor, cel_global_bytes_value_constructor,
)
from .functions import (
    cel_len_impl,
    string_contains_impl, string_ends_with_impl, string_matches_impl, string_starts_with_impl,
)
from .operators import (
    cel_operator_add_wrapper, cel_operator_subtract_wrapper, cel_operator_multiply_wrapper,
    cel_operator_divide_wrapper, cel_operator_modulo_wrapper, cel_operator_negate_wrapper,
    cel_operator_equals_wrapper, cel_operator_not_equals_wrapper,
    cel_operator_less_than_wrapper, cel_operator_less_than_equals_wrapper,
    cel_operator_greater_than_wrapper, cel_operator_greater_than_equals_wrapper,
    cel_operator_in_wrapper, cel_operator_logical_not_wrapper, cel_operator_index_wrapper,
    cel_operator_ternary_wrapper, cel_operator_is_wrapper, _dummy_logical_op_impl
)

STANDARD_LIBRARY = CelLibrary("standard")

# Helper types for clarity (used by Struct/ListValue wrappers' .cel_type)
# These represent the effective CEL types that Struct and ListValue behave as.
TYPE_STRUCT_AS_MAP = make_map_type(CEL_STRING, CEL_VALUE_WRAPPER) # map<string, Value>
TYPE_LIST_OF_VALUES = make_list_type(CEL_VALUE_WRAPPER)         # list<Value>

# ==============================================================================
# Section 1: Type Conversion Functions
# ==============================================================================
# Each conversion function typically has overloads for different input types.

from . import defs_type_conversion

# ==============================================================================
# Section 2: Standard Functions (Non-conversion, Non-operator)
# ==============================================================================

from . import defs_standard_functions

# ==============================================================================
# Section 3: Operators (Expressed as Functions)
# ==============================================================================

from . import defs_operator_comparison

# --- Arithmetic Operator: _+_ (Addition / Concatenation) ---

from . import defs_operator_arithmetic

# --- In Operator (_in_) ---

from . import defs_operator_misc


from . import defs_internal