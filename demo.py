#!/usr/bin/env python3
"""
Demo script for Disk Wipeout application
Shows the application capabilities without performing actual disk operations
"""

import sys
import os
import platform
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.disk_manager import DiskManager
from src.utils.logger import setup_logger

def demo_disk_detection():
    """Demonstrate disk detection capabilities"""
    print("🔍 Disk Detection Demo")
    print("=" * 50)
    
    disk_manager = DiskManager()
    disks = disk_manager.get_available_disks()
    
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Found {len(disks)} storage devices:")
    print()
    
    for i, disk in enumerate(disks, 1):
        size_gb = disk.size // (1024**3) if disk.size > 0 else 0
        is_writable = disk_manager.is_disk_writable(disk.device)
        status = "✅ Writable" if is_writable else "❌ Read-only"
        
        print(f"  {i}. {disk.device}")
        print(f"     📏 Size: {size_gb:,}GB")
        print(f"     💾 Type: {disk.type.upper()}")
        print(f"     🏷️  Model: {disk.model}")
        print(f"     🔒 Status: {status}")
        if disk.mountpoint:
            print(f"     📁 Mounted at: {disk.mountpoint}")
        print()

def demo_wipe_methods():
    """Demonstrate available wipe methods"""
    print("🛠️  Wipe Methods Demo")
    print("=" * 50)
    
    disk_manager = DiskManager()
    methods = disk_manager.get_wipe_methods()
    
    print("Available wipe methods for this platform:")
    print()
    
    method_descriptions = {
        'secure': 'Multi-pass secure wipe (recommended for sensitive data)',
        'quick': 'Single-pass quick wipe (faster, less secure)',
        'dd': 'DD-based wiping with random data (very secure)',
        'cipher': 'Windows Cipher.exe free space wipe',
        'hdparm': 'Linux hdparm secure erase (hardware-level)',
        'nvme': 'NVMe secure format (SSD-specific)',
        'blkdiscard': 'TRIM-based discard (SSD-optimized)',
        'saf': 'Android Storage Access Framework'
    }
    
    for method in methods:
        description = method_descriptions.get(method, 'Custom wipe method')
        print(f"  🔧 {method:<12} - {description}")
    
    print()

def demo_verification():
    """Demonstrate verification capabilities"""
    print("🔐 Verification Demo")
    print("=" * 50)
    
    disk_manager = DiskManager()
    verification_manager = disk_manager.verification_manager
    
    print("Verification features:")
    print("  ✅ Sample-based verification")
    print("  ✅ Pattern detection")
    print("  ✅ Entropy analysis")
    print("  ✅ Certificate generation")
    print("  ✅ Proof-of-erasure documentation")
    print()
    
    # Show verification history
    history = verification_manager.get_verification_history()
    print(f"Verification history: {len(history)} records")
    
    if history:
        print("Recent verifications:")
        for record in history[:3]:  # Show last 3
            device = record.get('device', 'Unknown')
            timestamp = record.get('timestamp', 'Unknown')
            clean_pct = record.get('analysis', {}).get('clean_percentage', 0)
            print(f"  📄 {device} - {clean_pct:.1f}% clean ({timestamp})")
    else:
        print("  No verification records found")
    print()

def demo_safety_features():
    """Demonstrate safety features"""
    print("🛡️  Safety Features Demo")
    print("=" * 50)
    
    disk_manager = DiskManager()
    system_disks = disk_manager.get_system_disks()
    
    print("Safety features:")
    print("  🔒 System disk protection")
    print("  ⚠️  Confirmation prompts")
    print("  🔍 Writable disk verification")
    print("  📊 Progress monitoring")
    print("  📝 Comprehensive logging")
    print()
    
    print(f"Protected system disks: {len(system_disks)}")
    for disk in system_disks:
        print(f"  🚫 {disk}")
    print()

def demo_cli_commands():
    """Show CLI command examples"""
    print("💻 CLI Commands Demo")
    print("=" * 50)
    
    commands = [
        ("List disks", "python main.py --cli list"),
        ("Show disk info", "python main.py --cli info /dev/sdb"),
        ("Show methods", "python main.py --cli methods"),
        ("Wipe disk", "python main.py --cli wipe /dev/sdb --method secure --passes 3"),
        ("Quick wipe", "python main.py --cli wipe /dev/sdb --method quick --force"),
    ]
    
    print("Example CLI commands:")
    print()
    for description, command in commands:
        print(f"  📋 {description}:")
        print(f"     {command}")
        print()

def main():
    """Run the demo"""
    print("🚀 Disk Wipeout - Application Demo")
    print("=" * 60)
    print("This demo shows the application capabilities without performing")
    print("any actual disk operations.")
    print()
    
    # Setup logging (quiet mode for demo)
    setup_logger(logging.WARNING)
    
    try:
        # Run demo sections
        demo_disk_detection()
        time.sleep(1)
        
        demo_wipe_methods()
        time.sleep(1)
        
        demo_verification()
        time.sleep(1)
        
        demo_safety_features()
        time.sleep(1)
        
        demo_cli_commands()
        
        print("🎉 Demo completed successfully!")
        print()
        print("To use the application:")
        print("  GUI mode: python main.py")
        print("  CLI mode: python main.py --cli")
        print("  Test suite: python test_app.py")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import logging
    success = main()
    sys.exit(0 if success else 1)
