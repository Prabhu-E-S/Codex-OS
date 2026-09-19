"""
Demo Project — Calculator Module
Codex OS Demonstration Target

This module intentionally contains the following issues for Codex OS to find,
fix, and report on:

  1. BUG: divide() does not guard against division by zero
  2. BUG: add() silently accepts non-numeric types without validation
  3. MISSING: No input type validation on any public function
  4. MISSING: power() result can overflow for large exponents without warning

These are representative of real engineering issues that Codex OS's autonomous
agent pipeline (Architect → Builder → Tester → Breaker → Security → Evaluation)
is designed to detect and remediate.
"""


def add(a, b):
    """Return the sum of two numbers."""
    return a + b


def subtract(a, b):
    """Return the difference of two numbers."""
    return a - b


def multiply(a, b):
    """Return the product of two numbers."""
    return a * b


def divide(a, b):
    """Return the quotient of a divided by b.

    BUG: No guard against ZeroDivisionError when b == 0.
    """
    return a / b  # noqa: BUG001 — intentional demo bug


def power(base, exp):
    """Return base raised to the power of exp."""
    return base ** exp


def sqrt(n):
    """Return the square root of n.

    BUG: No guard against negative input (math domain error).
    """
    import math
    return math.sqrt(n)  # noqa: BUG002 — intentional demo bug


def factorial(n):
    """Return n! (factorial of n).

    BUG: No guard for negative integers or non-integers.
    """
    import math
    return math.factorial(n)  # will raise ValueError for negative n, silently
