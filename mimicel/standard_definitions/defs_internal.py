from . import STANDARD_LIBRARY
from ..cel_values.cel_types import (
    CelFunctionDefinition,
    CEL_TIMESTAMP,
    CEL_DURATION,
    CEL_STRING,
    CEL_BOOL, CEL_INT,
)

# Implementation functions from other modules
from .conversions import (
    cel_convert_duration_impl,
    cel_convert_timestamp_dispatcher,
)
from .operators import (
    _dummy_logical_op_impl
)


# ==============================================================================
# Section 4: Literal Constructor Pseudo-Functions (Internal)
# ==============================================================================
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_lit_duration_", arg_types=[CEL_STRING], result_type=CEL_DURATION, implementation=cel_convert_duration_impl, is_method=False, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_lit_timestamp_", arg_types=[CEL_STRING], result_type=CEL_TIMESTAMP, implementation=cel_convert_timestamp_dispatcher, is_method=False, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_lit_timestamp_", arg_types=[CEL_INT], result_type=CEL_TIMESTAMP, implementation=cel_convert_timestamp_dispatcher, is_method=False, expects_cel_values=True))

# ==============================================================================
# Section 5: Dummy Implementations for Logical Operators (If needed for Type Checker registry)
# ==============================================================================
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_&&_", arg_types=[CEL_BOOL, CEL_BOOL], result_type=CEL_BOOL, implementation=_dummy_logical_op_impl, expects_cel_values=True))
STANDARD_LIBRARY.add_function(CelFunctionDefinition(name="_||_", arg_types=[CEL_BOOL, CEL_BOOL], result_type=CEL_BOOL, implementation=_dummy_logical_op_impl, expects_cel_values=True))
