"""MicroPython's ``machine`` module - hardware-level control.

Has no CPython equivalent, so without this stub Pylance reports
``Import "machine" could not be resolved``. Members verified against Hub OS
1.8.149 with ``dir(machine)``; this hub exposes only the subset below, not the
Pin/I2C/SPI classes found on other MicroPython ports.

Note the reset functions the upstream `hub` stub wrongly claimed live here.
"""


def soft_reset() -> None:
    """Restart the interpreter, keeping power on. This is what
    ``mpremote soft-reset`` triggers."""


def reset() -> None:
    """Hard-reset the hub, as if the power were cycled."""


def bootloader() -> None:
    """Reboot into the firmware bootloader. Do not call casually."""


def idle() -> None:
    """Gate the CPU clock briefly to save power; any interrupt wakes it."""


def reset_cause() -> int:
    """Why the hub last reset, as an integer code."""


def unique_id() -> bytes:
    """The board's unique identifier as bytes."""
