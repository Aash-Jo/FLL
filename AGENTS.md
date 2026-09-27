# AGENTS.md

This repository is for LEGO SPIKE Prime robot programs used from VS Code and for upload into the SPIKE app.

## Core principles

- Prefer code that works in the SPIKE Prime app, not just in the local VS Code environment.
- Use the hub API and standard SPIKE Prime modules (`motor`, `motor_pair`, `runloop`, `hub.port`, etc.).
- Do not introduce desktop-only or VS Code-only patterns unless explicitly asked for local tooling work.
- Keep robot programs simple, safe, and easy for kids to understand.
- Write for 5th-grade learners: short examples, simple explanations, and easy-to-read code.
- Favor the easiest working solution over clever or advanced patterns.

## Audience and teaching style

- The kids may have little or no programming experience.
- Some kids will use VS Code with an agent, some will write in VS Code and copy code into the SPIKE app, and some will build directly in the SPIKE app.
- Code must work in all of those scenarios, so it must be valid SPIKE Prime app Python.
- When giving API help, keep it short: name the API, show a quick example, and explain the important parameters in plain English.
- Keep explanations simple and concrete. Use phrases like "move the robot forward" or "turn the arm 90 degrees" instead of complex technical wording.

## Project structure

- `programs/` contains robot Python programs.
- `programs/robot.py` is the team's shared helper module: port settings and functions such as
  `drive_cm` and `turn_deg`. Programs use it with
  `from robot import drive_cm, turn_deg`. Never `import robot`.
- `programs/template.py` is the starting point for a new program: copy it, rename it, fill in `main()`.
- `typings/` contains API stubs for the hub modules.
- `tools/` contains helper tooling such as `spike_ble.py` and `llsp3.py`.
- `hubs.json` stores hub names and connection details.
- `projects/` stores `.llsp3` robot project files when needed.

## Learning-first approach for a rookie FLL team

- Treat learning as the main goal. The code should help kids understand what is happening, not just make the robot move.
- Start with the simplest working examples first. Do not jump to advanced motion control or clever tricks before the team understands the basics.
- Show one concept at a time: drive, turn, wait, arm, repeat, sensor, then combine ideas.
- Prefer small test programs over large, complicated programs that are hard to debug.
- When helping kids, explain the robot behavior in the same words they will use in the challenge: drive, turn, lift, wait, stop, repeat.
- Make it easy for students to try a new idea and see the result quickly.

## Beginner-friendly problem solving

- If a robot action fails, check the easiest things first: port names, motor direction, speed, and wiring.
- If the robot drifts, test slower and smaller moves before changing code complexity.
- If a move is inconsistent, try splitting one long action into several smaller actions.
- Encourage the team to test one change at a time so they learn what each change does.
- Simple experiments are better than guessing at a big rewrite.

## Team habits for new students

- Keep code readable enough that another kid can understand it without a long explanation.
- Use clear names, short comments, and consistent patterns.
- Save working versions before trying risky changes.
- When a program works, explain why it works in plain language.
- Celebrate small wins: drive 10 cm, move an arm 90 degrees, read a sensor, repeat a loop.

## API guidance

- Use `motor_pair.pair(...)` for driving a two-wheel base.
- Use `motor_pair.move_for_degrees(...)` for straight or guided driving.
- Use `motor.run_for_degrees(...)` for single-motor movements, such as an arm or loader.
- Use `runloop.run(main())` as the standard entry point for asynchronous programs.
- Keep port assignments explicit and easy to change for different robots.
- When suggesting an API, give a tiny working example and explain only the main parameters students need:
  - pair or port names
  - how far or how much to rotate
  - speed
  - steering when driving

Example:

```python
motor_pair.pair(motor_pair.PAIR_1, port.A, port.E)
await motor_pair.move_for_degrees(motor_pair.PAIR_1, 360, 0, velocity=250)
```

This pairs the two drive motors and runs them straight for 360 degrees at 250 degrees per second. `steering=0` means go straight.

## Avoid

- `device.ready(...)` for normal SPIKE app programs.
- VS Code-specific helpers that are not part of the robot runtime.
- Using unsupported modules or APIs not present in the SPIKE app environment.
- Large complex abstractions that hide the robot behavior from students.

## Safety and hardware notes

- Robot movement should be tested slowly and safely.
- Check motor directions and port assignments before running on a real robot.
- When adjusting a drivebase, prefer small speed changes and gentle acceleration before large behavior changes.
- Always assume the robot can drift or skid if started too aggressively.
- Prefer small, staged tests over full-power runs while tuning a robot.
- If a program changes motor or sensor wiring, verify the new port mapping before any longer run.
- Keep tests short and safe for kids: slow speed, clear floor space, and easy-to-stop code.

