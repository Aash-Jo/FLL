"""Changes centimeters to degrees to move the motor"""
#from programs/yaw_correction import correct_yaw

from hub import port
from hub import motion_sensor
import runloop
import motor_pair
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

def cm_to_degrees(distance):
    """Changes how many inches you want to move to how many rotaitions you want to move the wheel"""
    wheel_diameter = 8.3
    wheel_circumfrence = 3.14 * wheel_diameter #To find the circumfrence, you multiply pi by the wheel diameter 
    wheel_rotations = distance/wheel_circumfrence
    wheel_degrees = wheel_rotations*360.0# This is converting it to degrees
    print(wheel_degrees)
    wheel_degrees = int(wheel_degrees)
    return wheel_degrees

async def main():
    """example"""
    motion_sensor.reset_yaw(0)
    degrees = cm_to_degrees(100)
    degrees = int(degrees)
    motor_pair.pair(motor_pair.PAIR_1,port.A,port.E)
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, degrees, 0)
    current = motion_sensor.tilt_angles()[0]
    target = 0
    slack = 10
    await correct_yaw(current,target,slack)

runloop.run(main())
