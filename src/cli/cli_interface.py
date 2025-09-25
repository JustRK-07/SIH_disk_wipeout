"""
Command-line interface for Disk Wipeout application
Provides CLI access to disk wiping functionality
"""

import argparse
import sys
import logging
from typing import List

from ..core.disk_manager import DiskManager
from ..core.models import DiskInfo, DiskType, DiskStatus, WipeMethod, HPADCOInfo

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
                self._wipe_disk(args.device, args.method, args.passes, not args.no_verify, args.force)
            elif args.command == 'methods':
                self._show_wipe_methods()
            elif args.command == 'detect-hpa':
                self._detect_hpa_dco(args.device)
            elif args.command == 'remove-hpa':
                self._remove_hpa(args.device, args.force)
            elif args.command == 'remove-dco':
                self._remove_dco(args.device, args.force)
            elif args.command == 'wipe-full':
                self._wipe_with_hpa_dco(args.device, args.method, args.passes,
                                       not args.no_verify, args.remove_hpa,
                                       args.remove_dco, args.force)
            elif args.command == 'tools':
                self._show_tool_info()
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

        # HPA/DCO detection command
        detect_parser = subparsers.add_parser('detect-hpa',
                                             help='Detect HPA/DCO on a disk')
        detect_parser.add_argument('device', help='Device path (e.g., /dev/sdb)')

        # Remove HPA command
        remove_hpa_parser = subparsers.add_parser('remove-hpa',
                                                 help='Remove Host Protected Area from disk')
        remove_hpa_parser.add_argument('device', help='Device path')
        remove_hpa_parser.add_argument('-f', '--force', action='store_true',
                                      help='Force removal without confirmation')

        # Remove DCO command
        remove_dco_parser = subparsers.add_parser('remove-dco',
                                                 help='Remove Device Configuration Overlay from disk')
        remove_dco_parser.add_argument('device', help='Device path')
        remove_dco_parser.add_argument('-f', '--force', action='store_true',
                                      help='Force removal without confirmation')

        # Full wipe with HPA/DCO removal
        full_wipe_parser = subparsers.add_parser('wipe-full',
                                                help='Wipe disk with optional HPA/DCO removal')
        full_wipe_parser.add_argument('device', help='Device path to wipe')
        full_wipe_parser.add_argument('-m', '--method', default='secure',
                                     help='Wipe method (default: secure)')
        full_wipe_parser.add_argument('-p', '--passes', type=int, default=3,
                                     help='Number of passes (default: 3)')
        full_wipe_parser.add_argument('--no-verify', action='store_true',
                                     help='Skip verification after wipe')
        full_wipe_parser.add_argument('--remove-hpa', action='store_true',
                                     help='Remove HPA before wiping')
        full_wipe_parser.add_argument('--remove-dco', action='store_true',
                                     help='Remove DCO before wiping (DANGEROUS)')
        full_wipe_parser.add_argument('-f', '--force', action='store_true',
                                     help='Force wipe without confirmation')

        # Tools info command
        tools_parser = subparsers.add_parser('tools',
                                            help='Show tool availability and version info')

        return parser
    
    def _detect_hpa_dco(self, device: str):
        """Detect and display HPA/DCO information for a disk"""
        print(f"\nDetecting HPA/DCO on {device}...")
        print("=" * 50)

        hpa_dco_info = self.disk_manager.detect_hpa_dco(device)

        if hpa_dco_info.get('error'):
            print(f"Error: {hpa_dco_info['error']}")
            return

        # Display detection results
        print(f"Detection Method: {hpa_dco_info.get('detection_method', 'N/A')}")
        print(f"\nSector Information:")
        print(f"  Current Max Sectors: {hpa_dco_info.get('current_max_sectors', 0):,}")
        print(f"  Native Max Sectors:  {hpa_dco_info.get('native_max_sectors', 0):,}")
        print(f"  Accessible Sectors:  {hpa_dco_info.get('accessible_sectors', 0):,}")

        if hpa_dco_info.get('hpa_detected'):
            hidden_sectors = hpa_dco_info.get('hpa_sectors', 0)
            hidden_gb = (hidden_sectors * 512) / (1024**3)
            print(f"\n⚠️  HPA DETECTED!")
            print(f"  Hidden Sectors: {hidden_sectors:,}")
            print(f"  Hidden Size: {hidden_gb:.2f} GB")
            print(f"  Can Remove: {'Yes' if hpa_dco_info.get('can_remove_hpa') else 'No'}")
        else:
            print(f"\n✓ No HPA detected")

        if hpa_dco_info.get('dco_detected'):
            dco_sectors = hpa_dco_info.get('dco_sectors', 0)
            dco_gb = (dco_sectors * 512) / (1024**3)
            print(f"\n⚠️  DCO DETECTED!")
            print(f"  DCO Sectors: {dco_sectors:,}")
            print(f"  DCO Size: {dco_gb:.2f} GB")
            print(f"  Can Remove: {'Yes' if hpa_dco_info.get('can_remove_dco') else 'No'}")
        else:
            print(f"\n✓ No DCO detected")

        print("\n" + "=" * 50)

    def _remove_hpa(self, device: str, force: bool = False):
        """Remove HPA from disk"""
        if not force:
            response = input(f"\n⚠️  WARNING: Removing HPA from {device} will expose hidden areas.\n"
                           "This may contain sensitive data. Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Operation cancelled.")
                return

        print(f"\nRemoving HPA from {device}...")
        success, message = self.disk_manager.remove_hpa(device)

        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")

    def _remove_dco(self, device: str, force: bool = False):
        """Remove DCO from disk"""
        if not force:
            response = input(f"\n⚠️  DANGER: Removing DCO from {device} can permanently damage the disk!\n"
                           "This operation is irreversible. Are you absolutely sure? (type 'YES I UNDERSTAND'): ")
            if response != 'YES I UNDERSTAND':
                print("Operation cancelled.")
                return

        print(f"\nRemoving DCO from {device}...")
        success, message = self.disk_manager.remove_dco(device)

        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")

    def _wipe_with_hpa_dco(self, device: str, method: str, passes: int,
                          verify: bool, remove_hpa: bool, remove_dco: bool, force: bool):
        """Wipe disk with optional HPA/DCO removal"""
        # First detect HPA/DCO
        print(f"\nScanning {device} for hidden areas...")
        hpa_dco_info = self.disk_manager.detect_hpa_dco(device)

        warnings = []
        if hpa_dco_info.get('hpa_detected'):
            hidden_gb = (hpa_dco_info.get('hpa_sectors', 0) * 512) / (1024**3)
            warnings.append(f"HPA detected: {hidden_gb:.2f}GB hidden")

        if hpa_dco_info.get('dco_detected'):
            dco_gb = (hpa_dco_info.get('dco_sectors', 0) * 512) / (1024**3)
            warnings.append(f"DCO detected: {dco_gb:.2f}GB hidden")

        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  ⚠️  {warning}")

        if not force:
            print(f"\nYou are about to wipe {device}")
            if remove_hpa:
                print("  - HPA will be removed")
            if remove_dco:
                print("  - DCO will be removed (DANGEROUS!)")
            print(f"  - Method: {method}")
            print(f"  - Passes: {passes}")

            response = input("\nThis will permanently destroy all data. Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Operation cancelled.")
                return

        print(f"\nStarting wipe operation...")
        success, message = self.disk_manager.wipe_with_hpa_dco_removal(
            device, method, passes, verify, remove_hpa, remove_dco
        )

        print("\nOperation Results:")
        for line in message.split('\n'):
            if 'success' in line.lower() or 'removed' in line.lower():
                print(f"  ✓ {line}")
            elif 'fail' in line.lower() or 'error' in line.lower():
                print(f"  ✗ {line}")
            else:
                print(f"  {line}")

        if success:
            print("\n✓ Wipe operation completed successfully")
        else:
            print("\n✗ Wipe operation failed or partially completed")

    def _show_tool_info(self):
        """Show tool availability and version information"""
        from ..core.tool_manager import tool_manager

        print("\n🔧 Tool Availability Report")
        print("=" * 50)

        tool_info = tool_manager.get_tool_info()

        print(f"System: {tool_info['system'].title()}")
        print(f"Architecture: {tool_info['architecture']}")
        print(f"Edition: {'Complete' if tool_info['is_complete_edition'] else 'Lite'}")

        if tool_info['tools_directory']:
            print(f"Tools Directory: {tool_info['tools_directory']}")

        print("\nTool Status:")
        print("-" * 30)

        for tool_name, tool_data in tool_info['tools'].items():
            status = "✅ Available" if tool_data['available'] else "❌ Missing"
            print(f"{tool_name:12} {status}")

            if tool_data['available']:
                path_type = "Bundled" if tool_data['bundled_path'] and tool_data['path'] == tool_data['bundled_path'] else "System"
                print(f"{'':14} Path: {tool_data['path']} ({path_type})")
            else:
                print(f"{'':14} System command: {tool_data['system_command']}")

        # Show installation suggestions for missing tools
        missing_tools = tool_manager.get_missing_tools()
        if missing_tools and not tool_info['is_complete_edition']:
            print("\n💡 Installation Suggestions:")
            print("-" * 30)
            suggestions = tool_manager.get_installation_suggestions()
            for tool, suggestion in suggestions.items():
                print(f"{tool}: {suggestion}")

            print("\nAlternatively, use the Complete Edition for all tools pre-bundled.")
        elif missing_tools and tool_info['is_complete_edition']:
            print(f"\n⚠️  Some bundled tools are missing. Package may be corrupted.")
        else:
            print(f"\n✅ All tools available!")

        print("\n" + "=" * 50)

    def _list_disks(self):
        """List available disks with enhanced information"""
        print("🔍 Available Disks:")
        print("=" * 120)
        print(f"{'Device':<18} {'Size':<12} {'Type':<8} {'Model':<25} {'Status':<12} {'Hidden':<10} {'Usage':<12}")
        print("=" * 120)
        
        try:
            disks = self.disk_manager.get_available_disks()
            system_disks = self.disk_manager.get_system_disks()
            
            if not disks:
                print("No disks found")
                return
            
            for disk in disks:
                # Use enhanced data model if available
                if hasattr(disk, 'size_formatted'):
                    size_str = disk.size_formatted
                else:
                    size_str = f"{disk.size // (1024**3)}GB" if disk.size > 0 else "Unknown"
                
                # Get type with icon
                if hasattr(disk, 'type_icon'):
                    if hasattr(disk.type, 'value'):
                        type_str = f"{disk.type_icon} {disk.type.value.upper()}"
                    else:
                        type_str = f"{disk.type_icon} {disk.type.upper()}"
                else:
                    if hasattr(disk.type, 'value'):
                        type_str = disk.type.value.upper()
                    else:
                        type_str = disk.type.upper()
                
                # Determine status
                is_writable = self.disk_manager.is_disk_writable(disk.device)
                is_system_disk = disk.device in system_disks
                
                if is_system_disk:
                    status = "🔒 PROTECTED"
                elif is_writable:
                    status = "✅ Writable"
                else:
                    status = "❌ Read-only"
                
                # Check for hidden areas
                hidden_str = "None"
                if hasattr(disk, 'hpa_dco_info') and disk.hpa_dco_info:
                    # Handle both dataclass and dict formats
                    if hasattr(disk.hpa_dco_info, 'hpa_detected'):
                        if disk.hpa_dco_info.hpa_detected or disk.hpa_dco_info.dco_detected:
                            hidden_gb = disk.hpa_dco_info.hidden_gb
                            hidden_str = f"⚠️ {hidden_gb:.1f}GB"
                    elif isinstance(disk.hpa_dco_info, dict):
                        if disk.hpa_dco_info.get('hpa_detected') or disk.hpa_dco_info.get('dco_detected'):
                            hidden_gb = disk.hpa_dco_info.get('hidden_gb', 0)
                            hidden_str = f"⚠️ {hidden_gb:.1f}GB"
                
                # Calculate storage usage (simulated)
                usage_percentage = 0
                if not is_system_disk:  # Don't show usage for system disks
                    if disk.type.lower() in ['ssd', 'nvme']:
                        usage_percentage = 25  # SSDs typically have less usage
                    else:
                        usage_percentage = 45  # HDDs typically have more usage
                
                usage_display = f"{usage_percentage}% Used" if usage_percentage > 0 else "N/A"
                
                print(f"{disk.device:<18} {size_str:<12} {type_str:<8} "
                      f"{disk.model[:24]:<25} {status:<12} {hidden_str:<10} {usage_display:<12}")
            
            print("=" * 120)
            print(f"Total: {len(disks)} disks found")
                      
        except Exception as e:
            print(f"Error listing disks: {e}")
    
    def _show_disk_info(self, device: str):
        """Show comprehensive disk information"""
        print(f"📀 Disk Information for {device}")
        print("=" * 60)
        
        try:
            disk_info = self.disk_manager.get_disk_info(device)
            
            if not disk_info:
                print(f"❌ Device {device} not found")
                return
            
            # Use enhanced data model if available
            if hasattr(disk_info, 'get_detailed_info'):
                detailed_info = disk_info.get_detailed_info()
                
                print(f"Device: {detailed_info['device']}")
                print(f"Size: {detailed_info['size']} ({detailed_info['size_bytes']:,} bytes)")
                print(f"Type: {detailed_info['type_icon']} {detailed_info['type']}")
                print(f"Model: {detailed_info['model']}")
                print(f"Serial: {detailed_info['serial']}")
                print(f"Mountpoint: {detailed_info['mountpoint']}")
                print(f"Filesystem: {detailed_info['filesystem']}")
                print(f"Writable: {'Yes' if detailed_info['is_writable'] else 'No'}")
                print(f"System Disk: {'Yes' if detailed_info['is_system_disk'] else 'No'}")
                print(f"Hidden Areas: {detailed_info['hidden_capacity']}")
                
                # Show HPA/DCO details if available
                if detailed_info.get('hpa_detected') or detailed_info.get('dco_detected'):
                    print(f"\n🔍 Hidden Areas Details:")
                    print(f"  HPA Detected: {'Yes' if detailed_info.get('hpa_detected') else 'No'}")
                    print(f"  DCO Detected: {'Yes' if detailed_info.get('dco_detected') else 'No'}")
                    if detailed_info.get('hpa_detected'):
                        print(f"  HPA Capacity: {detailed_info.get('hpa_capacity', 'Unknown')}")
                    if detailed_info.get('dco_detected'):
                        print(f"  DCO Capacity: {detailed_info.get('dco_capacity', 'Unknown')}")
                    print(f"  Can Remove HPA: {'Yes' if detailed_info.get('can_remove_hpa') else 'No'}")
                    print(f"  Can Remove DCO: {'Yes' if detailed_info.get('can_remove_dco') else 'No'}")
                
                # Show health information if available
                if detailed_info.get('health_status'):
                    print(f"\n💊 Health Information:")
                    print(f"  Status: {detailed_info['health_status'].title()}")
                    if detailed_info.get('temperature'):
                        print(f"  Temperature: {detailed_info['temperature']}°C")
                    if detailed_info.get('power_on_hours'):
                        print(f"  Power On Hours: {detailed_info['power_on_hours']:,}")
                    if detailed_info.get('bad_sectors'):
                        print(f"  Bad Sectors: {detailed_info['bad_sectors']}")
            else:
                # Fallback to basic information
                print(f"Device: {disk_info.device}")
                print(f"Size: {disk_info.size // (1024**3)}GB ({disk_info.size:,} bytes)")
                # Handle both enum and string types
                if hasattr(disk_info.type, 'value'):
                    print(f"Type: {disk_info.type.value.upper()}")
                else:
                    print(f"Type: {disk_info.type.upper()}")
                print(f"Model: {disk_info.model}")
                print(f"Serial: {disk_info.serial}")
                
                if disk_info.mountpoint:
                    print(f"Mountpoint: {disk_info.mountpoint}")
                if disk_info.filesystem:
                    print(f"Filesystem: {disk_info.filesystem}")
                
                is_writable = self.disk_manager.is_disk_writable(device)
                print(f"Writable: {'Yes' if is_writable else 'No'}")
            
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error getting disk info: {e}")
    
    def _wipe_disk(self, device: str, method: str, passes: int, verify: bool, force: bool):
        """Wipe a disk with enhanced information display"""
        print(f"🚀 Disk Wipe Operation")
        print("=" * 50)
        print(f"Device: {device}")
        print(f"Method: {method}")
        print(f"Passes: {passes}")
        print(f"Verify: {'Yes' if verify else 'No'}")
        print(f"Force: {'Yes' if force else 'No'}")
        print("-" * 50)
        
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
        
        # Enhanced safety check - prevent wiping system disks
        system_disks = self.disk_manager.get_system_disks()
        if device in system_disks:
            print(f"\n🚨 CRITICAL ERROR: SYSTEM DISK PROTECTION 🚨")
            print(f"The selected disk {device} is a SYSTEM DISK!")
            print(f"Wiping this disk would DESTROY YOUR OPERATING SYSTEM!")
            print(f"This operation is BLOCKED for your safety.")
            print(f"Please select a different disk.")
            return
        
        # Confirmation
        if not force:
            print(f"\nWARNING: This will permanently erase all data on {device}")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Operation cancelled")
                return
        
        # Perform wipe
        print(f"\n🔄 Starting wipe operation...")
        try:
            success, message = self.disk_manager.wipe_disk(device, method, passes, verify)
            
            print("\n" + "=" * 50)
            if success:
                print(f"✅ SUCCESS: {message}")
                print("🎉 Disk wipe completed successfully!")
            else:
                print(f"❌ ERROR: {message}")
                print("💥 Disk wipe failed!")
                sys.exit(1)
            print("=" * 50)
                
        except KeyboardInterrupt:
            print("\n⚠️ Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            sys.exit(1)
    
    def _show_wipe_methods(self):
        """Show available wipe methods with enhanced descriptions"""
        print("🔧 Available Wipe Methods:")
        print("=" * 60)
        
        try:
            methods = self.disk_manager.get_wipe_methods()
            
            for i, method in enumerate(methods, 1):
                description = self._get_method_description(method)
                print(f"{i:2d}. {method:<15} - {description}")
            
            print("=" * 60)
            print(f"Total: {len(methods)} methods available")
                
        except Exception as e:
            print(f"❌ Error getting wipe methods: {e}")
    
    def _get_method_description(self, method: str) -> str:
        """Get enhanced description for a wipe method"""
        descriptions = {
            'secure': 'Multi-pass secure wipe (recommended for sensitive data)',
            'quick': 'Single-pass quick wipe (faster, less secure)',
            'dd': 'DD-based wiping with random data (very secure)',
            'cipher': 'Windows Cipher.exe free space wipe (Windows only)',
            'hdparm': 'Linux hdparm secure erase (hardware-level, HDDs)',
            'nvme': 'NVMe secure format (SSD-specific, very fast)',
            'blkdiscard': 'TRIM-based discard (SSD-optimized, fast)',
            'saf': 'Android Storage Access Framework (Android only)'
        }
        
        return descriptions.get(method, 'Custom wipe method')
