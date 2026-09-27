@echo off
rem FLL patch v1 - Windows launcher. Double-click me. Runs apply.ps1 next to me.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply.ps1"
