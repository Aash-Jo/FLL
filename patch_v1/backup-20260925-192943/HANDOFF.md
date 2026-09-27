# HANDOFF - setting up a PC to program the FLL SPIKE Prime robots

You are an agent setting up a new Windows PC so that programs in this folder
run on LEGO SPIKE Prime robots **over Bluetooth from VS Code**, with USB as a
fallback. Everything you need is in this folder. This document tells you what
"working" means, how to get there, how to prove it, and every trap that was
hit building this. Read it fully before acting; most of the traps are
non-obvious and several will silently look like success.

`manifest.json` holds the same key facts machine-readably.

---

## 1. What "done" looks like

All of these true on the new PC, in this order:

1. `spike --help` prints usage in a freshly opened terminal (no profile tricks).
2. `spike discover` lists a robot over Bluetooth (with the hub on and its
   Bluetooth light **blinking**).
3. `spike run programs\hello_hub.py` prints `Hello from the hub` in the terminal,
   and the hub scrolls "Hello!" and beeps. Exit code 0.
4. In VS Code with this folder open, `Ctrl+Shift+B` on an open program does the
   same thing.
5. `.venv\Scripts\python -m pyright programs\` reports **0 errors**.

If 1-4 pass, the workflow is working. Do not declare success on anything less
than a program's `print()` arriving back over Bluetooth - "connected" and
"uploaded" both happen even when nothing runs (see trap #6).

## 2. Hardware

| | robot1 | robot2 |
|---|---|---|
| Hub | LEGO SPIKE Prime hub (STM32F413) | LEGO SPIKE Prime hub |
| Hub OS | 1.8.149 (SPIKE App 3 generation) | assume the same; verify with `spike info` |
| Bluetooth address | `E0:FF:F1:6C:45:B6` | **unknown - register it (section 6)** |
| Advertised name | `BioBuddies_2` (not always present in the advert) | unknown |
| USB serial | `335234693132` | unknown |
| Ports | A, E: Large Motors (drive base); C, D: Medium Motors; B, F: Color Sensors | unknown - read with `spike usb exec "import device; from hub import port; print([device.id(p) for p in (port.A,port.B,port.C,port.D,port.E,port.F)])"` (48 medium motor, 49 large motor, 61 color sensor, 62 distance, 63 force) |

Both are registered in `hubs.json`; robot2's fields are `null` until filled.

**Hub OS 1.8.149 is the current generation. Do not "upgrade" it.** The SPIKE
*app* is versioned 3.x; the hub *firmware* is versioned 1.x. There is no "Hub
OS 3". The SPIKE 3 web app connects to this firmware without offering an update
because none is needed. A whole afternoon was lost to this confusion.

The hub runs MicroPython 1.24.0 and exposes the App 3 Python API: `hub`
(`port`, `light_matrix`, `sound`, `button`, `light`, `motion_sensor`),
`motor`, `motor_pair`, `runloop`, `color`, `color_sensor`, `distance_sensor`,
`force_sensor`, `device`, `orientation`, `color_matrix`, plus the MicroPython
stdlib. The `app` module (`app.display`, `app.sound`, ...) does **not** exist
on this firmware. The legacy `spike` module does not exist either.

## 3. Software requirements

- **Windows 10/11 or macOS** (Linux should work; untested) with a **Bluetooth
  adapter** (BLE). Without one, only USB works. Windows uses `setup.ps1`,
  macOS/Linux use `setup.sh`; everything else is identical.
- **Python 3.12** (user install). Newer is not better here: `bleak` relies on
  native WinRT bindings that lag new CPython releases.
- `bleak`, `mpremote`, `pyright` - exact versions in `requirements.txt`.
- **VS Code** with `ms-python.python`, `ms-python.vscode-pylance`,
  `ms-python.pylint`.
- `winget` (standard on Windows 11) lets `setup.ps1` install Python and VS Code
  unattended, user-scope, no admin.
- **Do not install** the `peterstaev.lego-spikeprime-mindstorms-vscode`
  extension (trap #1) or Pybricks (it is replacement *firmware*, not a package,
  and would wipe the hub).

## 4. Setup - the short version

Copy or sync this folder to the new PC (OneDrive does this if the same account
is signed in), open PowerShell, and run:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\<user>\OneDrive\FLL\setup.ps1"
```

It prints a pass/fail table. It is idempotent - re-run it freely. It:

1. finds or installs Python 3.12;
2. **deletes and recreates** `.venv` and installs `requirements.txt` into it;
3. finds or installs VS Code and its three extensions;
4. writes `%LOCALAPPDATA%\Microsoft\WindowsApps\spike.cmd` - a two-line batch
   file that runs `.venv\Scripts\python.exe tools\spike_ble.py %*`. That folder
   is on every Windows user's PATH by default, so `spike` works in any terminal
   immediately. This is the **only file written outside this folder**;
