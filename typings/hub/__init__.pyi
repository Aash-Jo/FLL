"""The ``hub`` package is home to all of the modules used to interact with
various integrated inputs (gyroscope, buttons) and outputs (lights, sound) on a
Spike Hub (e.g. LEGO parts 45601 or 45609). This package also contains the
`hub` module with several direct functions used to interrogate and control the
hub itself.

To use the ``hub`` module itself, add the following import statement to
your project:

::

    import hub

All functions in the module should be called inside the ``hub``
module as a prefix like so:

::

    t = hub.temperature()

**NOTE**: The ``hub`` module contains a number of functions that are not
documented in the official LEGO materials. These are marked as
**UNDOCUMENTED** in the function descriptions below. Their behavior has been
determined empirically and they should be used with caution.
"""


def device_uuid() -> str:
    """Get the device id.

    :rtype: str
    """


def hardware_id() -> str:
    """Get the hardware id.

    :rtype: str
    """


def power_off() -> int:
    """Turn off the hub.

    :rtype: int
    """


def temperature() -> int:
    """Get the hub temperature measured in decidegrees Celsius (d°C),
    which is 1/10 of a degree Celsius (°C).

    :rtype: int
    """


# `soft_reset`, `reset` and `bootloader` were declared here by the upstream
# stub but do NOT exist on Hub OS 1.8.149 - `hasattr(hub, "soft_reset")` is
# False for all three, so calling them raises AttributeError. The equivalents
# live in the `machine` module (machine.soft_reset, machine.reset,
# machine.bootloader). Removed so autocomplete stops offering them.

class _Config:
    """Opaque hub configuration object. `dir()` exposes no public members on
    Hub OS 1.8.149 and it is not callable."""


config: _Config
"""**UNDOCUMENTED** An opaque `<config>` object present on the hub but absent
from the upstream stub."""


def battery_voltage() -> int:
    """**UNDOCUMENTED** Get the battery voltage.

    :rtype: int
    """


def battery_temperature() -> int:
    """**UNDOCUMENTED** Get the battery temperature.

    :rtype: int
    """


def battery_current() -> int:
    """**UNDOCUMENTED** Get the battery current.

    :rtype: int
    """


def usb_charge_current() -> int:
    """**UNDOCUMENTED** Get the USB charge current.

    :rtype: int
    """
