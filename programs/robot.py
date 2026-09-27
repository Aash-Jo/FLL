"""Team helper functions for our robot. Use them in any program with one line:

    from robot import drive_cm, turn_deg

Then inside `async def main():`

    await drive_cm(77)        # forward 77 cm
    await drive_cm(-28)       # backward 28 cm
    await turn_deg(9)         # turn right 9 degrees, on the spot
    await turn_deg(-10)       # turn left 10 degrees

The numbers come from mission8_reachingroots.py, tested on our robot:
    wheel degrees = cm * 13.0435      (large wheel, 27.6 cm around)
    wheel degrees = turn * 1.63       (turning on the spot)
    speed 150

The Run button (and `spike run`) copies this file into your program before
sending it, so the hub still gets one file. For the SPIKE app, run
`spike bundle programs/yourfile.py` and paste build/yourfile.py into the app.

Rules for this file:
  - Only functions and settings. No `runloop.run(main())` here; that goes in
    each program.
  - Test a change with a tiny program before the team relies on it.
"""

import motor_pair
import motor
from hub import port
from hub import motion_sensor


# ---- Robot setup. Change these to match the robot. ----
LEFT = port.A             # left drive motor
RIGHT = port.E            # right drive motor
DEGREES_PER_CM = 13.0435  # wheel degrees for 1 cm: 360 / 27.6 (large wheel). Small wheel: 360 / 18.6
DEGREES_PER_TURN_DEG = 1.63  # wheel degrees for 1 degree of turning on the spot
SPEED = 150               # degrees per second

PAIR = motor_pair.PAIR_1
_paired = False


def _ready():
    """Pair the drive motors the first time a drive function is used."""
    global _paired  # pylint: disable=global-statement
    if not _paired:
        motor_pair.pair(PAIR, LEFT, RIGHT)
        _paired = True


async def drive_cm(distance_cm, speed=SPEED):
    """Drive straight. Positive = forward, negative = backward."""
    _ready()
    velocity = speed if distance_cm >= 0 else -speed
    await motor_pair.move_for_degrees(
        PAIR,
        round(abs(distance_cm) * DEGREES_PER_CM),  # how far to move
        0,  # steering: 0 for straight
        velocity=velocity,
    )


async def turn_deg(turn_deg, speed=SPEED):
    """Turn on the spot. Positive = right, negative = left."""
    _ready()
    velocity = speed if turn_deg >= 0 else -speed
    await motor_pair.move_for_degrees(
        PAIR,
        round(abs(turn_deg) * DEGREES_PER_TURN_DEG),  # how far to move
        100,  # steering: 100 for turning on the spot
        velocity=velocity,
    )

#Aashvi's
def arm_to_motor_angle(arm_angle, g1_teeth,g2_teeth ,g3_teeth):
    """""Changes how many degrees you need to move your arm to
    how many degrees you need to move the motor"""
    arm_angle = float(arm_angle)
    g1_teeth = float(g1_teeth)
    g2_teeth = float(g2_teeth)
    g3_teeth = float(g3_teeth)
    return int((((g2_teeth/g1_teeth) * (g3_teeth/g2_teeth)) * arm_angle))#motor angle

def cm_to_degrees(distance):
    """Changes how many inches you want to move to how many rotaitions you want to move the wheel"""
    wheel_diameter = 8.3
    wheel_circumfrence = 3.14 * wheel_diameter #To find the circumfrence, you multiply pi by the wheel diameter 
    wheel_rotations = distance/wheel_circumfrence
    wheel_degrees = wheel_rotations*360.0# This is converting it to degrees
    print(wheel_degrees)
    wheel_degrees = int(wheel_degrees)
    return wheel_degrees

async def correct_yaw(current_yaw, target_yaw, slack):
    """.takes the current yaw, the target yaw, and the amount of slack
        . figures out which direction it is facing to much to
        . adjusts it 3 times then stops to conserve time"""
    motion_sensor.set_yaw_face(motion_sensor.RIGHT)
    tally = 3
    speed = int((current_yaw - target_yaw)/10)
    distance = int(speed * 280/90)

    while tally != 0:

        #If it over shot
        if (current_yaw - target_yaw) > slack:
            await(motor.run_for_degrees(port.A, -distance ,speed * tally))
        #If it under shot
        elif (target_yaw -current_yaw) > slack:
            await(motor.run_for_degrees(port.E, distance ,speed * tally))
        #if it got close enough
        else:
            tally = 0
            break

        tally -= 1
        current_yaw = motion_sensor.tilt_angles()[0]
        