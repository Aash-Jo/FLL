"""First version to complete Drone Suvey(m1)"""
from cm_to_wheel_rotations import cm_to_degrees
from hub import port
import motor
import runloop

async def main():
    """Making it move forward"""
    motor_degrees = cm_to_degrees(71)
    print(motor_degrees)
    await motor.run_for_degrees(port.D, motor_degrees, motor_degrees)

runloop.run(main())

