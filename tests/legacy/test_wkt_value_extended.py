# tests/test_wkt_value_extended.py

import pytest
from google.protobuf.struct_pb2 import Value, Struct, ListValue, NULL_VALUE
from mimicel.api import CelEnv
from mimicel.cel_values import CelBool, CelString, CelDouble, CelNull, CelInt, CelList


# CELEnv と実行コンテキストのヘルパー (テスト間で共通化可能)
def setup_value_env_context(variable_name: str, pb_value_instance: Value):
    env = CelEnv(variables={
        variable_name: "google.protobuf.Value"
    })
    context = {
        variable_name: pb_value_instance
    }
    return env, context


# --- Value が StructValue を内包する場合のテスト ---

# ここらへんは出来ちゃいけないようだ
# def test_value_containing_struct_field_access_string():
#     """Value(struct_value): 文字列フィールドへのアクセスと値の比較"""
#     pb_struct = Struct()
#     pb_struct.fields["name"].string_value = "alpha"
#     pb_struct.fields["type"].string_value = "test"
#
#     pb_value_container = Value()
#     pb_value_container.struct_value.CopyFrom(pb_struct)
#
#     env, context = setup_value_env_context("data_val", pb_value_container)
#
#     expr = "data_val.name == 'alpha'"
#     program = env.compile(expr)
#     result = program.eval(context)
#     assert result == True, f"Expected CelBool(True), Got {result!r}"
#
#
# def test_value_containing_struct_field_access_number():
#     """Value(struct_value): 数値フィールドへのアクセスと値の比較"""
#     pb_struct = Struct()
#     pb_struct.fields["score"].number_value = 99.5
#
#     pb_value_container = Value()
#     pb_value_container.struct_value.CopyFrom(pb_struct)
#
#     env, context = setup_value_env_context("data_val", pb_value_container)
#
#     expr = "data_val.score < 100.0"
#     program = env.compile(expr)
#     result = program.eval(context)
#     assert result == True, f"Expected CelBool(True), Got {result!r}"


# def test_value_containing_struct_in_operator():
#     """Value(struct_value): 'in' 演算子のテスト"""
#     pb_struct = Struct()
#     pb_struct.fields["key1"].string_value = "present"
#
#     pb_value_container = Value()
#     pb_value_container.struct_value.CopyFrom(pb_struct)
#
#     env, context = setup_value_env_context("data_val", pb_value_container)
#
#     expr_true = "'key1' in data_val"
#     program_true = env.compile(expr_true)
#     result_true = program_true.eval(context)
#     assert result_true == True, f"Expected 'key1' in data_val to be true, Got {result_true!r}"
#
#     expr_false = "'key_absent' in data_val"
#     program_false = env.compile(expr_false)
#     result_false = program_false.eval(context)
#     assert result_false == False, f"Expected 'key_absent' in data_val to be false, Got {result_false!r}"


def test_value_containing_struct_size_function():
    """Value(struct_value): size() 関数のテスト"""
    pb_struct = Struct()
    pb_struct.fields["a"].bool_value = True
    pb_struct.fields["b"].null_value = NULL_VALUE

    pb_value_container = Value()
    pb_value_container.struct_value.CopyFrom(pb_struct)

    env, context = setup_value_env_context("data_val", pb_value_container)

    expr = "size(data_val) == 2"
    program = env.compile(expr)
    result = program.eval(context)
    assert result == True, f"Expected size(data_val) == 2 to be true, Got {result!r}"


# --- Value が ListValue を内包する場合のテスト ---

def test_value_containing_list_element_access():
    """Value(list_value): 要素へのインデックスアクセスと値の比較"""
    pb_list_value = ListValue()
    pb_list_value.values.add().string_value = "first"
    pb_list_value.values.add().number_value = 2.0

    pb_value_container = Value()
    pb_value_container.list_value.CopyFrom(pb_list_value)

    env, context = setup_value_env_context("data_val", pb_value_container)

    expr1 = "data_val[0] == 'first'"
    program1 = env.compile(expr1)
    result1 = program1.eval(context)
    assert result1 == True, f"Expected data_val[0] == 'first' to be true, Got {result1!r}"

    expr2 = "data_val[1] > 1.0"
    program2 = env.compile(expr2)
    result2 = program2.eval(context)
    assert result2 == True, f"Expected data_val[1] > 1.0 to be true, Got {result2!r}"


def test_value_containing_list_size_function():
    """Value(list_value): size() 関数のテスト"""
    pb_list_value = ListValue()
    pb_list_value.values.add().bool_value = False
    pb_list_value.values.add().string_value = "item"

    pb_value_container = Value()
    pb_value_container.list_value.CopyFrom(pb_list_value)

    env, context = setup_value_env_context("data_val", pb_value_container)

    expr = "size(data_val) == 2"
    program = env.compile(expr)
    result = program.eval(context)
    assert result == True, f"Expected size(data_val) == 2 to be true, Got {result!r}"


# def test_value_containing_list_in_operator():
#     """Value(list_value): 'in' 演算子のテスト"""
#     pb_list_value = ListValue()
#     pb_list_value.values.add().string_value = "apple"
#     pb_list_value.values.add().number_value = 100.0
#
#     pb_value_container = Value()
#     pb_value_container.list_value.CopyFrom(pb_list_value)
#
#     env, context = setup_value_env_context("data_val", pb_value_container)
#
#     expr_true = "'apple' in data_val"
#     program_true = env.compile(expr_true)
#     result_true = program_true.eval(context)
#     assert result_true == True, f"Expected 'apple' in data_val to be true, Got {result_true!r}"
#
#     expr_false = "false in data_val"  # 'false' (bool) はリストにない
#     program_false = env.compile(expr_false)
#     result_false = program_false.eval(context)
#     assert result_false == False, f"Expected false in data_val to be false, Got {result_false!r}"