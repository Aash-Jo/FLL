# Runs automatically when the folder opens in VS Code (see tasks.json).
# Silent when this PC is set up; otherwise prints the one command to run.
$Root = Split-Path $PSScriptRoot -Parent
$problems = @()
if (-not (Test-Path (Join-Path $Root ".venv\Scripts\python.exe"))) { $problems += "no .venv" }
if (-not (Get-Command spike -ErrorAction SilentlyContinue)) { $problems += "no 'spike' command" }
if ($problems.Count -eq 0) { exit 0 }
[Console]::Error.WriteLine("")
[Console]::Error.WriteLine("FLL is not set up on this PC yet ($($problems -join ', ')). Run this once, then reopen VS Code:")
[Console]::Error.WriteLine("")
[Console]::Error.WriteLine("    powershell -ExecutionPolicy Bypass -File `"$Root\setup.ps1`"")
[Console]::Error.WriteLine("")
exit 1
