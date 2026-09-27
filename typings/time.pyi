"""MicroPython's ``time``, which is *not* CPython's.

Without this stub Pylance resolves ``time`` against desktop CPython's typeshed,
so ``time.ticks_ms()`` and friends are reported as errors while the CPython-only
names it offers instead do not exist on the hub.

Members verified against Hub OS 1.8.149 with ``dir(time)``.
"""

from typing import Tuple


def sleep(seconds: float) -> None:
    """Sleep for the given number of seconds (accepts a float)."""


def sleep_ms(ms: int) -> None:
    """Sleep for the given number of milliseconds."""


def sleep_us(us: int) -> None:
    """Sleep for the given number of microseconds."""


def ticks_ms() -> int:
    """Millisecond counter with an arbitrary reference point. Wraps around, so
    only ever compare two values with ``ticks_diff``."""


def ticks_us() -> int:
    """Microsecond counter. Same wrapping caveat as ``ticks_ms``."""


def ticks_cpu() -> int:
    """Highest-resolution counter available on this port."""


def ticks_add(ticks: int, delta: int) -> int:
    """Offset a ticks value by delta, respecting wraparound."""


def ticks_diff(ticks1: int, ticks2: int) -> int:
    """``ticks1 - ticks2`` computed correctly across wraparound. Always use
    this rather than subtracting two ticks values directly."""


def time() -> int:
    """Seconds since the port's epoch."""


def time_ns() -> int:
    """Nanoseconds since the port's epoch."""


def gmtime(secs: int | None = None) -> Tuple[int, int, int, int, int, int, int, int]:
    """Convert seconds since the epoch to an 8-tuple in UTC."""


def localtime(secs: int | None = None) -> Tuple[int, int, int, int, int, int, int, int]:
    """Convert seconds since the epoch to an 8-tuple in local time."""


def mktime(t: Tuple[int, int, int, int, int, int, int, int]) -> int:
    """Inverse of ``localtime``."""
