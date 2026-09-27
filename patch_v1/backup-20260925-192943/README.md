# FLL - SPIKE Prime robots from VS Code

Program the team's two LEGO SPIKE Prime robots from VS Code **over Bluetooth**,
no cable, and move finished code into the SPIKE app when it is ready. This
folder is the whole project; it also holds a few team files (spreadsheets, a
PDF, a `.llsp3`) that live here as before.

```
programs/            your Python programs - the source of truth
tools/spike_ble.py   the `spike` command: talks to the hub over Bluetooth or USB
hubs.json            which robot is which (Bluetooth address, USB serial, port layout)
typings/             autocomplete stubs for the hub API, checked against the real hub
projects/ + tools/llsp3.py   move code between .py and the SPIKE app's .llsp3 files
setup.ps1            sets up a PC (Python, packages, VS Code, the `spike` command)
HANDOFF.md           the full story for the next person or agent setting up a PC
.venv/               this PC's Python environment - built by setup.ps1, never copied
```

## New computer (Windows or Mac)

Sync this folder (OneDrive) or copy it, then:

```powershell
# Windows - PowerShell
powershell -ExecutionPolicy Bypass -File "C:\Users\<you>\OneDrive\FLL\setup.ps1"
```
```bash
# macOS (or Linux) - Terminal
bash ~/OneDrive/FLL/setup.sh
```

Either installs what is missing, builds `.venv`, creates the `spike` command,
and finishes by running `hello_hub.py` on a hub if one is in range. Re-run any
time; it is safe. `START-HERE.md` is the short version; `HANDOFF.md` has every
detail and pitfall.

## Every day

Hub on, **Bluetooth light blinking**, SPIKE app closed. Then either:

**VS Code** - open a program, press `Ctrl+Shift+B`. It connects, uploads, runs,
shows `print()` output, disconnects. More under Terminal > Run Task
(`Hub (BLE): ...` and `Hub (USB): ...`).

**Terminal** - stay connected and re-run as you edit:

```
cd C:\Users\<you>\OneDrive\FLL
spike session
   spike> run programs\drive_demo.py
   spike> r            re-run after saving an edit
   spike> stop         or Ctrl+C while it runs
   spike> quit         disconnect
```

Two robots on at once? Name one: `spike session --hub robot2`. Without a name,
Bluetooth takes whichever hub is advertising.

Other useful commands:

```
spike discover                    every hub in range, Bluetooth and USB - use it to register a new robot
spike info                        firmware / protocol details
spike upload programs\x.py --slot 3   store in a hub slot without running (the SPIKE app sees it there)
spike usb run programs\x.py       same program over the USB cable
spike usb repl                    interactive MicroPython prompt (USB only; Ctrl-] to exit)
```

## Into the SPIKE app

Paste the program into a Python project in the app, or `spike upload` it into
a slot - the Bluetooth tool stores programs exactly the way the app does.
`py tools/llsp3.py import programs/X.py` writes an `.llsp3` project file the
app can open; `export` goes the other way.

## Autocomplete

`typings/` holds stubs for every module the hub exposes, with LEGO's docstrings.
They were audited against the live hub - several upstream mistakes are fixed
there (see `HANDOFF.md` §9.10). `app.*` is parked in `stubs-unavailable/`
because this firmware does not have it. Check the whole tree with
`.venv\Scripts\python -m pyright programs\` - it should say 0 errors.

## Hardware notes

robot1: A and E are the drive motors (Large), C and D Medium Motors, B and F
colour sensors. Hub OS 1.8.149 - that *is* the current generation; do not look
for an upgrade. robot2 is not registered yet: `HANDOFF.md` §6.

The LEGO VS Code extension does not work with these hubs (wrong protocol
generation) and is deliberately marked unwanted in `.vscode/extensions.json`.
