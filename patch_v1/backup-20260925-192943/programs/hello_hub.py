"""Smallest useful program: say hello on the light matrix and in the console.

Run it with the `Hub: run current file` task (Ctrl+Shift+B), or open it in the
SPIKE app after `py tools/llsp3.py import programs/hello_hub.py`.
"""

import runloop
from hub import light_matrix, sound 


async def main():
    """Display a greeting on the hub and in the console."""
    light_matrix.write("Hello!")
    await runloop.sleep_ms(3000)
    await sound.beep(440, 300)
    print("Hello from the hub")  # shows up in the task's terminal


runloop.run(main())
