from datetime import timedelta, datetime

import pytest

from antlr4 import InputStream, CommonTokenStream
from mimicel.CELLexer import CELLexer
from mimicel.CELParser import CELParser
from mimicel.api import CelEnv, CELCompileError
from mimicel.cel_values.cel_types import CEL_INT, CEL_LIST
from mimicel.cel_values import CelValue, CelMap, CelString, CelInt, CelStruct
from mimicel.context import EvalContext
from mimicel.standard_definitions import STANDARD_LIBRARY
from mimicel.cel_ast_builder import CelASTBuilder
from mimicel.eval_pb import eval_expr_pb
from mimicel.type_registry import TypeRegistry


def eval_expr(expr: str, context_dict: dict = None) -> object:
    """CEL式をコンパイルして評価し、Pythonのプリミティブ値として返す（CelValueをunwrap）"""
    if isinstance(context_dict, CelEnv):
        context = context_dict
    else:
        context = EvalContext(base=context_dict or {}, builtins=STANDARD_LIBRARY)

    input_stream = InputStream(expr)
    lexer = CELLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CELParser(stream)
    tree = parser.start()
    ast = CelASTBuilder().visit(tree)
    print(ast)
    result = eval_expr_pb(ast, context)

    return result.value if isinstance(result, CelValue) else result

def test_cel_eval_one():
    ret = eval_expr("a * 3 == 6", {"a": 2})
    assert ret == True

@pytest.mark.parametrize("expr, context_dict, structure, expected", [
    ("a * 3 == 6", {"a": 2},{"a": "int"}, True),
    ("a * 3 != 6", {"a": 3},{"a": "int"}, True),
    ("a < 10", {"a": 5},{"a": "int"}, True),
    ("a >= 3", {"a": 3},{"a": "int"}, True),
    ("a == 2 || a == 3", {"a": 2},{"a": "int"}, True),
    ("a == 2 || a == 3", {"a": 4},{"a": "int"}, False),
    ("a == 2 && b == 1", {"a": 2, "b": 1},{"a": "int", "b": "int"}, True),
    ("a == 2 && b == 1", {"a": 2, "b": 0},{"a": "int", "b": "int"}, False),
    ("a == 2 || (a == 3 && b == 1)", {"a": 3, "b": 1},{"a": "int", "b": "int"}, True),
    ("a == 2 || (a == 3 && b == 0)", {"a": 3, "b": 0},{"a": "int", "b": "int"}, True),
])
def test_eval_expr_pb(expr, context_dict, structure, expected):
    env = CelEnv(variables=structure)
    expr_pb = env.parse(expr)
    program = env.program(expr_pb)
    result = program.eval(context_dict)
    assert result == expected

def test_cel_env_pb_eval():
    env = CelEnv(variables={"a": "int"})
    expr_pb = env.parse("a * 3 == 6")
    program = env.program(expr_pb)
    assert program.eval({"a": 2}) is True


@pytest.mark.parametrize("expr, context_dict, expected_exception", [
    ("1 + true", {}, RuntimeError),
    ("'a' < 3", {}, RuntimeError),
    ("a && 1", {"a": True}, RuntimeError),
])
def test_type_errors(expr, context_dict, expected_exception):
    with pytest.raises(expected_exception):
        eval_expr(expr, context_dict)

# Null比較はFalseになることを確認
def test_null_safe_comparison():
    with pytest.raises(RuntimeError):
        eval_expr("b == 3", {})

@pytest.mark.parametrize("expr, context_dict, expected", [
    ("!false", {}, True),
    ("!(a == 2)", {"a": 2}, False),
    ("a in [1, 2]", {"a": 2}, True),
    ("a in [1, 2]", {"a": 3}, False),
    ("size([1, 2, 3]) == 3", {}, True),
])
def test_extended_exprs(expr, context_dict, expected):
    result = eval_expr(expr, context_dict)
    assert result == expected

@pytest.mark.parametrize("expr, context_dict, expected", [
    ("is_even(2)", {"is_even": lambda x: x % 2 == 0}, True),
    ("is_even(3)", {"is_even": lambda x: x % 2 == 0}, False),
    ("_double(3) == 6", {"_double": lambda x: x * 2}, True),
])
def test_user_defined_functions(expr, context_dict, expected):
    result = eval_expr(expr, context_dict)
    assert result == expected

