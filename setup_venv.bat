@echo off
REM setup_venv.bat - Create virtual environment using uv on Windows

echo Creating virtual environment with uv...
uv venv venv

if errorlevel 1 (
    echo Error: uv not found!
    echo.
    echo Please install uv first:
    echo   Option 1: pip install uv
    echo   Option 2: Download from https://github.com/astral-sh/uv
    echo   Option 3: Use PowerShell: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

echo.
echo Virtual environment created successfully!
echo.
echo To activate the virtual environment, run:
echo   venv\Scripts\activate.bat
echo.
echo Or just run start_both.bat - it will use venv Python automatically.
echo.
pause

