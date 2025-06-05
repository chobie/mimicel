import mimicel as cel

try:
    from user_pb2 import User
except ImportError:
    try:
        from examples.user_pb2 import User
    except ImportError:
        from example.user_pb2 import User

def string_upper(self: str) -> str:
    """String method to convert to uppercase."""
    return self.upper()

def string_contains(self: str, substr: str) -> bool:
    """String method to check if string contains substring."""
    return substr in self

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
        cel.Variable("user", cel.ObjectType("example.User")),
        cel.Function("upper",
            cel.MemberOverload("string_upper",
                cel.StringType,  # receiver type
                [],  # no additional arguments
                cel.StringType,  # return type
                cel.UnaryBinding(string_upper))),
        cel.Function("contains",
            cel.MemberOverload("string_contains",
                cel.StringType,  # receiver type
                [cel.StringType],  # one string argument
                cel.BoolType,  # return type
                cel.BinaryBinding(string_contains))))

    if err is not None:
        raise err

    # Test string methods
    ast, issue = env.compile("'hello world'.upper()")
    if issue is not None:
        raise issue

    program, err = env.program(ast)
    if err is not None:
        raise err

    out, detail, err = program.eval({})
    print("'hello world'.upper() =", out)

    # Test contains method
    ast2, issue2 = env.compile("'hello world'.contains('world')")
    if issue2 is not None:
        raise issue2

    program2, err2 = env.program(ast2)
    if err2 is not None:
        raise err2

    out2, detail2, err2 = program2.eval({})
    print("'hello world'.contains('world') =", out2)

    # Test with variable
    ast3, issue3 = env.compile("b.upper()")
    if issue3 is not None:
        raise issue3

    program3, err3 = env.program(ast3)
    if err3 is not None:
        raise err3

    out3, detail3, err3 = program3.eval({
        'a': 15,
        'b': "Hello World",
        'user': user
    })
    print("b.upper() =", out3)


if __name__ == '__main__':
    main()