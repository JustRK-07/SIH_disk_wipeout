#!/usr/bin/env python3
"""
Test script for HPA/DCO detection functionality
Demonstrates cross-platform HPA/DCO detection capabilities
"""

import sys
import os
import platform
import logging
from src.core.disk_manager import DiskManager
from src.cli.cli_interface import CLIInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def print_header():
    """Print application header"""
    print("=" * 70)
    print("DISK WIPEOUT - HPA/DCO DETECTION TEST")
    print(f"Platform: {platform.system()} {platform.release()}")
    print("=" * 70)
    print()

def test_hpa_dco_detection():
    """Test HPA/DCO detection on available disks"""
    try:
        # Initialize disk manager
        disk_manager = DiskManager()

        print("Initializing Disk Manager...")
        print(f"Detected platform: {disk_manager.system}")
        print()

        # Get available disks
        print("Scanning for available disks...")
        disks = disk_manager.get_available_disks()

        if not disks:
            print("No disks found or insufficient permissions.")
            print("Try running with sudo/administrator privileges.")
            return

        print(f"Found {len(disks)} disk(s):\n")

        # Test HPA/DCO detection on each disk
        for i, disk in enumerate(disks, 1):
            print(f"{i}. {disk}")
            print("-" * 60)

            # Detect HPA/DCO
            hpa_dco_info = disk_manager.detect_hpa_dco(disk.device)

            # Display results
            if hpa_dco_info.get('error'):
                print(f"   Error: {hpa_dco_info['error']}")
            else:
                print(f"   Detection Method: {hpa_dco_info.get('detection_method', 'N/A')}")

                # Display sector information
                current_max = hpa_dco_info.get('current_max_sectors', 0)
                native_max = hpa_dco_info.get('native_max_sectors', 0)
                accessible = hpa_dco_info.get('accessible_sectors', 0)

                if current_max > 0:
                    current_gb = (current_max * 512) / (1024**3)
                    print(f"   Current Max: {current_max:,} sectors ({current_gb:.2f} GB)")

                if native_max > 0:
                    native_gb = (native_max * 512) / (1024**3)
                    print(f"   Native Max:  {native_max:,} sectors ({native_gb:.2f} GB)")

                if accessible > 0:
                    accessible_gb = (accessible * 512) / (1024**3)
                    print(f"   Accessible:  {accessible:,} sectors ({accessible_gb:.2f} GB)")

                # HPA detection results
                if hpa_dco_info.get('hpa_detected'):
                    hpa_sectors = hpa_dco_info.get('hpa_sectors', 0)
                    hpa_gb = (hpa_sectors * 512) / (1024**3)
                    print(f"   ⚠️  HPA DETECTED!")
                    print(f"      Hidden: {hpa_sectors:,} sectors ({hpa_gb:.2f} GB)")
                    print(f"      Removable: {'Yes' if hpa_dco_info.get('can_remove_hpa') else 'No'}")
                else:
                    print(f"   ✓ No HPA detected")

                # DCO detection results
                if hpa_dco_info.get('dco_detected'):
                    dco_sectors = hpa_dco_info.get('dco_sectors', 0)
                    dco_gb = (dco_sectors * 512) / (1024**3)
                    print(f"   ⚠️  DCO DETECTED!")
                    print(f"      Hidden: {dco_sectors:,} sectors ({dco_gb:.2f} GB)")
                    print(f"      Removable: {'Yes' if hpa_dco_info.get('can_remove_dco') else 'No'}")
                else:
                    print(f"   ✓ No DCO detected")

            print()

        # Platform-specific notes
        print("=" * 70)
        print("PLATFORM-SPECIFIC NOTES:")

        if platform.system() == 'Linux':
            print("• Linux: Ensure hdparm and smartctl are installed for best results")
            print("  Install: sudo apt-get install hdparm smartmontools")
            print("• Run with sudo for full disk access")

        elif platform.system() == 'Windows':
            print("• Windows: Run as Administrator for full disk access")
            print("• Some features require specialized tools like HDAT2")
            print("• WMI access improves detection accuracy")

        elif 'android' in platform.system().lower():
            print("• Android: Root access required for HPA/DCO detection")
            print("• Install hdparm via Termux or custom ROM if available")
            print("• eMMC devices may have RPMB (hardware-protected areas)")

        print("=" * 70)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point"""
    print_header()

    # Check for help argument
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python test_hpa_dco.py")
        print("\nThis script tests HPA/DCO detection on all available disks.")
        print("Run with appropriate privileges (sudo/administrator) for best results.")
        return

    # Check privileges warning
    if platform.system() == 'Linux' and os.geteuid() != 0:
        print("⚠️  WARNING: Not running as root. Some features may be limited.")
        print("   Run with sudo for full functionality.\n")
    elif platform.system() == 'Windows':
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("⚠️  WARNING: Not running as Administrator.")
            print("   Run as Administrator for full functionality.\n")

    # Run the test
    test_hpa_dco_detection()

if __name__ == "__main__":
    main()