"""
Linux-specific disk handling implementation
Uses hdparm for HDDs, nvme-cli for SSDs, and blkdiscard for TRIM
"""

import os
import subprocess
import logging
import psutil
import glob
from typing import List, Tuple, Dict
from pathlib import Path

from .base_handler import BaseDiskHandler
from ..models import DiskInfo, DiskType
from ..tool_manager import tool_manager

logger = logging.getLogger(__name__)

class LinuxDiskHandler(BaseDiskHandler):
    """Linux-specific disk handler"""
    
    def __init__(self):
        self.block_devices_path = "/sys/block"
        self.dev_path = "/dev"
        self.tool_manager = tool_manager
    
    def detect_hpa_dco(self, device: str) -> Dict:
        """
        Detect Host Protected Area (HPA) and Device Configuration Overlay (DCO)
        Returns dict with HPA/DCO detection results
        """
        hpa_dco_info = {
            'hpa_detected': False,
            'hpa_sectors': 0,
            'dco_detected': False,
            'dco_sectors': 0,
            'native_max_sectors': 0,
            'current_max_sectors': 0,
            'accessible_sectors': 0,
            'hidden_sectors': 0,
            'detection_method': None,
            'can_remove_hpa': False,
            'can_remove_dco': False,
            'error': None
        }

        try:
            # Check if hdparm is available using tool manager
            hdparm_path = self.tool_manager.get_tool_path('hdparm')
            if not hdparm_path:
                suggestions = self.tool_manager.get_installation_suggestions()
                error_msg = "hdparm not available."
                if not self.tool_manager.is_complete_edition:
                    if 'hdparm' in suggestions:
                        error_msg += f" Install with: {suggestions['hdparm']}"
                    else:
                        error_msg += " Please install hdparm package or use Complete Edition."
                else:
                    error_msg += " Bundled hdparm not found - package may be corrupted."
                hpa_dco_info['error'] = error_msg
                return hpa_dco_info

            # Get disk identification info
            # Try without sudo first, then with sudo if needed
            cmd = [hdparm_path, "-I", device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # If hdparm fails without sudo, try with sudo but handle password prompt
            if result.returncode != 0:
                cmd = ["sudo", "-n", hdparm_path, "-I", device]  # -n for non-interactive
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                # If still fails, provide informative error
                if result.returncode != 0:
                    if "sudo: a password is required" in result.stderr or "sudo: a terminal is required" in result.stderr:
                        hpa_dco_info['error'] = "HPA/DCO detection requires sudo permissions. Please run with sudo or configure passwordless sudo for hdparm."
                        return hpa_dco_info
                    else:
                        hpa_dco_info['error'] = f"Failed to query disk: {result.stderr}"
                        return hpa_dco_info

            if result.returncode == 0:
                output = result.stdout

                # Parse LBA sectors from hdparm output
                import re

                # Look for LBA48 user addressable sectors
                lba48_match = re.search(r'LBA48\s+user\s+addressable\s+sectors:\s+(\d+)', output)
                if lba48_match:
                    hpa_dco_info['accessible_sectors'] = int(lba48_match.group(1))

                # Look for device max sectors
                device_max_match = re.search(r'device\s+size\s+with\s+M\s+=\s+\d+:\s+(\d+)\s+sectors', output)
                if device_max_match:
                    hpa_dco_info['current_max_sectors'] = int(device_max_match.group(1))

                # Check for HPA using --dco-identify
                cmd_dco = [hdparm_path, "--dco-identify", device]
                result_dco = subprocess.run(cmd_dco, capture_output=True, text=True, timeout=10)
                
                # If DCO command fails without sudo, try with sudo
                if result_dco.returncode != 0:
                    cmd_dco = ["sudo", "-n", hdparm_path, "--dco-identify", device]
                    result_dco = subprocess.run(cmd_dco, capture_output=True, text=True, timeout=10)

                if result_dco.returncode == 0:
                    dco_output = result_dco.stdout

                    # Parse DCO information
                    real_max_match = re.search(r'Real max sectors:\s+(\d+)', dco_output)
                    if real_max_match:
                        hpa_dco_info['native_max_sectors'] = int(real_max_match.group(1))
                        hpa_dco_info['detection_method'] = 'hdparm_dco'

                # Alternative: Get native max address
                cmd_native = [hdparm_path, "-N", device]
                result_native = subprocess.run(cmd_native, capture_output=True, text=True, timeout=10)
                
                # If native command fails without sudo, try with sudo
                if result_native.returncode != 0:
                    cmd_native = ["sudo", "-n", hdparm_path, "-N", device]
                    result_native = subprocess.run(cmd_native, capture_output=True, text=True, timeout=10)

                if result_native.returncode == 0:
                    native_output = result_native.stdout

                    # Parse native max sectors
                    native_match = re.search(r'max sectors\s+=\s+(\d+)/(\d+)', native_output)
                    if native_match:
                        current = int(native_match.group(1))
                        native = int(native_match.group(2))

                        if hpa_dco_info['native_max_sectors'] == 0:
                            hpa_dco_info['native_max_sectors'] = native
                        if hpa_dco_info['current_max_sectors'] == 0:
                            hpa_dco_info['current_max_sectors'] = current

                        # Detect HPA
                        if native > current:
                            hpa_dco_info['hpa_detected'] = True
                            hpa_dco_info['hpa_sectors'] = native - current
                            hpa_dco_info['hidden_sectors'] = native - current
                            hpa_dco_info['can_remove_hpa'] = True
                            if not hpa_dco_info['detection_method']:
                                hpa_dco_info['detection_method'] = 'hdparm_native'

                # Check for DCO by comparing native max with physical sectors
                # Get physical disk size from kernel
                device_name = os.path.basename(device)
                size_file = f"/sys/block/{device_name}/size"

                if os.path.exists(size_file):
                    with open(size_file, 'r') as f:
                        kernel_sectors = int(f.read().strip())

                    if hpa_dco_info['native_max_sectors'] > 0:
                        # If native max is less than kernel reported size, DCO might be present
                        if kernel_sectors > hpa_dco_info['native_max_sectors']:
                            hpa_dco_info['dco_detected'] = True
                            hpa_dco_info['dco_sectors'] = kernel_sectors - hpa_dco_info['native_max_sectors']
                            hpa_dco_info['can_remove_dco'] = True

                # Additional SMART data check for hidden areas
                smartctl_path = self.tool_manager.get_tool_path('smartctl')
                if smartctl_path:
                    cmd_smart = [smartctl_path, "-i", device]
                    result_smart = subprocess.run(cmd_smart, capture_output=True, text=True, timeout=10)
                    
                    # If smartctl fails without sudo, try with sudo
                    if result_smart.returncode != 0:
                        cmd_smart = ["sudo", "-n", smartctl_path, "-i", device]
                        result_smart = subprocess.run(cmd_smart, capture_output=True, text=True, timeout=10)
                else:
                    result_smart = subprocess.CompletedProcess([], 1)  # Simulate failure

                if result_smart.returncode == 0:
                    smart_output = result_smart.stdout
                    capacity_match = re.search(r'User Capacity:.*\[(\d+) bytes\]', smart_output)
                    if capacity_match:
                        smart_bytes = int(capacity_match.group(1))
                        smart_sectors = smart_bytes // 512

                        # Cross-verify with SMART data
                        if hpa_dco_info['accessible_sectors'] > 0 and smart_sectors < hpa_dco_info['accessible_sectors']:
                            potential_hidden = hpa_dco_info['accessible_sectors'] - smart_sectors
                            if potential_hidden > 0 and hpa_dco_info['hidden_sectors'] == 0:
                                hpa_dco_info['hidden_sectors'] = potential_hidden
                                hpa_dco_info['hpa_detected'] = True

            else:
                hpa_dco_info['error'] = f"Failed to query disk: {result.stderr}"

        except subprocess.TimeoutExpired:
            hpa_dco_info['error'] = "Operation timed out"
        except Exception as e:
            hpa_dco_info['error'] = f"Error detecting HPA/DCO: {str(e)}"

        return hpa_dco_info

    def remove_hpa(self, device: str) -> Tuple[bool, str]:
        """
        Remove Host Protected Area from disk
        WARNING: This exposes hidden disk areas
        """
        try:
            # First detect HPA
            hpa_info = self.detect_hpa_dco(device)

            if not hpa_info['hpa_detected']:
                return False, "No HPA detected on this disk"

            if not hpa_info['can_remove_hpa']:
                return False, "Cannot remove HPA from this disk"

            # Use hdparm to remove HPA by setting max sectors to native max
            native_max = hpa_info['native_max_sectors']
            hdparm_path = self.tool_manager.get_tool_path('hdparm')

            if not hdparm_path:
                return False, "hdparm not available for HPA removal"

            cmd = [hdparm_path, "-N", f"p{native_max}", device]
            from ..sudo_manager import SudoManager
            sudo_manager = SudoManager()
            success, stdout, stderr = sudo_manager.run_with_sudo(cmd, "remove HPA", timeout=60)
            
            if success:
                # Verify HPA removal
                new_info = self.detect_hpa_dco(device)
                if not new_info['hpa_detected']:
                    return True, f"Successfully removed HPA, exposed {hpa_info['hpa_sectors']} hidden sectors"
                else:
                    return False, "HPA removal attempted but verification failed"
            else:
                return False, f"Failed to remove HPA: {stderr}"

        except Exception as e:
            return False, f"Error removing HPA: {str(e)}"

    def remove_dco(self, device: str) -> Tuple[bool, str]:
        """
        Remove Device Configuration Overlay from disk
        WARNING: This is a dangerous operation that can damage the disk
        """
        try:
            # First detect DCO
            dco_info = self.detect_hpa_dco(device)

            if not dco_info['dco_detected']:
                return False, "No DCO detected on this disk"

            if not dco_info['can_remove_dco']:
                return False, "Cannot remove DCO from this disk"

            # Use hdparm to remove DCO
            hdparm_path = self.tool_manager.get_tool_path('hdparm')

            if not hdparm_path:
                return False, "hdparm not available for DCO removal"

            cmd = [hdparm_path, "--dco-restore", device]
            from ..sudo_manager import SudoManager
            sudo_manager = SudoManager()
            success, stdout, stderr = sudo_manager.run_with_sudo(cmd, "remove DCO", timeout=60)
            
            if success:
                # Verify DCO removal
                new_info = self.detect_hpa_dco(device)
                if not new_info['dco_detected']:
                    return True, f"Successfully removed DCO, exposed {dco_info['dco_sectors']} hidden sectors"
                else:
                    return False, "DCO removal attempted but verification failed"
            else:
                return False, f"Failed to remove DCO: {stderr}"

        except Exception as e:
            return False, f"Error removing DCO: {str(e)}"

    def get_available_disks(self) -> List[DiskInfo]:
        """Get available disks on Linux"""
        disks = []
        
        try:
            # Get block devices from /sys/block
            if os.path.exists(self.block_devices_path):
                for device_name in os.listdir(self.block_devices_path):
                    # Skip loop devices and partitions
                    if device_name.startswith('loop') or device_name.startswith('ram'):
                        continue
                    
                    device_path = os.path.join(self.dev_path, device_name)
                    if os.path.exists(device_path):
                        disk_info = self._get_disk_info_from_sysfs(device_name, device_path)
                        if disk_info:
                            disks.append(disk_info)
            
            # Also check for NVMe devices
            nvme_devices = glob.glob("/dev/nvme*n1")
            for nvme_device in nvme_devices:
                device_name = os.path.basename(nvme_device)
                disk_info = self._get_disk_info_from_sysfs(device_name, nvme_device)
                if disk_info:
                    disks.append(disk_info)
                    
        except Exception as e:
            logger.error(f"Error getting available disks: {e}")
        
        return disks
    
    def _get_disk_info_from_sysfs(self, device_name: str, device_path: str) -> DiskInfo:
        """Get disk information from sysfs with enhanced detection"""
        try:
            # Get size
            size_file = os.path.join(self.block_devices_path, device_name, "size")
            if os.path.exists(size_file):
                with open(size_file, 'r') as f:
                    size_sectors = int(f.read().strip())
                    size_bytes = size_sectors * 512  # Assuming 512-byte sectors
            else:
                size_bytes = 0

            # Get model, vendor and serial
            model = "Unknown"
            serial = ""
            vendor = "Unknown"

            # Try to get from /sys/block/device_name/device/model
            model_file = os.path.join(self.block_devices_path, device_name, "device", "model")
            if os.path.exists(model_file):
                with open(model_file, 'r') as f:
                    model = f.read().strip()

            # Try to get vendor
            vendor_file = os.path.join(self.block_devices_path, device_name, "device", "vendor")
            if os.path.exists(vendor_file):
                with open(vendor_file, 'r') as f:
                    vendor = f.read().strip()

            # Try to get serial from /sys/block/device_name/device/serial
            serial_file = os.path.join(self.block_devices_path, device_name, "device", "serial")
            if os.path.exists(serial_file):
                with open(serial_file, 'r') as f:
                    serial = f.read().strip()

            # Check if device is removable
            is_removable = False
            removable_file = os.path.join(self.block_devices_path, device_name, "removable")
            if os.path.exists(removable_file):
                with open(removable_file, 'r') as f:
                    is_removable = f.read().strip() == "1"

            # Check if it's a USB device by examining device path
            is_usb = False
            try:
                device_path_real = os.path.realpath(os.path.join(self.block_devices_path, device_name, "device"))
                if 'usb' in device_path_real.lower():
                    is_usb = True
                    is_removable = True  # USB devices are removable
            except:
                pass

            # Determine disk type with USB detection
            if is_usb or is_removable:
                disk_type = DiskType.REMOVABLE
            else:
                disk_type = self._determine_disk_type(device_name, model)

            # Get all mount points and filesystems for this device
            mount_points = []
            filesystems = set()
            is_mounted = False

            try:
                for partition in psutil.disk_partitions():
                    if partition.device.startswith(device_path):
                        mount_points.append(partition.mountpoint)
                        filesystems.add(partition.fstype)
                        is_mounted = True
            except Exception:
                pass

            # Check if it's a system disk
            is_system = self._is_system_disk(device_path)

            # Determine status string
            if is_system:
                status = "SYSTEM"
            elif is_mounted:
                status = "MOUNTED"
            elif is_removable:
                status = "REMOVABLE"
            else:
                status = "AVAILABLE"

            # Create DiskInfo with enhanced attributes
            disk_info = DiskInfo(device_path, size_bytes, disk_type, model, serial)

            # Set additional attributes
            disk_info.vendor = vendor
            # size_gb is a computed property from size, no need to set it
            disk_info.is_removable = is_removable
            disk_info.is_ssd = disk_type in [DiskType.SSD, DiskType.NVME]
            disk_info.mount_points = mount_points
            disk_info.is_mounted = is_mounted
            disk_info.is_system = is_system
            disk_info.status = status
            disk_info.mountpoint = mount_points[0] if mount_points else ""
            disk_info.filesystem = list(filesystems)[0] if filesystems else ""

            # Add HPA/DCO detection for non-removable devices only
            if not is_removable:
                try:
                    hpa_dco_info = self.detect_hpa_dco(device_path)
                    disk_info.hpa_dco_info = hpa_dco_info
                    disk_info.hpa_detected = hpa_dco_info.get('hpa_detected', False)
                    disk_info.dco_detected = hpa_dco_info.get('dco_detected', False)
                except Exception as e:
                    logger.debug(f"HPA/DCO detection failed for {device_path}: {e}")
                    disk_info.hpa_dco_info = {
                        'hpa_detected': False,
                        'dco_detected': False,
                        'error': 'Detection requires sudo permissions'
                    }
                    disk_info.hpa_detected = False
                    disk_info.dco_detected = False
            else:
                # For removable devices, skip HPA/DCO detection
                disk_info.hpa_dco_info = {
                    'hpa_detected': False,
                    'dco_detected': False,
                    'error': 'Not applicable for removable devices'
                }
                disk_info.hpa_detected = False
                disk_info.dco_detected = False

            return disk_info

        except Exception as e:
            logger.error(f"Error getting disk info for {device_name}: {e}")
            return None

    def _is_system_disk(self, device: str) -> bool:
        """Check if a disk is a system disk"""
        try:
            # Check if any critical mount points are on this device
            critical_mounts = ['/', '/boot', '/boot/efi', '/var', '/usr', '/home']
            for partition in psutil.disk_partitions():
                if partition.device.startswith(device) and partition.mountpoint in critical_mounts:
                    return True
            return False
        except Exception:
            return False
    
    def _determine_disk_type(self, device_name: str, model: str) -> DiskType:
        """Determine disk type based on device name and model"""
        device_lower = device_name.lower()
        model_lower = model.lower()
        
        if 'nvme' in device_lower:
            return DiskType.NVME
        elif 'ssd' in model_lower or 'solid' in model_lower:
            return DiskType.SSD
        elif any(x in device_lower for x in ['sd', 'hd']):
            return DiskType.HDD
        else:
            return DiskType.UNKNOWN
    
    def get_disk_info(self, device: str) -> DiskInfo:
        """Get detailed information about a specific disk"""
        device_name = os.path.basename(device)
        return self._get_disk_info_from_sysfs(device_name, device)
    
    def wipe_disk(self, device: str, method: str, passes: int) -> Tuple[bool, str]:
        """Wipe disk using Linux-specific methods"""
        try:
            # Check if it's a USB/removable device
            disk_info = self.get_disk_info(device)
            if disk_info and disk_info.is_removable:
                # For USB devices, optimize all methods
                if method == "quick":
                    return self._wipe_usb_optimized(device)
                elif method == "secure":
                    # Limit to 1 pass for USB
                    if passes > 1:
                        print(f"Note: Using 1 pass for USB device (multiple passes unnecessary)")
                        passes = 1
                    return self._wipe_with_dd(device, 1)
                elif method == "dd":
                    # For dd on USB, use optimized approach
                    if passes > 1:
                        print(f"Note: Using 1 pass for USB device")
                        passes = 1
                    return self._wipe_with_dd(device, 1)
            
            if method == "hdparm":
                return self._wipe_with_hdparm(device)
            elif method == "nvme":
                return self._wipe_with_nvme(device)
            elif method == "blkdiscard":
                return self._wipe_with_blkdiscard(device)
            elif method == "dd":
                return self._wipe_with_dd(device, passes)
            elif method == "secure":
                return self._wipe_secure(device, passes)
            elif method == "quick":
                return self._wipe_quick(device)
            else:
                return False, f"Unknown wipe method: {method}"
                
        except Exception as e:
            logger.error(f"Error wiping disk {device}: {e}")
            return False, str(e)
    
    def _wipe_with_hdparm(self, device: str) -> Tuple[bool, str]:
        """Use hdparm for HDD secure erase"""
        try:
            # Check if hdparm is available
            hdparm_path = self.tool_manager.get_tool_path('hdparm')
            if not hdparm_path:
                return False, "hdparm not available"
            
            # First, set security password (required for secure erase)
            cmd1 = [hdparm_path, "--user-master", "u", "--security-set-pass", "p", device]
            from ..sudo_manager import SudoManager
            sudo_manager = SudoManager()
            success1, stdout1, stderr1 = sudo_manager.run_with_sudo(cmd1, "set hdparm security password")
            
            if not success1:
                return False, f"Failed to set security password: {stderr1}"
            
            # Perform secure erase
            cmd2 = [hdparm_path, "--user-master", "u", "--security-erase", "p", device]
            success2, stdout2, stderr2 = sudo_manager.run_with_sudo(cmd2, "hdparm secure erase")
            
            if not success2:
                return False, f"hdparm secure erase failed: {stderr2}"
            
            return True, "Disk wiped successfully using hdparm secure erase"
                
        except subprocess.TimeoutExpired:
            return False, "hdparm operation timed out"
        except subprocess.CalledProcessError:
            return False, "hdparm command failed or insufficient permissions"
        except Exception as e:
            return False, f"hdparm error: {e}"
    
    def _wipe_with_nvme(self, device: str) -> Tuple[bool, str]:
        """Use nvme-cli for NVMe secure erase"""
        try:
            # Check if nvme-cli is available
            nvme_path = self.tool_manager.get_tool_path('nvme')
            if not nvme_path:
                return False, "nvme-cli not available"
            
            # Format the device (secure erase)
            cmd = [nvme_path, "format", device, "--ses=1", "--force"]
            from ..sudo_manager import SudoManager
            sudo_manager = SudoManager()
            success, stdout, stderr = sudo_manager.run_with_sudo(cmd, "nvme secure format")
            
            if success:
                return True, "NVMe disk wiped successfully using nvme-cli"
            else:
                return False, f"nvme format failed: {stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "nvme operation timed out"
        except subprocess.CalledProcessError:
            return False, "nvme-cli command failed or insufficient permissions"
        except Exception as e:
            return False, f"nvme error: {e}"
    
    def _wipe_with_blkdiscard(self, device: str) -> Tuple[bool, str]:
        """Use blkdiscard for TRIM-based wiping"""
        try:
            # Check if blkdiscard is available
            blkdiscard_path = self.tool_manager.get_tool_path('blkdiscard')
            if not blkdiscard_path:
                return False, "blkdiscard not available"
            
            # Perform TRIM discard
            cmd = [blkdiscard_path, device]
            from ..sudo_manager import SudoManager
            sudo_manager = SudoManager()
            success, stdout, stderr = sudo_manager.run_with_sudo(cmd, "blkdiscard TRIM")
            
            if success:
                return True, "Disk wiped successfully using blkdiscard TRIM"
            else:
                return False, f"blkdiscard failed: {stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "blkdiscard operation timed out"
        except subprocess.CalledProcessError:
            return False, "blkdiscard command failed or insufficient permissions"
        except Exception as e:
            return False, f"blkdiscard error: {e}"
    
    def _wipe_with_dd(self, device: str, passes: int) -> Tuple[bool, str]:
        """Use dd for secure multi-pass wiping"""
        try:
            # Check if dd is available
            subprocess.run(["which", "dd"], check=True, capture_output=True)
            
            # Get disk size
            disk_info = self.get_disk_info(device)
            if not disk_info or disk_info.size == 0:
                return False, "Could not determine disk size"
            
            # Calculate disk size in MB for count parameter
            disk_size_mb = disk_info.size // (1024 * 1024)
            logger.info(f"Disk size: {disk_info.size} bytes ({disk_size_mb} MB)")
            
            # Perform multiple passes
            for pass_num in range(passes):
                logger.info(f"Starting dd wipe pass {pass_num + 1}/{passes}")
                
                # Use /dev/urandom for random data with proper count parameter
                cmd = ["dd", f"if=/dev/urandom", f"of={device}", 
                       "bs=1M", f"count={disk_size_mb}", "status=progress", "conv=fsync"]
                
                # Use the sudo manager's run_with_sudo method to handle cached password
                # Get the global sudo manager instance that has the cached password
                from ..sudo_manager import SudoManager
                sudo_manager = SudoManager()
                success, stdout, stderr = sudo_manager.run_with_sudo(cmd, f"dd wipe pass {pass_num + 1}")
                
                if not success:
                    return False, f"dd wipe pass {pass_num + 1} failed: {stderr}"
            
            return True, f"Disk wiped successfully using dd with {passes} passes"
            
        except subprocess.TimeoutExpired:
            return False, "dd operation timed out"
        except subprocess.CalledProcessError:
            return False, "dd not available or insufficient permissions"
        except Exception as e:
            return False, f"dd error: {e}"
    
    def _wipe_secure(self, device: str, passes: int) -> Tuple[bool, str]:
        """Perform secure multi-pass wipe using dd"""
        return self._wipe_with_dd(device, passes)
    
    def _wipe_quick(self, device: str) -> Tuple[bool, str]:
        """Perform quick single-pass wipe"""
        return self._wipe_with_dd(device, 1)
    
    def _wipe_usb_optimized(self, device: str) -> Tuple[bool, str]:
        """Optimized wipe for USB devices - fast and effective"""
        try:
            from ..sudo_manager import SudoManager
            sudo_manager = SudoManager()
            
            print("🔄 USB device detected - using optimized wipe...")
            
            # Method 1: Try wipefs first (fastest)
            cmd = ['wipefs', '-a', device]
            success, stdout, stderr = sudo_manager.run_with_sudo(cmd, "wipefs USB")
            
            if success:
                print("✅ USB wiped using wipefs (fastest method)")
                return True, "USB device wiped successfully (signatures removed)"
            
            # Method 2: Fallback to dd for partition table only
            print("Wipefs unavailable, using dd for partition table...")
            
            # Only wipe first 10MB (partition table + boot sector)
            cmd = ['dd', 'if=/dev/zero', f'of={device}', 'bs=1M', 'count=10', 'status=progress']
            success, stdout, stderr = sudo_manager.run_with_sudo(cmd, "dd USB quick wipe")
            
            if success:
                # Optionally wipe last 10MB (backup GPT)
                try:
                    # Get device size
                    size_cmd = ['blockdev', '--getsize64', device]
                    size_success, size_out, _ = sudo_manager.run_with_sudo(size_cmd, "get size")
                    if size_success:
                        size_bytes = int(size_out.strip())
                        last_offset = max(0, (size_bytes // (1024*1024)) - 10)
                        
                        # Wipe last 10MB
                        cmd_end = ['dd', 'if=/dev/zero', f'of={device}', 'bs=1M', 
                                  'count=10', f'seek={last_offset}']
                        sudo_manager.run_with_sudo(cmd_end, "wipe backup GPT")
                except:
                    pass  # Not critical if we can't wipe the end
                
                return True, "USB device wiped successfully (partition table cleared)"
            else:
                return False, f"USB wipe failed: {stderr}"
                
        except Exception as e:
            return False, f"USB wipe error: {str(e)}"
    
    def get_wipe_methods(self) -> List[str]:
        """Get available wiping methods for Linux"""
        methods = ["dd", "secure", "quick"]

        # Check for tools using tool manager
        if self.tool_manager.is_tool_available('hdparm'):
            methods.append("hdparm")

        if self.tool_manager.is_tool_available('nvme'):
            methods.append("nvme")

        if self.tool_manager.is_tool_available('blkdiscard'):
            methods.append("blkdiscard")

        return methods
    
    def is_disk_writable(self, device: str) -> bool:
        """Check if disk is writable"""
        try:
            # Check if it's a system disk
            system_disks = self.get_system_disks()
            if device in system_disks:
                return False
            
            # Get disk info to check if it's removable
            disk_info = self.get_disk_info(device)
            is_removable = disk_info and disk_info.is_removable
            
            # For removable devices, allow wiping even if mounted (we'll unmount them)
            if is_removable:
                return True
            
            # For non-removable devices, check if it's mounted
            for partition in psutil.disk_partitions():
                if partition.device == device:
                    return False  # Don't wipe mounted non-removable devices
            
            # Check if it's a partition of a mounted disk
            device_name = os.path.basename(device)
            for partition in psutil.disk_partitions():
                if device_name in partition.device:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if disk is writable: {e}")
            return False
    
    def get_system_disks(self) -> List[str]:
        """Get list of system disks with enhanced protection"""
        system_disks = []
        
        try:
            # Method 1: Get root filesystem from df command
            import subprocess
            try:
                result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, check=True)
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    root_device = lines[1].split()[0]
                    if root_device.startswith('/dev/'):
                        # Extract disk device (remove partition number)
                        disk_device = ''.join(c for c in root_device if c.isalpha())
                        if disk_device:
                            system_disks.append(f"/dev/{disk_device}")
            except subprocess.CalledProcessError:
                pass
            
            # Method 2: Check all mounted system partitions
            for partition in psutil.disk_partitions():
                if partition.mountpoint in ['/', '/boot', '/boot/efi', '/var', '/usr', '/home']:
                    device = partition.device
                    if device.startswith('/dev/'):
                        # Extract disk device (remove partition number)
                        disk_device = ''.join(c for c in device if c.isalpha())
                        if disk_device:
                            system_disks.append(f"/dev/{disk_device}")
            
            # Method 3: Check /proc/mounts for additional system devices
            try:
                with open('/proc/mounts', 'r') as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            device = parts[0]
                            mountpoint = parts[1]
                            if mountpoint in ['/', '/boot', '/boot/efi', '/var', '/usr', '/home']:
                                if device.startswith('/dev/'):
                                    # Extract disk device
                                    disk_device = ''.join(c for c in device if c.isalpha())
                                    if disk_device:
                                        system_disks.append(f"/dev/{disk_device}")
            except FileNotFoundError:
                pass
            
            # Method 4: Check for boot device from /proc/cmdline
            try:
                with open('/proc/cmdline', 'r') as f:
                    cmdline = f.read()
                    # Look for root= parameter
                    import re
                    root_match = re.search(r'root=([^\s]+)', cmdline)
                    if root_match:
                        root_device = root_match.group(1)
                        if root_device.startswith('/dev/'):
                            disk_device = ''.join(c for c in root_device if c.isalpha())
                            if disk_device:
                                system_disks.append(f"/dev/{disk_device}")
            except FileNotFoundError:
                pass
            
            # Method 5: Additional safety - protect common system disk patterns
            try:
                with open('/proc/partitions', 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            device_name = parts[3]
                            # Only check if it actually has system partitions
                            # Don't pre-filter by device name!
                            if self._has_system_partitions(f"/dev/{device_name}"):
                                system_disks.append(f"/dev/{device_name}")
            except FileNotFoundError:
                pass
                                    
        except Exception as e:
            logger.error(f"Error getting system disks: {e}")
        
        # Remove duplicates and log protected disks
        unique_disks = list(set(system_disks))
        logger.info(f"Protected system disks: {unique_disks}")
        return unique_disks
    
    def _has_system_partitions(self, device: str) -> bool:
        """Check if a device contains system partitions"""
        try:
            # Only consider it a system disk if it has critical mount points
            device_name = os.path.basename(device)
            for partition in psutil.disk_partitions():
                if device_name in partition.device:
                    # Only system-critical mount points
                    if partition.mountpoint in ['/', '/boot', '/boot/efi', '/usr', '/var']:
                        return True
            return False
        except Exception:
            return False
