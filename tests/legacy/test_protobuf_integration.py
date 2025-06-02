# tests/test_protobuf_integration.py (Protobuf生成コードを使用するように修正)
# protoc --mypy_out=. --python_out=. test_messages.proto

import pytest

# --- 必要なモジュールをインポート ---
from mimicel.api import CelEnv, CELCompileError, CelProgram
from mimicel.cel_values import CelStruct, CelString, CelInt
from mimicel.type_registry import TypeRegistry

# --- 生成されたProtobufモジュールをインポート ---
# "protoc --python_out=. test_messages.proto" で生成されたファイルをインポート
# ファイルがテストディレクトリのサブディレクトリにある場合は、パスを調整してください。
try:
    import test_messages_pb2  # 同じディレクトリにある場合
    # from .. import test_messages_pb2 # 親ディレクトリの test_messages_pb2 を参照する場合など
except ImportError:
    # プロジェクトの構造に合わせて適切なインポートパスを指定してください
    # 例: from generated_protos import test_messages_pb2
    # pytestの実行カレントディレクトリからの相対パスで解決されることもあります。
    # pytest.skip("Generated protobuf module 'test_messages_pb2.py' not found.", allow_module_level=True)
    # ここでは、テスト実行時に見つからない場合はエラーとする
    raise ImportError("Could not import generated protobuf module 'test_messages_pb2.py'. "
                      "Please ensure it's generated and in the Python path.")


