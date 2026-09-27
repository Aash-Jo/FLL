"""Simple drive and turn demo using motor_pair directly (no robot.py).

Drive forward, turn right, drive back, turn back. The robot moves as soon as
it starts, so give it floor space. Click Stop if it gets away from you.

Drive motors on ports A and E. If the robot drives backwards or turns the
wrong way, swap port.A and port.E in the pair line.

Numbers used below (large wheel, 27.6 cm around):
    1 cm forward      = 13.0435 wheel degrees   ->  30 cm = 391
    1 degree of turn  = 1.63 wheel degrees      ->  90 degrees = 147
"""

import motor_pair
import runloop
from hub import port


async def main():
    """Out and back: forward, turn right, backward, turn left."""
    motor_pair.pair(motor_pair.PAIR_1, port.A, port.E)  # left motor A, right motor E

    # Forward 30 cm. Steering 0 means both wheels turn the same way: straight.
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 391, 0, velocity=150)

    # Pause half a second so the moves are easy to see.
    await runloop.sleep_ms(500)

    # Turn right 90 degrees. Steering 100 means the wheels turn opposite ways:
    # the robot spins on the spot.
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 147, 100, velocity=150)

    await runloop.sleep_ms(500)

    # Backward 30 cm. Same as forward, but a negative velocity.
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 391, 0, velocity=-150)

    await runloop.sleep_ms(500)

    # Turn left 90 degrees: negative velocity turns the other way.
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 147, 100, velocity=-150)


runloop.run(main())
