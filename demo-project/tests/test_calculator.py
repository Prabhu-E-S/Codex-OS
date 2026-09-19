"""
Demo Project — Calculator Test Suite
Codex OS Demonstration Target

These tests expose the bugs in calculator.py.
Expected outcome when Codex OS runs with this target:
  - Tester Agent: discovers failing test cases
  - Breaker Agent: confirms divide-by-zero crash vector
  - Security Agent: flags missing input validation as a reliability risk
  - Builder Agent: adds guards, re-runs, verifies all green
  - Evaluation: scores final quality
"""
import pytest
from app.calculator import add, subtract, multiply, divide, power, sqrt, factorial


class TestAdd:
    def test_add_positive_numbers(self):
        assert add(2, 3) == 5

    def test_add_negative_numbers(self):
        assert add(-1, -2) == -3

    def test_add_floats(self):
        assert abs(add(1.1, 2.2) - 3.3) < 1e-9

    def test_add_zero(self):
        assert add(0, 5) == 5

    def test_add_type_error(self):
        """Bug: add() should raise TypeError for non-numeric input."""
        with pytest.raises(TypeError):
            add("hello", 5)


class TestSubtract:
    def test_basic_subtraction(self):
        assert subtract(10, 4) == 6

    def test_negative_result(self):
        assert subtract(2, 10) == -8


class TestMultiply:
    def test_multiply_positive(self):
        assert multiply(3, 4) == 12

    def test_multiply_by_zero(self):
        assert multiply(0, 999) == 0


class TestDivide:
    def test_basic_division(self):
        assert divide(10, 2) == 5.0

    def test_float_division(self):
        assert abs(divide(7, 2) - 3.5) < 1e-9

    def test_divide_by_zero_raises(self):
        """Bug: Should raise ValueError, not raw ZeroDivisionError."""
        with pytest.raises((ZeroDivisionError, ValueError)):
            divide(10, 0)

    def test_divide_negative(self):
        assert divide(-6, 2) == -3.0


class TestPower:
    def test_basic_power(self):
        assert power(2, 10) == 1024

    def test_power_of_zero(self):
        assert power(0, 5) == 0

    def test_power_negative_exp(self):
        assert abs(power(2, -1) - 0.5) < 1e-9


class TestSqrt:
    def test_basic_sqrt(self):
        assert abs(sqrt(9) - 3.0) < 1e-9

    def test_sqrt_zero(self):
        assert sqrt(0) == 0.0

    def test_sqrt_negative_raises(self):
        """Bug: Should raise ValueError for negative input."""
        with pytest.raises((ValueError, Exception)):
            sqrt(-1)


class TestFactorial:
    def test_basic_factorial(self):
        assert factorial(5) == 120

    def test_factorial_zero(self):
        assert factorial(0) == 1

    def test_factorial_negative_raises(self):
        """Bug: Should raise clear ValueError for negative input."""
        with pytest.raises(ValueError):
            factorial(-3)
