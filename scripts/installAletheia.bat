@echo off
setlocal enabledelaydexpansion

echo [INFO] Starting Aletheia build process...

:: First navigate to the root directory
cd /d "%~do0.."

:: Verify the python installation is there
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not available in the system PATH.
    exit \b 1
)

:: Create and activate a local vitual env
echo [INFO] Creating virtual environment...
python -m venv build_env
call build_env\Scripts\activate

:: Install dependencies
echo [INFO] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -e
python -m pip install pyinstaller

:: Execute pyinstaller with spec
echo [INFO] Compiling the Aletheia binary...
if exist "Aletheia.spec" (
    pyinstaller Aletheia.spec --clean
) else (
    echo [ERROR] Aletheia.spec file not found in the root directory
    exit \b 1
)

:: Check for success
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed. Check logs for details
    exit \b 1
)

echo [INFO] Build complete.
echo [INFO] The compiled binary is located in the "dist" directory
exit \b 0