5. checks a Bluetooth radio is present;
6. runs `spike discover` and then `hello_hub.py` over Bluetooth (skip with
   `-NoVerify` if no hub is handy).

Then open the project in VS Code - double-click `FLL.code-workspace`, or
`code "<folder>"` - select the interpreter if asked (`.venv\Scripts\python.exe`
/ `.venv/bin/python`; settings already point there), and press `Ctrl+Shift+B`
(`Cmd+Shift+B`) with a program open.

Opening the folder auto-runs the task **"Check environment (runs on open)"**
(`tools/check_env.ps1` / `check_env.sh`) after VS Code asks once to allow
automatic tasks. It is silent when `.venv` and the `spike` command exist and
otherwise prints the one setup command to run - so a machine that has only had
the folder copied to it tells you what to do the moment it opens. The
workspace file itself holds nothing but the folder reference; `.vscode/` is
the single source of truth for settings, tasks and extensions.

### macOS (or Linux)

```bash
bash ~/OneDrive/FLL/setup.sh          # same steps, same pass/fail table
```

Differences from Windows, all handled by the script: Python and VS Code come
from Homebrew if `brew` exists (otherwise install them by hand and re-run); the
venv interpreter is `.venv/bin/python`; the `spike` command is written to
`~/.local/bin/spike` and one `export PATH=...` line is appended to `~/.zshrc`
(or `~/.bashrc`) if that folder is not already on PATH - open a new terminal
afterwards. **The first Bluetooth scan triggers a macOS permission dialog for
the terminal app (or VS Code); it must be allowed** (System Settings > Privacy &
Security > Bluetooth), or every scan silently finds nothing. In VS Code the
build shortcut is Cmd+Shift+B. See trap #15 for how robot matching differs.

### If setup.ps1 cannot be used

Do the same by hand:

```powershell
winget install --id Python.Python.3.12 -e --scope user
cd <folder>
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
winget install --id Microsoft.VisualStudioCode -e --scope user
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-python.pylint
# spike command:
Set-Content "$env:LOCALAPPDATA\Microsoft\WindowsApps\spike.cmd" -Encoding ASCII -Value "@echo off`r`n`"<folder>\.venv\Scripts\python.exe`" `"<folder>\tools\spike_ble.py`" %*"
```

## 5. Verify, in this order

```
spike --help                            # usage text -> the command resolves
spike discover                          # robot listed under Bluetooth with its address
spike info                              # "firmware 1.8.149  rpc 1.0.47  max packet 509B ... max chunk 4096B"
spike -v run programs\hello_hub.py      # ends with:  Hello from the hub   /  [hub] program stopped  / exit 0
.venv\Scripts\python -m pyright programs\   # 0 errors (reportMissingModuleSource warnings are expected)
```

Expected `-v run` transcript (robot1):

```
scanning for any SPIKE hub (10s)...
found BioBuddies_2 at E0:FF:F1:6C:45:B6
[hub] <- 0x01 ...
[hub] firmware 1.8.149  rpc 1.0.47  max packet 509B  max message 5000B  max chunk 4096B  product group 0
[hub] <- 0x47 47 00            clear slot acknowledged
[hub] <- 0x0D 0d 00            upload accepted
[hub] <- 0x11 11 00            chunk accepted
[hub] uploading 483/483 bytes
[hub] <- 0x1F 1f 00            start acknowledged
[hub] <- 0x20 20 00            program started
Hello from the hub
[hub] <- 0x20 20 01            program stopped
```

If `spike discover` shows nothing under Bluetooth: the hub is off, asleep, or
**connected to something** - most often the SPIKE app in a browser tab. A hub
connected to anything stops advertising. Blinking light = advertising; solid =
taken; off = press the hub's Bluetooth button.

## 6. Registering robot2 (or any new hub)

1. Switch on **only** robot2, Bluetooth light blinking, no SPIKE app running.
2. `spike discover` - it prints the hub's address and a JSON snippet.
3. Paste the address (and name) into `hubs.json` under `robot2`.
4. Plug robot2 into USB, `spike discover` again, paste `usb_serial`.
5. Test: `spike info --hub robot2`, then `spike run programs\hello_hub.py --hub robot2`.
6. Read its port layout (command in section 2) and write it into `notes`.

Naming rule: without `--hub`, Bluetooth takes whichever hub is advertising and
USB takes the one hub plugged in - fine when one robot is on. With both on, use
`--hub robot1` / `--hub robot2`; Bluetooth then matches by address **or by
name** (`ble_name`), so it is never ambiguous. Fill in both. On macOS only the
name can match (trap #15), so give the two robots different names in the SPIKE
app and record them.

## 7. Daily workflow (what the user does)

```
spike session                     # connect once, stay connected (from the project folder)
   spike> run programs\drive_demo.py
   spike> r                       # edit in VS Code, save, re-run - no rescan
   spike> stop                    # or Ctrl+C while it runs
   spike> quit                    # disconnect
