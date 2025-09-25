"""
Android-specific disk handling implementation
Integrates with Android's Storage Access Framework and root-level commands
"""

import os
import subprocess
import logging
import psutil
from typing import List, Tuple, Dict
import json

try:
    from jnius import autoclass, PythonJavaClass, java_method
    JNIUS_AVAILABLE = True
except ImportError:
    JNIUS_AVAILABLE = False
    logging.warning("JNIUS not available. Some Android features may be limited.")

from .base_handler import BaseDiskHandler
from ..models import DiskInfo
from ..tool_manager import tool_manager

logger = logging.getLogger(__name__)

class AndroidDiskHandler(BaseDiskHandler):
    """Android-specific disk handler"""
    
    def __init__(self):
        self.is_rooted = self._check_root_access()
        self.storage_manager = None
        self.tool_manager = tool_manager
        self._init_storage_manager()

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
            # Android detection requires root access for most methods
            if not self.is_rooted:
                hpa_dco_info['error'] = "Root access required for HPA/DCO detection on Android"
                return hpa_dco_info

            # Method 1: Use hdparm if available (some Android devices have it)
            try:
                hdparm_path = self.tool_manager.get_tool_path('hdparm')
                if hdparm_path:
                    # hdparm is available, use it
                    cmd = ["su", "-c", f"{hdparm_path} -I {device}"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                else:
                    # Try system hdparm as fallback
                    result = subprocess.run(["su", "-c", "which hdparm"],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode != 0:
                        result = subprocess.CompletedProcess([], 1)  # Skip this method
                    else:
                        cmd = ["su", "-c", f"hdparm -I {device}"]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                    if result.returncode == 0:
                        output = result.stdout
                        import re

                        # Parse LBA sectors
                        lba48_match = re.search(r'LBA48\s+user\s+addressable\s+sectors:\s+(\d+)', output)
                        if lba48_match:
                            hpa_dco_info['accessible_sectors'] = int(lba48_match.group(1))

                        # Get native max address
                        hdparm_cmd = hdparm_path if hdparm_path else "hdparm"
                        cmd_native = ["su", "-c", f"{hdparm_cmd} -N {device}"]
                        result_native = subprocess.run(cmd_native, capture_output=True, text=True, timeout=10)

                        if result_native.returncode == 0:
                            native_output = result_native.stdout
                            native_match = re.search(r'max sectors\s+=\s+(\d+)/(\d+)', native_output)

                            if native_match:
                                current = int(native_match.group(1))
                                native = int(native_match.group(2))

                                hpa_dco_info['current_max_sectors'] = current
                                hpa_dco_info['native_max_sectors'] = native

                                # Detect HPA
                                if native > current:
                                    hpa_dco_info['hpa_detected'] = True
                                    hpa_dco_info['hpa_sectors'] = native - current
                                    hpa_dco_info['hidden_sectors'] = native - current
                                    hpa_dco_info['can_remove_hpa'] = True
                                    hpa_dco_info['detection_method'] = 'hdparm'
            except:
                pass

            # Method 2: Check /sys/block for size discrepancies
            if device.startswith('/dev/block/'):
                device_name = os.path.basename(device)

                # Get size from /sys/block
                size_file = f"/sys/block/{device_name}/size"
                cmd_size = ["su", "-c", f"cat {size_file}"]
                result_size = subprocess.run(cmd_size, capture_output=True, text=True, timeout=5)

                if result_size.returncode == 0:
                    kernel_sectors = int(result_size.stdout.strip())

                    if hpa_dco_info['accessible_sectors'] == 0:
                        hpa_dco_info['accessible_sectors'] = kernel_sectors

                    # Check partition table for hidden areas
                    cmd_parts = ["su", "-c", f"cat /proc/partitions | grep {device_name}"]
                    result_parts = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=5)

                    if result_parts.returncode == 0:
                        lines = result_parts.stdout.strip().split('\n')
                        total_partition_sectors = 0

                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 3:
                                # Skip the main device entry
                                if not parts[-1].endswith(device_name):
                                    blocks = int(parts[2])
                                    total_partition_sectors += blocks * 2  # blocks are 1KB, sectors are 512B

                        # If kernel reports more sectors than partitions use, HPA might exist
                        if kernel_sectors > total_partition_sectors and total_partition_sectors > 0:
                            unused_sectors = kernel_sectors - total_partition_sectors
                            if unused_sectors > 2048:  # More than 1MB unused
                                hpa_dco_info['hpa_detected'] = True
                                hpa_dco_info['hidden_sectors'] = unused_sectors
                                hpa_dco_info['hpa_sectors'] = unused_sectors
                                if not hpa_dco_info['detection_method']:
                                    hpa_dco_info['detection_method'] = 'partition_analysis'

            # Method 3: Use smartctl if available (some custom ROMs include it)
            try:
                smartctl_path = self.tool_manager.get_tool_path('smartctl')
                if smartctl_path:
                    cmd_smart = ["su", "-c", f"{smartctl_path} -i {device}"]
                    result_smart = subprocess.run(cmd_smart, capture_output=True, text=True, timeout=10)
                else:
                    # Try system smartctl as fallback
                    result = subprocess.run(["su", "-c", "which smartctl"],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        cmd_smart = ["su", "-c", f"smartctl -i {device}"]
                        result_smart = subprocess.run(cmd_smart, capture_output=True, text=True, timeout=10)
                    else:
                        result_smart = subprocess.CompletedProcess([], 1)  # Skip this method

                    if result_smart.returncode == 0:
                        smart_output = result_smart.stdout
                        import re

                        capacity_match = re.search(r'User Capacity:.*\[(\d+) bytes\]', smart_output)
                        if capacity_match:
                            smart_bytes = int(capacity_match.group(1))
                            smart_sectors = smart_bytes // 512

                            if hpa_dco_info['accessible_sectors'] == 0:
                                hpa_dco_info['accessible_sectors'] = smart_sectors
                            elif smart_sectors < hpa_dco_info['accessible_sectors']:
                                # SMART reports less than kernel, possible HPA
                                hpa_dco_info['hpa_detected'] = True
                                hpa_dco_info['hidden_sectors'] = hpa_dco_info['accessible_sectors'] - smart_sectors
                                if not hpa_dco_info['detection_method']:
                                    hpa_dco_info['detection_method'] = 'smartctl'
            except:
                pass

            # Method 4: Direct block device IOCTL (Android-specific)
            if device.startswith('/dev/block/'):
                try:
                    # Get block device size using BLKGETSIZE64 ioctl
                    cmd_ioctl = ["su", "-c", f"blockdev --getsize64 {device}"]
                    result_ioctl = subprocess.run(cmd_ioctl, capture_output=True, text=True, timeout=5)

                    if result_ioctl.returncode == 0:
                        device_bytes = int(result_ioctl.stdout.strip())
                        device_sectors = device_bytes // 512

                        if hpa_dco_info['current_max_sectors'] == 0:
                            hpa_dco_info['current_max_sectors'] = device_sectors

                        # Also get sector size to ensure accuracy
                        cmd_sector = ["su", "-c", f"blockdev --getss {device}"]
                        result_sector = subprocess.run(cmd_sector, capture_output=True, text=True, timeout=5)

                        if result_sector.returncode == 0:
                            sector_size = int(result_sector.stdout.strip())
                            if sector_size != 512:
                                # Recalculate with actual sector size
                                device_sectors = device_bytes // sector_size
                                hpa_dco_info['current_max_sectors'] = device_sectors

                        if not hpa_dco_info['detection_method']:
                            hpa_dco_info['detection_method'] = 'blockdev'
                except:
                    pass

            # Check for eMMC-specific hidden areas (common on Android)
            if 'mmc' in device or 'emmc' in device:
                try:
                    # Check for RPMB (Replay Protected Memory Block) partition
                    cmd_rpmb = ["su", "-c", "ls -la /dev/block/mmcblk*rpmb"]
                    result_rpmb = subprocess.run(cmd_rpmb, capture_output=True, text=True, timeout=5)

                    if result_rpmb.returncode == 0 and 'rpmb' in result_rpmb.stdout:
                        # RPMB exists, it's a hidden area but not traditional HPA
                        hpa_dco_info['hpa_detected'] = True
                        hpa_dco_info['hidden_sectors'] = 8192  # RPMB is typically 4MB
                        hpa_dco_info['detection_method'] = 'emmc_rpmb'
                        hpa_dco_info['error'] = "eMMC RPMB partition detected (hardware-protected area)"
                except:
                    pass

            # Set final status
            if not hpa_dco_info['detection_method'] and not hpa_dco_info['error']:
                hpa_dco_info['error'] = "Unable to fully detect HPA/DCO on this Android device"

        except Exception as e:
            hpa_dco_info['error'] = f"Error detecting HPA/DCO: {str(e)}"

        return hpa_dco_info

    def remove_hpa(self, device: str) -> Tuple[bool, str]:
        """
        Remove Host Protected Area from disk on Android
        WARNING: This requires root access and may void warranty
        """
        try:
            if not self.is_rooted:
                return False, "Root access required to remove HPA on Android"

            # First detect HPA
            hpa_info = self.detect_hpa_dco(device)

            if not hpa_info['hpa_detected']:
                return False, "No HPA detected on this device"

            if not hpa_info['can_remove_hpa']:
                return False, "Cannot remove HPA from this device (may be hardware-protected)"

            # Try to use hdparm if available
            hdparm_path = self.tool_manager.get_tool_path('hdparm')
            if not hdparm_path:
                # Try system hdparm as fallback
                result = subprocess.run(["su", "-c", "which hdparm"],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    return False, "hdparm not available - cannot remove HPA on this Android device"
                hdparm_path = "hdparm"

            # Use hdparm to remove HPA
            native_max = hpa_info['native_max_sectors']
            cmd = ["su", "-c", f"{hdparm_path} -N p{native_max} {device}"]
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
        Remove Device Configuration Overlay from disk on Android
        WARNING: This is extremely dangerous and may brick the device
        """
        try:
            if not self.is_rooted:
                return False, "Root access required to remove DCO on Android"

            # DCO removal on Android is extremely risky
            # Most Android devices don't have traditional DCO
            # eMMC devices use different protection mechanisms

            return False, "DCO removal not supported on Android devices due to risk of permanent damage"

        except Exception as e:
            return False, f"Error removing DCO: {str(e)}"
    
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

            # Check for additional tools
            if self.tool_manager.is_tool_available('hdparm'):
                methods.append("hdparm")

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