def test_missing_function():
    with pytest.raises(RuntimeError):
        eval_expr("unknown_func(1)", {})

#@pytest.mark.parametrize("expr, expected", [
#    ("let x = 1; x == 1", True),
#    ("let a = 2; let b = 3; a * b == 6", True),
#    ("let x = 5; x + 1 == 6", True),
#])
#def test_let_expr(expr, expected):
#    result = eval_expr(expr, {})
#    assert result == expected

def test_missing_map_key_raises():
    m = CelMap({CelString("a"): CelInt(1)})
    with pytest.raises(RuntimeError):
        _ = m["b"]  # ← CEL 的にはエラーでよい

@pytest.mark.parametrize("expr, context_dict, expected", [
    ("user.name == 'alice'", {"user": {"name": "alice"}}, True),
    ("user.age > 18", {"user": {"age": 20}}, True),
    ("config.db.host == 'localhost'", {"config": {"db": {"host": "localhost"}}}, True),
])
def test_select_expr(expr, context_dict, expected):
    result = eval_expr(expr, context_dict)
    assert result == expected


@pytest.mark.parametrize("expr, context_dict, expected", [
    ('{"a": 1, "b": 2}["a"]', {}, 1),
    ('{"x": 10}["x"] == 10', {}, True),
])
def test_map_literal_success(expr, context_dict, expected):
    result = eval_expr(expr, context_dict)
    assert result == expected


@pytest.mark.parametrize("expr, context_dict, expected_exception", [
    ('{"a": 1, "b": 2}["c"]', {}, RuntimeError),
])
def test_map_literal_errors(expr, context_dict, expected_exception):
    with pytest.raises(RuntimeError):
        eval_expr(expr, context_dict)

@pytest.mark.parametrize("expr, context_dict, expected", [
    ("true ? 1 : 2", {}, 1),
    ("false ? 1 : 2", {}, 2),
    ("a > 0 ? 'positive' : 'non-positive'", {"a": 3}, "positive"),
    ("a > 0 ? 'positive' : 'non-positive'", {"a": 0}, "non-positive"),
])
def test_ternary_operator(expr, context_dict, expected):
    result = eval_expr(expr, context_dict)
    assert result == expected

@pytest.mark.parametrize("expr, context_dict, expected", [
    ("has(user.name)", {"user": {"name": "alice"}}, True),
    ("has(user.name)", {"user": {"name": None}}, True),
    # ("has(user)", {"user": None}, False),  ← 除外 or has_macro拡張
    ("has(user.age)", {"user": {}}, False),
])
def test_has_macro(expr, context_dict, expected):
    result = eval_expr(expr, context_dict)
    assert result == expected


@pytest.mark.parametrize("expr, expected", [
    ('"abc".matches("a.*")', True),
    ('"def".matches("a.*")', False),
])
def test_string_matches(expr, expected):
    assert eval_expr(expr, {}) == expected


@pytest.mark.parametrize("expr, expected", [
    #("type(123)", "int"),
    #("type('abc')", "string"),
    ("1 is 'int'", True),
    # ("1 is 'string'", False),
    # ("[1, 2] is 'list'", True),
    # ("null is 'null'", True),
])

def test_type_checks(expr, expected):
    assert eval_expr(expr, {}) == expected


def test_short_circuit_and():
    called = {"value": False}

    def fail_fn():
        called["value"] = True
        raise AssertionError("should not be called")

    result = eval_expr("false && f()", {"f": fail_fn})

    assert result is False
    assert called["value"] is False

def test_short_circuit_or():
    called = {"value": False}

    def fail_fn():
        called["value"] = True
        raise AssertionError("should not be called")

    result = eval_expr("true || f()", {"f": fail_fn})
    assert result is True
    assert called["value"] is False


@pytest.mark.parametrize("expr, expected", [
    ('duration("1h")', timedelta(hours=1)),
    ('duration("2m30s")', timedelta(minutes=2, seconds=30)),
    ('duration("1h15m5s")', timedelta(hours=1, minutes=15, seconds=5)),
])
def test_duration_literal(expr, expected):
    result = eval_expr(expr, {})
    assert result == expected


