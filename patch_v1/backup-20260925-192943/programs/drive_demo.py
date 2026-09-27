"""Drive a two-motor base forward, then turn, then stop on a colour.

Drive motors on ports A and E, colour sensor on port B - change to match your
build.

Run it with the `Hub: run current file` task (Ctrl+Shift+B). The robot moves as
soon as it starts, so give it floor space or put it on blocks. `Hub: stop
running program` soft-resets the hub if it gets away from you.
"""

import color
import color_sensor
import device
import motor_pair
import runloop
from hub import port

# Detected on the hub: A/E Large Motors, C/D Medium Motors, B/F Colour Sensors.
# If the base drives backwards or turns the wrong way, swap LEFT and RIGHT.
LEFT = port.A
RIGHT = port.E
SENSOR = port.B


async def wait_for_ports(*ports, timeout_ms=5000):
    """Block until every port has finished enumerating.

    mpremote resets the device stack when it connects, so the LPF2 ports are
    still coming up when the program starts - touching a motor before then
    fails with OSError EPERM, every time. `runloop.run()` alone does not take
    long enough to cover it. Costs about 50 ms here and nothing in the SPIKE
    app, where devices are already up.
    """
    for _ in range(timeout_ms // 50):
        if all(device.ready(p) for p in ports):
            return
        await runloop.sleep_ms(50)
    raise RuntimeError(f"ports not ready after {timeout_ms} ms")


async def main():
    """Drive forward, turn, and stop when the colour sensor sees red."""
    await wait_for_ports(LEFT, RIGHT, SENSOR)

    motor_pair.pair(motor_pair.PAIR_1, LEFT, RIGHT)

    # 360 degrees forward at 500 deg/sec, both wheels at the same speed.
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 360, 0, velocity=500)

    # Spin in place a quarter turn.
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 180, 100, velocity=300)

    # Creep forward until the sensor sees red, then stop.
    # The timeout matters: `until` with the default timeout=0 never resolves,
    # so without it the base drives until the battery dies if red never shows.
    # A sensor reading of -1 (color.UNKNOWN) means it sees no surface at all.
    motor_pair.move(motor_pair.PAIR_1, 0, velocity=200)
    # `until` returns runloop.SUCCESS (1) or runloop.TIMEOUT (2) - both are
    # truthy, so compare explicitly rather than testing the result directly.
    result = await runloop.until(
        lambda: color_sensor.color(SENSOR) == color.RED,
        timeout=5000,
    )
    motor_pair.stop(motor_pair.PAIR_1)

    if result == runloop.SUCCESS:
        print("done - stopped on red")
    else:
        print("stopped on timeout - never saw red")


runloop.run(main())
