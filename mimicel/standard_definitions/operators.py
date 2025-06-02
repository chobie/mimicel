# standard_definitions/operators.py
from typing import Callable, Any

from ..cel_values.cel_types import (
    CEL_DYN,
    CEL_NULL
)
from ..cel_values import (
    CelValue, CelBool, CelString, CelList, CelMap, CelNull, CelProtobufValue, CelProtobufListValue,
    CelProtobufStruct, CelUInt,  # 基本的な値
)
from ..cel_values.errors import CelErrorValue

def cel_operator_add_wrapper(op1: CelValue, op2: CelValue) -> CelValue:
    return op1 + op2  # type: ignore


def cel_operator_subtract_wrapper(op1: CelValue, op2: CelValue) -> CelValue:
    return op1 - op2  # type: ignore


def cel_operator_multiply_wrapper(op1: CelValue, op2: CelValue) -> CelValue:
    return op1 * op2  # type: ignore


def cel_operator_divide_wrapper(op1: CelValue, op2: CelValue) -> CelValue:
    return op1 / op2  # type: ignore


def cel_operator_modulo_wrapper(op1: CelValue, op2: CelValue) -> CelValue:
    return op1 % op2  # type: ignore


def cel_operator_negate_wrapper(op: CelValue) -> CelValue:
    if isinstance(op, CelUInt):
        raise RuntimeError(f"no_such_overload: !uint / no such overload")
    if isinstance(op, CelBool):
        raise RuntimeError(f"no_such_overload: !bool")

    return -op  # type: ignore


def _compare_ops_wrapper(op1: CelValue, op2: CelValue, op_lambda: Callable[[Any, Any], bool], op_display_name: str) -> CelBool:
    try:
        result = op_lambda(op1, op2)
        if not isinstance(result, bool):
             raise TypeError(f"Internal error: comparison op_lambda did not return bool for {op1.cel_type.name} and {op2.cel_type.name}")
        return CelBool(result)
    except TypeError as e: # 例: list < list で CelList.__lt__ が TypeError を出す場合
        raise RuntimeError(f"no such overload: {e}") from e


def cel_operator_equals_wrapper(op1: CelValue, op2: CelValue) -> CelValue:
    if isinstance(op1, CelErrorValue): return op1
    if isinstance(op2, CelErrorValue): return op2
    return _compare_ops_wrapper(op1, op2, lambda a, b: a == b, "'=='")

def cel_operator_not_equals_wrapper(op1: CelValue, op2: CelValue) -> CelValue: # 返り値をCelValueに
    if isinstance(op1, CelErrorValue): return op1
    if isinstance(op2, CelErrorValue): return op2
    return _compare_ops_wrapper(op1, op2, lambda a, b: a != b, "'!='")


def cel_operator_less_than_wrapper(op1: CelValue, op2: CelValue) -> CelValue: # 返り値をCelValueに
    if isinstance(op1, CelErrorValue): return op1
    if isinstance(op2, CelErrorValue): return op2
    return _compare_ops_wrapper(op1, op2, lambda a, b: a < b, "'<'")


def cel_operator_less_than_equals_wrapper(op1: CelValue, op2: CelValue) -> CelValue: # 返り値をCelValueに
    if isinstance(op1, CelErrorValue): return op1
    if isinstance(op2, CelErrorValue): return op2
    return _compare_ops_wrapper(op1, op2, lambda a, b: a <= b, "'<='")


def cel_operator_greater_than_wrapper(op1: CelValue, op2: CelValue) -> CelValue: # 返り値をCelValueに
    if isinstance(op1, CelErrorValue): return op1 # ★ エラーを伝播 (テスト[0.2]のため)
    if isinstance(op2, CelErrorValue): return op2 # ★ エラーを伝播
    return _compare_ops_wrapper(op1, op2, lambda a, b: a > b, "'>'")

def cel_operator_greater_than_equals_wrapper(op1: CelValue, op2: CelValue) -> CelValue: # 返り値をCelValueに
    if isinstance(op1, CelErrorValue): return op1
    if isinstance(op2, CelErrorValue): return op2
    return _compare_ops_wrapper(op1, op2, lambda a, b: a >= b, "'>='")


def cel_operator_in_wrapper(element: CelValue, container: CelValue) -> CelBool:
    actual_container = container
    if isinstance(container, CelProtobufValue):
        try:
            actual_container = container._dynamic_convert()
        except NotImplementedError:
            raise TypeError(f"'in' operator not supported for Value kind '{container.get_kind()}' (conversion not implemented)")
        if not isinstance(actual_container, (CelList, CelMap, CelProtobufListValue, CelProtobufStruct)):
            raise TypeError(f"'in' operator not supported for dynamically converted type '{actual_container.cel_type.name}' from Value kind '{container.get_kind()}'")

    if isinstance(actual_container, (CelList, CelMap, CelProtobufListValue, CelProtobufStruct)):
        return CelBool(element in actual_container) # __contains__ に委譲
    # ... (エラー処理) ...
    type_name = actual_container.cel_type.name if hasattr(actual_container, 'cel_type') else type(actual_container).__name__
    raise TypeError(f"'in' operator not supported for container type {type_name}")



