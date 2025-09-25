#!/bin/bash

# SIH Disk Wipeout - Standalone Executable Launcher
# This script makes it easy to run the SIH Disk Wipeout software

echo "=========================================="
echo "    SIH Disk Wipeout v1.0"
echo "    Secure Data Erasure Tool"
echo "=========================================="
echo ""

# Check if executable exists
if [ ! -f "./SIH_Disk_Wipeout" ] && [ ! -f "./dist/SIH_Disk_Wipeout" ]; then
    echo "Error: SIH_Disk_Wipeout executable not found!"
    echo "Please make sure you're in the correct directory."
    exit 1
fi

# Determine executable path
if [ -f "./dist/SIH_Disk_Wipeout" ]; then
    EXECUTABLE="./dist/SIH_Disk_Wipeout"
else
    EXECUTABLE="./SIH_Disk_Wipeout"
fi

# Make executable if not already
chmod +x "$EXECUTABLE"

# Check for command line arguments
if [ $# -eq 0 ]; then
    echo "Starting SIH Disk Wipeout GUI..."
    echo "Note: This will open the graphical interface."
    echo ""
    "$EXECUTABLE"
else
    echo "Running SIH Disk Wipeout with arguments: $@"
    echo ""
    "$EXECUTABLE" "$@"
fi
