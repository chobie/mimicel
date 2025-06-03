# astdump

A tool for executing CEL (Common Expression Language) expressions using cel-go and exporting the AST (Abstract Syntax Tree) in JSON format.

## Overview

`astdump` is a command-line tool that:
- Parses and type-checks CEL expressions using the cel-go library
- Evaluates the expressions with sample variables
- Exports both parsed and checked AST representations to a JSON file
- Displays the evaluation result to the console

This tool is useful for:
- Understanding CEL expression structure
- Testing cel-go compatibility with other CEL implementations
- Debugging CEL expressions by examining their AST

## Build Instructions

### Prerequisites

- Go 1.21 or later
- cel-go library (automatically downloaded during build)

### Building

```bash
cd tools/astdump
go mod download
go build -o astdump main.go
```

## Usage

```bash
./astdump -expr "<CEL expression>" [-output <output_file>]
```

### Options

- `-expr`: The CEL expression to evaluate (required)
- `-output`: Output file for the AST in JSON format (default: `ast.json`)

### Examples

Evaluate a simple arithmetic expression:
```bash
./astdump -expr "1 + 1"
```

Use variables in expressions:
```bash
./astdump -expr "x * 2 + y.size()"
```

Specify custom output file:
```bash
./astdump -expr "x > 5 && y == 'hello'" -output my_ast.json
```

## Sample Variables

The tool provides two predefined variables for testing:
- `x`: integer with value 10
- `y`: string with value "hello"

## Output Format

The generated JSON file contains:
- `expression`: The original CEL expression string
- `parsed`: The parsed AST before type checking
- `checked`: The type-checked AST with resolved types

Example output for `1 + 1`:
```json
{
  "expression": "1 + 1",
  "parsed": {
    "callExpr": {
      "function": "_+_",
      "args": [
        {"constExpr": {"int64Value": "1"}, "id": "1"},
        {"constExpr": {"int64Value": "1"}, "id": "3"}
      ]
    },
    "id": "2"
  },
  "checked": {
    "callExpr": {
      "function": "_+_",
      "args": [
        {"constExpr": {"int64Value": "1"}, "id": "1"},
        {"constExpr": {"int64Value": "1"}, "id": "3"}
      ]
    },
    "id": "2"
  }
}
```

## Integration with mimicel

The generated AST can be loaded and evaluated by mimicel using the `examples/compatibility.py` script, demonstrating compatibility between cel-go and mimicel implementations.