def cel_operator_logical_not_wrapper(op: CelValue) -> CelBool:
    if not isinstance(op, CelBool):
        raise TypeError("Operand for '!' must be boolean")
    return CelBool(not op.value)


def cel_operator_index_wrapper(container: CelValue, key: CelValue) -> CelValue:
    actual_container = container
    if isinstance(container, CelProtobufValue):
        try:
            actual_container = container._dynamic_convert()
        except NotImplementedError:
            raise TypeError(
                f"Indexing not supported for Value kind '{container.get_kind()}' (conversion not implemented)")
        if not isinstance(actual_container, (CelList, CelMap, CelProtobufListValue, CelProtobufStruct)):
            raise TypeError(
                f"Indexing not supported for dynamically converted type '{actual_container.cel_type.name}' from Value kind '{container.get_kind()}'")

    if isinstance(actual_container, (CelList, CelMap, CelProtobufListValue, CelProtobufStruct)):
        try:
            return actual_container[key]  # __getitem__ に委譲
        except (RuntimeError, KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Error during index operation on '{actual_container.cel_type.name}': {e}") from e

    type_name = actual_container.cel_type.name if hasattr(actual_container, 'cel_type') else type(
        actual_container).__name__
    raise TypeError(f"Indexing not supported for container type {type_name}")


def cel_operator_ternary_wrapper(condition: CelValue, true_branch: CelValue, false_branch: CelValue) -> CelValue:
    # ★ 条件部がエラーなら、そのエラーを伝播
    if isinstance(condition, CelErrorValue):
        return condition

    if not isinstance(condition, CelBool):
        # 条件がboolでもエラーでもない場合は型エラー。
        # このエラーメッセージも conformance test の期待に合わせる必要があるかもしれない。
        # 以前ユーザーが "no matching overload" に修正していた。
        raise TypeError(
            f"no matching overload: condition for ternary operator must be bool, got {condition.cel_type.name}")

    # true_branch と false_branch は、condition の評価後、必要に応じて評価される（遅延評価）。
    # このラッパー関数は既に評価済みの値を受け取るので、ここでは単純に選択する。
    # eval_pb.py の handle_call_expr で三項演算子の遅延評価を実装する必要がある。
    # ここでは、渡された値をそのまま使う。
    return true_branch if condition.value else false_branch


def cel_operator_is_wrapper(value: CelValue, type_name_val: CelValue) -> CelBool:
    # 実装は conversions.py の cel_is_impl や、そこで使われる cel_type_of に依存
    # ここではラッパーとして定義。
    from .conversions import cel_type_of  # 遅延インポートで循環参照を避ける
    if not isinstance(type_name_val, CelString):
        raise TypeError("Type name for 'is' operator must be a string.")

    expected_type_name_str = type_name_val.value
    actual_cel_type = cel_type_of(value)  # conversions.py の cel_type_of を使用

    # ParameterizedCelType の場合、ベースタイプ名 (list, map) で比較
    from ..cel_values.cel_types import ParameterizedCelType, _LIST_BASE_TYPE, _MAP_BASE_TYPE

    final_actual_type_name_to_compare = actual_cel_type.name
    if isinstance(actual_cel_type, ParameterizedCelType):
        if actual_cel_type.base_type == _LIST_BASE_TYPE:
            final_actual_type_name_to_compare = "list"
        elif actual_cel_type.base_type == _MAP_BASE_TYPE:
            final_actual_type_name_to_compare = "map"

    # null is null_type
    if isinstance(value, CelNull) and expected_type_name_str == CEL_NULL.name:  # "null_type"
        return CelBool(True)

    return CelBool(final_actual_type_name_to_compare == expected_type_name_str)

def _dummy_logical_op_impl(lhs: CelValue, rhs: CelValue) -> CelBool:
    # この関数は実際には呼び出されない。短絡評価は評価器(eval_pb.py)で行うため。
    raise NotImplementedError("Logical AND/OR should be short-circuited by evaluator")

# Comparison Operators (==, !=, <, <=, >, >=)
comparison_operators_map = {
    "_==_": cel_operator_equals_wrapper,
    "_!=_": cel_operator_not_equals_wrapper,
    "_<__": cel_operator_less_than_wrapper,
    "_<=_": cel_operator_less_than_equals_wrapper,
    "_>__": cel_operator_greater_than_wrapper,
    "_>=_": cel_operator_greater_than_equals_wrapper
}

# Arithmetic Operators (+, -, *, /, %)
arithmetic_binary_operators_map = {
    "_+_": (cel_operator_add_wrapper, CEL_DYN),  # デフォルトの戻り値型
    "_-_": (cel_operator_subtract_wrapper, CEL_DYN),
    "_*_": (cel_operator_multiply_wrapper, CEL_DYN),
    "_/_": (cel_operator_divide_wrapper, CEL_DYN),
    "_%_": (cel_operator_modulo_wrapper, CEL_DYN)
}
