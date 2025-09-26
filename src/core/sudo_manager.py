"""
Sudo Permission Manager
Handles automatic sudo permission requests and management
"""

import os
import subprocess
import logging
import getpass
import sys
from typing import Tuple, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class SudoManager:
    """Manages sudo permissions and automatic privilege escalation"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SudoManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.has_sudo = self._check_sudo_availability()
            self.sudo_password = None
            self.sudo_cached = False
            SudoManager._initialized = True
        
    def _check_sudo_availability(self) -> bool:
        """Check if sudo is available on the system"""
        try:
            result = subprocess.run(['which', 'sudo'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_passwordless_sudo(self, command: str) -> bool:
        """Check if passwordless sudo is available for a specific command"""
        try:
            # Test with -n flag (non-interactive)
            test_cmd = ['sudo', '-n', 'true']
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def request_sudo_password(self) -> Optional[str]:
        """Request sudo password from user"""
        try:
            if not self.has_sudo:
                return None
            
            # Check if we're in an interactive environment
            if not sys.stdin.isatty():
                print("\n🔐 Sudo Permission Required")
                print("=" * 50)
                print("This operation requires administrator privileges.")
                print("Please run the application in an interactive terminal.")
                print("Alternatively, you can:")
                print("1. Run with sudo: sudo python3 main.py --cli wipe /dev/sda --method dd")
                print("2. Configure passwordless sudo for the current user")
                return None
                
            print("\n🔐 Sudo Permission Required")
            print("=" * 50)
            print("This operation requires administrator privileges.")
            print("Please enter your sudo password:")
            
            # Get password securely
            password = getpass.getpass("Password: ")
            
            # Test the password
            if self._test_sudo_password(password):
                self.sudo_password = password
                self.sudo_cached = True
                print("✅ Sudo password verified successfully!")
                return password
            else:
                print("❌ Invalid password. Please try again.")
                return None
                
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user.")
            return None
        except Exception as e:
            logger.error(f"Error requesting sudo password: {e}")
            return None
    
    def _test_sudo_password(self, password: str) -> bool:
        """Test if the provided sudo password is valid"""
        try:
            # Use echo to test password
            cmd = ['sudo', '-S', 'true']
            result = subprocess.run(
                cmd, 
                input=password + '\n', 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def run_with_sudo(self, command: List[str], description: str = "operation", timeout: int = None) -> Tuple[bool, str, str]:
        """
        Run a command with sudo, handling password prompts automatically
        
        Args:
            command: Command to run (without sudo prefix)
            description: Description of the operation for user feedback
            timeout: Timeout in seconds (None for no timeout, auto-detected for wipe operations)
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            # Auto-detect timeout for wipe operations
            if timeout is None:
                if any(cmd in ' '.join(command) for cmd in ['dd', 'hdparm', 'nvme', 'blkdiscard']):
                    timeout = 7200  # 2 hours for wipe operations
                else:
                    timeout = 30  # 30 seconds for other operations
            
            # First try without sudo
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return True, result.stdout, result.stderr
            
            # If that fails, try with passwordless sudo
            if self._check_passwordless_sudo('true'):
                sudo_cmd = ['sudo'] + command
                result = subprocess.run(sudo_cmd, capture_output=True, text=True, timeout=timeout)
                if result.returncode == 0:
                    return True, result.stdout, result.stderr
            
            # If passwordless sudo doesn't work, request password
            if not self.sudo_cached:
                password = self.request_sudo_password()
                if not password:
                    # Provide helpful error message
                    error_msg = (
                        "Sudo password required but not provided. "
                        "Please run the application with sudo or configure passwordless sudo. "
                        "Example: sudo python3 main.py --cli wipe /dev/sda --method dd"
                    )
                    return False, "", error_msg
            
            # Run with sudo and password
            sudo_cmd = ['sudo', '-S'] + command
            result = subprocess.run(
                sudo_cmd,
                input=self.sudo_password + '\n',
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout, result.stderr
            else:
                # Check if it's a password authentication error
                if "password" in result.stderr.lower() or "authentication" in result.stderr.lower():
                    # Clear cached password and request new one
                    self.sudo_cached = False
                    self.sudo_password = None
                    error_msg = (
                        "Sudo password authentication failed. "
                        "Please run the application with sudo or provide a valid password. "
                        "Example: sudo python3 main.py --cli wipe /dev/sda --method dd"
                    )
                    return False, "", error_msg
                else:
                    return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", f"Error running command: {str(e)}"
    
    def unmount_device(self, device: str) -> Tuple[bool, str]:
        """Unmount a device using sudo if needed"""
        try:
            # Get mount points for the device
            mount_points = self._get_mount_points(device)
            
            if not mount_points:
                return True, "Device is not mounted"
            
            success_count = 0
            error_messages = []
            
            for mount_point in mount_points:
                print(f"🔄 Unmounting {mount_point}...")
                
                # Try unmount without sudo first
                result = subprocess.run(['umount', mount_point], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ Successfully unmounted {mount_point}")
                    success_count += 1
                    continue
                
                # Try with sudo
                success, stdout, stderr = self.run_with_sudo(['umount', mount_point], f"unmount {mount_point}")
                if success:
                    print(f"✅ Successfully unmounted {mount_point} (with sudo)")
                    success_count += 1
                else:
                    error_msg = f"Failed to unmount {mount_point}: {stderr}"
                    error_messages.append(error_msg)
                    print(f"❌ {error_msg}")
            
            if success_count == len(mount_points):
                return True, f"Successfully unmounted {success_count} mount point(s)"
            elif success_count > 0:
                return True, f"Partially successful: {success_count}/{len(mount_points)} unmounted. Errors: {'; '.join(error_messages)}"
            else:
                return False, f"Failed to unmount any mount points. Errors: {'; '.join(error_messages)}"
                
        except Exception as e:
            return False, f"Error unmounting device: {str(e)}"
    
    def _get_mount_points(self, device: str) -> List[str]:
        """Get mount points for a device"""
        try:
            import psutil
            mount_points = []
            
            for partition in psutil.disk_partitions():
                if partition.device.startswith(device):
                    mount_points.append(partition.mountpoint)
            
            return mount_points
        except Exception:
            return []
    
    def wipe_disk_with_sudo(self, device: str, method: str, passes: int) -> Tuple[bool, str]:
        """Wipe a disk with automatic sudo handling"""
        try:
            print(f"\n🗑️ Starting disk wipe operation...")
            print(f"Device: {device}")
            print(f"Method: {method}")
            print(f"Passes: {passes}")
            print("=" * 50)
            
            # Step 1: Unmount the device
            print("Step 1: Unmounting device...")
            unmount_success, unmount_msg = self.unmount_device(device)
            if not unmount_success:
                print(f"⚠️ Warning: {unmount_msg}")
                # Continue anyway, some operations might work
            
            # Step 2: Perform the wipe based on method
            print(f"Step 2: Wiping disk using {method} method...")
            
            if method == "dd":
                return self._wipe_with_dd_sudo(device, passes)
            elif method == "quick":
                return self._wipe_quick_sudo(device)
            elif method == "secure":
                return self._wipe_secure_sudo(device, passes)
            else:
                return False, f"Unsupported wipe method: {method}"
                
        except Exception as e:
            return False, f"Error during wipe operation: {str(e)}"
    
    def _wipe_with_dd_sudo(self, device: str, passes: int) -> Tuple[bool, str]:
        """Wipe disk using dd with sudo"""
        try:
            # Get disk size first
            disk_size_cmd = ['blockdev', '--getsize64', device]
            success, stdout, stderr = self.run_with_sudo(disk_size_cmd, "get disk size")
            
            if not success:
                return False, f"Failed to get disk size: {stderr}"
            
            try:
                disk_size_bytes = int(stdout.strip())
                disk_size_mb = disk_size_bytes // (1024 * 1024)
                print(f"📊 Disk size: {disk_size_bytes} bytes ({disk_size_mb} MB)")
            except ValueError:
                return False, f"Invalid disk size: {stdout.strip()}"
            
            for pass_num in range(passes):
                print(f"🔄 Wipe pass {pass_num + 1}/{passes}...")
                
                # Use dd with random data and proper count parameter
                cmd = ['dd', f'if=/dev/urandom', f'of={device}', 'bs=1M', f'count={disk_size_mb}', 'status=progress', 'conv=fsync']
                success, stdout, stderr = self.run_with_sudo(cmd, f"dd wipe pass {pass_num + 1}")
                
                if not success:
                    return False, f"DD wipe pass {pass_num + 1} failed: {stderr}"
                
                print(f"✅ Pass {pass_num + 1} completed successfully")
            
            return True, f"Disk wiped successfully using dd with {passes} passes"
            
        except Exception as e:
            return False, f"DD wipe error: {str(e)}"
    
    def _wipe_quick_sudo(self, device: str) -> Tuple[bool, str]:
        """Quick wipe - only wipe first and last 10MB for speed"""
        try:
            print("🔄 Performing quick wipe (partition table and signatures only)...")
            
            # First try wipefs for fastest results
            wipefs_cmd = ['wipefs', '-a', device]
            success, stdout, stderr = self.run_with_sudo(wipefs_cmd, "wipefs signatures")
            
            if success:
                return True, "Quick wipe completed (filesystem signatures removed)"
            
            # Fallback to dd for first 10MB only
            print("Wipefs not available, using dd for partition table...")
            cmd = ['dd', 'if=/dev/zero', f'of={device}', 'bs=1M', 'count=10', 'status=progress']
            success, stdout, stderr = self.run_with_sudo(cmd, "quick partition wipe")
            
            if success:
                return True, "Quick wipe completed (partition table cleared)"
            else:
                return False, f"Quick wipe failed: {stderr}"
                
        except Exception as e:
            return False, f"Quick wipe error: {str(e)}"
    
    def _wipe_secure_sudo(self, device: str, passes: int) -> Tuple[bool, str]:
        """Secure multi-pass wipe"""
        try:
            print(f"🔄 Performing secure wipe with {passes} passes...")
            
            # Get disk size first
            disk_size_cmd = ['blockdev', '--getsize64', device]
            success, stdout, stderr = self.run_with_sudo(disk_size_cmd, "get disk size")
            
            if not success:
                return False, f"Failed to get disk size: {stderr}"
            
            try:
                disk_size_bytes = int(stdout.strip())
                disk_size_mb = disk_size_bytes // (1024 * 1024)
                print(f"📊 Disk size: {disk_size_bytes} bytes ({disk_size_mb} MB)")
            except ValueError:
                return False, f"Invalid disk size: {stdout.strip()}"
            
            for pass_num in range(passes):
                print(f"🔄 Secure pass {pass_num + 1}/{passes}...")
                
                if pass_num == 0:
                    # First pass with zeros
                    cmd = ['dd', f'if=/dev/zero', f'of={device}', 'bs=1M', f'count={disk_size_mb}', 'status=progress', 'conv=fsync']
                else:
                    # Subsequent passes with random data
                    cmd = ['dd', f'if=/dev/urandom', f'of={device}', 'bs=1M', f'count={disk_size_mb}', 'status=progress', 'conv=fsync']
                
                success, stdout, stderr = self.run_with_sudo(cmd, f"secure wipe pass {pass_num + 1}")
                
                if not success:
                    return False, f"Secure wipe pass {pass_num + 1} failed: {stderr}"
                
                print(f"✅ Secure pass {pass_num + 1} completed")
            
            return True, f"Disk wiped successfully using secure method with {passes} passes"
            
        except Exception as e:
            return False, f"Secure wipe error: {str(e)}"
    
    def check_disk_access(self, device: str) -> Tuple[bool, str]:
        """Check if we can access a disk for wiping"""
        try:
            # Check if device exists
            if not os.path.exists(device):
                return False, f"Device {device} does not exist"
            
            # Try to read device info
            cmd = ['lsblk', '-n', '-o', 'NAME,SIZE,TYPE', device]
            success, stdout, stderr = self.run_with_sudo(cmd, f"check disk access for {device}")
            
            if success:
                return True, f"Device {device} is accessible"
            else:
                return False, f"Cannot access device {device}: {stderr}"
                
        except Exception as e:
            return False, f"Error checking disk access: {str(e)}"
