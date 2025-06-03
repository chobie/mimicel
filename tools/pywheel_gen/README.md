# pywheel_gen

A tool to generate Bazel `py_wheel` BUILD rules from `pyproject.toml` files.

## Overview

This tool reads a `pyproject.toml` file and generates the corresponding Bazel `py_wheel` rule configuration. It's designed to work with both Python 3.10 and 3.11+.

## Python 3.10 Compatibility

The tool originally used Python 3.11's built-in `tomllib` module. For Python 3.10 compatibility, it now falls back to the `tomli` library (which is a backport of `tomllib`).

## Usage

### Direct execution with Bazel

```bash
# Run with explicit path to pyproject.toml
bazel run //tools/pywheel_gen:pywheel_gen -- /path/to/pyproject.toml

# From the workspace root
bazel run //tools/pywheel_gen:pywheel_gen -- $(pwd)/pyproject.toml
```

### Generate wheel BUILD content

```bash
# Generate wheel_build_content.txt with the py_wheel rule
bazel build //tools/pywheel_gen:generate_wheel_build

# View the generated content
cat bazel-bin/tools/pywheel_gen/wheel_build_content.txt
```

## Output

The tool generates a `py_wheel` rule with the following information extracted from `pyproject.toml`:
- Package name and version
- Description and metadata
- Author information
- License
- Dependencies (both required and optional)
- Python version requirements

## Example Output

```python
py_wheel(
    name = "mimicel_wheel",
    distribution = "mimicel",
    version = "0.0.1",
    python_tag = "py3",
    platform = "any",
    homepage = "https://github.com/chobie/mimicel",
    summary = "A CEL (Common Expression Language) compliant expression engine for Python",
    author = "Shuhei Tanuma",
    author_email = "shuhei.tanuma@gmail.com",
    license = "Apache-2.0",
    python_requires = ">=3.10",
    requires = ["antlr4-python3-runtime>=4.13.2", "protobuf>=6.30.2", ...],
    extra_requires = {
        "dev": ["mypy-protobuf>=3.6.0", "pytest>=8.3.5"],
    },
    description_file = "//:README.md",
    description_content_type = "text/markdown",
    extra_distinfo_files = {
        "//:LICENSE": "LICENSE",
    },
    deps = [
        ":mimicel_pkg",
    ],
)
```