import inspect
import logging
from abc import ABC
from typing import Optional, Dict, Union, Callable, Any, List, get_type_hints, get_args, get_origin

from google.protobuf import message_factory
from google.protobuf.descriptor import Descriptor
from google.protobuf.message import Message

from .api import CelEnv, CelProgram
from .cel_library import CelLibrary
from .cel_values import CelType, CelValue
from .cel_values.cel_types import CelFunctionRegistry, CEL_STRING, CEL_INT, CEL_DOUBLE, CEL_BYTES, CEL_UINT, CEL_BOOL, \
    CEL_FLOAT, CEL_MAP, CEL_LIST, CelFunctionDefinition, CEL_ERROR, CEL_DYN
from .type_registry import TypeRegistry

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# このファイルの実装は人の手で管理されています。
# 基本的にここらへんの機能を使っていれば大きなBreaking Changesには遭遇しないと思います。

_reserved_words = [
    "false", "in", "null", "true",
    "as", "break", "const", "continue", "else", "for", "function", "if", "import", "let", "loop", "package",
    "namespace", "return", "var", "void", "while"
]


class CelAstWrapper:
    def __init__(self, orig, checked):
        self.orig = orig
        self.checked = checked

class CelIssue:
    def __init__(self, ex : Exception):
        self._exception = ex

    def err(self):
        return self._exception

class CelProgramWrapper:
    def __init__(self, program: CelProgram):
        self.program = program

    def eval(self, context: Any) -> (Any, Any, Exception):
        result = None
        detail = None
        issue = None

        try:
            result = self.program.eval(context)
        except Exception as e:
            issue = CelIssue(e)

        return result, detail, issue

class CelEnvWrapper:
    def __init__(self, env: CelEnv):
        self.env = env

    def compile(self, expr: str):
        ast = None
        issue = None
        try:
            expr_pb = self.env.parse(expr)
            checked_expr_pb = self.env.check(expr_pb)
            ast = CelAstWrapper(expr_pb, checked_expr_pb)
        except Exception as e:
            issue = CelIssue(e)

        return ast, issue

    def program(self, ast: CelAstWrapper) -> (CelProgramWrapper, Exception):
        program = None
        issue = None
        try:
            program = CelProgramWrapper(CelProgram(ast.checked, self.env))
        except Exception as e:
            issue = CelIssue(e)

        return program, issue


def _process_env_arg(arg, types, variables, functions, registry):
    """Process a single argument for new_env."""
    if isinstance(arg, Types):
        descriptor: Descriptor = arg.descriptor
        types[arg.descriptor.full_name] = descriptor
        message_class = message_factory.GetMessageClass(descriptor)
        registry.register_message_type(message_class)
    elif isinstance(arg, NativeTypes):
        # Register native Python type using reflection
        native_type = arg.type
        type_name = native_type.__name__
        
        # Register the native type in the registry
        registry.register_native_type(native_type)
        types[type_name] = native_type
    elif isinstance(arg, Variable):
        # Check if variable name is a reserved word
        if arg.name in _reserved_words:
            raise ValueError(f"'{arg.name}' is a reserved word and cannot be used as a variable name")
        
        if isinstance(arg.type, CelType):
            if isinstance(arg.type, ObjectType):
                if types.get(arg.type.name):
                    variables[arg.name] = arg.type.name
                else:
                    pass
            else:
                variables[arg.name] = arg.type.name
                pass
    elif isinstance(arg, Function):
        if arg.name in _reserved_words:
            raise ValueError(f"'{arg.name}' is a reserved word and cannot be used as a function name")

        if isinstance(arg.overload, Overload):
            functions.register(CelFunctionDefinition(name=arg.name,
                                                        arg_types=arg.overload.args,
                                                        result_type=arg.overload.result,
                                                        implementation=arg.overload.get_binding(),
                                                        is_method=False,
                                                        expects_cel_values=False))
        elif isinstance(arg.overload, MemberOverload):
            functions.register(CelFunctionDefinition(name=arg.name,
                                                        arg_types=arg.overload.args,
                                                        result_type=arg.overload.result,
                                                        implementation=arg.overload.get_binding(),
                                                        is_method=True,
                                                        receiver_type=arg.overload.receiver,
                                                        expects_cel_values=False))
        else:
            raise ValueError(f"'{arg.name}' is a reserved word and cannot be used as a function name")

    else:
        raise TypeError(f"'{arg}' is not a function or variable")


def new_env(*args):
    env = None
    issue = None
    try:
        types = {}
        variables = {}
        functions = CelFunctionRegistry()
        registry = TypeRegistry()

        # Process args in two passes:
        # 1. First pass: Process Types and NativeTypes to register all types
        for arg in args:
            if isinstance(arg, (Types, NativeTypes)):
                _process_env_arg(arg, types, variables, functions, registry)
        
        # 2. Second pass: Process Variables and Functions that may reference the registered types
        for arg in args:
            if not isinstance(arg, (Types, NativeTypes)):
                _process_env_arg(arg, types, variables, functions, registry)

        env = CelEnvWrapper(CelEnv(
            variables=variables,
            builtins=functions,
            type_registry=registry,
        ))
    except Exception as exc:
        issue = exc

    return env, issue

class ObjectType(CelType):
    def __init__(self, name: str):
        # Generate a unique ID for this type instance
        type_id = CelType._generate_id()
        # Call parent's __init__ with name and id
        super().__init__(name, type_id)
        # Note: We don't register ObjectType instances in the CelType registry
        # because they are placeholders that will be replaced by actual
        # CelMessageType instances when the message types are registered

