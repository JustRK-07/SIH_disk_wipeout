#!/usr/bin/env python3
"""
Test script for Disk Wipeout application
Verifies basic functionality without performing actual disk operations
"""

import sys
import os
import platform
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.disk_manager import DiskManager
from src.utils.logger import setup_logger

def test_disk_manager():
    """Test the disk manager functionality"""
    print("Testing Disk Wipeout Application")
    print("=" * 50)
    
    # Setup logging
    setup_logger(logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize disk manager
        print(f"Platform: {platform.system()} {platform.release()}")
        disk_manager = DiskManager()
        
        # Test getting available disks
        print("\n1. Testing disk detection...")
        disks = disk_manager.get_available_disks()
        print(f"Found {len(disks)} disks:")
        
        for i, disk in enumerate(disks, 1):
            size_gb = disk.size // (1024**3) if disk.size > 0 else 0
            is_writable = disk_manager.is_disk_writable(disk.device)
            status = "Writable" if is_writable else "Read-only"
            
            print(f"  {i}. {disk.device}")
            print(f"     Size: {size_gb}GB")
            print(f"     Type: {disk.type.upper()}")
            print(f"     Model: {disk.model}")
            print(f"     Status: {status}")
            print()
        
        # Test getting wipe methods
        print("2. Testing wipe methods...")
        methods = disk_manager.get_wipe_methods()
        print(f"Available wipe methods: {', '.join(methods)}")
        
        # Test system disk detection
        print("\n3. Testing system disk detection...")
        system_disks = disk_manager.get_system_disks()
        print(f"System disks: {system_disks}")
        
        # Test verification manager
        print("\n4. Testing verification manager...")
        verification_manager = disk_manager.verification_manager
        history = verification_manager.get_verification_history()
        print(f"Verification history: {len(history)} records")
        
        print("\n✅ All tests completed successfully!")
        print("\nNote: This test only verifies detection and initialization.")
        print("No actual disk wiping operations were performed.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}")
        return False
    
    return True

def test_imports():
    """Test that all modules can be imported"""
    print("Testing module imports...")
    
    try:
        from src.core.disk_manager import DiskManager
        from src.core.verification import VerificationManager
        from src.gui.main_window import MainWindow
        from src.cli.cli_interface import CLIInterface
        from src.utils.logger import setup_logger
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    print("Disk Wipeout - Test Suite")
    print("=" * 30)
    
    # Test imports first
    if not test_imports():
        sys.exit(1)
    
    # Test disk manager
    if not test_disk_manager():
        sys.exit(1)
    
    print("\n🎉 All tests passed! The application is ready to use.")
    print("\nTo run the application:")
    print("  GUI mode: python main.py")
    print("  CLI mode: python main.py --cli")
