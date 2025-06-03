# Mimicel: Common Expression Language Engine

Mimicel is a personal project of the Common Expression Language python implementation, built with the help of generative AI.

## Beginning (2025 Golden Week)

During Golden Week, I spent some time doing development in a different, more playful way than usual.  
I needed a policy engine, but none of the existing Python implementations of CEL passed the official Conformance Tests.  
Since Gemini Pro had just become available, I started experimenting with it for code generation and testing.

After about 10 days of experimentation using Gemmini for testing, I managed to get much of CEL working.
If written in the usual way, a library of this scale and complexity would probably take three to six months to build.

How far can we go when combining the Language Definition, Conformance Tests, existing code, and generative AI?

> **Note**: Golden Week is a major holiday period in Japan, lasting about 10 days from late April to early May.

## GOAL

* Verify the creation and maintenance of software artifacts using AI
* Gain practical knowledge on how to maintain consistency across complex contexts with AI
* Provide a CEL-compliant evaluation engine

## Not Goal

* To keep traditional open-source development style

However, I may return to a conventional development process at some point.

## Current Status: Developer Preview

As of May 2025, the engine passes the core set of conformance tests:

| Filename              | Status     | Comment                                        |
|-----------------------|------------|------------------------------------------------|
| plumbing.textproto    | ✅ Passed  |                                                |
| basic.textproto       | ✅ Passed  |                                                |
| comparisons.textproto | ✅ Passed  |                                                |
| conversions.textproto | ✅ Passed  |                                                |
| dynamic.textproto     | ✅ Passed  |                                                |
| enums.textproto       | ✅ Passed  |                                                |
| fields.textproto      | ✅ Passed  |                                                |
| fp_math.textproto     | ✅ Passed  |                                                |
| integer_math.textproto| ✅ Passed  |                                                |
| lists.textproto       | ✅ Passed  |                                                |
| logic.textproto       | ✅ Passed  | The `left_error` and `right_error` are skipped |
| macros.textproto      | ✅ Passed  |                                                |
| namespace.textproto   | ✅ Passed  |                                                |
| parse.textproto       | ✅ Passed  |                                                |
| proto2.textproto      | ✅ Passed  |                                                |
| proto3.textproto      | ✅ Passed  |                                                |
| string.textproto      | ✅ Passed  |                                                |
| timestamps.textproto  | ✅ Passed  |                                                |
| unknowns.textproto    | ✅ Passed  |                                                |


It passes the basic tests excluding extension-related ones, making Mimic a CEL-compliant engine.

```
# requirements: java
curl -o third_party/antlr4/antlr-4.13.2-complete.jar https://www.antlr.org/download/antlr-4.13.2-complete.jar
bazel run //conformance:run_basic_test
```

...Of course, this only means it slipped through the gaps in the Conformance Test coverage,  
and does not imply it's production-ready.

Currently, the focus is on improving design consistency, as well as enhancing the reliability and robustness of the library.

## Setup

⚠️ **Important**: The installation of mimicel requires additional steps beyond `pip install`. The library depends on Protocol Buffer definitions that must be generated separately.

### Prerequisites