@pytest.mark.parametrize("expr, expected_year", [
    ('timestamp("2020-01-01T00:00:00")', 2020),
    ('timestamp("1999-12-31T23:59:59")', 1999),
])
def test_timestamp_literal(expr, expected_year):
    result = eval_expr(expr, {})
    assert isinstance(result, datetime)
    assert result.year == expected_year


@pytest.mark.parametrize("expr, expected", [
    ('b"abc"', b"abc"),
    ('b"\\x61\\x62\\x63"', b"abc"),   # a=0x61, b=0x62, c=0x63
    ('b"\\n"', b"\n"),
    ('b"\\r\\n"', b"\r\n"),
])
def test_bytes_literal(expr, expected):
    result = eval_expr(expr, {})
    assert result == expected


def test_env_compile_eval_startswith():
    env = CelEnv(variables={"name": "string", "group": "string"})
    ast = env.parse('name.startsWith("/groups/" + group)')
    prg = env.program(ast)

    result = prg.eval({
        "name": "/groups/acme.co/documents/secret-stuff",
        "group": "acme.co"
    })

    assert result is True



def test_env_compile_eval_numeric():
    env = CelEnv(variables={"x": "int", "y": "int"})
    ast = env.parse('x * y == 42')
    prg = env.program(ast)

    result = prg.eval({"x": 6, "y": 7})
    assert result is True


def test_env_compile_eval_bool_logic():
    env = CelEnv(variables={"a": "bool", "b": "bool"})
    ast = env.parse('a && b')
    prg = env.program(ast)

    result = prg.eval({"a": True, "b": False})
    assert result is False



def test_compile_error_reports_location():
    env = CelEnv()
    # リスト内包表記はCELで未サポート
    expr = "[x for x in list]"

    with pytest.raises(CELCompileError) as exc_info:
        env.parse(expr)

    msg = str(exc_info.value)
    assert "Syntax error" in msg
    assert "line" in msg and "column" in msg


def compile_and_eval(expr: str, vars: dict, env: CelEnv):
    ast = env.parse(expr)
    program = env.program(ast)
    return program.eval(vars)


def test_field_access_via_typeregistry():
    class User:
        def __init__(self, name, age):
            self.name = name
            self.age = age

    user = User(name="Alice", age=30)

    registry = TypeRegistry()
    registry.register(User, ["name", "age"])

    env = CelEnv(type_registry=registry)
    ctx = EvalContext(base={"user": user}, builtins=env.builtins, env=env)

    ast = env.parse("user.name")
    result = eval_expr_pb(ast, ctx)
    assert result.value == "Alice"


def test_has_macro_with_typeregistry():
    class Profile:
        def __init__(self, bio=None):
            self.bio = bio

    registry = TypeRegistry()
    registry.register(Profile, ["bio"])

    env = CelEnv(type_registry=registry)
    ctx = EvalContext({"profile": Profile()}, env=env)
    ast = env.parse("has(profile.bio)")
    result = eval_expr_pb(ast, ctx)

    assert result.value is True  # bio is None

    # 再設定して bio があるケース
    ctx.set("profile", Profile(bio="..."))
    result2 = eval_expr_pb(ast, ctx)
    assert result2.value is True

def test_map_index_access():
    from mimicel.cel_values import CelString, CelInt
    m = CelMap({CelString("a"): CelInt(1)})
    assert m[CelString("a")] == CelInt(1)


@pytest.mark.parametrize("expr, context, expected", [
    ("1.5 == 1.5", {}, True),
    ("2.0 + 3.0 == 5.0", {}, True),
    ("5.0 - 1.5 == 3.5", {}, True),
    ("2.0 * 3.5 == 7.0", {}, True),
    ("7.0 / 2.0 == 3.5", {}, True),
    ("3.0 < 4.0", {}, True),
    ("4.0 >= 4.0", {}, True),
])
def test_double_operations(expr, context, expected):
    assert eval_expr(expr, context) == expected


