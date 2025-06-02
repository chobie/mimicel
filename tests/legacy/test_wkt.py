import pytest
from google.protobuf.struct_pb2 import Struct, ListValue, Value

from mimicel.api import CelEnv
from mimicel.cel_values import CelBool, CelList, CelString, CelInt


def test_wkt_int32_addition():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 123} + 1'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 124

def test_wkt_int32_subtraction():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 123} - 1'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 122

def test_wkt_int32_multiply():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 123} * 2'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 246

def test_wkt_int32_divide():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 120} / 2'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 60

def test_wkt_int32_divided():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 120} % 60'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 0


def test_wkt_int32_addition_2():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 123} + google.protobuf.Int32Value{value: 1}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 124

def test_wkt_int32_subtraction_2():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 123} - google.protobuf.Int32Value{value: 1}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 122

def test_wkt_int32_multiply_2():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 123} * google.protobuf.Int32Value{value: 2}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 246

def test_wkt_int32_divide_2():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 120} / google.protobuf.Int32Value{value: 2}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 60

def test_wkt_int32_divided_2():
    env = CelEnv()
    expr = 'google.protobuf.Int32Value{value: 120} % google.protobuf.Int32Value{value: 60}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 0

def test_wkt_int32_addition_3():
    env = CelEnv()
    expr = '1 + google.protobuf.Int32Value{value: 123}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 124

def test_wkt_int32_subtraction_3():
    env = CelEnv()
    expr = '123 - google.protobuf.Int32Value{value: 1}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 122

def test_wkt_int32_multiply_3():
    env = CelEnv()
    expr = '123 * google.protobuf.Int32Value{value: 2}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 246

def test_wkt_int32_divide_3():
    env = CelEnv()
    expr = '120 / google.protobuf.Int32Value{value: 2}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 60

def test_wkt_int32_divided_3():
    env = CelEnv()
    expr = '120 % google.protobuf.Int32Value{value: 60}'
    prog = env.compile(expr)
    result = prog.eval()
    assert result is 0


def test_wkt_struct():
    pb_struct = Struct()
    pb_struct.fields["name"].string_value = "test_user"
    pb_struct.fields["score"].number_value = 100.5
    pb_struct.fields["active"].bool_value = True
    pb_struct.fields["meta"].null_value = 0  # NullValue.NULL_VALUE

    env = CelEnv(variables={
        "data": "google.protobuf.Struct"
    })
    context = {
        "data": pb_struct
    }
    program = env.compile("data['name'] == 'test_user'")
    assert program.eval(context) is True

    program = env.compile("data['score'] == 100.5")
    assert program.eval(context) is True

    program = env.compile("data['active'] == true")
    assert program.eval(context) is True

    program = env.compile("data['meta'] == null")
    assert program.eval(context) is True


def setup_list_value_env_context():
    """pytestフィクスチャの代わりのヘルパー関数"""
    pb_list_value = ListValue()
    pb_list_value.values.add().string_value = "hello"  # index 0
    pb_list_value.values.add().number_value = 123.0  # index 1
    pb_list_value.values.add().bool_value = True  # index 2
    pb_list_value.values.add().null_value = 0  # index 3
    pb_list_value.values.add().string_value = "world"  # index 4
    env = CelEnv(variables={
        "my_list": "google.protobuf.ListValue",
        "another_list": "list"

    })
    context = {
        "my_list": pb_list_value,
        "another_list": [Value(string_value="another"), Value(number_value=456.0)]  # 実行時の値
    }
    return env, context, pb_list_value


def test_list_value_access_string_element():
    """ListValue: 文字列要素へのインデックスアクセスと値の比較"""
    env, context, _ = setup_list_value_env_context()
    expr = "my_list[0] == 'hello'"
    program = env.compile(expr)
    result = program.eval(context)
    assert result == True, f"Expected CelBool(True), Got {result!r}"


def test_list_value_access_number_element():
    """ListValue: 数値要素へのインデックスアクセスと値の比較"""
    env, context, _ = setup_list_value_env_context()
    expr = "my_list[1] == 123.0"
    program = env.compile(expr)
    result = program.eval(context)
    assert result == True, f"Expected CelBool(True), Got {result!r}"


