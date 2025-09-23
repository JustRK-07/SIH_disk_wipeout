"""
Windows-specific disk handling implementation
Uses WinAPI, Cipher.exe, and DeviceIoControl for low-level access
"""

import os
import subprocess
import logging
import psutil
from typing import List, Tuple
import ctypes
from ctypes import wintypes

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False
    logging.warning("WMI not available. Some disk information may be limited.")

from .base_handler import BaseDiskHandler
from ..models import DiskInfo

logger = logging.getLogger(__name__)

class WindowsDiskHandler(BaseDiskHandler):
    """Windows-specific disk handler"""
    
    def __init__(self):
        self.wmi_conn = None
        if WMI_AVAILABLE:
            try:
                self.wmi_conn = wmi.WMI()
            except Exception as e:
                logger.warning(f"Could not initialize WMI: {e}")
    
    def get_available_disks(self) -> List[DiskInfo]:
        """Get available disks on Windows"""
        disks = []
        
        try:
            # Get physical disks using WMI
            if self.wmi_conn:
                for disk in self.wmi_conn.Win32_DiskDrive():
                    device = f"\\\\.\\PhysicalDrive{disk.Index}"
                    size = int(disk.Size) if disk.Size else 0
                    model = disk.Model or "Unknown"
                    serial = disk.SerialNumber or ""
                    
                    # Determine disk type
                    disk_type = "hdd"
                    if "SSD" in model.upper() or "SOLID" in model.upper():
                        disk_type = "ssd"
                    elif "NVME" in model.upper():
                        disk_type = "nvme"
                    
                    disk_info = DiskInfo(device, size, disk_type, model, serial)
                    disks.append(disk_info)
            
            # Fallback to psutil if WMI fails
            if not disks:
                for partition in psutil.disk_partitions():
                    if partition.device.startswith('\\\\.\\'):
                        continue
                    
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_info = DiskInfo(
                            partition.device,
                            usage.total,
                            "unknown",
                            "Unknown",
                            ""
                        )
                        disk_info.mountpoint = partition.mountpoint
                        disk_info.filesystem = partition.fstype
                        disks.append(disk_info)
                    except PermissionError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error getting available disks: {e}")
        
        return disks
    
    def get_disk_info(self, device: str) -> DiskInfo:
        """Get detailed information about a specific disk"""
        try:
            if self.wmi_conn:
                # Extract disk index from device path
                if "PhysicalDrive" in device:
                    disk_index = int(device.split("PhysicalDrive")[1])
                    for disk in self.wmi_conn.Win32_DiskDrive():
                        if disk.Index == disk_index:
                            size = int(disk.Size) if disk.Size else 0
                            model = disk.Model or "Unknown"
                            serial = disk.SerialNumber or ""
                            
                            disk_type = "hdd"
                            if "SSD" in model.upper() or "SOLID" in model.upper():
                                disk_type = "ssd"
                            elif "NVME" in model.upper():
                                disk_type = "nvme"
                            
                            return DiskInfo(device, size, disk_type, model, serial)
            
            # Fallback
            return DiskInfo(device, 0, "unknown", "Unknown", "")
            
        except Exception as e:
            logger.error(f"Error getting disk info for {device}: {e}")
            return DiskInfo(device, 0, "unknown", "Unknown", "")
    
    def wipe_disk(self, device: str, method: str, passes: int) -> Tuple[bool, str]:
        """Wipe disk using Windows-specific methods"""
        try:
            if method == "cipher":
                return self._wipe_with_cipher(device)
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
    
    def _wipe_with_cipher(self, device: str) -> Tuple[bool, str]:
        """Use Cipher.exe to wipe free space"""
        try:
            # Cipher.exe only works on mounted drives
            if not device.startswith("\\\\.\\"):
                cmd = ["cipher", "/w:" + device]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
                
                if result.returncode == 0:
                    return True, "Disk wiped successfully using Cipher.exe"
                else:
                    return False, f"Cipher.exe failed: {result.stderr}"
            else:
                return False, "Cipher.exe requires a mounted drive, not a physical device"
                
        except subprocess.TimeoutExpired:
            return False, "Cipher.exe operation timed out"
        except Exception as e:
            return False, f"Cipher.exe error: {e}"
    
    def _wipe_with_dd(self, device: str, passes: int) -> Tuple[bool, str]:
        """Use dd-like approach with Python for secure wiping"""
        try:
            # This is a simplified implementation
            # In a real scenario, you'd need to use DeviceIoControl for low-level access
            return False, "DD method requires low-level DeviceIoControl implementation"
            
        except Exception as e:
            return False, f"DD wipe error: {e}"
    
    def _wipe_secure(self, device: str, passes: int) -> Tuple[bool, str]:
        """Perform secure multi-pass wipe"""
        try:
            # This would require DeviceIoControl implementation
            # For now, return a placeholder
            return False, "Secure wipe requires DeviceIoControl implementation"
            
        except Exception as e:
            return False, f"Secure wipe error: {e}"
    
    def _wipe_quick(self, device: str) -> Tuple[bool, str]:
        """Perform quick single-pass wipe"""
        try:
            # Quick wipe implementation
            return False, "Quick wipe requires DeviceIoControl implementation"
            
        except Exception as e:
            return False, f"Quick wipe error: {e}"
    
    def get_wipe_methods(self) -> List[str]:
        """Get available wiping methods for Windows"""
        methods = ["cipher", "secure", "quick"]
        # Add dd if available
        try:
            subprocess.run(["where", "dd"], capture_output=True, check=True)
            methods.append("dd")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return methods
    
    def is_disk_writable(self, device: str) -> bool:
        """Check if disk is writable"""
        try:
            # Check if it's a system disk
            system_disks = self.get_system_disks()
            if device in system_disks:
                return False
            
            # Check if it's mounted and writable
            if not device.startswith("\\\\.\\"):
                try:
                    test_file = os.path.join(device, "test_write.tmp")
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    return True
                except (PermissionError, OSError):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if disk is writable: {e}")
            return False
    
    def get_system_disks(self) -> List[str]:
        """Get list of system disks"""
        system_disks = []
        
        try:
            # Get system drive
            system_drive = os.environ.get('SystemDrive', 'C:')
            system_disks.append(system_drive)
            
            # Get boot drive
            boot_drive = os.environ.get('SystemRoot', 'C:\\Windows')
            if boot_drive:
                system_disks.append(boot_drive[:2])  # Get drive letter
            
        except Exception as e:
            logger.error(f"Error getting system disks: {e}")
        
        return system_disks
