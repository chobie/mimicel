import mimicel as cel
from typing import List

class Person:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

class Address:
    def __init__(self, street: str, city: str, country: str):
        self.street = street
        self.city = city
        self.country = country

class Company:
    def __init__(self, name: str, employees: List[Person]):
        self.name = name
        self.employees = employees
        self.employee_count = len(employees)

def hello_str_str(arg: str) -> str:
    return "Hello " + arg

def main():
    """Main function demonstrating native types support."""
    # Create test data
    person1 = Person("John Doe", 30)
    person2 = Person("Jane Smith", 25)
    person3 = Person("Bob Johnson", 35)
    
    address = Address("123 Main St", "Tokyo", "Japan")
    company = Company("Tech Corp", [person1, person2, person3])

    # Note: NativeTypes must be registered before any Variable that references it
    env, err = cel.new_env(
        cel.NativeTypes(Person),  # Register Person type first
        cel.NativeTypes(Address),
        cel.NativeTypes(Company),
        cel.Variable("person", cel.ObjectType("Person")),
        cel.Variable("address", cel.ObjectType("Address")),
        cel.Variable("company", cel.ObjectType("Company")),
        cel.Function("hello",
            cel.Overload("hello_str_str",
                [cel.StringType],
                cel.StringType,
                cel.UnaryBinding(hello_str_str))))

    if err is not None:
        raise err

    # Test 1: Basic field access
    print("Test 1: Basic field access")
    ast1, issue1 = env.compile("person.name + ' is ' + string(person.age) + ' years old'")
    if issue1 is not None:
        raise issue1.err()
    
    program1, err1 = env.program(ast1)
    if err1 is not None:
        raise err1
    
    out1, _, err1 = program1.eval({
        'person': person1,
        'address': address,
        'company': company
    })
    if err1 is not None:
        raise err1.err()
    print(f"  Result: {out1}")

    # Test 2: Complex field access
    print("\nTest 2: Complex field access")
    ast2, issue2 = env.compile("'Company ' + company.name + ' has ' + string(company.employee_count) + ' employees'")
    if issue2 is not None:
        raise issue2.err()
    
    program2, err2 = env.program(ast2)
    if err2 is not None:
        raise err2
    
    out2, _, err2 = program2.eval({
        'person': person1,
        'address': address,
        'company': company
    })
    if err2 is not None:
        raise err2.err()
    print(f"  Result: {out2}")

    # Test 3: Address formatting
    print("\nTest 3: Address formatting")
    ast3, issue3 = env.compile("address.street + ', ' + address.city + ', ' + address.country")
    if issue3 is not None:
        raise issue3.err()
    
    program3, err3 = env.program(ast3)
    if err3 is not None:
        raise err3
    
    out3, _, err3 = program3.eval({
        'person': person1,
        'address': address,
        'company': company
    })
    if err3 is not None:
        raise err3.err()
    print(f"  Result: {out3}")

    # Test 4: Using function with native type field
    print("\nTest 4: Using function with native type field")
    ast4, issue4 = env.compile("hello(person.name)")
    if issue4 is not None:
        raise issue4.err()
    
    program4, err4 = env.program(ast4)
    if err4 is not None:
        raise err4
    
    out4, _, err4 = program4.eval({
        'person': person1,
        'address': address,
        'company': company
    })
    if err4 is not None:
        raise err4.err()
    print(f"  Result: {out4}")


if __name__ == '__main__':
    main()