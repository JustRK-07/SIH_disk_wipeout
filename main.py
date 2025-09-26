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
from src.core.sudo_manager import SudoManager

def check_sudo_permissions():
    """Check and request sudo permissions at startup"""
    print("🔐 SIH Disk Wipeout - Secure Data Erasure Tool")
    print("=" * 60)
    print("This application requires administrator privileges to perform disk wiping operations.")
    print("Please enter your sudo password when prompted.")
    print("=" * 60)
    
    sudo_manager = SudoManager()
    
    # Check if we already have sudo permissions
    if sudo_manager._check_passwordless_sudo('true'):
        print("✅ Sudo permissions already available (passwordless sudo configured)")
        return True
    
    # Request sudo password
    password = sudo_manager.request_sudo_password()
    if password:
        print("✅ Sudo permissions verified successfully!")
        return True
    else:
        print("❌ Failed to obtain sudo permissions.")
        print("\nAlternative options:")
        print("1. Run the application with sudo: sudo python3 main.py")
        print("2. Configure passwordless sudo for your user")
        print("3. Run specific commands with sudo: sudo python3 main.py --cli wipe /dev/sda --method dd")
        return False

def main():
    """Main entry point for the application"""
    setup_logger()
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting SIH Disk Wipeout on {platform.system()} {platform.release()}")
    
    # Check sudo permissions at startup
    if not check_sudo_permissions():
        print("\n❌ Cannot proceed without sudo permissions.")
        sys.exit(1)
    
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
