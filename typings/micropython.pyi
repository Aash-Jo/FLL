"""MicroPython's ``micropython`` module - interpreter internals.

No CPython equivalent, so it needs a stub or Pylance reports it unresolved.
Members verified against Hub OS 1.8.149 with ``dir(micropython)``.
"""

from typing import Any, Callable, TypeVar

_T = TypeVar("_T")


class RingIO:
    """Fixed-size ring buffer with a stream interface."""

    def __init__(self, size: int) -> None: ...
    def read(self, nbytes: int = -1) -> bytes: ...
    def readinto(self, buf) -> int: ...
    def readline(self) -> bytes: ...
    def write(self, data) -> int: ...
    def close(self) -> None: ...
    def any(self) -> int: ...


def const(value: _T) -> _T:
    """Declare a true compile-time constant. Assign at module level
    (``_FOO = const(3)``) so the compiler inlines it rather than allocating."""


def opt_level(level: int | None = None) -> int | None:
    """Get or set the compiler optimisation level."""


def mem_info(verbose: Any = None) -> None:
    """Print heap usage. Pass any truthy value for the detailed dump."""


def qstr_info(verbose: Any = None) -> None:
    """Print interned-string statistics."""


def stack_use() -> int:
    """Current stack usage in bytes."""


def heap_lock() -> int:
    """Forbid heap allocation. Allocating while locked raises MemoryError."""


def heap_unlock() -> int:
    """Re-permit heap allocation."""


def kbd_intr(chr_: int) -> None:
    """Set the character that raises KeyboardInterrupt, or -1 to disable."""


def schedule(func: Callable[[Any], Any], arg: Any) -> None:
    """Queue ``func(arg)`` to run at the next opportunity - the safe way to do
    real work from an interrupt handler."""


def alloc_emergency_exception_buf(size: int) -> None:
    """Reserve a buffer so exceptions can still be reported from an ISR."""
