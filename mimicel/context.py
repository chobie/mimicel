# context.py
from typing import Callable, Union, Any, List, Optional, Dict, TYPE_CHECKING

from cel.expr import checked_pb2
from .cel_values.cel_types import (
    CelFunctionDefinition,
    CelFunctionRegistry,
    CEL_DYN
)
from .cel_values import wrap_value
from .cel_library import CelLibrary

if TYPE_CHECKING:
    from .api import CelEnv


class EvalContext:
    def __init__(self,
                 base: Optional[Dict[str, Any]] = None,
                 env: Optional['CelEnv'] = None,
                 builtins: Optional[Union[Dict[str, Callable[..., Any]], CelFunctionRegistry, CelLibrary]] = None,
                 checked_expr: checked_pb2.CheckedExpr = None
                 ):
        self.checked_expr = checked_expr
        self.scopes: List[Dict[str, Any]] = []
        if base:
            self.scopes.append(base.copy())
        else:
            self.scopes.append({})

        self.env = env

        # 関数レジストリの初期化 (元のロジックを維持しつつ、self.env を利用)
        self.function_registry: CelFunctionRegistry = CelFunctionRegistry()
        if self.env and hasattr(self.env, 'builtins') and \
                isinstance(self.env.builtins, CelFunctionRegistry):
            self.function_registry = self.env.builtins.copy()
        # EvalContext に直接渡された builtins の処理 (マージまたは上書き)
        if builtins is not None:
            if isinstance(builtins, CelLibrary):
                builtins.register_functions_to(self.function_registry)
            elif isinstance(builtins, CelFunctionRegistry):
                # env.builtins と builtins が異なるインスタンスの場合、マージする
                if not (self.env and self.env.builtins == builtins):
                    for func_name_key in list(builtins._functions.keys()):
                        overloads_list = builtins._functions[func_name_key]
                        for fn_def in overloads_list:
                            self.function_registry.register(fn_def)
            elif isinstance(builtins, dict):
                for name, impl in builtins.items():
                    if callable(impl):
                        self.function_registry.register(CelFunctionDefinition(
                            name=name, arg_types=[CEL_DYN], result_type=CEL_DYN, implementation=impl
                        ))
            # 型エラーチェックは CELEnv の __init__ で行うためここでは省略 (元のコードにもなかった)

        # base スコープ内の呼び出し可能オブジェクトを関数として登録するロジック (元のまま)
        if base:
            self._register_callables_from_scope(base)

    def _register_callables_from_scope(self, source_dict: dict):
        # (元のコードのまま)
        for name, impl in source_dict.items():
            if callable(impl) and not isinstance(impl, CelFunctionDefinition):
                existing_overloads = self.function_registry._functions.get(name)
                if not existing_overloads:  # 既にCelFunctionDefinitionとして登録されていなければ
                    try:
                        self.function_registry.register(CelFunctionDefinition(
                            name=name, arg_types=[CEL_DYN], result_type=CEL_DYN, implementation=impl,
                        ))
                    except Exception as e:
                        # ここでのエラーは警告に留めるか、より厳格に処理するか
                        print(f"Warning: Could not auto-register callable '{name}' from scope: {e}")

    def get(self, name: str, arg_types_str_list: Optional[List[str]] = None) -> Any:
        # デバッグ用: どの名前とコンテナで呼ばれているか確認
        # print(f"EvalContext.get(name='{name}', container='{self.env.container_name if self.env else None}')")

        # 優先順位1: (コンテナが指定されている場合) container_name + "." + name で解決を試みる
        # この検索は、主にトップレベルのバインディング (self.scopes[0]) に対して行うべき。
        # なぜなら、コンテナ修飾された名前は通常、グローバルな名前空間や入力変数セットで定義されるため。
        if self.env and self.env.container_name:
            qualified_name = f"{self.env.container_name}.{name}"
            # self.scopes[0] が存在し、その中に qualified_name があればそれを返す
            if self.scopes and qualified_name in self.scopes[0]:
                # print(f"  Found '{qualified_name}' in top scope (bindings).")
                return wrap_value(self.scopes[0][qualified_name])
            # もし、コンテナ内の変数がネストしたスコープ（let束縛など）で定義されるシナリオを
            # サポートする場合、ここでの検索ロジックを拡張する必要があるが、
            # 通常のCELのコンテナはトップレベルの名前空間を指す。

        # 優先順位2: name そのもので現在のスコープ階層を逆順に探す
        #   - 通常の識別子 (例: "y" で container がない場合)
        #   - ドットを含むトップレベル変数名 (例: "x.y" で container がない場合)
        #     (これは eval_pb.py の handle_select_expr から "x.y" という name で呼ばれるか、
        #      またはパーサーが Ident("x.y") を生成する場合に該当)
        for scope in reversed(self.scopes):
            if name in scope:
                # print(f"  Found '{name}' in a scope.")
                return wrap_value(scope[name])

        # どのスコープにも見つからなかった場合
        current_container_for_msg = self.env.container_name if self.env and self.env.container_name else ""
        container_info = f" (in container '{current_container_for_msg}')"
        raise NameError(f"undeclared reference to '{name}' (in container '{container_info}')")

    def set(self, name: str, value: Any):
        self.scopes[-1][name] = value

    def push(self):
        self.scopes.append({})

    def pop(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
        else:
            self.scopes[-1].clear()

    def copy(self) -> 'EvalContext':
        new_ctx = EvalContext(base=self.scopes[0].copy() if self.scopes else None, env=self.env)
        new_ctx.function_registry = self.function_registry.copy()
        if len(self.scopes) > 1:
            new_ctx.scopes.extend([s.copy() for s in self.scopes[1:]])
        return new_ctx