class NativeTypes:
    def __init__(self, type: Any):
        self.type = type

class Variable:
    def __init__(self, variable_name: str, kata: CelType):
        self._variable_name = variable_name
        self._type = kata

    @property
    def name(self) -> str:
        return self._variable_name

    @property
    def type(self) -> CelType:
        return self._type

StringType = CEL_STRING
IntType = CEL_INT
UIntType = CEL_UINT
BoolType = CEL_BOOL
FloatType = CEL_FLOAT
DoubleType = CEL_DOUBLE
BytesType = CEL_BYTES
ListType = CEL_LIST
MapType = CEL_MAP
DynType = CEL_DYN

class TypeParamType:
    def __init__(self, name):
        self._name = name

class OverloadOpt:
    def __init__(self, binding):
        self.binding = binding

# MEMO: primitiveな型を指定するほうがハマりづらいのでは？
# CelStringなどはimportを間違えると型比較で失敗することもある
# Anyだと広すぎるのでもう少し制限したい
UnaryOp = Callable[[Any], Any]
BinaryOp = Callable[[Any, Any], Any]
FunctionOp = Callable[[List[Any]], Any]

class Binding(ABC):
    pass

    def _is_valid_return_type(self, return_type):
        origin = get_origin(return_type)
        args = get_args(return_type)

        if return_type in ALLOWED_RETURN_TYPES:
            return True
        elif origin in (list, dict):
            return True
        elif isinstance(return_type, type) and issubclass(return_type, (Message, CelType)):
            return True
        return False


class UnaryBinding(Binding):
    def __init__(self, op: UnaryOp):
        self.op = op

        # 型ヒントを取得
        type_hints = get_type_hints(op)
        sig = inspect.signature(op)

        # 引数の個数チェック
        if len(sig.parameters) != 1:
            raise TypeError("Unary function must take exactly one argument")

        # 引数と返り値の型を取得
        param_name = next(iter(sig.parameters))
        arg_type = type_hints.get(param_name)
        return_type = type_hints.get('return')

        if arg_type is not str or return_type is not str:
            raise TypeError(f"Unary function must be of type (str) -> str, got ({arg_type}) -> {return_type}")

        if not self._is_valid_return_type(return_type):
            raise TypeError(f"Return type {return_type} is not an allowed CEL type")

class BinaryBinding(Binding):
    def __init__(self, op: BinaryOp):
        self.op = op

        # 型ヒントを取得
        type_hints = get_type_hints(op)
        sig = inspect.signature(op)

        # 引数の個数チェック
        if len(sig.parameters) != 2:
            raise TypeError("Binary function must take exactly two arguments")

        # 引数と返り値の型を取得
        param_names = list(sig.parameters.keys())
        if len(param_names) >= 2:
            arg1_type = type_hints.get(param_names[0])
            arg2_type = type_hints.get(param_names[1])
        else:
            arg1_type = None
            arg2_type = None
        return_type = type_hints.get('return')

        # 型チェック（必要に応じて実装）
        # ここでは型チェックをコメントアウトし、任意の型を許可
        # if arg1_type is not str or arg2_type is not str or return_type is not str:
        #     raise TypeError(f"Binary function must be of type (str, str) -> str, got ({arg1_type}, {arg2_type}) -> {return_type}")

        if not self._is_valid_return_type(return_type):
            raise TypeError(f"Return type {return_type} is not an allowed CEL type")

ALLOWED_RETURN_TYPES = (
    int, float, bool, str, bytes, list, dict, type(None)
)
ALLOWED_RETURN_TYPES += (Message, CelType, CEL_ERROR)

class FunctionBinding(Binding):
    def __init__(self, op: FunctionOp):
        # Store the original function that expects List[Any]
        self._original_op = op
        
        # Create a wrapper that converts *args to List[Any]
        def wrapper(*args):
            return op(list(args))
        
        self.op = wrapper

        # 型ヒントを取得
        type_hints = get_type_hints(op)
        sig = inspect.signature(op)

        # 引数の個数チェック
        if len(sig.parameters) != 1:
            raise TypeError("Function must take exactly one argument (List[Any])")

        # 引数と返り値の型を取得
        param_name = next(iter(sig.parameters))
        arg_type = type_hints.get(param_name)
        return_type = type_hints.get('return')

        # Check if the argument type is List[Any] or compatible
        if hasattr(arg_type, '__origin__') and arg_type.__origin__ is list:
            # This is a List type, which is what we expect for FunctionOp
            pass
        else:
            raise TypeError(f"Function must take List[Any] as argument, got {arg_type}")

        if not self._is_valid_return_type(return_type):
            raise TypeError(f"Return type {return_type} is not an allowed CEL type")


class Overload:
    def __init__(self, overload_id: str, args, result, impl : Binding):
        self.overload_id = overload_id
        self.args = args
        self.result = result
        self.impl = impl

    def get_binding(self):
        return self.impl.op

class MemberOverload:
    def __init__(self, overload_id: str, receiver, args, result, impl : OverloadOpt):
        self.receiver = receiver
        self.overload_id = overload_id
        self.args = args
        self.result = result
        self.impl = impl

    def get_binding(self):
        return self.impl.op


class Function:
    def __init__(self, name: str, overload: Overload):
        self.name = name
        self.overload = overload

class Types:
    # descriptor
    def __init__(self, descriptor: Descriptor):
        self.descriptor = descriptor
