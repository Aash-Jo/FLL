# START HERE - FLL robots from VS Code over Bluetooth

This folder is the whole project. Copy it (or let OneDrive sync it) to any PC,
run one script, and you can program the robots from VS Code with no cable.

## 1. Set up a computer (first time only)

**Windows** - open PowerShell and run:

```
powershell -ExecutionPolicy Bypass -File "C:\Users\<you>\OneDrive\FLL\setup.ps1"
```

**Mac** - open Terminal and run:

```
bash ~/OneDrive/FLL/setup.sh
```

(adjust the path to wherever OneDrive put the folder - or drag the folder into
the Terminal window to paste its path.) The first time it scans for a robot,
macOS asks whether Terminal may use Bluetooth - click **Allow**.

Either script installs Python 3.12 and VS Code if missing, builds this folder's
`.venv`, installs the packages, adds the `spike` command, and finishes by
running `hello_hub.py` on a robot if one is on. It prints a pass/fail table.
Safe to re-run any time.

Then open the project in VS Code: **double-click `FLL.code-workspace`** in
this folder (or `code "<path to the FLL folder>"`). The first time, VS Code
asks whether to allow automatic tasks - say **Allow**. From then on, opening
the project silently checks the machine is set up, and if it is not, shows
the one setup command to run.

## 2. Every day

Robot on, **Bluetooth light blinking**, SPIKE app closed. Then:

**Buttons** at the bottom-left of the VS Code window:

1. Click **Connect**. The panel says which robot it found.
2. Open a program, click **Run**. The robot runs it; output shows in the panel.
3. Edit, save, click **Run** again. Or open a different program and click **Run**.
4. **Stop** stops the robot. **Disconnect** when you are done.

Skipping Connect is fine: Run then connects, runs and disconnects by itself.
Both robots on? Use **Robots > Connect to a chosen robot**.

**Keyboard:** open a program, press **Ctrl+Shift+B** (Mac: **Cmd+Shift+B**).
It connects, runs it, shows the output, disconnects.

**Terminal (stay connected while you edit):**

```
cd <the FLL folder>          e.g.  cd C:\Users\<you>\OneDrive\FLL   or   cd ~/OneDrive/FLL
spike session
   spike> run programs\hello_hub.py
   spike> r          <- re-run after you save an edit
   spike> stop       <- or Ctrl+C while it runs
   spike> quit       <- disconnect
```

If it says "no SPIKE hub found": the light is not blinking. Press the hub's
Bluetooth button, and make sure the SPIKE app is closed - a hub connected to
the app is invisible to everything else.

## 3. Two robots

Only one on? Nothing to do - it connects to whichever is advertising.
Both on? Name it:  `spike session --hub robot2`

**Register robot2** (once): switch on only robot2, run `spike discover`, paste
the address **and name** it prints into `hubs.json` under `robot2`. Plug it
into USB and run `spike discover` again for its USB serial.

On a **Mac**, Bluetooth addresses are hidden, so robots are told apart by
their **name** (`ble_name` in `hubs.json`). Give each robot a different name
in the SPIKE app and keep `ble_name` filled in.

## 4. Useful commands

```
spike discover                    what robots are in range (Bluetooth and USB)
spike run programs\x.py           run once and disconnect
spike upload programs\x.py --slot 3   store in a hub slot without running
spike usb run programs\x.py       over the USB cable instead
spike usb repl                    interactive Python prompt on the hub (USB only)
```

## 5. Finished code into the SPIKE app

Paste the program into a Python project in the app, or `spike upload` it into
a slot - it lands exactly where the app would put it.

## 6. On this PC, one time

An empty `C:\Users\bpatel\spike-prime` folder is left over from the move.
Close any terminal or VS Code window that is open on it, then delete it, and
reopen VS Code on this folder.

## If anything goes wrong

`HANDOFF.md` has the full story: every requirement, every step, and every
trap that was hit building this. Give it to whoever (or whatever) is setting
up the next PC.
