import mimicel as cel

try:
    from user_pb2 import User
except ImportError:
    try:
        from examples.user_pb2 import User
    except ImportError:
        from example.user_pb2 import User

def add_int_int(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

def concat_str_str(a: str, b: str) -> str:
    """Concatenate two strings."""
    return a + b

def max_int_int(a: int, b: int) -> int:
    """Return the maximum of two integers."""
    return max(a, b)

def main():
    """Main function that can be called from wrapper or __main__."""
    user = User(
        name="Shuhei Tanuma",
        age=10
    )

    env, err = cel.new_env(
        cel.Types(User.DESCRIPTOR),
        cel.Variable("a", cel.IntType),
        cel.Variable("b", cel.StringType),
        cel.Variable("x", cel.IntType),
        cel.Variable("y", cel.IntType),
        cel.Variable("user", cel.ObjectType("example.User")),
        cel.Function("add",
            cel.Overload("add_int_int",
                [cel.IntType, cel.IntType],
                cel.IntType,
                cel.BinaryBinding(add_int_int))),
        cel.Function("concat",
            cel.Overload("concat_str_str",
                [cel.StringType, cel.StringType],
                cel.StringType,
                cel.BinaryBinding(concat_str_str))),
        cel.Function("max",
            cel.Overload("max_int_int",
                [cel.IntType, cel.IntType],
                cel.IntType,
                cel.BinaryBinding(max_int_int))))

    if err is not None:
        raise err

    # Test add function
    ast1, issue1 = env.compile("add(10, 20)")
    if issue1 is not None:
        raise issue1

    program1, err1 = env.program(ast1)
    if err1 is not None:
        raise err1

    out1, detail1, err1 = program1.eval({
        'a': 15,
        'b': "Hello World",
        'x': 5,
        'y': 10,
        'user': user
    })
    print("add(10, 20) =", out1)

    # Test concat function
    ast2, issue2 = env.compile("concat('Hello', ' World')")
    if issue2 is not None:
        raise issue2

    program2, err2 = env.program(ast2)
    if err2 is not None:
        raise err2

    out2, detail2, err2 = program2.eval({
        'a': 15,
        'b': "Hello World",
        'x': 5,
        'y': 10,
        'user': user
    })
    print("concat('Hello', ' World') =", out2)

    # Test max function with variables
    ast3, issue3 = env.compile("max(x, y)")
    if issue3 is not None:
        raise issue3

    program3, err3 = env.program(ast3)
    if err3 is not None:
        raise err3

    out3, detail3, err3 = program3.eval({
        'a': 15,
        'b': "Hello World",
        'x': 5,
        'y': 10,
        'user': user
    })
    print("max(x, y) where x=5, y=10 =", out3)

    # Test combining functions
    ast4, issue4 = env.compile("add(max(x, y), a)")
    if issue4 is not None:
        raise issue4

    program4, err4 = env.program(ast4)
    if err4 is not None:
        raise err4

    out4, detail4, err4 = program4.eval({
        'a': 15,
        'b': "Hello World",
        'x': 5,
        'y': 10,
        'user': user
    })
    print("add(max(x, y), a) where x=5, y=10, a=15 =", out4)


if __name__ == '__main__':
    main()