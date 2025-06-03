#!/bin/bash
# setup_cel_protos.sh - Convenience script to generate required CEL protocol buffer files

echo "Setting up CEL protocol buffer files for mimicel..."

# Check if grpcio-tools is installed
if ! python -c "import grpc_tools.protoc" 2>/dev/null; then
    echo "Installing grpcio-tools..."
    pip install grpcio-tools
fi

# Clone required repositories
echo "Cloning cel-spec and googleapis repositories..."
git clone --depth=1 https://github.com/google/cel-spec /tmp/cel-spec
git clone --depth=1 https://github.com/googleapis/googleapis /tmp/googleapis

# Generate proto files
echo "Generating protocol buffer files..."
python -m grpc_tools.protoc \
    -I=/tmp/cel-spec/proto \
    -I=/tmp/googleapis/ \
    --python_out=./ \
   /tmp/cel-spec/proto/cel/expr/syntax.proto \
   /tmp/cel-spec/proto/cel/expr/checked.proto \
   /tmp/cel-spec/proto/cel/expr/eval.proto \
   /tmp/cel-spec/proto/cel/expr/value.proto \
   /tmp/cel-spec/proto/cel/expr/explain.proto \
   /tmp/cel-spec/proto/cel/expr/conformance/test/simple.proto \
   /tmp/cel-spec/proto/cel/expr/conformance/test/suite.proto \
   /tmp/cel-spec/proto/cel/expr/conformance/conformance_service.proto \
   /tmp/cel-spec/proto/cel/expr/conformance/env_config.proto \
   /tmp/cel-spec/proto/cel/expr/conformance/proto2/test_all_types.proto \
   /tmp/cel-spec/proto/cel/expr/conformance/proto2/test_all_types_extensions.proto \
   /tmp/cel-spec/proto/cel/expr/conformance/proto3/test_all_types.proto \
   /tmp/googleapis/google/rpc/status.proto \
   /tmp/googleapis/google/rpc/code.proto

# Cleanup
rm -rf /tmp/cel-spec /tmp/googleapis

echo "✅ CEL proto files generated successfully!"
echo ""
echo "You can now test the installation with:"
echo "  python -c \"import mimicel as cel; print('mimicel is ready!')\""