def test_list_value_access_bool_element():
    """ListValue: 真偽値要素へのインデックスアクセスと値の比較"""
    env, context, _ = setup_list_value_env_context()
    expr = "my_list[2] == true"
    program = env.compile(expr)
    result = program.eval(context)
    assert result == True, f"Expected CelBool(True), Got {result!r}"


def test_list_value_access_null_element():
    """ListValue: null要素へのインデックスアクセスと値の比較"""
    env, context, _ = setup_list_value_env_context()
    expr = "my_list[3] == null"
    program = env.compile(expr)
    result = program.eval(context)
    assert result == True, f"Expected CelBool(True), Got {result!r}"


def test_list_value_size_function():
    """ListValue: size() 関数のテスト"""
    env, context, pb_list_value = setup_list_value_env_context()
    expected_size = len(pb_list_value.values)  # 5

    # size(my_list) の結果が CelInt であることを確認
    expr_size_val = "size(my_list)"
    program_size_val = env.compile(expr_size_val)
    result_size_val = program_size_val.eval(context)
    assert result_size_val == expected_size, \
        f"size(my_list) expected CelInt({expected_size}), Got {result_size_val!r}"

    # size(my_list) == N の式全体が CelBool(True) になることを確認
    expr_comparison = f"size(my_list) == {expected_size}"
    program_comparison = env.compile(expr_comparison)
    result_comparison = program_comparison.eval(context)
    assert result_comparison == True, \
        f"size(my_list) == {expected_size} expected CelBool(True), Got {result_comparison!r}"


def test_list_value_index_out_of_bounds():
    """ListValue: 範囲外インデックスアクセスでエラーが発生することを確認"""
    env, context, pb_list_value = setup_list_value_env_context()
    invalid_index = len(pb_list_value.values)  # 確実に範囲外のインデックス
    expr = f"my_list[{invalid_index}]"

    with pytest.raises(RuntimeError) as excinfo:  # またはより具体的なCELエラー型
        program = env.compile(expr)
        program.eval(context)
    # エラーメッセージに "index out of range" や "KeyError" (実装による) が含まれることを確認してもよい
    assert "out of range" in str(excinfo.value).lower() or \
           "keyerror" in str(excinfo.value).lower() or \
           "no_such_field" in str(excinfo.value).lower()  # 実装依存のエラーメッセージ


def test_list_value_in_operator_true():
    """ListValue: 'in' 演算子 (要素が存在する場合) のテスト"""
    env, context, _ = setup_list_value_env_context()
    expr = "'hello' in my_list"  # my_list[0] は "hello"
    program = env.compile(expr)
    result = program.eval(context)
    assert result == True, f"Expected 'hello' in my_list to be true, Got {result!r}"


def test_list_value_in_operator_number_true():
    """ListValue: 'in' 演算子 (数値要素が存在する場合) のテスト"""
    env, context, _ = setup_list_value_env_context()
    expr = "123.0 in my_list"  # my_list[1] は 123.0
    program = env.compile(expr)
    result = program.eval(context)
    assert result == True, f"Expected 123.0 in my_list to be true, Got {result!r}"


def test_list_value_in_operator_false():
    """ListValue: 'in' 演算子 (要素が存在しない場合) のテスト"""
    env, context, _ = setup_list_value_env_context()
    expr = "'goodbye' in my_list"
    program = env.compile(expr)
    result = program.eval(context)
    assert result == False, f"Expected 'goodbye' in my_list to be false, Got {result!r}"


def test_list_value_concatenation_with_cel_list():
    """ListValue: CelList との結合テスト"""
    env, context, pb_list_value = setup_list_value_env_context()
    expr = "my_list + another_list"
    program = env.compile(expr)
    result = program.eval(context)

    assert isinstance(result, list), f"Expected result to be CelList, got {type(result).__name__}"
    expected_len = len(pb_list_value.values) + 2
    assert len(result) == expected_len, f"Expected combined list length {expected_len}, got {len(result)}"

    assert result[0] == "hello"
    assert result[expected_len - 2] == "another"
