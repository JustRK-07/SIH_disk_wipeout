#!/usr/bin/env python3
"""
Disk Wipeout - Cross-platform data wiping application
Supports Windows, Linux, and Android platforms
"""

import sys
import os
import platform
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.disk_manager import DiskManager
from src.gui.main_window import MainWindow
from src.utils.logger import setup_logger

def main():
    """Main entry point for the application"""
    # Setup logging
    setup_logger()
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting Disk Wipeout on {platform.system()} {platform.release()}")
    
    try:
        # Initialize disk manager
        disk_manager = DiskManager()
        
        # Check if running in GUI mode or CLI mode
        if len(sys.argv) > 1 and sys.argv[1] == '--cli':
            # Remove --cli from argv and pass to CLI
            sys.argv.pop(1)
            from src.cli.cli_interface import CLIInterface
            cli = CLIInterface(disk_manager)
            cli.run()
        else:
            # Launch GUI
            app = MainWindow(disk_manager)
            app.run()
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
