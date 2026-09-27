"""correcting the yaw angle"""
from hub import port
from hub import motion_sensor
import motor

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