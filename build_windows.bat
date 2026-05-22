@echo off
REM Build CS2 Quote floating window into a single .exe on Windows.
REM Pure ASCII script - do not add Chinese characters here.

setlocal EnableDelayedExpansion
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Install Python 3.10+ from https://www.python.org/
    echo During install, check "Add Python to PATH", then run this script again.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [FAIL] Could not create virtual environment.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo [2/3] Installing dependencies via Tsinghua mirror...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
if errorlevel 1 (
    echo [FAIL] pip install requirements failed.
    pause
    exit /b 1
)
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "pyinstaller>=6.0"
if errorlevel 1 (
    echo [FAIL] pip install pyinstaller failed.
    pause
    exit /b 1
)

echo [3/3] Building exe with PyInstaller...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm cs2_quote.spec
if errorlevel 1 (
    echo [FAIL] PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  SUCCESS. Look inside the "dist" folder for the .exe.
echo  Double-click the .exe to run.
echo ============================================================
pause
