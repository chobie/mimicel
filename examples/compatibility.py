#!/usr/bin/env python3
"""
Compatibility test for cel-go generated AST.
Loads AST from tools/astdump/ast.json and evaluates it using mimicel.
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import mimicel
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rules_python.python.runfiles import runfiles
except ImportError:
    runfiles = None

from google.protobuf.json_format import ParseDict
from cel.expr import syntax_pb2, checked_pb2
from mimicel import CelAstWrapper, CelEnvWrapper, new_env, Variable, IntType, StringType


def load_ast_json(filepath):
    """Load AST from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def json_to_parsed_expr(expr_dict):
    """Convert JSON dict to protobuf ParsedExpr message."""
    parsed = syntax_pb2.ParsedExpr()
    parsed.expr.CopyFrom(syntax_pb2.Expr())
    ParseDict(expr_dict, parsed.expr)
    return parsed


def json_to_checked_expr(expr_dict):
    """Convert JSON dict to protobuf CheckedExpr message."""
    checked = checked_pb2.CheckedExpr()
    checked.expr.CopyFrom(syntax_pb2.Expr())
    ParseDict(expr_dict, checked.expr)
    return checked


def main():
    # Load AST from JSON file
    # Try multiple possible locations including Bazel runfiles
    possible_paths = []
    
    # Try Bazel runfiles first if available
    if runfiles:
        r = runfiles.Create()
        if r:
            ast_runfile_path = r.Rlocation("_main/tools/astdump/ast.json")
            if ast_runfile_path:
                possible_paths.append(Path(ast_runfile_path))
    
    # Add fallback paths
    possible_paths.extend([
        # Direct path from workspace
        Path("/workspace/mimicel/tools/astdump/ast.json"),
        # Relative path from current directory
        Path("tools/astdump/ast.json"),
        # Relative from parent
        Path(__file__).parent.parent / "tools" / "astdump" / "ast.json",
    ])
    
    ast_file = None
    for path in possible_paths:
        if path.exists():
            ast_file = path
            break
    
    if not ast_file:
        print("Error: AST file not found at any of these locations:")
        for path in possible_paths:
            print(f"  - {path}")
        print("\nPlease run 'tools/astdump/astdump -expr \"1 + 1\"' first")
        print("\nNote: Make sure ast.json exists at tools/astdump/ast.json")
        return 1

    print(f"Loading AST from: {ast_file}")
    ast_data = load_ast_json(ast_file)
    
    print(f"Expression: {ast_data['expression']}")
    
    # Convert JSON to protobuf
    parsed_expr = json_to_parsed_expr(ast_data['parsed'])
    checked_expr = json_to_checked_expr(ast_data['checked'])
    
    # Create CelAstWrapper with protobuf objects
    ast_wrapper = CelAstWrapper(parsed_expr, checked_expr)
    
    # Create CEL environment with variables (matching astdump)
    env_wrapper, issue = new_env(
        Variable("x", IntType),
        Variable("y", StringType)
    )
    if issue:
        print(f"Error creating environment: {issue}")
        return 1
    
    # Create program from AST
    program, prog_issue = env_wrapper.program(ast_wrapper)
    if prog_issue:
        print(f"Error creating program: {prog_issue.err()}")
        return 1
    
    # Evaluate with sample values (matching astdump)
    context = {
        "x": 10,
        "y": "hello"
    }
    
    print(f"\nEvaluating with context: {context}")
    
    result, detail, issue = program.eval(context)
    
    if issue:
        print(f"Evaluation error: {issue.err()}")
        return 1
    
    print(f"Result: {result}")
    print(f"Type: {type(result).__name__}")
    
    # For the "1 + 1" expression, we expect result to be 2
    if ast_data['expression'] == "1 + 1":
        expected = 2
        if result == expected:
            print(f"\n✓ Success: AST evaluation returned expected value {expected}")
        else:
            print(f"\n✗ Failed: Expected {expected}, got {result}")
            return 1
    
    print("\n✓ Successfully loaded and evaluated cel-go generated AST!")
    return 0


if __name__ == "__main__":
    sys.exit(main())