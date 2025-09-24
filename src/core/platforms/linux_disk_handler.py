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
from ..models import DiskInfo
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
            cmd = ["sudo", hdparm_path, "-I", device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

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
                cmd_dco = ["sudo", hdparm_path, "--dco-identify", device]
                result_dco = subprocess.run(cmd_dco, capture_output=True, text=True, timeout=10)

                if result_dco.returncode == 0:
                    dco_output = result_dco.stdout

                    # Parse DCO information
                    real_max_match = re.search(r'Real max sectors:\s+(\d+)', dco_output)
                    if real_max_match:
                        hpa_dco_info['native_max_sectors'] = int(real_max_match.group(1))
                        hpa_dco_info['detection_method'] = 'hdparm_dco'

                # Alternative: Get native max address
                cmd_native = ["sudo", hdparm_path, "-N", device]
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
                    cmd_smart = ["sudo", smartctl_path, "-i", device]
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

            cmd = ["sudo", hdparm_path, "-N", f"p{native_max}", device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Verify HPA removal
                new_info = self.detect_hpa_dco(device)
                if not new_info['hpa_detected']:
                    return True, f"Successfully removed HPA, exposed {hpa_info['hpa_sectors']} hidden sectors"
                else:
                    return False, "HPA removal attempted but verification failed"
            else:
                return False, f"Failed to remove HPA: {result.stderr}"

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

            cmd = ["sudo", hdparm_path, "--dco-restore", device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Verify DCO removal
                new_info = self.detect_hpa_dco(device)
                if not new_info['dco_detected']:
                    return True, f"Successfully removed DCO, exposed {dco_info['dco_sectors']} hidden sectors"
                else:
                    return False, "DCO removal attempted but verification failed"
            else:
                return False, f"Failed to remove DCO: {result.stderr}"

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
        """Get disk information from sysfs"""
        try:
            # Get size
            size_file = os.path.join(self.block_devices_path, device_name, "size")
            if os.path.exists(size_file):
                with open(size_file, 'r') as f:
                    size_sectors = int(f.read().strip())
                    size_bytes = size_sectors * 512  # Assuming 512-byte sectors
            else:
                size_bytes = 0
            
            # Get model and serial
            model = "Unknown"
            serial = ""
            
            # Try to get from /sys/block/device_name/device/model
            model_file = os.path.join(self.block_devices_path, device_name, "device", "model")
            if os.path.exists(model_file):
                with open(model_file, 'r') as f:
                    model = f.read().strip()
            
            # Try to get serial from /sys/block/device_name/device/serial
            serial_file = os.path.join(self.block_devices_path, device_name, "device", "serial")
            if os.path.exists(serial_file):
                with open(serial_file, 'r') as f:
                    serial = f.read().strip()
            
            # Determine disk type
            disk_type = self._determine_disk_type(device_name, model)
            
            # Get mountpoint and filesystem
            mountpoint = ""
            filesystem = ""
            try:
                for partition in psutil.disk_partitions():
                    if partition.device.startswith(device_path):
                        mountpoint = partition.mountpoint
                        filesystem = partition.fstype
                        break
            except Exception:
                pass
            
            disk_info = DiskInfo(device_path, size_bytes, disk_type, model, serial)
            disk_info.mountpoint = mountpoint
            disk_info.filesystem = filesystem

            # Add HPA/DCO detection
            hpa_dco_info = self.detect_hpa_dco(device_path)
            disk_info.hpa_dco_info = hpa_dco_info

            return disk_info
            
        except Exception as e:
            logger.error(f"Error getting disk info for {device_name}: {e}")
            return None
    
    def _determine_disk_type(self, device_name: str, model: str) -> str:
        """Determine disk type based on device name and model"""
        device_lower = device_name.lower()
        model_lower = model.lower()
        
        if 'nvme' in device_lower:
            return 'nvme'
        elif 'ssd' in model_lower or 'solid' in model_lower:
            return 'ssd'
        elif any(x in device_lower for x in ['sd', 'hd']):
            return 'hdd'
        else:
            return 'unknown'
    
    def get_disk_info(self, device: str) -> DiskInfo:
        """Get detailed information about a specific disk"""
        device_name = os.path.basename(device)
        return self._get_disk_info_from_sysfs(device_name, device)
    
    def wipe_disk(self, device: str, method: str, passes: int) -> Tuple[bool, str]:
        """Wipe disk using Linux-specific methods"""
        try:
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
            cmd1 = ["sudo", hdparm_path, "--user-master", "u", "--security-set-pass", "p", device]
            result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=30)
            
            if result1.returncode != 0:
                return False, f"Failed to set security password: {result1.stderr}"
            
            # Perform secure erase
            cmd2 = ["sudo", hdparm_path, "--user-master", "u", "--security-erase", "p", device]
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=3600)
            
            if result2.returncode == 0:
                return True, "Disk wiped successfully using hdparm secure erase"
            else:
                return False, f"hdparm secure erase failed: {result2.stderr}"
                
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
            cmd = ["sudo", nvme_path, "format", device, "--ses=1", "--force"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                return True, "NVMe disk wiped successfully using nvme-cli"
            else:
                return False, f"nvme format failed: {result.stderr}"
                
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
            cmd = ["sudo", blkdiscard_path, device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                return True, "Disk wiped successfully using blkdiscard TRIM"
            else:
                return False, f"blkdiscard failed: {result.stderr}"
                
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
            
            # Perform multiple passes
            for pass_num in range(passes):
                logger.info(f"Starting dd wipe pass {pass_num + 1}/{passes}")
                
                # Use /dev/urandom for random data
                cmd = ["sudo", "dd", f"if=/dev/urandom", f"of={device}", 
                       "bs=1M", "status=progress", "conv=fsync"]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
                
                if result.returncode != 0:
                    return False, f"dd wipe pass {pass_num + 1} failed: {result.stderr}"
            
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
            
            # Check if it's mounted
            for partition in psutil.disk_partitions():
                if partition.device == device:
                    return False  # Don't wipe mounted devices
            
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
            # This prevents wiping disks that might contain system partitions
            try:
                with open('/proc/partitions', 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 4 and parts[3].startswith(('nvme', 'sda', 'sdb')):
                            device_name = parts[3]
                            # Check if this device has system partitions
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
            # Check if device has partitions that are mounted as system partitions
            device_name = os.path.basename(device)
            for partition in psutil.disk_partitions():
                if device_name in partition.device and partition.mountpoint in ['/', '/boot', '/boot/efi']:
                    return True
            return False
        except Exception:
            return False