@pytest.mark.parametrize("expr", [
    "'abc' < 3.14",
    "null >= 0.5",
])
def test_double_type_errors(expr):
    with pytest.raises(RuntimeError):
        eval_expr(expr, {})

@pytest.mark.parametrize("expr", [
    "1.0 + true",
])
def test_double_type_errors2(expr):
    with pytest.raises(RuntimeError):
        eval_expr(expr, {})



@pytest.mark.parametrize("expr, expected", [
    ("timestamp(\"2024-05-01T00:00:00\") < timestamp(\"2024-05-02T00:00:00\")", True),
    ("duration(\"1h\") < duration(\"90m\")", True),
])
def test_temporal_literals(expr, expected):
    assert eval_expr(expr, {}) == expected

@pytest.mark.parametrize("expr, context_dict, expected", [
    ('{name: "Alice", age: 30}.name', {}, "Alice"),
    ('{name: "Alice", age: 30}.age', {}, 30),
])
def test_struct_field_access(expr, context_dict, expected):
    result = eval_expr(expr, context_dict)
    assert result == expected

@pytest.mark.parametrize("expr, context_dict, expected", [
    ('{name: "Alice"}["age"]', {}, RuntimeError),  # Map的アクセスで存在しないキー
])
def test_struct_field_access2(expr, context_dict, expected):
    with pytest.raises(expected):
        eval_expr(expr, {})

def test_nested_struct_field_access():
    expr = '{user: {name: "alice", age: 20}}.user.name'
    assert eval_expr(expr) == "alice"

    expr = '{user: {name: "alice", age: 20}}["user"].age'
    assert eval_expr(expr) == 20

    expr = '{user: {profile: {email: "a@example.com"}}}.user.profile.email'
    assert eval_expr(expr) == "a@example.com"

    expr = '{user: {profile: {email: "a@example.com"}}}["user"]["profile"]["email"]'
    assert eval_expr(expr) == "a@example.com"


@pytest.mark.parametrize("expr, context, expected", [
    ("has(user.name)", {"user": {"name": "Alice"}}, True),
    ("has(user)", {"user": "some value"}, True),
])
def test_has_macro_struct(expr, context, expected):
    assert eval_expr(expr, context) == expected

@pytest.mark.parametrize("expr, context, expected", [
# 今ちょっと無理
#    ("has(user.name)", {"user": {}}, NameError),
    ("has(user.name)", {}, RuntimeError),
    ("has(user)", {}, RuntimeError),
])
def test_has_macro_struct_raise(expr, context, expected):
    with pytest.raises(expected):
        ret = eval_expr(expr, context)
        print(ret)


