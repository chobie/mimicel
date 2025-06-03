#!/usr/bin/env python3
"""Bazel protobuf compatibility wrapper.

This wrapper addresses the issue where mimicel's eval_pb.py unconditionally imports
from google._upb._message, which is not available when using Bazel's py_proto_library.

The issue occurs because:
1. Bazel's py_proto_library generates Python protobuf code without the C++ _upb extension
2. mimicel/eval_pb.py has: from google._upb._message import RepeatedScalarContainer, RepeatedCompositeContainer
3. This import fails in Bazel environments

This wrapper sets up dummy modules to satisfy the import requirements before loading mimicel.
The actual types (RepeatedScalarContainer, RepeatedCompositeContainer) are only used for
isinstance checks in eval_pb.py, so using list as a substitute works fine.

This is a temporary workaround until mimicel is updated to handle the import gracefully,
similar to how it's already done in mimicel/cel_values/__init__.py.
"""

import sys
import types
import os

# Set environment to use pure Python protobuf
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# First, let protobuf initialize normally
import google.protobuf

# Now add the fake _upb module that mimicel expects
# This is a workaround for eval_pb.py's unconditional import
if 'google._upb' not in sys.modules:
    sys.modules['google._upb'] = types.ModuleType('google._upb')
    
if 'google._upb._message' not in sys.modules:
    upb_message = types.ModuleType('google._upb._message')
    # Add the expected types as simple list aliases
    # These are only used for isinstance checks in eval_pb.py
    upb_message.RepeatedScalarContainer = list
    upb_message.RepeatedCompositeContainer = list
    sys.modules['google._upb._message'] = upb_message

# Now import and run the actual simple module
import simple

# Execute the main function
if __name__ == '__main__':
    simple.main()