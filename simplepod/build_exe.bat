@echo off
setlocal

cd /d "%~dp0"
pyinstaller simplepod.spec --clean --noconfirm
if errorlevel 1 (
    echo Build failed!
    exit /b 1
)

if not exist "release" mkdir release
xcopy /E /I /Y "dist\SimplePod" "release\SimplePod"

echo.
echo Build successful! Output copied to release\SimplePod
endlocal