@pytest.mark.parametrize("expr, context, expected", [
    ('matches("abc", "a.*")', {}, True),
    ('matches("xyz", "^a.*")', {}, False),
    ('matches("hello123", "hello\\\\d+")', {}, True),  # ← ここ重要
    ('matches("abc", "[")', {}, RuntimeError),  # ← ValueError ではなく RuntimeError に統一
])
def test_matches_function(expr, context, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            eval_expr(expr, context)
    else:
        assert eval_expr(expr, context) == expected

def test_all_empty_list():
    env = CelEnv()
    prog = env.compile("([]).all(x, x > 0)")
    ret = prog.eval()

    assert ret is True

def test_all_empty_map():
    env = CelEnv()
    prog = env.compile("({}).all(x, x > 0)")
    ret = prog.eval()

    assert ret is True

def test_all_list_all_true():
    env = CelEnv()
    prog = env.compile("([1, 2, 3]).all(x, x > 0)")
    ret = prog.eval()

    assert ret is True

def test_all_list_some_false():
    env = CelEnv()
    prog = env.compile("([1, 0, 3]).all(x, x > 0)")
    assert prog.eval() is False


def test_all_list_first_false_short_circuit():
    # 短絡評価の直接的な観測は難しいが、結果が正しいことを確認
    env = CelEnv()
    # 0 / x が x=0 のときにエラーになることを利用するが、
    # CELの all のエラー吸収ルールを考えると、このテストはより慎重に設計する必要がある。
    # まずは単純なケースから。
    prog = env.compile("([false, true, true]).all(x, x)")
    assert prog.eval() is False

    prog2 = env.compile("([-1, 1, 2]).all(x, x > 0)")
    assert prog2.eval() is False


def test_all_list_with_complex_predicate():
    env = CelEnv(variables={"p_val": CEL_INT})
    prog = env.compile("([1, 2, 3, 4]).all(i, i < p_val)")
    assert prog.eval({"p_val": 5}) is True
    assert prog.eval({"p_val": 3}) is False

def test_all_map_keys_all_true():
    env = CelEnv()
    # つまりlen(a)が1ですという
    prog = env.compile("({'a': 1, 'b': 2}).all(k, k.size() == 1)")
    assert prog.eval() is True

def test_all_map_keys_some_false():
    env = CelEnv()
    prog = env.compile("({'a': 1, 'bb': 2}).all(k, k.size() == 1)")
    assert prog.eval() is False

def test_all_map_values_not_directly_iterable_by_all():
    # allマクロはマップのキーをイテレートする
    env = CelEnv()
    # 以下の式は、キーが述語を満たすかどうかを見る
    prog = env.compile("({'a': 1, 'b': -1}).all(k, {'a': 1, 'b': -1}[k] > 0)")
    assert prog.eval() is False

def test_all_empty_list3():
    env = CelEnv(variables={
        "y": CEL_LIST
    })
    prog = env.compile("y.all(x, x > 0)")
    ret = prog.eval({
        "y": [1,2,3,4]
    })

    assert ret is True

def test_all_non_iterable_target_compile_error():
    env = CelEnv()
    with pytest.raises(CELCompileError):
        env.compile("123.all(x, x > 0)")

def test_all_predicate_not_bool_compile_error():
    env = CelEnv(variables={"my_list": "list<int>"})

    with pytest.raises(CELCompileError) as exc_info:
        # `x` は int であり、bool ではない
        env.compile("my_list.all(x, x)")

    # 型チェックで loop_step (accu && predicate) が bool にならない、
    # または predicate が bool でないというエラーを期待
    assert "type" in str(exc_info.value).lower()
    assert "bool" in str(exc_info.value).lower()

def test_all_iter_var_wrong_type_in_predicate_compile_error():
    env = CelEnv(variables={"str_list": "list<string>"})
    with pytest.raises(CELCompileError) as exc_info:
        # x は string なので x > 0 は型エラーになるはず
        env.compile("str_list.all(x, x > 0)")

    error_message = str(exc_info.value).lower()
    assert "op '_>_'" in error_message
    assert "cannot compare 'string' and 'int'" in error_message

def test_all_result_is_bool_type():
    env = CelEnv(variables={"int_list": "list<int>"})
    # _check_node が CheckedExpr を返すなら、その中の type_map からルートノードの型を取得できる
    # ここではコンパイルが通ることを確認し、評価結果の型を見ることで代用
    prog = env.compile("int_list.all(x, x > 0)")
    # 評価のためには値が必要
    result = prog.eval({"int_list": [1,2,3]})
    assert isinstance(result, bool) # Python bool (unwrap後の想定)
    # もし CelValue が返るなら assert isinstance(result, CelBool)

def test_exists():
    env = CelEnv(variables={"items": "list<int>"})
    prog = env.compile("items.exists(i, i < 0)")
    result = prog.eval({"items": [1,-1,3]})
    assert result is True

def test_exists2():
    env = CelEnv(variables={"items": "list<int>"})
    prog = env.compile("items.exists(i, i < 0)")
    result = prog.eval({"items": [1,2,3]})
    assert result is False

def test_exists_one():
    env = CelEnv(variables={"items": "list<int>"})
    prog = env.compile("items.exists_one(i, i < 0)")
    result = prog.eval({"items": [1,-1,3]})
    assert result is True


def test_map():
    env = CelEnv()
    prog = env.compile("[1, 2, 3].map(n, n * n) ")
    result = prog.eval()
    assert result[0] is 1
    assert result[1] is 4
    assert result[2] is 9


def test_filter2():
    env = CelEnv()
    prog = env.compile("[1, 2, 3, 4].filter(n, n / 2 > 0) ")
    result = prog.eval()
    assert len(result) is 3
    assert result[0] is 2
    assert result[1] is 3
    assert result[2] is 4
