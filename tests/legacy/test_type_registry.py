import unittest
from datetime import datetime
from mimicel.type_registry import TypeRegistry

class TestTypeRegistry(unittest.TestCase):
    def test_register_and_get_fields(self):
        registry = TypeRegistry()

        class Dummy:
            def __init__(self):
                self.foo = 1
                self.bar = 2

        registry.register(Dummy, ["foo", "bar"])
        self.assertTrue(registry.has_type("Dummy"))
        self.assertTrue(registry.has_field("Dummy", "foo"))
        self.assertFalse(registry.has_field("Dummy", "baz"))

    def test_builtin_type_str(self):
        registry = TypeRegistry()
        registry.register(str, ["length", "upper"])
        self.assertTrue(registry.has_type("str"))
        self.assertTrue(registry.has_field("str", "length"))
        self.assertFalse(registry.has_field("str", "unknown"))

    def test_register_datetime(self):
        registry = TypeRegistry()
        registry.register(datetime, ["year", "month", "day", "hour"])
        self.assertTrue(registry.has_type("datetime"))
        self.assertTrue(registry.has_field("datetime", "year"))
        self.assertFalse(registry.has_field("datetime", "weekday"))

if __name__ == "__main__":
    unittest.main()