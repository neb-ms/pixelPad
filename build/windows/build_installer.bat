@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.." >NUL 2>&1
if errorlevel 1 goto :pushd_failed

if not exist "dist\PixelPad\PixelPad.exe" goto :missing_bundle

set "ISCC_CMD="
where iscc >NUL 2>&1
if not errorlevel 1 set "ISCC_CMD=iscc"
if not defined ISCC_CMD (
    set "ISCC_CANDIDATE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    if exist "%ISCC_CANDIDATE%" set "ISCC_CMD=%ISCC_CANDIDATE%"
)
if not defined ISCC_CMD (
    set "ISCC_CANDIDATE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    if exist "%ISCC_CANDIDATE%" set "ISCC_CMD=%ISCC_CANDIDATE%"
)
if not defined ISCC_CMD (
    set "ISCC_CANDIDATE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if exist "%ISCC_CANDIDATE%" set "ISCC_CMD=%ISCC_CANDIDATE%"
)
if not defined ISCC_CMD goto :missing_iscc

"%ISCC_CMD%" "%SCRIPT_DIR%pixelpad-installer.iss"
set "BUILD_ERROR=%ERRORLEVEL%"
popd >NUL 2>&1
exit /b %BUILD_ERROR%

:missing_bundle
echo PyInstaller output not found at dist\PixelPad.
echo Run build\windows\package_pixelpad.bat first.
popd >NUL 2>&1
exit /b 1

:missing_iscc
echo Inno Setup Compiler (iscc.exe) not found in PATH.
echo Install Inno Setup and add iscc.exe to PATH.
popd >NUL 2>&1
exit /b 1

:pushd_failed
echo Failed to change directory to project root.
exit /b 1
