@echo off
setlocal
cd /d "%~dp0"
set "APP=%~dp0git_rewind_gui.py"

REM pythonw = Python OHNE Konsolen-Fenster
where pythonw >nul 2>&1
if %errorlevel%==0 goto :launch_pythonw

REM Fallback: nur python vorhanden -> minimiertes Fenster
where python >nul 2>&1
if %errorlevel%==0 goto :launch_min

echo Python wurde nicht gefunden.
echo Bitte Python installieren (https://www.python.org) und diese BAT erneut starten.
pause
exit /b 1

:launch_pythonw
start "" pythonw "%APP%"
exit /b 0

:launch_min
echo Hinweis: pythonw wurde nicht gefunden - starte mit minimiertem Fenster.
start /min python "%APP%"
exit /b 0
