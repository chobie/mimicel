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

