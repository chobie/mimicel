# Examples

This directory contains example usage of mimicel.

## Files

- `simple.py` - Basic example using CEL with custom functions and protobuf messages
- `like-a-pydantic.py` - Example showing Pydantic-like usage
- `compatibility.py` - Tests compatibility with cel-go generated AST
- `user.proto` - Protocol buffer definition used in examples

## Building and Running

Examples are built and run using Bazel:

```bash
bazel run //examples:simple
bazel run //examples:like-a-pydantic
bazel run //examples:compatibility
```

## Proto Generation

The `user.proto` file is compiled to Python using Bazel's `py_proto_library` rule.
The generated files (`user_pb2.py`, `user_pb2.pyi`) are no longer committed to the repository.

## Bazel Protobuf Compatibility

The examples use `bazel_protobuf_wrapper.py` to work around a compatibility issue between Bazel's `py_proto_library` and mimicel.

### The Issue

When running examples that use `cel.Types()` to register custom protobuf types, you may encounter:
```
ModuleNotFoundError: No module named 'google._upb'
```

This occurs because:
1. `mimicel/eval_pb.py` has an unprotected import: `from google._upb._message import RepeatedScalarContainer, RepeatedCompositeContainer`
2. Bazel's `py_proto_library` generates Python protobuf code without the C++ `_upb` extension
3. The `_upb` module is part of the C++ protobuf implementation and isn't available in Bazel environments

### The Solution

`bazel_protobuf_wrapper.py` provides a workaround by:
1. Setting up dummy `google._upb._message` module before importing mimicel
2. Providing `list` as a substitute for `RepeatedScalarContainer` and `RepeatedCompositeContainer`
3. These types are only used for `isinstance` checks, so the substitution works correctly

### Long-term Fix

The proper fix would be to update `mimicel/eval_pb.py` to handle the import gracefully, similar to how it's already done in `mimicel/cel_values/__init__.py`:

```python
try:
    from google._upb._message import RepeatedScalarContainer, RepeatedCompositeContainer
    _UPB_CONTAINERS_LOADED = True
except ImportError:
    _UPB_CONTAINERS_LOADED = False
    RepeatedScalarContainer, RepeatedCompositeContainer = None, None
```