class TestProtobufIntegration:

    @pytest.fixture
    def type_registry(self) -> TypeRegistry:
        """テスト用のTypeRegistryをセットアップします。"""
        registry = TypeRegistry()
        # 生成されたProtobufメッセージクラスを登録
        registry.register_message_type(test_messages_pb2.SimpleTestMessage)
        registry.register_message_type(test_messages_pb2.NestedTestMessage)
        return registry

    @pytest.fixture
    def cel_env(self, type_registry: TypeRegistry) -> CelEnv:
        """テスト用のCELEnvをセットアップします。"""
        return CelEnv(type_registry=type_registry)

    def test_message_construction_and_field_access(self, cel_env: CelEnv):
        """メッセージ構築とフィールドアクセスの基本的なテスト"""
        expr = 'testproto.SimpleTestMessage{string_field: "hello", int_field: 123, bool_field: true}'
        prog = cel_env.compile(expr)
        result_msg_obj = prog.eval()  # 評価結果は Python の Protobuf オブジェクトのはず

        assert isinstance(result_msg_obj, test_messages_pb2.SimpleTestMessage)
        assert result_msg_obj.string_field == "hello"
        assert result_msg_obj.int_field == 123
        assert result_msg_obj.bool_field is True

        # フィールドアクセス式の評価
        env_with_var = CelEnv(
            variables={"msg_var": "testproto.SimpleTestMessage"},  # 型名を文字列で指定
            type_registry=cel_env.type_registry
        )
        prog_field_access = env_with_var.compile("msg_var.int_field")

        # 評価時には実際のメッセージインスタンスを渡す
        # SimpleTestMessage は test_messages_pb2 からインポートしたもの
        message_instance = test_messages_pb2.SimpleTestMessage(string_field="dummy", int_field=789)
        result_field_access = prog_field_access.eval({"msg_var": message_instance})
        assert result_field_access == 789

    def test_repeated_field_construction_and_access(self, cel_env: CelEnv):
        """繰り返しフィールドの構築とアクセスのテスト"""
        expr = 'testproto.SimpleTestMessage{repeated_string_field: ["a", "b", "c"]}'
        prog = cel_env.compile(expr)
        result_msg = prog.eval()

        assert isinstance(result_msg, test_messages_pb2.SimpleTestMessage)
        assert list(result_msg.repeated_string_field) == ["a", "b", "c"]

        env_with_var = CelEnv(
            variables={"msg_var": "testproto.SimpleTestMessage"},
            type_registry=cel_env.type_registry
        )
        prog_access_repeated = env_with_var.compile("msg_var.repeated_string_field[1]")
        result_access_repeated = prog_access_repeated.eval({"msg_var": result_msg})
        assert result_access_repeated == "b"

    def test_nested_message_construction_and_access(self, cel_env: CelEnv):
        """ネストしたメッセージの構築とアクセスのテスト"""
        expr = """
            testproto.NestedTestMessage{
                simple_message: testproto.SimpleTestMessage{
                    string_field: "nested_hello",
                    int_field: 456
                },
                description: "this is nested"
            }
        """
        prog = cel_env.compile(expr)
        result_nested_msg = prog.eval()

        assert isinstance(result_nested_msg, test_messages_pb2.NestedTestMessage)
        assert result_nested_msg.description == "this is nested"
        assert isinstance(result_nested_msg.simple_message, test_messages_pb2.SimpleTestMessage)
        assert result_nested_msg.simple_message.string_field == "nested_hello"
        assert result_nested_msg.simple_message.int_field == 456

        env_with_var = CelEnv(
            variables={"nested_var": "testproto.NestedTestMessage"},
            type_registry=cel_env.type_registry
        )
        prog_access_nested = env_with_var.compile("nested_var.simple_message.int_field")
        result_access_nested = prog_access_nested.eval({"nested_var": result_nested_msg})
        assert result_access_nested == 456

    def test_has_macro_on_message_field(self, cel_env: CelEnv):
        """has()マクロの基本的なテスト (メッセージフィールド)"""
        # SimpleTestMessage は test_messages_pb2 からインポートしたものを使用
        msg_instance_full = test_messages_pb2.SimpleTestMessage(string_field="test", int_field=1, bool_field=True)
        msg_instance_partial_no_int = test_messages_pb2.SimpleTestMessage(string_field="test",
                                                                          bool_field=False)  # int_field はデフォルト(0)
        msg_instance_empty = test_messages_pb2.SimpleTestMessage()

        env_with_var = CelEnv(
            variables={"msg": "testproto.SimpleTestMessage"},
            type_registry=cel_env.type_registry
        )

        prog_has_str = env_with_var.compile("has(msg.string_field)")
        prog_has_int = env_with_var.compile("has(msg.int_field)")
        prog_has_bool = env_with_var.compile("has(msg.bool_field)")

        # string_field: 値が設定されていれば has() は true (空文字列はデフォルト値なのでfalse)
        assert prog_has_str.eval({"msg": msg_instance_full}) is True
        assert prog_has_str.eval({"msg": test_messages_pb2.SimpleTestMessage(string_field="")}) is False  # 空文字列はデフォルト

        # int_field: proto3ではプリミティブ型がデフォルト値(0)の場合、has()はfalseを返す
        assert prog_has_int.eval({"msg": msg_instance_full}) is True  # 1 はデフォルトではない
        assert prog_has_int.eval({"msg": msg_instance_partial_no_int}) is False  # デフォルト値0
        assert prog_has_int.eval({"msg": test_messages_pb2.SimpleTestMessage(int_field=0)}) is False  # 明示的に0でもデフォルト

        # bool_field: proto3ではプリミティブ型がデフォルト値(false)の場合、has()はfalseを返す
        assert prog_has_bool.eval({"msg": msg_instance_full}) is True  # true はデフォルトではない
        assert prog_has_bool.eval({"msg": msg_instance_partial_no_int}) is False  # bool_field=false はデフォルト
        assert prog_has_bool.eval(
            {"msg": test_messages_pb2.SimpleTestMessage(bool_field=False)}) is False  # 明示的にfalseでもデフォルト

        # 存在しないフィールド (型チェックでエラーになるべき)
        with pytest.raises(CELCompileError, match="Unknown field 'non_existent_field'"):
            env_with_var.compile("has(msg.non_existent_field)")

    def test_type_check_message_construction_errors(self, cel_env: CelEnv):
        """メッセージ構築時の型チェックエラーのテスト"""
        with pytest.raises(CELCompileError, match="Unknown field 'wrong_field'"):
            cel_env.compile('testproto.SimpleTestMessage{wrong_field: "error"}')
        with pytest.raises(CELCompileError, match="Type mismatch for field 'int_field'"):
            cel_env.compile('testproto.SimpleTestMessage{int_field: "not_an_int"}')
        with pytest.raises(CELCompileError, match="Type mismatch for field 'repeated_string_field'"):
            cel_env.compile('testproto.SimpleTestMessage{repeated_string_field: "not_a_list"}')

    def test_type_check_field_access_errors(self, cel_env: CelEnv):
        """フィールドアクセス時の型チェックエラーのテスト"""
        env_with_var = CelEnv(
            variables={"msg": "testproto.SimpleTestMessage"},
            type_registry=cel_env.type_registry
        )
        with pytest.raises(CELCompileError, match="Unknown field 'non_existent'"):
            env_with_var.compile("msg.non_existent")
        with pytest.raises(CELCompileError, match="cannot compare 'string' and 'int'"):
            env_with_var.compile("msg.string_field > 0")


    def test_struct_equality(self, cel_env: CelEnv):
        struct1 = CelStruct("testproto.EqualityMessage", fields={
            "name": CelString("Alice"),
            "age": CelInt(30)
        })
        struct2 = CelStruct("testproto.EqualityMessage", fields={
            "name": CelString("Alice"),
            "age": CelInt(30)
        })
        struct3 = CelStruct("testproto.EqualityMessage", fields={
            "name": CelString("Bob"),
            "age": CelInt(30)
        })

        assert struct1 == struct2
        assert struct1 != struct3
