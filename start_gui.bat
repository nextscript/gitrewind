@echo off
setlocal
cd /d "%~dp0"
set "APP=%~dp0git_rewind_gui.py"

REM pythonw = Python WITHOUT a console window
where pythonw >nul 2>&1
if %errorlevel%==0 goto :launch_pythonw

REM Fallback: only python available -> minimized window
where python >nul 2>&1
if %errorlevel%==0 goto :launch_min

echo Python was not found.
echo Please install Python (https://www.python.org) and run this BAT again.
pause
exit /b 1

:launch_pythonw
start "" pythonw "%APP%"
exit /b 0

:launch_min
echo Note: pythonw was not found - starting in a minimized window.
start /min python "%APP%"
exit /b 0
