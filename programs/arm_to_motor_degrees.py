"""
Run it with the `Hub: run current file` task (Ctrl+Shift+B), or open it in the
SPIKE app after `py tools/llsp3.py import programs/hello_hub.py`.
"""

from hub import port
import runloop
#import motor_pair
import motor


## .500 degrees is actual 360 degrees
## .Motor -> Gear1 -> Gear2 -> Gear3 -> Arm
## .Gear1 teeth - 20
## .Gear2/Gear3 teeth - 30

def arm_to_motor_angle(arm_angle, g1_teeth,g2_teeth ,g3_teeth):
    """""Changes how many degrees you need to move your arm to
    how many degrees you need to move the motor"""
    arm_angle = float(arm_angle)
    g1_teeth = float(g1_teeth)
    g2_teeth = float(g2_teeth)
    g3_teeth = float(g3_teeth)
    return int((((g2_teeth/g1_teeth) * (g3_teeth/g2_teeth)) * arm_angle))#motor angle

async def main():
    """Making the arm hit the floor, 
    then move up exactly 90 degrees using the function as an example"""
    ## Arm starting position just above the ground
    is_stalled = await motor.run_for_degrees(port.D, 50, -50)
    print(is_stalled)
    ## If the arm is hitting the ground
    if is_stalled[0] == motor.STALLED or is_stalled[0] == motor.READY:
        print('Stalled')
        motor.stop(port.D)
        ## Arm is touching the ground
        motor.reset_relative_position(port.D, 0)
        motor_angle = arm_to_motor_angle(90, 20, 30, 30)
        print("motor angle =", motor_angle)
        await motor.run_to_relative_position(port.D, motor_angle, motor_angle)

runloop.run(main())
