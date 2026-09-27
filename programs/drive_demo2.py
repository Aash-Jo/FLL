"""Drive forward 10 cm and move the back motor up and down 90 degrees ten times."""

import motor
import motor_pair
import runloop
from hub import port

# Use the large drive motors on ports A and E.
LEFT = port.A
RIGHT = port.E

# Back motor. If your mechanism is on a different port, change this.
FRONT_MOTOR = port.D
BACK_MOTOR = port.C

# Approximate wheel circumference for a 56 mm wheel.
WHEEL_DIAMETER_MM = 56
WHEEL_CIRCUMFERENCE_MM = 3.14159 * WHEEL_DIAMETER_MM
TARGET_DISTANCE_MM = 100
DEGREES = int((TARGET_DISTANCE_MM / WHEEL_CIRCUMFERENCE_MM) * 360)


async def main():
    """Drive forward 10 cm, then move the back motor up/down 10 times."""
    motor_pair.pair(motor_pair.PAIR_1, LEFT, RIGHT)
    print("Driving forward 10 cm")
    await motor_pair.move_for_degrees(
        motor_pair.PAIR_1,
        DEGREES,
        0,
        velocity=300,
    )

    for _ in range(10):
        print("Moving front motor up 90 degrees")
        await motor.run_for_degrees(FRONT_MOTOR, 90, 300)

        print("Moving front motor down 90 degrees")
        await motor.run_for_degrees(FRONT_MOTOR, -90, 300)


runloop.run(main())
