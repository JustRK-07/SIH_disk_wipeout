#!/usr/bin/env python3
"""
SIH Disk Wipeout - Secure Data Erasure Tool
Cross-platform data wiping application
"""

import sys
import os
import platform
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.disk_manager import DiskManager
from src.gui.enhanced_main_window import EnhancedMainWindow
from src.utils.logger import setup_logger

def main():
    """Main entry point for the application"""
    setup_logger()
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting SIH Disk Wipeout on {platform.system()} {platform.release()}")
    
    try:
        disk_manager = DiskManager()
        
        if len(sys.argv) > 1 and sys.argv[1] == '--cli':
            sys.argv.pop(1)
            from src.cli.cli_interface import CLIInterface
            cli = CLIInterface(disk_manager)
            cli.run()
        else:
            # Always use enhanced GUI (default)
            app = EnhancedMainWindow(disk_manager)
            app.run()
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
