"""
Android-specific disk handling implementation
Integrates with Android's Storage Access Framework and root-level commands
"""

import os
import subprocess
import logging
import psutil
from typing import List, Tuple
import json

try:
    from jnius import autoclass, PythonJavaClass, java_method
    JNIUS_AVAILABLE = True
except ImportError:
    JNIUS_AVAILABLE = False
    logging.warning("JNIUS not available. Some Android features may be limited.")

from .base_handler import BaseDiskHandler
from ..models import DiskInfo

logger = logging.getLogger(__name__)

class AndroidDiskHandler(BaseDiskHandler):
    """Android-specific disk handler"""
    
    def __init__(self):
        self.is_rooted = self._check_root_access()
        self.storage_manager = None
        self._init_storage_manager()
    
    def _check_root_access(self) -> bool:
        """Check if device has root access"""
        try:
            result = subprocess.run(["su", "-c", "id"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _init_storage_manager(self):
        """Initialize Android Storage Manager"""
        if JNIUS_AVAILABLE:
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                self.storage_manager = activity.getSystemService("storage")
            except Exception as e:
                logger.warning(f"Could not initialize Storage Manager: {e}")
    
    def get_available_disks(self) -> List[DiskInfo]:
        """Get available storage devices on Android"""
        disks = []
        
        try:
            # Get internal storage
            internal_storage = self._get_internal_storage()
            if internal_storage:
                disks.append(internal_storage)
            
            # Get external storage (SD cards, USB drives)
            external_storages = self._get_external_storages()
            disks.extend(external_storages)
            
            # If rooted, get additional block devices
            if self.is_rooted:
                root_disks = self._get_root_block_devices()
                disks.extend(root_disks)
                
        except Exception as e:
            logger.error(f"Error getting available disks: {e}")
        
        return disks
    
    def _get_internal_storage(self) -> DiskInfo:
        """Get internal storage information"""
        try:
            # Get internal storage path
            internal_path = os.environ.get('ANDROID_STORAGE', '/storage/emulated/0')
            
            if os.path.exists(internal_path):
                # Get storage info using psutil
                usage = psutil.disk_usage(internal_path)
                
                disk_info = DiskInfo(
                    device=internal_path,
                    size=usage.total,
                    type="internal",
                    model="Internal Storage",
                    serial=""
                )
                disk_info.mountpoint = internal_path
                disk_info.filesystem = "f2fs"  # Common on Android
                
                return disk_info
                
        except Exception as e:
            logger.error(f"Error getting internal storage: {e}")
        
        return None
    
    def _get_external_storages(self) -> List[DiskInfo]:
        """Get external storage devices"""
        external_disks = []
        
        try:
            # Check common external storage paths
            external_paths = [
                '/storage/sdcard1',  # External SD card
                '/storage/usbotg',   # USB OTG
                '/mnt/media_rw',     # Mounted external storage
                '/storage/external_storage'
            ]
            
            for path in external_paths:
                if os.path.exists(path):
                    try:
                        usage = psutil.disk_usage(path)
                        
                        disk_info = DiskInfo(
                            device=path,
                            size=usage.total,
                            type="external",
                            model="External Storage",
                            serial=""
                        )
                        disk_info.mountpoint = path
                        disk_info.filesystem = "vfat"  # Common for external storage
                        
                        external_disks.append(disk_info)
                        
                    except (OSError, PermissionError):
                        continue
            
            # Also check /proc/mounts for mounted external devices
            if os.path.exists('/proc/mounts'):
                with open('/proc/mounts', 'r') as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 3:
                            device = parts[0]
                            mountpoint = parts[1]
                            filesystem = parts[2]
                            
                            # Check if it's an external storage device
                            if (device.startswith('/dev/block/') and 
                                mountpoint.startswith('/storage/') and
                                mountpoint not in ['/storage/emulated/0']):
                                
                                try:
                                    usage = psutil.disk_usage(mountpoint)
                                    
                                    disk_info = DiskInfo(
                                        device=device,
                                        size=usage.total,
                                        type="external",
                                        model="External Storage",
                                        serial=""
                                    )
                                    disk_info.mountpoint = mountpoint
                                    disk_info.filesystem = filesystem
                                    
                                    external_disks.append(disk_info)
                                    
                                except (OSError, PermissionError):
                                    continue
                                    
        except Exception as e:
            logger.error(f"Error getting external storages: {e}")
        
        return external_disks
    
    def _get_root_block_devices(self) -> List[DiskInfo]:
        """Get block devices using root access"""
        root_disks = []
        
        try:
            # Get block devices from /sys/block
            cmd = ["su", "-c", "ls /sys/block"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                devices = result.stdout.strip().split('\n')
                
                for device in devices:
                    if device and not device.startswith('loop'):
                        device_path = f"/dev/block/{device}"
                        
                        # Get device info
                        cmd_info = ["su", "-c", f"cat /sys/block/{device}/size"]
                        result_info = subprocess.run(cmd_info, capture_output=True, text=True, timeout=5)
                        
                        if result_info.returncode == 0:
                            try:
                                size_sectors = int(result_info.stdout.strip())
                                size_bytes = size_sectors * 512
                                
                                disk_info = DiskInfo(
                                    device=device_path,
                                    size=size_bytes,
                                    type="block",
                                    model="Block Device",
                                    serial=""
                                )
                                
                                root_disks.append(disk_info)
                                
                            except ValueError:
                                continue
                                
        except Exception as e:
            logger.error(f"Error getting root block devices: {e}")
        
        return root_disks
    
    def get_disk_info(self, device: str) -> DiskInfo:
        """Get detailed information about a specific disk"""
        try:
            if device.startswith('/storage/'):
                # It's a mounted storage
                if os.path.exists(device):
                    usage = psutil.disk_usage(device)
                    
                    disk_type = "internal" if "emulated" in device else "external"
                    
                    return DiskInfo(
                        device=device,
                        size=usage.total,
                        type=disk_type,
                        model="Android Storage",
                        serial=""
                    )
            
            elif device.startswith('/dev/block/') and self.is_rooted:
                # It's a block device
                device_name = os.path.basename(device)
                
                cmd = ["su", "-c", f"cat /sys/block/{device_name}/size"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    size_sectors = int(result.stdout.strip())
                    size_bytes = size_sectors * 512
                    
                    return DiskInfo(
                        device=device,
                        size=size_bytes,
                        type="block",
                        model="Block Device",
                        serial=""
                    )
            
        except Exception as e:
            logger.error(f"Error getting disk info for {device}: {e}")
        
        return DiskInfo(device, 0, "unknown", "Unknown", "")
    
    def wipe_disk(self, device: str, method: str, passes: int) -> Tuple[bool, str]:
        """Wipe disk using Android-specific methods"""
        try:
            if method == "dd":
                return self._wipe_with_dd(device, passes)
            elif method == "secure":
                return self._wipe_secure(device, passes)
            elif method == "quick":
                return self._wipe_quick(device)
            elif method == "saf":
                return self._wipe_with_saf(device)
            else:
                return False, f"Unknown wipe method: {method}"
                
        except Exception as e:
            logger.error(f"Error wiping disk {device}: {e}")
            return False, str(e)
    
    def _wipe_with_dd(self, device: str, passes: int) -> Tuple[bool, str]:
        """Use dd for wiping (requires root)"""
        if not self.is_rooted:
            return False, "DD method requires root access"
        
        try:
            for pass_num in range(passes):
                logger.info(f"Starting dd wipe pass {pass_num + 1}/{passes}")
                
                # Use /dev/zero for faster wiping
                cmd = ["su", "-c", f"dd if=/dev/zero of={device} bs=1M status=progress"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
                
                if result.returncode != 0:
                    return False, f"dd wipe pass {pass_num + 1} failed: {result.stderr}"
            
            return True, f"Disk wiped successfully using dd with {passes} passes"
            
        except subprocess.TimeoutExpired:
            return False, "dd operation timed out"
        except Exception as e:
            return False, f"dd error: {e}"
    
    def _wipe_secure(self, device: str, passes: int) -> Tuple[bool, str]:
        """Perform secure multi-pass wipe"""
        return self._wipe_with_dd(device, passes)
    
    def _wipe_quick(self, device: str) -> Tuple[bool, str]:
        """Perform quick single-pass wipe"""
        return self._wipe_with_dd(device, 1)
    
    def _wipe_with_saf(self, device: str) -> Tuple[bool, str]:
        """Use Storage Access Framework for wiping"""
        try:
            # This would require integration with Android's SAF
            # For now, return a placeholder
            return False, "SAF wipe method requires Android app integration"
            
        except Exception as e:
            return False, f"SAF wipe error: {e}"
    
    def get_wipe_methods(self) -> List[str]:
        """Get available wiping methods for Android"""
        methods = ["quick"]
        
        if self.is_rooted:
            methods.extend(["dd", "secure"])
        
        # SAF method is always available but requires app integration
        methods.append("saf")
        
        return methods
    
    def is_disk_writable(self, device: str) -> bool:
        """Check if disk is writable"""
        try:
            # Check if it's a system storage
            system_storages = self.get_system_disks()
            if device in system_storages:
                return False
            
            # Check if it's mounted and writable
            if device.startswith('/storage/'):
                try:
                    test_file = os.path.join(device, "test_write.tmp")
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    return True
                except (PermissionError, OSError):
                    return False
            
            # For block devices, check if we have root access
            if device.startswith('/dev/block/'):
                return self.is_rooted
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if disk is writable: {e}")
            return False
    
    def get_system_disks(self) -> List[str]:
        """Get list of system disks"""
        system_disks = []
        
        try:
            # Internal storage is usually a system disk
            internal_storage = os.environ.get('ANDROID_STORAGE', '/storage/emulated/0')
            system_disks.append(internal_storage)
            
            # System partition
            system_disks.append('/system')
            system_disks.append('/vendor')
            system_disks.append('/boot')
            
        except Exception as e:
            logger.error(f"Error getting system disks: {e}")
        
        return system_disks
