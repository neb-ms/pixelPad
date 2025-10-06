@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.." >NUL 2>&1
if errorlevel 1 (
    echo Failed to change directory to project root.
    exit /b 1
)

call "%SCRIPT_DIR%package_pixelpad.bat"
if errorlevel 1 (
    echo PyInstaller packaging failed. Aborting release build.
    popd >NUL 2>&1
    exit /b %ERRORLEVEL%
)

call "%SCRIPT_DIR%build_installer.bat"
if errorlevel 1 (
    echo Installer compilation failed. Aborting release build.
    popd >NUL 2>&1
    exit /b %ERRORLEVEL%
)

popd >NUL 2>&1

echo.
echo Release artifacts ready:
echo   dist\PixelPad (portable bundle)
echo   dist\PixelPad.exe (one-file executable)
echo   build\windows\installer\PixelPad-Setup.exe (Windows installer)
echo.
exit /b 0
