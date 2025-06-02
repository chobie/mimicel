import mimicel as cel
from user_pb2 import User

def hello_str_str(arg: str) -> str:
    return "Hello " + arg

if __name__ == '__main__':
    user = User(
        name="Shuhei Tanuma",
        age=10
    )

    env, err = cel.new_env(
        cel.Types(User.DESCRIPTOR),
        cel.Variable("a", cel.IntType),
        cel.Variable("b", cel.StringType),
        cel.Variable("user", cel.ObjectType("example.User")),
        cel.Function("hello",
            cel.Overload("hello_str_str",
                [cel.StringType],
                cel.StringType,
                cel.UnaryBinding(hello_str_str))))

    if err is not None:
        raise err

    ast, issue = env.compile("hello('World')")
    if issue is not None:
        raise issue

    program, err = env.program(ast)
    if err is not None:
        raise err

    out, detail, err = program.eval({
        'a': 15,
        'b': "Hello World",
        'user': user
    })
    print(out)