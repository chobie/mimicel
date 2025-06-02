import mimicel as cel
import inspect
import sys
from typing import Any, get_type_hints, get_origin, get_args, Union, Dict, Type
import types
from dataclasses import dataclass, field
import traceback  # エラーハンドリングのため

# Python 3.10 以前の場合は typing_extensions からインポート
from typing_extensions import dataclass_transform

# Python 3.11 以降の場合は typing から直接インポート可能
# from typing import dataclass_transform

# --- 0. 設定値を保持するデータクラス (変更なし) ---
@dataclass
class CelConfigData:
    model_name: str
    rules: Dict[str, str]
    fail_fast: bool = False

    def __post_init__(self):
        if not isinstance(self.model_name, str) or not self.model_name:
            raise ValueError("CelConfigData.model_name は空でない文字列である必要があります。")
        if not isinstance(self.rules, dict):
            raise ValueError("CelConfigData.rules は辞書である必要があります。")


# --- 1. 汎用バリデーション関数 (変更なし) ---
def validate_instance_with_cel(
        instance_to_validate: object, model_name_in_cel: str, rules: dict[str, str], fail_fast: bool = False
) -> tuple[bool, dict[str, str]]:
    env, err = cel.new_env(cel.Variable(model_name_in_cel, cel.DynType))
    if err is not None: raise RuntimeError(f"CEL環境の作成に失敗しました: {err}")
    validation_errors: dict[str, str] = {};
    all_valid = True
    for rule_name, rule_expr in rules.items():
        ast, issues = env.compile(rule_expr)
        if issues is not None and issues.err() is not None:
            validation_errors[rule_name] = f"コンパイルエラー: {issues.err()}";
            all_valid = False
            if fail_fast: break; continue
        program, prog_err = env.program(ast)
        if prog_err is not None:
            validation_errors[rule_name] = f"プログラム作成エラー: {prog_err}";
            all_valid = False
            if fail_fast: break; continue
        activation = {model_name_in_cel: instance_to_validate}
        eval_result, _, eval_err = program.eval(activation)
        if eval_err is not None:
            validation_errors[rule_name] = f"評価時エラー: {eval_err}";
            all_valid = False
            if fail_fast: break; continue
        if not isinstance(eval_result, bool):
            validation_errors[rule_name] = (f"検証式の戻り値がブール値ではありません。"
                                            f"期待値: bool, 実際値: {type(eval_result).__name__} (値: {eval_result})")
            all_valid = False;
            if fail_fast: break; continue
        if eval_result is False:
            validation_errors[rule_name] = f"検証ルール '{rule_expr}' に違反しました。";
            all_valid = False
            if fail_fast: break
    return all_valid, validation_errors


# --- 2. カスタム例外クラス (変更なし) ---
class CelValidationError(Exception):
    def __init__(self, errors: dict[str, str], model_instance):
        self.errors = errors;
        self.model_instance = model_instance
        error_messages = [f"'{rule}': {msg}" for rule, msg in errors.items()]
        super().__init__(f"{type(model_instance).__name__} の検証に失敗しました:\n - " + "\n - ".join(error_messages))