Before installing mimicel, ensure you have:
- Python 3.8 or later
- protoc (Protocol Buffer compiler) - Install via `pip install grpcio-tools` or from [protobuf releases](https://github.com/protocolbuffers/protobuf/releases)

### Installation Steps

#### Step 1: Install mimicel

Using pip:
```bash
pip install mimicel
```

Using uv package manager:
```bash
uv add mimicel
```

#### Step 2: Generate required Protocol Buffer files

**This step is mandatory!** Mimicel depends on CEL protocol buffer definitions that are not included in the package and must be generated manually.

##### Option A: Using the provided setup script (Recommended)

A convenience script is provided in the mimicel repository. Copy and run it in your project directory:

```bash
# If you cloned the mimicel repo:
cp path/to/mimicel/setup_cel_protos.sh ./
chmod +x setup_cel_protos.sh
./setup_cel_protos.sh

# Or download directly:
curl -O https://raw.githubusercontent.com/chobie/mimicel/main/setup_cel_protos.sh
chmod +x setup_cel_protos.sh
./setup_cel_protos.sh
```

##### Option B: Manual generation

If you prefer to generate the files manually:

If you’re using Bazel, you can use the following command to make use of the proto files generated from `cel-spec`.

```
bazel build '@cel-spec//proto/cel/expr:cel_expr_py_proto'
cp -r bazel-bin/external/cel-spec+/proto/cel/expr/_virtual_imports/python_proto/cel .
```

If you want to generate them manually, you can do so by running the following command.

```bash
git clone https://github.com/google/cel-spec
git clone https://github.com/googleapis/googleapis

protoc -I=./cel-spec/proto -I=./googleapis/ \
       --python_out=./ \
      --mypy_out=./ \
       ./cel-spec/proto/cel/expr/syntax.proto \
       ./cel-spec/proto/cel/expr/checked.proto \
       ./cel-spec/proto/cel/expr/eval.proto \
       ./cel-spec/proto/cel/expr/value.proto \
       ./cel-spec/proto/cel/expr/explain.proto \
       ./cel-spec/proto/cel/expr/conformance/test/simple.proto \
       ./cel-spec/proto/cel/expr/conformance/test/suite.proto \
       ./cel-spec/proto/cel/expr/conformance/conformance_service.proto \
       ./cel-spec/proto/cel/expr/conformance/env_config.proto \
       ./cel-spec/proto/cel/expr/conformance/proto2/test_all_types.proto \
       ./cel-spec/proto/cel/expr/conformance/proto2/test_all_types_extensions.proto \
       ./cel-spec/proto/cel/expr/conformance/proto3/test_all_types.proto \
       ./googleapis/google/rpc/status.proto \
       ./googleapis/google/rpc/code.proto
```

As of now, cel-spec does not provide pre-generated Protocol Buffers artifacts for Python. For googleapis, you can use the googleapis-common-protos package.
Currently, you need to generate the Protocol Buffers artifacts from cel-spec yourself.

### Verifying Installation

After completing the setup, test your installation with this simple script:

```python
import mimicel as cel

# Create a simple environment
env, err = cel.new_env()
if err is not None:
    print(f"Failed to create environment: {err}")
else:
    print("Success! Mimicel is properly installed.")
    
    # Test a simple expression
    ast, issue = env.compile("1 + 1")
    if issue is None:
        program, _ = env.program(ast)
        result, _, _ = program.eval({})
        print(f"1 + 1 = {result}")
```

### Troubleshooting

#### Error: `ModuleNotFoundError: No module named 'cel'`

This is the most common error and indicates that the CEL protocol buffer files haven't been generated. Make sure you've completed Step 2 of the installation process.

#### Error: `protoc-gen-mypy: program not found`

If you encounter this error when using the manual generation method with `--mypy_out`, you can either:
1. Install mypy-protobuf: `pip install mypy-protobuf`
2. Or simply omit the `--mypy_out` flag from the protoc command

#### Generated files in wrong location

Ensure the proto files are generated in your project's Python path. The generated `cel` directory should be at the same level as your Python scripts or in a location that's in your `PYTHONPATH`.

## Examples

The API design follows the style of `go-cel`, so for basic use cases, it should be fairly straightforward to use.

```python
import mimicel as cel

env, err = cel.new_env(
    cel.Variable("a", cel.IntType),
    cel.Variable("b", cel.StringType),
    cel.Function("hello",
                 cel.Overload("hello_str",
                              [cel.StringType],
                              cel.StringType
)))

if err is not None:
    raise err

ast, issue = env.compile("b.startsWith('Hello')")
if issue is not None:
    raise issue

program, err = env.program(ast)
if err is not None:
    raise err

out, detail, err = program.eval({
    'a': 15,
    'b': "Hello World",
})
print(out)
```

# Architecture

`mimicel/__init__.py` is the CEL frontend designed and implemented by a human.
The rest of the code was generated using generative AI. Since much of that output is difficult to use as-is, the frontend was manually designed and implemented.

The backend generated by the AI passes the standard CEL Conformance Tests.
However, there are admittedly many incomplete parts in the implementation.
Improving reliability will be a key focus going forward.

Advanced use cases are not yet well-supported.
You can access internal code via modules like mimicel.api, but since the APIs are subject to significant change, their use is not recommended.

## Contribution Guidelines

This project is an experimental open-source initiative leveraging generative AI.
Please feel free to share your great prompts and techniques.

* Test code can be written manually.
  * critically important for maintenance, so I prefer not to rely on AI-generated test code.  
* It is recommended to let AI read and interpret the code rather than trying to analyze it seriously yourself.
  * Much of this source code was generated by AI. There is little consistency in the design.
* For library code, use of output generated by AI is recommended.
  * If the conformance tests pass, I often adopt bold or experimental changes.

This project is not so much a conventional OSS activity,  
but more of a game-like challenge to explore what's possible with modern tooling.  

## License

* Apache License 2.0

## Disclaimer

As everyone knows, this software is provided "AS IS" with no warranties of any kind.  
