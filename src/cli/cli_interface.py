"""
Command-line interface for Disk Wipeout application
Provides CLI access to disk wiping functionality
"""

import argparse
import sys
import logging
from typing import List

from ..core.disk_manager import DiskManager

logger = logging.getLogger(__name__)

class CLIInterface:
    """Command-line interface for the disk wiping application"""
    
    def __init__(self, disk_manager: DiskManager):
        self.disk_manager = disk_manager
    
    def run(self):
        """Run the CLI interface"""
        parser = self._create_parser()
        args = parser.parse_args()
        
        # Configure logging level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        elif args.quiet:
            logging.getLogger().setLevel(logging.WARNING)
        
        try:
            if args.command == 'list':
                self._list_disks()
            elif args.command == 'info':
                self._show_disk_info(args.device)
            elif args.command == 'wipe':
                self._wipe_disk(args.device, args.method, args.passes, args.verify, args.force)
            elif args.command == 'methods':
                self._show_wipe_methods()
            else:
                parser.print_help()
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create command-line argument parser"""
        parser = argparse.ArgumentParser(
            description="Disk Wipeout - Secure Data Erasure Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s list                    # List available disks
  %(prog)s info /dev/sdb           # Show disk information
  %(prog)s wipe /dev/sdb --method dd --passes 3  # Wipe disk with 3 passes
  %(prog)s methods                 # Show available wipe methods
            """
        )
        
        # Global options
        parser.add_argument('-v', '--verbose', action='store_true',
                          help='Enable verbose output')
        parser.add_argument('-q', '--quiet', action='store_true',
                          help='Suppress non-error output')
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # List command
        list_parser = subparsers.add_parser('list', help='List available disks')
        
        # Info command
        info_parser = subparsers.add_parser('info', help='Show disk information')
        info_parser.add_argument('device', help='Device path (e.g., /dev/sdb)')
        
        # Wipe command
        wipe_parser = subparsers.add_parser('wipe', help='Wipe a disk')
        wipe_parser.add_argument('device', help='Device path to wipe')
        wipe_parser.add_argument('-m', '--method', default='secure',
                               help='Wipe method (default: secure)')
        wipe_parser.add_argument('-p', '--passes', type=int, default=3,
                               help='Number of passes (default: 3)')
        wipe_parser.add_argument('--no-verify', action='store_true',
                               help='Skip verification after wipe')
        wipe_parser.add_argument('-f', '--force', action='store_true',
                               help='Force wipe without confirmation')
        
        # Methods command
        methods_parser = subparsers.add_parser('methods', help='Show available wipe methods')
        
        return parser
    
    def _list_disks(self):
        """List available disks"""
        print("Available Disks:")
        print("-" * 80)
        print(f"{'Device':<20} {'Size':<10} {'Type':<8} {'Model':<25} {'Status':<10}")
        print("-" * 80)
        
        try:
            disks = self.disk_manager.get_available_disks()
            
            if not disks:
                print("No disks found")
                return
            
            for disk in disks:
                size_str = f"{disk.size // (1024**3)}GB" if disk.size > 0 else "Unknown"
                is_writable = self.disk_manager.is_disk_writable(disk.device)
                status = "Writable" if is_writable else "Read-only"
                
                print(f"{disk.device:<20} {size_str:<10} {disk.type.upper():<8} "
                      f"{disk.model[:24]:<25} {status:<10}")
                      
        except Exception as e:
            print(f"Error listing disks: {e}")
    
    def _show_disk_info(self, device: str):
        """Show detailed disk information"""
        print(f"Disk Information for {device}:")
        print("-" * 40)
        
        try:
            disk_info = self.disk_manager.get_disk_info(device)
            
            if not disk_info:
                print(f"Device {device} not found")
                return
            
            print(f"Device: {disk_info.device}")
            print(f"Size: {disk_info.size // (1024**3)}GB ({disk_info.size:,} bytes)")
            print(f"Type: {disk_info.type.upper()}")
            print(f"Model: {disk_info.model}")
            print(f"Serial: {disk_info.serial}")
            
            if disk_info.mountpoint:
                print(f"Mountpoint: {disk_info.mountpoint}")
            if disk_info.filesystem:
                print(f"Filesystem: {disk_info.filesystem}")
            
            is_writable = self.disk_manager.is_disk_writable(device)
            print(f"Writable: {'Yes' if is_writable else 'No'}")
            
        except Exception as e:
            print(f"Error getting disk info: {e}")
    
    def _wipe_disk(self, device: str, method: str, passes: int, verify: bool, force: bool):
        """Wipe a disk"""
        print(f"Wiping disk: {device}")
        print(f"Method: {method}")
        print(f"Passes: {passes}")
        print(f"Verify: {'Yes' if verify else 'No'}")
        print("-" * 40)
        
        # Check if device exists
        try:
            disk_info = self.disk_manager.get_disk_info(device)
            if not disk_info:
                print(f"Error: Device {device} not found")
                return
        except Exception as e:
            print(f"Error: {e}")
            return
        
        # Check if writable
        if not self.disk_manager.is_disk_writable(device):
            print(f"Error: Device {device} is not writable")
            return
        
        # Check if it's a system disk
        system_disks = self.disk_manager.get_system_disks()
        if device in system_disks:
            print(f"Warning: {device} appears to be a system disk!")
            if not force:
                response = input("Are you sure you want to continue? (yes/no): ")
                if response.lower() != 'yes':
                    print("Operation cancelled")
                    return
        
        # Confirmation
        if not force:
            print(f"\nWARNING: This will permanently erase all data on {device}")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Operation cancelled")
                return
        
        # Perform wipe
        print(f"\nStarting wipe operation...")
        try:
            success, message = self.disk_manager.wipe_disk(device, method, passes, verify)
            
            if success:
                print(f"SUCCESS: {message}")
            else:
                print(f"ERROR: {message}")
                sys.exit(1)
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    
    def _show_wipe_methods(self):
        """Show available wipe methods"""
        print("Available Wipe Methods:")
        print("-" * 30)
        
        try:
            methods = self.disk_manager.get_wipe_methods()
            
            for method in methods:
                description = self._get_method_description(method)
                print(f"{method:<15} - {description}")
                
        except Exception as e:
            print(f"Error getting wipe methods: {e}")
    
    def _get_method_description(self, method: str) -> str:
        """Get description for a wipe method"""
        descriptions = {
            'secure': 'Multi-pass secure wipe (recommended)',
            'quick': 'Single-pass quick wipe',
            'dd': 'DD-based wiping with random data',
            'cipher': 'Windows Cipher.exe free space wipe',
            'hdparm': 'Linux hdparm secure erase (HDDs)',
            'nvme': 'NVMe secure format (SSDs)',
            'blkdiscard': 'TRIM-based discard (SSDs)',
            'saf': 'Android Storage Access Framework'
        }
        
        return descriptions.get(method, 'Unknown method')