# --- 3. メタクラス (generated_init_impl を修正) ---
@dataclass_transform()
class ValidatedCelModelMeta(type):
    def __new__(mcs, name: str, bases: tuple[type, ...], attrs: dict[str, Any]):
        if name == 'ValidatedCelModel' and not bases:
            return super().__new__(mcs, name, bases, attrs)
        _annotations: dict[str, Any] = {}
        processed_mro_classes = set()
        for base_cls in bases:
            if not hasattr(base_cls, '__mro__'): continue
            for mro_cls in reversed(base_cls.__mro__):
                if mro_cls is object or mro_cls in processed_mro_classes: continue
                if hasattr(mro_cls, '__annotations__'):
                    try:
                        module = sys.modules.get(mro_cls.__module__)
                        global_ns = module.__dict__ if module else None
                        _annotations.update(get_type_hints(mro_cls, globalns=global_ns, localns=None))
                    except Exception:
                        _annotations.update(mro_cls.__annotations__)
                processed_mro_classes.add(mro_cls)
        if '__annotations__' in attrs:
            current_class_raw_annotations = attrs['__annotations__']
            try:
                module_name = attrs.get('__module__')
                module = sys.modules.get(module_name)
                global_ns = module.__dict__ if module else None
                temp_dummy_cls = type(name, (),
                                      {'__annotations__': current_class_raw_annotations, '__module__': module_name})
                _annotations.update(get_type_hints(temp_dummy_cls, globalns=global_ns, localns=None))
            except Exception:
                _annotations.update(current_class_raw_annotations)
        params = [inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD)];
        field_names = []
        for field_name, field_type in _annotations.items():
            if field_name.startswith('_') or field_name == 'cel_config': continue
            field_names.append(field_name)
            parameter_default = attrs.get(field_name, inspect.Parameter.empty)
            if parameter_default is inspect.Parameter.empty: parameter_default = None
            params.append(inspect.Parameter(name=field_name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                            default=parameter_default, annotation=field_type))

        # generated_init_impl の修正: __post_init__ 呼び出しを追加
        def generated_init_impl(self_param, *args_param, **kwargs_param):
            try:
                bound_args = generated_init_impl.__signature__.bind(self_param, *args_param, **kwargs_param)
            except TypeError as e:
                class_name_for_error = type(self_param).__name__
                sig_for_error_msg_obj = getattr(generated_init_impl, '__signature__', '(unknown signature)')
                raise TypeError(f"{class_name_for_error}.__init__{sig_for_error_msg_obj} "
                                f"への引数のバインドに失敗しました: {e}") from e
            bound_args.apply_defaults()
            for arg_name, value in bound_args.arguments.items():
                if arg_name == 'self': continue
                setattr(self_param, arg_name, value)

            cls_of_instance = type(self_param)
            cel_config_instance = getattr(cls_of_instance, 'cel_config', None)
            should_validate = False
            if isinstance(cel_config_instance, CelConfigData):
                should_validate = True
            else:
                class_display_name = cls_of_instance.__name__
                if class_display_name != 'ValidatedCelModel' and not class_display_name.startswith('_'):
                    print(f"警告: {class_display_name} に 'cel_config' (CelConfigDataインスタンス) が"
                          "正しく定義されていないため、バリデーションはスキップされます。")
            try:
                if should_validate and hasattr(self_param, 'validate') and callable(self_param.validate):
                    self_param.validate()  # バリデーション実行 (CelValidationError を送出する可能性)

                # バリデーションが成功した (またはスキップされた) 場合に __post_init__ を呼び出す
                if hasattr(self_param, '__post_init__') and callable(self_param.__post_init__):
                    self_param.__post_init__()

            except CelValidationError:  # バリデーションエラーはそのまま再送出 (__post_init__ は呼ばれない)
                raise
            # __post_init__ 内で発生した他の例外はここでキャッチせず、呼び出し元に伝播させる
            # (ただし、CelValidationErrorと区別してロギングしたい場合は別途対応)

        init_sig = inspect.Signature(parameters=params)
        generated_init_impl.__signature__ = init_sig;
        generated_init_impl.__name__ = "__init__"
        generated_init_impl.__qualname__ = f"{name}.__init__"
        attrs['__init__'] = generated_init_impl;
        attrs['_field_names_'] = field_names
        return super().__new__(mcs, name, bases, attrs)


# --- 4. ベースモデルクラス ( __post_init__ を追加) ---
@dataclass_transform()
class ValidatedCelModel(metaclass=ValidatedCelModelMeta):
    def __post_init__(self):
        """
        インスタンスのフィールド初期化とCELバリデーションが完了した後に呼び出されるフック。
        サブクラスはこのメソッドをオーバーライドして、追加の初期化ロジックや
        副作用を伴う処理を記述できます。
        このベースクラスの実装では何もしません。
        """
        pass

    def validate(self):
        cls = type(self)
        config_instance = getattr(cls, 'cel_config', None)
        if not isinstance(config_instance, CelConfigData):
            default_model_name = cls.__name__.lower()
            print(f"情報: {cls.__name__} に cel_config (CelConfigDataのインスタンス) が正しく定義されていません。"
                  f"model_name='{default_model_name}', rules={{}} を使用します。")
            config_instance = CelConfigData(model_name=default_model_name, rules={})
        model_name = config_instance.model_name;
        rules = config_instance.rules;
        fail_fast = config_instance.fail_fast
        if not rules and cls.__name__ != 'Order':  # Orderはテスト用にrulesが空のことがある
            print(f"情報: {cls.__name__} の cel_config の 'rules' が空です。実質的なバリデーションは行われません。")
        is_valid, errors = validate_instance_with_cel(
            instance_to_validate=self, model_name_in_cel=model_name, rules=rules, fail_fast=fail_fast
        )
        if not is_valid: raise CelValidationError(errors, self)

    def __repr__(self) -> str:
        if hasattr(self, '_field_names_') and self._field_names_:
            fields_repr = ", ".join(
                f"{name}={getattr(self, name)!r}" for name in self._field_names_ if hasattr(self, name))
            return f"<{type(self).__name__}({fields_repr})>"
        return super().__repr__()


