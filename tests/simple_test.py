import math

def test_math_operations():
    assert 2 + 2 == 4
    assert 10 - 5 == 5
    assert 3 * 3 == 9
    assert 8 / 2 == 4

def test_string_operations():
    text = "Hello, World!"
    
    assert len(text) == 13
    assert text.startswith("Hello")
    assert text.endswith("World!")
    assert text.upper() == "HELLO, WORLD!"

def test_math_functions():
    assert math.sqrt(16) == 4
    assert math.pow(2, 3) == 8
    assert math.pi == 3.141592653589793
    assert math.factorial(5) == 120
