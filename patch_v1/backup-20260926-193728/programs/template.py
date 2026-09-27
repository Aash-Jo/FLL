"""WHAT THIS PROGRAM DOES: (write one sentence here)

How to start a new program:
  1. Right-click template.py > Copy, then Paste in the programs folder.
  2. Rename the copy, for example mission_3.py. Keep the .py ending.
  3. Change the sentence at the top so it says what your program does.
  4. Write your steps inside main(), one action per line.
  5. Click Run and watch the robot.

Two ways to move the robot are shown below. Both do the same thing.
  Part 1 uses the team helpers from robot.py: short and easy to read.
  Part 2 uses motor_pair directly: more typing, but you see every number.
Keep the way you like and delete the other.
"""

import motor_pair
import runloop
from hub import port
from robot import drive_cm, turn_deg

# ---- Robot setup (only needed for Part 2; robot.py has its own copy) ----
LEFT = port.A             # left drive motor
RIGHT = port.E            # right drive motor
PAIR = motor_pair.PAIR_1  # the two drive motors working together
DEGREES_PER_CM = 13.0435  # wheel degrees for 1 cm (large wheel, 27.6 cm around)
DEGREES_PER_TURN_DEG = 1.63  # wheel degrees for 1 degree of turning on the spot


async def main():
    """The robot does these steps in order, top to bottom."""

    # ---- Part 1: team helpers from robot.py ----
    # Every robot action starts with `await`. The number is the amount.
    await drive_cm(20)          # forward 20 cm (a minus number drives backward)
    await turn_deg(90)          # turn right 90 degrees (a minus number turns left)

    # Wait, in milliseconds: 1000 is one second.
    await runloop.sleep_ms(1000)

    # ---- Part 2: the same moves with motor_pair directly ----
    motor_pair.pair(PAIR, LEFT, RIGHT)   # tell the hub which two motors drive

    distance_cm = 20
    await motor_pair.move_for_degrees(
        PAIR,
        round(distance_cm * DEGREES_PER_CM),  # how far the wheels turn
        0,  # steering: 0 = straight, 100 = turn on the spot
        velocity=150,  # speed; a minus number goes backward
    )

    turn = 90
    await motor_pair.move_for_degrees(
        PAIR,
        round(turn * DEGREES_PER_TURN_DEG),  # how far the wheels turn
        100,  # steering: 100 = turn on the spot
        velocity=150,  # speed; a minus number turns the other way
    )


runloop.run(main())
