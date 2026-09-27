"""Try the team helpers from robot.py: drive a square.

Put the robot on the floor with room to move. Click Run. If the square does
not close, change DEGREES_PER_CM or DEGREES_PER_TURN_DEG in robot.py.
"""

import runloop
from robot import drive_cm, turn_deg


async def main():
    """Four sides, four right turns."""
    for _ in range(4):
        await drive_cm(20)   # one side of the square
        await turn_deg(90)   # corner


runloop.run(main())
