<#
FLL patch v1 - apply the status-bar buttons to an FLL folder that has the old setup.
Windows. Double-click apply.cmd (it runs this with the right policy).

  1. Copies files\** into the FLL folder (the folder this patch_v1 sits in),
     backing up anything it replaces into backup-<date>\ here.
  2. Installs the VS Code extension that draws the buttons.
  3. Checks the folder's .venv still runs the tool.
#>
$ErrorActionPreference = "Stop"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Split-Path -Parent $Here
$Ext    = "spencerwmiles.vscode-task-buttons"
$Unwanted = "peterstaev.lego-spikeprime-mindstorms-vscode"

function Done($code) { Write-Host ""; Read-Host "Press Enter to close" | Out-Null; exit $code }
function IsFLL($p) {
    $p -and (Test-Path (Join-Path $p "hubs.json")) -and (Test-Path (Join-Path $p "tools\spike_ble.py"))
}

Write-Host "FLL patch v1 - status-bar buttons"
Write-Host "=================================="
if (-not (IsFLL $Target)) {
    Write-Host "This patch_v1 folder is not inside an FLL folder (no hubs.json / tools\spike_ble.py next to it)."
    $Target = Read-Host "Type the full path of the FLL folder on this PC"
    if (-not (IsFLL $Target)) { Write-Host "That is not the FLL folder either. Nothing was changed."; Done 1 }
}
Write-Host "FLL folder: $Target"

# ---- 1. copy files -----------------------------------------------------------
$Files  = Join-Path $Here "files"
$Backup = Join-Path $Here ("backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$copied = @()
Get-ChildItem -LiteralPath $Files -Recurse -File -Force | ForEach-Object {
    $rel  = $_.FullName.Substring($Files.Length + 1)
    $dest = Join-Path $Target $rel
    if (Test-Path -LiteralPath $dest) {
        $bak = Join-Path $Backup $rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $bak) | Out-Null
        Copy-Item -LiteralPath $dest -Destination $bak -Force
        $what = "replaced"
    } else {
        $what = "added   "
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
    $copied += "  $what  $rel"
}
Write-Host ""
Write-Host "Files:"
$copied | ForEach-Object { Write-Host $_ }
if (Test-Path -LiteralPath $Backup) { Write-Host "  (old versions saved in $Backup)" }

# ---- 2. VS Code extension ----------------------------------------------------
Write-Host ""
$code = $null
$c = Get-Command code -ErrorAction SilentlyContinue
if ($c) { $code = $c.Source }
elseif (Test-Path (Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code\bin\code.cmd")) {
    $code = Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code\bin\code.cmd"
}
$extOk = $false
if ($code) {
    # code.cmd prints Node warnings on stderr; under "Stop" those would abort the script.
    $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & $code --install-extension $Ext --force *> $null
    $list = @(& $code --list-extensions 2>$null)
    $ErrorActionPreference = $eap
    $extOk = ($list -contains $Ext)
    if ($extOk) { Write-Host "Extension: $Ext installed." }
    else        { Write-Host "Extension: could not confirm $Ext. In VS Code, Extensions (Ctrl+Shift+X), search 'Task Buttons', Install." }
    if ($list -contains $Unwanted) {
        Write-Host "Note: the LEGO SPIKE Prime extension ($Unwanted) is installed. It cannot talk to these hubs;"
        Write-Host "      its 'LEGO Hub: Disconnected' status item is unrelated to the buttons. Uninstalling it is optional."
    }
} else {
    Write-Host "Extension: VS Code's 'code' command was not found. In VS Code, Extensions (Ctrl+Shift+X), search 'Task Buttons', Install."
}

# ---- 3. venv check -----------------------------------------------------------
Write-Host ""
$vpy = Join-Path $Target ".venv\Scripts\python.exe"
$venvOk = $false
if (Test-Path -LiteralPath $vpy) {
    Push-Location $Target
    $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    try {
        $out = & $vpy "tools\spike_ble.py" send ping 2>&1 | Out-String
        # "no session open" normally; "[session] connected" if a session happens to be open.
        $venvOk = ($out -match "no session open|\[session\] connected")
    } catch { $venvOk = $false }
    $ErrorActionPreference = $eap
    Pop-Location
}
if ($venvOk) { Write-Host "Python: .venv runs the new tool. No rebuild needed." }
else {
    Write-Host "Python: .venv did not run the tool. Rebuild it once (safe, takes a minute):"
    Write-Host "    powershell -ExecutionPolicy Bypass -File `"$Target\setup.ps1`" -NoVerify"
}

# ---- summary -----------------------------------------------------------------
Write-Host ""
Write-Host "Next: open FLL.code-workspace in VS Code. Buttons (Connect / Run / Stop / Disconnect / Robots)"
Write-Host "are at the bottom-left. If they are missing, Ctrl+Shift+P -> 'Reload Window'."
if ($extOk -and $venvOk) { Done 0 } else { Done 1 }
