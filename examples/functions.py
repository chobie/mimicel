import mimicel as cel
from typing import List, Any

try:
    from user_pb2 import User
except ImportError:
    try:
        from examples.user_pb2 import User
    except ImportError:
        from example.user_pb2 import User

def sum_numbers(args: List[Any]) -> int:
    """Sum a variable number of integer arguments."""
    return sum(int(arg) for arg in args)

def join_strings(args: List[Any]) -> str:
    """Join a variable number of string arguments with spaces."""
    return " ".join(str(arg) for arg in args)

def max_value(args: List[Any]) -> float:
    """Find the maximum value from a variable number of numeric arguments."""
    if not args:
        return float('-inf')
    return max(float(arg) for arg in args)

def format_values(args: List[Any]) -> str:
    """Format multiple values into a string."""
    if len(args) < 2:
        return "Need at least format string and one value"
    format_str = str(args[0])
    values = args[1:]
    try:
        return format_str.format(*values)
    except:
        return f"Format error: {format_str} with {values}"

def main():
    """Main function demonstrating FunctionOp usage."""
    user = User(
        name="Shuhei Tanuma",
        age=10
    )

    env, err = cel.new_env(
        cel.Types(User.DESCRIPTOR),
        cel.Variable("a", cel.IntType),
        cel.Variable("b", cel.IntType),
        cel.Variable("c", cel.IntType),
        cel.Variable("user", cel.ObjectType("example.User")),
        cel.Function("sum",
            cel.Overload("sum_variadic",
                [cel.IntType, cel.IntType, cel.IntType],
                cel.IntType,
                cel.FunctionBinding(sum_numbers))),
        cel.Function("join",
            cel.Overload("join_variadic",
                [cel.StringType, cel.StringType, cel.StringType],
                cel.StringType,
                cel.FunctionBinding(join_strings))),
        cel.Function("max",
            cel.Overload("max_variadic",
                [cel.DoubleType, cel.DoubleType, cel.DoubleType, cel.DoubleType],
                cel.DoubleType,
                cel.FunctionBinding(max_value))),
        cel.Function("format",
            cel.Overload("format_variadic",
                [cel.StringType, cel.StringType, cel.IntType],
                cel.StringType,
                cel.FunctionBinding(format_values))))

    if err is not None:
        raise err

    print("FunctionOp Examples:\n")
    
    # Test various FunctionOp examples
    test_cases = [
        ("sum(a, b, c)", {'a': 10, 'b': 20, 'c': 30}),
        ("sum(1, 2, 3)", {}),
        ('join("Hello", "world", "!")', {}),
        ('join(user.name, "is", string(user.age))', {}),
        ('max(1.5, 2.7, 3.9, 0.8)', {}),
        ('format("User {} is {} years old", user.name, user.age)', {}),
    ]
    
    for expr, extra_vars in test_cases:
        print(f"Expression: {expr}")
        
        ast, issue = env.compile(expr)
        if issue is not None:
            print(f"Compilation error: {issue}")
            continue
        
        program, err = env.program(ast)
        if err is not None:
            print(f"Program error: {err}")
            continue
        
        eval_vars = {
            'a': 1,
            'b': 2,
            'c': 3,
            'user': user
        }
        eval_vars.update(extra_vars)
        
        out, detail, err = program.eval(eval_vars)
        if err is not None:
            print(f"Evaluation error: {err}")
        else:
            print(f"Result: {out}")
        print()


if __name__ == '__main__':
    main()