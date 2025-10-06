@echo off
setlocal EnableExtensions EnableDelayedExpansion

if not exist "dist\PixelPad\PixelPad.exe" (
    echo missing
)

echo done
