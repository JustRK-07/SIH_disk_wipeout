"""
Linux-specific disk handling implementation
Uses hdparm for HDDs, nvme-cli for SSDs, and blkdiscard for TRIM
"""

import os
import subprocess
import logging
import psutil
import glob
from typing import List, Tuple
from pathlib import Path

from .base_handler import BaseDiskHandler
from ..models import DiskInfo

logger = logging.getLogger(__name__)

class LinuxDiskHandler(BaseDiskHandler):
    """Linux-specific disk handler"""
    
    def __init__(self):
        self.block_devices_path = "/sys/block"
        self.dev_path = "/dev"
    
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
            subprocess.run(["which", "hdparm"], check=True, capture_output=True)
            
            # First, set security password (required for secure erase)
            cmd1 = ["sudo", "hdparm", "--user-master", "u", "--security-set-pass", "p", device]
            result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=30)
            
            if result1.returncode != 0:
                return False, f"Failed to set security password: {result1.stderr}"
            
            # Perform secure erase
            cmd2 = ["sudo", "hdparm", "--user-master", "u", "--security-erase", "p", device]
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=3600)
            
            if result2.returncode == 0:
                return True, "Disk wiped successfully using hdparm secure erase"
            else:
                return False, f"hdparm secure erase failed: {result2.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "hdparm operation timed out"
        except subprocess.CalledProcessError:
            return False, "hdparm not available or insufficient permissions"
        except Exception as e:
            return False, f"hdparm error: {e}"
    
    def _wipe_with_nvme(self, device: str) -> Tuple[bool, str]:
        """Use nvme-cli for NVMe secure erase"""
        try:
            # Check if nvme-cli is available
            subprocess.run(["which", "nvme"], check=True, capture_output=True)
            
            # Format the device (secure erase)
            cmd = ["sudo", "nvme", "format", device, "--ses=1", "--force"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                return True, "NVMe disk wiped successfully using nvme-cli"
            else:
                return False, f"nvme format failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "nvme operation timed out"
        except subprocess.CalledProcessError:
            return False, "nvme-cli not available or insufficient permissions"
        except Exception as e:
            return False, f"nvme error: {e}"
    
    def _wipe_with_blkdiscard(self, device: str) -> Tuple[bool, str]:
        """Use blkdiscard for TRIM-based wiping"""
        try:
            # Check if blkdiscard is available
            subprocess.run(["which", "blkdiscard"], check=True, capture_output=True)
            
            # Perform TRIM discard
            cmd = ["sudo", "blkdiscard", device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                return True, "Disk wiped successfully using blkdiscard TRIM"
            else:
                return False, f"blkdiscard failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "blkdiscard operation timed out"
        except subprocess.CalledProcessError:
            return False, "blkdiscard not available or insufficient permissions"
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
        
        # Check for hdparm
        try:
            subprocess.run(["which", "hdparm"], check=True, capture_output=True)
            methods.append("hdparm")
        except subprocess.CalledProcessError:
            pass
        
        # Check for nvme-cli
        try:
            subprocess.run(["which", "nvme"], check=True, capture_output=True)
            methods.append("nvme")
        except subprocess.CalledProcessError:
            pass
        
        # Check for blkdiscard
        try:
            subprocess.run(["which", "blkdiscard"], check=True, capture_output=True)
            methods.append("blkdiscard")
        except subprocess.CalledProcessError:
            pass
        
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
        """Get list of system disks"""
        system_disks = []
        
        try:
            # Get root filesystem
            root_partition = psutil.disk_partitions()[0]  # Usually the root partition
            if root_partition:
                # Extract the disk device from partition
                device = root_partition.device
                if device.startswith('/dev/'):
                    # Remove partition number to get disk device
                    disk_device = ''.join(c for c in device if c.isalpha())
                    if disk_device:
                        system_disks.append(f"/dev/{disk_device}")
            
            # Also check /proc/mounts for mounted system devices
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        device = parts[0]
                        mountpoint = parts[1]
                        if mountpoint in ['/', '/boot', '/boot/efi']:
                            if device.startswith('/dev/'):
                                # Extract disk device
                                disk_device = ''.join(c for c in device if c.isalpha())
                                if disk_device:
                                    system_disks.append(f"/dev/{disk_device}")
                                    
        except Exception as e:
            logger.error(f"Error getting system disks: {e}")
        
        return list(set(system_disks))  # Remove duplicates
