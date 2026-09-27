FLL patch v1 - status-bar buttons + team helper module + program template
Made 2026-09-20 from the FLL folder on Brijesh's PC.

WHAT IT DOES
  1. Buttons at the bottom-left of VS Code so nobody has to type
     "spike session" or "run <file>" any more. Click Connect, open a program,
     click Run. Change to another program, click Run again. Stop, Disconnect.
  2. programs/robot.py: the team's shared functions (drive_cm, turn_deg). Any program uses them with
         from robot import drive_cm, turn_deg
     The tool copies robot.py into the program when sending, so the hub still
     gets one file. programs/robot_demo.py shows it working.
  3. programs/template.py: copy this to start a new program.

HOW TO APPLY ON A PC OR MAC THAT ALREADY HAS THE OLD SETUP
  1. Copy this whole patch_v1 folder INTO the FLL folder on that computer,
     so it sits next to hubs.json and setup.ps1.
  2. Close VS Code if it is open on the FLL folder.
  3. Windows: double-click   apply.cmd
     Mac:     double-click   apply.command
              (if the Mac says it cannot be opened or "permission denied",
               open Terminal, type  bash  and a space, drag apply.command
               into the window, press Enter.)
  4. Read the summary it prints. Then open FLL.code-workspace as usual.
     The buttons appear at the bottom-left.

WHAT THE SCRIPT DOES
  - Copies every file under files/ into the FLL folder, replacing the old
    versions. Anything it replaces is saved first in a backup-<date> folder
    here, so it can be undone by copying those back.
  - Installs the VS Code extension "Task Buttons"
    (spencerwmiles.vscode-task-buttons) that draws the buttons.
  - Checks that the folder's .venv still runs. No new Python packages are
    needed, so the old .venv is fine. If it does not run, the script tells
    you to run setup.ps1 (Windows) or setup.sh (Mac) once.

FILES IN files/  (paths relative to the FLL folder)
  Needed:
    tools/spike_ble.py          "spike send" (buttons), "spike bundle", copies robot.py in when sending
    tools/bundle.py             the copying-in logic, shared with llsp3.py
    tools/llsp3.py              .llsp3 import now copies robot.py in too
    programs/robot.py           the team's shared functions - edit this as the team grows
    programs/template.py        starting point for a new program
    programs/robot_demo.py      example using robot.py
    programs/drive_demo.py      simple drive-and-turn example using motor_pair directly
    programs/hello_hub.py       the team's edited hello program
    .vscode/tasks.json          the tasks the buttons run
    .vscode/settings.json       button definitions (when the folder is opened directly)
    .vscode/extensions.json     recommends the Task Buttons extension
    FLL.code-workspace          button definitions (when opened through this file)
  Documentation only:
    README.md, START-HERE.md, AGENTS.md, HANDOFF.md, .gitignore

  If that computer already has its own programs/robot.py with team changes,
  the script backs it up before replacing it - merge by hand from backup-<date>/.

IF THE BUTTONS DO NOT SHOW
  - In VS Code: Ctrl+Shift+P (Mac: Cmd+Shift+P), "Reload Window".
  - Still nothing: Ctrl+Shift+X opens Extensions; search "Task Buttons",
    install it, reload.
  - The old way still works meanwhile: Ctrl+Shift+B, or "spike session" in
    the terminal.
