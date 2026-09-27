"""MicroPython's ``uctypes`` - structured access to raw memory.

No CPython equivalent, so it needs a stub or Pylance reports it unresolved.
Members verified against Hub OS 1.8.149 with ``dir(uctypes)``.
"""

from typing import Any

LITTLE_ENDIAN: int
BIG_ENDIAN: int
NATIVE: int

VOID: int
UINT8: int
INT8: int
UINT16: int
INT16: int
UINT32: int
INT32: int
UINT64: int
INT64: int

FLOAT32: int
FLOAT64: int

SHORT: int
USHORT: int
INT: int
UINT: int
LONG: int
ULONG: int
LONGLONG: int
ULONGLONG: int

BFUINT8: int
BFINT8: int
BFUINT16: int
BFINT16: int
BFUINT32: int
BFINT32: int
BF_POS: int
BF_LEN: int

PTR: int
ARRAY: int


class struct:
    """Descriptor giving structured access to memory at an address."""

    def __init__(self, addr: int, descriptor: dict, layout_type: int = NATIVE) -> None: ...


def sizeof(struct_: Any, layout_type: int = NATIVE) -> int:
    """Size in bytes of a struct or descriptor."""


def addressof(obj: Any) -> int:
    """Address of a buffer-protocol object."""


def bytes_at(addr: int, size: int) -> bytes:
    """Copy ``size`` bytes from ``addr`` into a new bytes object."""


def bytearray_at(addr: int, size: int) -> bytearray:
    """Writable bytearray view over ``size`` bytes at ``addr``."""
