@echo off
REM Move to the directory of this script
cd /d "%~dp0"

REM Check if 'uv' is installed
where uv >nul 2>nul
if errorlevel 1 (
    pip install uv
)

REM Recreate venv only if needed
if not exist ".venv" (
    echo Creating virtual environment...
    uv venv .venv
) else (
    echo Using existing virtual environment...
)

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Install the required packages
uv pip install src/cli/

REM Set the PYTHONPATH environment variable
set PYTHONPATH=%PYTHONPATH%;%CD%\src\cli\