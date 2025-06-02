# cel_library.py
from typing import List, TYPE_CHECKING
from .cel_values.cel_types import CelFunctionDefinition, CelFunctionRegistry

if TYPE_CHECKING:
    from .api import CelEnv # 前方参照/型ヒントのため


class CelLibrary:
    """
    関連するCEL関数定義群をカプセル化するライブラリクラス。
    """
    def __init__(self, name: str):
        self.name: str = name
        self._function_definitions: List[CelFunctionDefinition] = []
        # 将来的には型定義やマクロ定義もここに追加可能
        # self.type_provider_configs: List[Any] = []
        # self.macro_configs: List[Any] = []


    def add_function(self, func_def: CelFunctionDefinition) -> None:
        """ライブラリに関数定義を追加します。"""
        self._function_definitions.append(func_def)

    def get_functions(self) -> List[CelFunctionDefinition]:
        """このライブラリに含まれる関数定義のリストを返します（コピー）。"""
        return list(self._function_definitions)

    def register_functions_to(self, registry: CelFunctionRegistry) -> None:
        """
        このライブラリが保持する全ての関数定義を、
        指定されたCelFunctionRegistryに登録します。
        """
        for func_def in self._function_definitions:
            registry.register(func_def)

    # 将来的には register_types_to(type_registry), register_macros_to(macro_registry) なども