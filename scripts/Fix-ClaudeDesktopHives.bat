@echo off
REM Launcher for Fix-ClaudeDesktopHives.ps1 - self-elevates to Administrator.
REM Clears stale Claude Desktop AppX container hives (error 0x80070020).

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Fix-ClaudeDesktopHives.ps1"
