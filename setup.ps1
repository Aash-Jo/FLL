<#
.SYNOPSIS
  Set up this PC to program the SPIKE Prime robots from this folder - over
  Bluetooth by default, USB as a fallback. Safe to re-run at any time.

.DESCRIPTION
  Run from anywhere:

      powershell -ExecutionPolicy Bypass -File "<this folder>\setup.ps1"

  What it does (all user-scope, no administrator rights needed):
    1. Finds Python 3.12, installing it with winget if missing.
    2. Recreates .venv in this folder and installs requirements.txt into it.
       (A venv is never portable between PCs - it is always rebuilt here.)
    3. Finds VS Code, installing it with winget if missing, and installs the
       extensions listed in .vscode\extensions.json.
    4. Writes the `spike` command (spike.cmd) into %LOCALAPPDATA%\Microsoft\WindowsApps,
       which is on every user's PATH - so `spike session` works in any terminal
       with no profile, PATH edit, or restart. This is the ONE file written
       outside this folder.
    5. Checks a Bluetooth radio is present.
    6. Unless -NoVerify: looks for a hub and runs programs\hello_hub.py on it
       over Bluetooth. The hub must be on, Bluetooth light blinking, and not
       connected to the SPIKE app.

  Everything it writes is either inside this folder (.venv) or the single
  spike.cmd above. Nothing else on the machine is changed.

.PARAMETER NoVerify
  Skip step 6 (no hub handy).
.PARAMETER SkipVSCode
  Skip step 3.
#>
param(
    [switch]$NoVerify,
    [switch]$SkipVSCode
)

$ErrorActionPreference = "Continue"   # native tools write warnings to stderr; judge them by results, not stream
$Root       = $PSScriptRoot
$KnownPy    = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$Venv       = Join-Path $Root ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$Tool       = Join-Path $Root "tools\spike_ble.py"
$results    = New-Object System.Collections.ArrayList

function Step($name, [bool]$ok, $detail) {
    [void]$results.Add([pscustomobject]@{ Step = $name; OK = $ok; Detail = $detail })
    $mark = "FAIL"; if ($ok) { $mark = " OK " }
    Write-Host ("[{0}] {1} - {2}" -f $mark, $name, $detail)
}

Write-Host ""
Write-Host "== SPIKE Prime robot setup ==" -ForegroundColor Cyan
Write-Host "Project folder: $Root"
Write-Host ""

# ---------------------------------------------------------------- 1. Python
function Find-Python312 {
    if (Test-Path $KnownPy) { return $KnownPy }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $p = (& py -3.12 -c "import sys; print(sys.executable)" 2>$null)
            if ($p -and (Test-Path $p)) { return $p }
        } catch { }
    }
    return $null
}

$python = Find-Python312
if (-not $python) {
    Write-Host "Python 3.12 not found - installing with winget (user scope)..."
    winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements | Out-Host
    $python = Find-Python312
}
if ($python) {
    $ver = (& $python --version) 2>&1
    Step "Python 3.12" $true "$python ($ver)"
} else {
    Step "Python 3.12" $false "not found and winget install failed. Install Python 3.12 (python.org, 'Install for me only'), then re-run."
    Write-Host ""; $results | Format-Table -AutoSize | Out-Host; exit 1
}

# ---------------------------------------------------------------- 2. venv
if (Test-Path $Venv) {
    Write-Host "Removing existing .venv (venvs are not portable; rebuilding fresh)..."
    Remove-Item -LiteralPath $Venv -Recurse -Force
}
& $python -m venv $Venv
if (-not (Test-Path $VenvPython)) {
    Step ".venv" $false "python -m venv failed"
    Write-Host ""; $results | Format-Table -AutoSize | Out-Host; exit 1
}
& $VenvPython -m pip install --quiet --upgrade pip
& $VenvPython -m pip install --quiet -r (Join-Path $Root "requirements.txt")
$pipOk = ($LASTEXITCODE -eq 0)
$installed = (& $VenvPython -m pip list --format=freeze 2>$null | Where-Object { $_ -match '^(bleak|mpremote|pyserial|pyright)==' }) -join ", "
Step ".venv + packages" $pipOk $installed

