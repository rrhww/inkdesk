"""CLI greeter module — SDK dogfooding example."""

from __future__ import annotations


def greet(name: str) -> str:
    """Return a greeting string for the given name.

    Args:
        name: The name to greet.  Must be a non‑empty string;
            ``None`` and empty strings are rejected.

    Returns:
        ``"Hello, {name}!"``

    Raises:
        TypeError: If *name* is not a string.
        ValueError: If *name* is an empty string.
    """
    if not isinstance(name, str):
        raise TypeError(f"name must be a string, got {type(name).__name__}")
    if not name:
        raise ValueError("name must not be empty")
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet("World"))
