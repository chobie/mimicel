# Examples

This directory contains example usage of mimicel.

## Files

- `simple.py` - Basic example using CEL with custom functions and protobuf messages
- `binary.py` - Demonstrates registering binary functions (add, concat, max) that operate on two arguments
- `functions.py` - Demonstrates variadic functions that accept variable number of arguments
- `method.py` - Demonstrates registering Python functions as CEL methods (e.g., "text".upper())
- `native_types.py` - Demonstrates using native Python classes as CEL types without protobuf
- `like-a-pydantic.py` - Example showing Pydantic-like validation using CEL expressions with dataclasses
- `compatibility.py` - Tests compatibility with cel-go generated AST
- `user.proto` - Protocol buffer definition used in examples

## Building and Running

Examples are built and run using Bazel:

```bash
bazel run //examples:simple
bazel run //examples:binary
bazel run //examples:functions
bazel run //examples:method
bazel run //examples:native_types
bazel run //examples:like-a-pydantic
bazel run //examples:compatibility
```

## Proto Generation

The `user.proto` file is compiled to Python using Bazel's `py_proto_library` rule.
The generated files (`user_pb2.py`, `user_pb2.pyi`) are no longer committed to the repository.

## Bazel Protobuf Compatibility

The examples use `bazel_protobuf_wrapper.py` to work around a compatibility issue between Bazel's `py_proto_library` and mimicel.