# ---------------------------------------------------------------- 3. VS Code
if (-not $SkipVSCode) {
    function Find-Code {
        $c = Get-Command code -ErrorAction SilentlyContinue
        if ($c) { return $c.Source }
        $k = Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code\bin\code.cmd"
        if (Test-Path $k) { return $k }
        return $null
    }
    $code = Find-Code
    if (-not $code) {
        Write-Host "VS Code not found - installing with winget (user scope)..."
        winget install --id Microsoft.VisualStudioCode -e --scope user --silent --accept-package-agreements --accept-source-agreements | Out-Host
        $code = Find-Code
    }
    if ($code) {
        $raw  = Get-Content (Join-Path $Root ".vscode\extensions.json") -Raw
        $json = (($raw -split "`n") | Where-Object { $_ -notmatch '^\s*//' }) -join "`n" | ConvertFrom-Json
        foreach ($ext in $json.recommendations) {
            & $code --install-extension $ext --force 2>$null | Out-Null
        }
        Step "VS Code + extensions" $true ("$code ; " + ($json.recommendations -join ", "))
    } else {
        Step "VS Code" $false "not found and winget install failed. Install from code.visualstudio.com, then re-run (or pass -SkipVSCode)."
    }
}

# ---------------------------------------------------------------- 4. spike command
$appsDir = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
if (-not (Test-Path $appsDir)) { New-Item -ItemType Directory -Force -Path $appsDir | Out-Null }
$cmdPath = Join-Path $appsDir "spike.cmd"
$cmdBody = "@echo off`r`n`"$VenvPython`" `"$Tool`" %*`r`n"
Set-Content -LiteralPath $cmdPath -Value $cmdBody -Encoding ASCII -NoNewline
$onPath = @($env:Path -split ';' | Where-Object { $_.TrimEnd('\') -ieq $appsDir.TrimEnd('\') }).Count -gt 0
$note = $cmdPath
if (-not $onPath) { $note += "  (WindowsApps is not on PATH in THIS session; it is on the user PATH by default - open a new terminal)" }
Step "spike command" (Test-Path $cmdPath) $note

# ---------------------------------------------------------------- 5. Bluetooth
$radio = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue |
    Where-Object { $_.Status -eq 'OK' -and $_.FriendlyName -match 'Bluetooth' -and $_.FriendlyName -notmatch 'Enumerator|Attribute|Access Profile|Device Information|RFCOMM|Personal Area' } |
    Select-Object -First 1
if ($radio) { Step "Bluetooth radio" $true $radio.FriendlyName }
else        { Step "Bluetooth radio" $false "no Bluetooth adapter reported OK - Bluetooth path will not work on this PC; USB still will" }

# ---------------------------------------------------------------- 6. verify
& $VenvPython $Tool --help | Out-Null
Step "tool runs" ($LASTEXITCODE -eq 0) "tools\spike_ble.py --help"

if (-not $NoVerify) {
    Write-Host ""
    Write-Host "Looking for hubs (Bluetooth, then USB)..." -ForegroundColor Cyan
    & $VenvPython $Tool discover --seconds 6
    Write-Host ""
    Write-Host "Running programs\hello_hub.py over Bluetooth on whichever hub is advertising..." -ForegroundColor Cyan
    & $VenvPython $Tool -v run (Join-Path $Root "programs\hello_hub.py") --timeout 20
    if ($LASTEXITCODE -eq 0) {
        Step "hello_hub over Bluetooth" $true "program ran on the hub and its print() came back"
    } else {
        Step "hello_hub over Bluetooth" $false "no hub reachable, or run failed. Hub on? Bluetooth light blinking? SPIKE app closed? Then: spike run programs\hello_hub.py"
    }
}

# ---------------------------------------------------------------- summary
Write-Host ""
Write-Host "== Summary ==" -ForegroundColor Cyan
$results | Format-Table -AutoSize -Wrap | Out-Host
$failed = @($results | Where-Object { -not $_.OK }).Count
if ($failed -eq 0) {
    Write-Host "All steps passed." -ForegroundColor Green
    Write-Host "Next:  code `"$Root`"   then open a program and press Ctrl+Shift+B"
    Write-Host "  or:  spike session      (in a new terminal, from this folder)"
    exit 0
} else {
    Write-Host "$failed step(s) need attention - see above." -ForegroundColor Yellow
    exit 1
}
