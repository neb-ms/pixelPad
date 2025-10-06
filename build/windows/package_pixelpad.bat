@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.." >NUL 2>&1
if errorlevel 1 (
    echo Failed to change directory to project root.
    exit /b 1
)

python -m PyInstaller --version >NUL 2>&1
if errorlevel 1 (
    echo PyInstaller is not installed in the current Python environment.
    echo Install it first with: python -m pip install --user pyinstaller
    popd >NUL 2>&1
    exit /b 1
)

python -m PyInstaller --noconfirm --clean "%SCRIPT_DIR%pixelpad.spec"
set "BUILD_ERROR=%ERRORLEVEL%"

popd >NUL 2>&1
exit /b %BUILD_ERROR%