# --- 5. サブクラスの例 ( __post_init__ を使用する例を追加) ---
class UserProfile(ValidatedCelModel):
    name: str
    age: int
    email: str | None
    is_active: bool = True
    greeting: str | None = None

    cel_config = CelConfigData(model_name="user", rules={
        "name_is_required": "user.name != null && user.name.size() > 0",
        "name_max_length_is_20": "user.name == null || user.name.size() <= 20",
        "age_is_required_and_adult": "user.age != null && user.age >= 18",
        "email_format_if_provided": "user.email == null || user.email.matches(r'^[^@]+@[^@.]+\\.[^@.]+')"
    }, fail_fast=True)

    def __post_init__(self):
        print(f"UserProfile ({self.name}): __post_init__ 呼び出し。")
        if self.is_active:
            self.greeting = f"Hello, {self.name}!"
        else:
            self.greeting = f"Goodbye, {self.name}."
        print(f"UserProfile ({self.name}): greeting を '{self.greeting}' に設定。")


class Product(ValidatedCelModel):
    product_id: str
    name: str
    price: float
    tags: list[str] | None
    stock: int = 0
    description: str | None = None  # __post_init__で設定する例

    cel_config = CelConfigData(model_name="item", rules={
        "product_id_required": "item.product_id != null && item.product_id.size() > 0",
        "name_required": "item.name != null && item.name.size() > 0",
        "price_required_and_positive": "item.price != null && item.price > 0.0",
        "stock_non_negative": "item.stock != null && item.stock >= 0",
    })

    def __post_init__(self):
        self.description = f"{self.name} (ID: {self.product_id}) - Price: ${self.price:.2f}"
        if self.tags:
            self.description += f" Tags: {', '.join(self.tags)}"


class Order(ValidatedCelModel):
    order_id: str
    amount: float
    # cel_config は未定義 (フォールバックテスト用)
    # __post_init__ も未定義 (ベースクラスのものが呼ばれるが何もしない)


# --- 6. 使用例 ( __post_init__ の動作確認を追加) ---
if __name__ == '__main__':
    print("--- UserProfile のテスト (with __post_init__) ---")
    try:
        user1 = UserProfile(name="Alice", age=30, email="alice@example.com", is_active=True)
        print(f"作成成功 (user1): {user1}, Greeting: {user1.greeting}")
        assert user1.greeting == "Hello, Alice!"

        user2 = UserProfile(name="Bob", age=25, is_active=False)
        print(f"作成成功 (user2): {user2}, Greeting: {user2.greeting}")
        assert user2.greeting == "Goodbye, Bob."

        print("\n--- UserProfile age省略 (バリデーションエラー期待, __post_init__ は呼ばれない) ---")
        try:
            user_no_age = UserProfile(name="NoAgeWillFail", is_active=False)  # age=None
            print(f"作成成功 (これは表示されないはず): {user_no_age}")
        except CelValidationError as e:
            print(f"予期したエラー (UserProfile - age省略): {e}")

    except CelValidationError as e:
        print(f"エラー: {e}")
    except Exception as e:
        print(f"予期せぬエラー (UserProfile作成): {e}"); import traceback; traceback.print_exc()

    print("\n--- Product のテスト (with __post_init__) ---")
    try:
        prod1 = Product(product_id="P001", name="Laptop X", price=1500.00, stock=10, tags=["tech", "electronics"])
        print(f"作成成功 (prod1): {prod1}, Description: {prod1.description}")
        assert prod1.description == "Laptop X (ID: P001) - Price: $1500.00 Tags: tech, electronics"

        prod2 = Product(product_id="P002", name="T-Shirt", price=25.0)  # stock=0, tags=None
        print(f"作成成功 (prod2): {prod2}, Description: {prod2.description}")
        assert prod2.description == "T-Shirt (ID: P002) - Price: $25.00"

        print("\n--- Product 複数エラー (バリデーションエラー期待, __post_init__ は呼ばれない) ---")
        try:
            invalid_product = Product(stock=-5)  # name, product_id, priceがNone, stockが-5
            print(f"作成成功 (これは表示されないはず): {invalid_product}")
        except CelValidationError as e:
            print(f"予期したエラー (Product - 複数フィールド省略/不正): {e}")
    except CelValidationError as e:
        print(f"エラー: {e}")
    except Exception as e:
        print(f"予期せぬエラー (Product作成): {e}"); import traceback; traceback.print_exc()

    print("\n--- cel_config なしのクラスのテスト (Order) ---")
    try:
        order = Order(order_id="O123", amount=99.99)
        print(f"作成成功 (Order): {order}")  # validate内で情報メッセージ
        # Orderには__post_init__がないので、ValidatedCelModelの空の__post_init__が呼ばれる(何も起こらない)
    except Exception as e:
        print(f"エラー (Order作成時): {e}")