## Port conventions

- For common drivebases, ports A and E are often the left and right drive motors.
- Use named constants such as `LEFT`, `RIGHT`, `ARM_MOTOR`, or `BACK_MOTOR` instead of raw port numbers in logic.
- Keep hardware mappings grouped near the top of the file so they are easy to update for a different robot.

## Compatibility checklist

- Before finalizing a change, ask: "Would this run in the SPIKE app with the standard hub modules?"
- Avoid Python features or patterns that are only available in a normal desktop Python environment.
- Prefer small, readable examples over clever abstraction layers.
- When a fix is uncertain, choose the simpler and more explicit version.
- Do not suggest code that depends on VS Code-only helpers, desktop Python modules, or unsupported app features.
- When teaching kids, give the easiest working option first, then more advanced options only if needed.

## Help for kids exploring robot APIs

- Start with the simplest robot actions: drive, turn, move arm, wait, repeat.
- Show the easiest API first, then explain one or two options if there are multiple ways to do the same thing.
- For motor control, explain the common choices:
  - `motor_pair.move_for_degrees(...)` for driving a robot in a straight line or mild turn
  - `motor.run_for_degrees(...)` for moving one motor on an arm or loader
  - `motor_pair.move(...)` for continuous motion with steering
- When kids ask about options, explain the tradeoff in plain English:
  - straight drive = same speed on both wheels
  - turn = different speeds or steering value
  - arm motor = one motor moving a mechanism
  - wait = pause before the next action
- Keep examples short and easy to test.

## Shared team code (`programs/robot.py`)

- The hub runs one file per slot and the SPIKE app holds one file per project, so a program
  cannot import another file on its own. `tools/bundle.py` fixes this: every send path
  (`spike run`, the Run button, `spike usb run`, `llsp3.py import`) replaces a top-level
  `from robot import ...` with the contents of `programs/robot.py` before sending.
- Only `from NAME import ...` at column 0 is handled. `import robot` is refused with a message.
- Put reusable functions in `robot.py`: async, plain-English verb names, one job each, with the
  port and wheel settings as named constants at the top. No `runloop.run(...)` in that file.
- Keep `robot.py` valid SPIKE app Python like everything else. Any other helper module in
  `programs/` works the same way, but one shared file is easier for kids to find.
- For the SPIKE app, `spike bundle programs/X.py` writes `build/X.py` with `robot.py` copied in.

## Typical commands

- `spike session` to connect and re-run code interactively. The VS Code Connect button.
- `spike send run FILE`, `spike send stop`, `spike send quit`: the Run / Stop / Disconnect
  buttons. They drive the open session over localhost, or fall back to a one-shot run/stop.
- `spike discover` to scan for hubs.
- `spike bundle programs/<file>.py` to write `build/<file>.py`, the one-file version for the SPIKE app.
- `spike usb run programs/<file>.py` for USB debugging.
- `py tools/llsp3.py import programs/<file>.py` to convert Python source into a `.llsp3` project file.

## When editing robot programs

- Keep examples understandable for children.
- Prefer clear names like `LEFT`, `RIGHT`, `ARM_MOTOR`, `TARGET_DISTANCE_MM`.
- Use short, readable scripts over generic abstractions.
- Add comments only when they help explain robot behavior or hardware setup.
- Keep code easy to copy into the SPIKE app without extra setup.
- Prefer simple patterns that kids can modify, not large frameworks or abstraction layers.

## Default preference

When uncertain, choose the simplest SPIKE Prime app-compatible version of the code, not the most clever or most advanced version.

## Personal preferences and common rules (read first)

This project normally lives under `AiWorkspace`. Before responding to or
acting on any request, read and follow, in this order:

1. `../personalization/personalization.md` — the owner's global preferences.
2. `../COMMON-RULES.md` — rules shared by every project under `AiWorkspace`
   (security boundary, portability, repositories, OneDrive, data sensitivity).

This file adds project-specific rules on top. If either file cannot be read,
for example when this repo is used on its own outside `AiWorkspace`, say so in
one line, do not substitute inferred preferences, and follow this file alone.
If your context has been compacted, or a previous reply lacked the required
`Confidence: NN% | ETU: N` footer, re-read them before continuing. Claude
Code: both are already imported through `../CLAUDE.md`; do not read them again.
