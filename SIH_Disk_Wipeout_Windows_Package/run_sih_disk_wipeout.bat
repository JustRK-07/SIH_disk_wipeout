@echo off
REM SIH Disk Wipeout - Windows Batch Launcher
REM This script makes it easy to run the SIH Disk Wipeout software on Windows

echo ==========================================
echo     SIH Disk Wipeout v1.0
echo     Secure Data Erasure Tool
echo ==========================================
echo.

REM Check if executable exists
if not exist "SIH_Disk_Wipeout_Windows.exe" (
    echo Error: SIH_Disk_Wipeout_Windows.exe not found!
    echo Please make sure you're in the correct directory.
    pause
    exit /b 1
)

REM Check for command line arguments
if "%~1"=="" (
    echo Starting SIH Disk Wipeout GUI...
    echo Note: This will open the graphical interface.
    echo.
    SIH_Disk_Wipeout_Windows.exe
) else (
    echo Running SIH Disk Wipeout with arguments: %*
    echo.
    SIH_Disk_Wipeout_Windows.exe %*
)

pause