```

or `Ctrl+Shift+B` (`Cmd+Shift+B` on macOS) in VS Code (one-shot: connect, run,
disconnect). Tasks are under Terminal > Run Task, grouped `Hub (BLE):` and
`Hub (USB):`; they pick `.venv\Scripts\python.exe` or `.venv/bin/python` by OS.

Finished code goes into the SPIKE app by pasting the file's contents into a
Python project there - or by `spike upload FILE --slot N`, which stores it in
the hub's slot exactly as the app would. `tools\llsp3.py` converts between
`.py` and the app's `.llsp3` project files.

## 8. How it works (architecture)

```
tools/spike_ble.py   one tool, two transports, one config
  Bluetooth ........ LEGO's published protocol (https://lego.github.io/spike-prime-docs/)
                      service 0000fd02-0000-1000-8000-00805f9b34fb
                      RX      0000fd02-0001-...  (write-without-response TO the hub)
                      TX      0000fd02-0002-...  (notifications FROM the hub)
                      framing: COBS, delimiter 0x02, max block 84, XOR 3, trailing 0x02
                      flow:    InfoRequest 0x00 -> InfoResponse 0x01 (max packet/chunk)
                               ClearSlot 0x46, StartFileUpload 0x0C, TransferChunk 0x10 (running CRC32),
                               ProgramFlowRequest 0x1E (action 0=start 1=stop), ProgramFlowNotification 0x20,
                               ConsoleNotification 0x21 = print() text
                      the uploaded file is ALWAYS named program.py (trap #6)
  USB .............. mpremote over the MicroPython REPL, addressed by USB serial (`id:...`)
hubs.json            robot name -> ble_address / usb_serial / notes
.vscode/tasks.json   every task = .venv python + tools/spike_ble.py ...
.vscode/settings.json  interpreter = .venv; Pylance stubs from typings/
typings/             .pyi stubs for the hub API, audited against the real hub (trap #10)
stubs-unavailable/   stubs for `app.*`, which this firmware lacks - parked so autocomplete cannot offer them
programs/            the user's programs; hello_hub.py (safe smoke test), drive_demo.py (drives motors)
projects/, tools/llsp3.py   .llsp3 <-> .py conversion for the SPIKE app
setup.ps1 / setup.sh   per-OS setup; tools/check_env.ps1 / .sh  the on-open check they satisfy
FLL.code-workspace     launcher only (folder reference); requirements.txt, manifest.json, this file
```

## 9. Traps - each of these cost real time

1. **The LEGO VS Code extension does not work with this hub.**
   `peterstaev.lego-spikeprime-mindstorms-vscode` speaks the legacy JSON-RPC
   protocol (`get_hub_info`, `start_write_program`). Hub OS 1.8.149 exposes a
   MicroPython REPL; send it `{"m":"get_hub_info",...}` and it echoes the JSON
   back as a Python dict at a `>>>` prompt. "Connecting to hub failed", always.
   It is in `unwantedRecommendations`. Do not install or debug it.

2. **`python` / `python3` on a fresh Windows PC are Microsoft Store stubs**
   (`%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe`). They are not the real
   interpreter and have none of our packages. Use `.venv\Scripts\python.exe`
   (which the tasks and `spike.cmd` do) or the full path to Python312.

3. **VS Code's terminal has a stale PATH** if VS Code started before Python was
   installed or PATH changed. `py`/`python` "not recognized" inside VS Code but
   fine elsewhere is this. `spike.cmd` sidesteps it (WindowsApps was on PATH
   from the start); otherwise restart VS Code entirely.

4. **Do not define a PowerShell function named `spike`.** Functions beat
   external commands in PowerShell, so a stale profile function would shadow
   `spike.cmd`. There are also two possible `Documents` folders (local and
   OneDrive-redirected) and profiles were found in the wrong one. `spike.cmd`
   on PATH avoids all of it. Two such profile files were created and then
   deleted during the build; none should exist now.

5. **The hub advertises only while connected to nothing.** The SPIKE web app
   in a Chrome tab holding a Web Bluetooth connection is invisible to Windows
   (no COM port, no device) yet makes the hub disappear from every scan. Close
   the tab / disconnect in the app. Also, hubs go to sleep after a few idle
   minutes - press a button.

6. **The uploaded file must be named `program.py`.** Uploading under the source
   filename is fully acknowledged by the hub - clear, upload, every chunk, start
   all return status 0 - and then nothing runs: no console output, no motion,
   no program-stopped notification. `spike_ble.py` always uses `program.py`.
   This is why "acknowledged" is not "working" (section 1).

7. **Over USB, touching a motor in the first ~50 ms fails with
   `OSError: [Errno 1] EPERM`**, reproducibly. `mpremote` resets the device
   stack when it enters the raw REPL and the ports are still enumerating.
   `drive_demo.py` has a `wait_for_ports()` helper (polls `device.ready()`).
   Over Bluetooth the same file works either way; the wait is harmless.

8. **`runloop.until()` returns `runloop.SUCCESS` (1) or `runloop.TIMEOUT`
   (2) - both truthy.** `if result:` is always true. Compare explicitly. And
   its default `timeout=0` means *wait forever* - a robot waiting for a colour
   it never sees drives until the battery dies. Always pass a timeout.

9. **Motor pairing does not persist across `mpremote run`s, but re-pairing
   within one program raises** `ValueError: PORTA is assigned to PAIR_1`.

10. **The upstream API stubs had real errors**, found by dumping `dir()` of
    every module off the live hub and diffing: `hub.soft_reset/reset/bootloader`
    declared but non-existent (they are `machine.*`); `hub.sound.sound` should
    be `play`; `motion_sensor.acceleration(raw_unfiltered)` made the argument
    required when it is optional; `device.set_mode/reset_mode/write_mode`
    missing; `runloop` constants undeclared. All fixed in `typings/`. Stubs
    for `time`, `machine`, `micropython`, `uctypes` were added because Pylance
    otherwise resolves them to desktop CPython's (`time.ticks_ms` "does not
    exist"). Verified: a stub in `typings/` overrides typeshed.

11. **`.venv` is not portable and OneDrive will try to sync it.** `setup.ps1`
    deletes and recreates it; a synced `.venv` from another PC is junk. If
    OneDrive sync churn on `.venv` becomes a problem, move the venv outside
    OneDrive and update the interpreter paths in settings/tasks/spike.cmd.

12. **This folder also holds the user's own FLL files** (spreadsheets, a PDF, a
    `.llsp3`) as OneDrive Files-On-Demand placeholders. Leave them alone; do
    not bulk-open or move them.

13. **Ctrl+C at the `spike>` prompt** exits Python, and because `spike` is a
    `.cmd`, Windows then asks "Terminate batch job (Y/N)?". Answer `N` - or
    just type `quit`, which is the intended exit. Ctrl+C *while a program is
    running* stops the program and stays connected.

14. **Version numbers lie.** `os.uname().release` on the hub is MicroPython's
    version (1.24.0), not the Hub OS version (1.8.149). The SPIKE app is 3.4.x.
    The Python language level is 3.4. Five different numbers. When in doubt,
    ask the hub (`spike info`, `spike usb exec`), do not reason from a number.

15. **macOS hides Bluetooth addresses.** CoreBluetooth never exposes a
    peripheral's real address; bleak reports a UUID that is unique *to that
    Mac* and different on every other machine. So `hubs.json`'s `ble_address`
    (`E0:FF:F1:6C:45:B6`) will never match on a Mac, and `spike discover` there
    prints UUIDs, not addresses. `spike_ble.py` therefore matches a named robot
    by `ble_address` **or** `ble_name`; on a Mac the name is the only thing that
    can match, so `ble_name` must be filled in and distinct per robot (robot1
    is `BioBuddies_2`). Do not paste a Mac's UUID into `ble_address` - it is
    meaningless anywhere else. Also on macOS: the first scan needs the
    Bluetooth permission dialog accepted for the terminal or VS Code, or it
    finds nothing forever with no error.

## 10. Do not

- install the LEGO VS Code extension, Pybricks, or any firmware "upgrade";
- copy `.venv` between machines, or `pip install` outside it;
- define a `spike` shell function or alias;
- rely on `python`/`py` resolving to the right interpreter;
- treat "upload acknowledged" as "program ran";
- edit anything in this folder that is not part of the project (section 9.12);
- change the on-hub filename from `program.py`.

## 11. Versions this was verified with (2026-09-13)

Windows 11 Enterprise 10.0.26100 · Python 3.12.10 · bleak 3.0.2 · mpremote
1.29.0 · pyserial 3.5 · pyright 1.1.414 · VS Code 1.10x with ms-python.python,
ms-python.vscode-pylance · Hub OS 1.8.149, RPC 1.0.47, MicroPython
v1.20.0-1742.gf212bbe83 (2025-03-27), max packet 509 B, max chunk 4096 B ·
robot1 Bluetooth `E0:FF:F1:6C:45:B6`, USB serial `335234693132`.
