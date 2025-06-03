import pytest
from mimicel import new_env, Variable, Function, Overload, UnaryBinding, StringType


def test_reserved_word_in_variable_name():
    """Test that using reserved words as variable names raises an error"""
    reserved_words = [
        "false", "in", "null", "true",
        "as", "break", "const", "continue", "else", "for", "function", "if", 
        "import", "let", "loop", "package", "namespace", "return", "var", "void", "while"
    ]
    
    for reserved in reserved_words:
        with pytest.raises(ValueError, match=f"'{reserved}' is a reserved word"):
            env, issue = new_env(
                Variable(reserved, StringType)
            )
            assert issue is None


def test_reserved_word_in_function_name():
    """Test that using reserved words as function names raises an error"""
    reserved_words = ["if", "for", "while", "function", "return"]
    
    def dummy_func(x: str) -> str:
        return x
    
    for reserved in reserved_words:
        with pytest.raises(ValueError, match=f"'{reserved}' is a reserved word"):
            env, issue = new_env(
                Function(reserved, Overload(
                    f"{reserved}_overload",
                    [StringType],
                    StringType,
                    UnaryBinding(dummy_func)
                ))
            )
            assert issue is None


def test_non_reserved_words_allowed():
    """Test that non-reserved words are allowed as variable and function names"""
    def my_func(x: str) -> str:
        return x.upper()
    
    # These should work without errors
    env, issue = new_env(
        Variable("my_var", StringType),
        Variable("user_input", StringType),
        Function("my_function", Overload(
            "my_function_overload",
            [StringType],
            StringType,
            UnaryBinding(my_func)
        ))
    )
    assert issue is None
    assert env is not None


def test_compile_with_reserved_word_variable():
    """Test that expressions with reserved word variables fail during compilation"""
    env, issue = new_env()
    assert issue is None
    
    # This should fail during compilation
    ast, compile_issue = env.compile("let + 5")
    assert compile_issue is not None
    assert "reserved" in str(compile_issue.err()).lower()


def test_partial_reserved_word_allowed():
    """Test that names containing reserved words as substrings are allowed"""
    def my_func(x: str) -> str:
        return x
    
    # These should be allowed
    env, issue = new_env(
        Variable("if_condition", StringType),  # contains "if"
        Variable("for_loop", StringType),      # contains "for"
        Variable("return_value", StringType),  # contains "return"
        Function("format", Overload(           # contains "for"
            "format_overload",
            [StringType],
            StringType,
            UnaryBinding(my_func)
        ))
    )
    assert issue is None
    assert env is not None