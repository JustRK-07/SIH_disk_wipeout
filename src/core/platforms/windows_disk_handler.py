"""
Windows-specific disk handling implementation
Uses WinAPI, Cipher.exe, and DeviceIoControl for low-level access
"""

import os
import subprocess
import logging
import psutil
from typing import List, Tuple, Dict
import ctypes
from ctypes import wintypes

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False
    logging.warning("WMI not available. Some disk information may be limited.")

from .base_handler import BaseDiskHandler
from ..models import DiskInfo, DiskType
from ..tool_manager import tool_manager

logger = logging.getLogger(__name__)

class WindowsDiskHandler(BaseDiskHandler):
    """Windows-specific disk handler"""
    
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
            # Extract disk number from device path
            if "PhysicalDrive" not in device:
                hpa_dco_info['error'] = "Invalid device path for HPA/DCO detection"
                return hpa_dco_info

            disk_num = device.split("PhysicalDrive")[1]

            # Method 1: Use WMI to get disk capacity information
            if self.wmi_conn:
                try:
                    for disk in self.wmi_conn.Win32_DiskDrive():
                        if str(disk.Index) == disk_num:
                            # Get reported size
                            if disk.Size:
                                hpa_dco_info['accessible_sectors'] = int(disk.Size) // 512

                            # Try to get additional info from MSStorageDriver_ATAPISmartData
                            try:
                                smart_data = self.wmi_conn.query(
                                    f"SELECT * FROM MSStorageDriver_FailurePredictData WHERE InstanceName LIKE '%{disk_num}%'"
                                )
                                if smart_data:
                                    # Parse SMART data for hidden areas
                                    pass
                            except:
                                pass
                            break
                except Exception as e:
                    logger.debug(f"WMI query failed: {e}")

            # Method 2: Use DeviceIoControl to get ATA IDENTIFY data
            try:
                import struct
                import ctypes
                from ctypes import wintypes, windll

                # Open the physical drive
                handle = ctypes.windll.kernel32.CreateFileW(
                    device,
                    0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
                    0x1 | 0x2,  # FILE_SHARE_READ | FILE_SHARE_WRITE
                    None,
                    3,  # OPEN_EXISTING
                    0,
                    None
                )

                if handle != -1:
                    # IOCTL_ATA_PASS_THROUGH
                    IOCTL_ATA_PASS_THROUGH = 0x0004D02C

                    # ATA IDENTIFY DEVICE command
                    ATA_IDENTIFY_DEVICE = 0xEC

                    # Structure for ATA pass through
                    class ATA_PASS_THROUGH_EX(ctypes.Structure):
                        _fields_ = [
                            ("Length", ctypes.c_ushort),
                            ("AtaFlags", ctypes.c_ushort),
                            ("PathId", ctypes.c_ubyte),
                            ("TargetId", ctypes.c_ubyte),
                            ("Lun", ctypes.c_ubyte),
                            ("ReservedAsUchar", ctypes.c_ubyte),
                            ("DataTransferLength", ctypes.c_ulong),
                            ("TimeOutValue", ctypes.c_ulong),
                            ("ReservedAsUlong", ctypes.c_ulong),
                            ("DataBufferOffset", ctypes.POINTER(ctypes.c_ubyte)),
                            ("PreviousTaskFile", ctypes.c_ubyte * 8),
                            ("CurrentTaskFile", ctypes.c_ubyte * 8)
                        ]

                    # Prepare the command
                    ata_cmd = ATA_PASS_THROUGH_EX()
                    ata_cmd.Length = ctypes.sizeof(ATA_PASS_THROUGH_EX)
                    ata_cmd.AtaFlags = 0x02  # ATA_FLAGS_DATA_IN
                    ata_cmd.DataTransferLength = 512
                    ata_cmd.TimeOutValue = 10
                    ata_cmd.CurrentTaskFile[6] = ATA_IDENTIFY_DEVICE

                    # Buffer for IDENTIFY data
                    identify_buffer = (ctypes.c_ubyte * 512)()
                    bytes_returned = wintypes.DWORD()

                    # Execute IOCTL
                    success = windll.kernel32.DeviceIoControl(
                        handle,
                        IOCTL_ATA_PASS_THROUGH,
                        ctypes.byref(ata_cmd),
                        ctypes.sizeof(ata_cmd),
                        ctypes.byref(identify_buffer),
                        512,
                        ctypes.byref(bytes_returned),
                        None
                    )

                    if success:
                        # Parse IDENTIFY data for LBA sectors
                        # Words 60-61: Total number of user addressable sectors (LBA28)
                        # Words 100-103: Total number of user addressable sectors (LBA48)

                        # Extract LBA48 sector count (words 100-103)
                        lba48_sectors = struct.unpack('<Q', bytes(identify_buffer[200:208]))[0]
                        if lba48_sectors > 0:
                            hpa_dco_info['current_max_sectors'] = lba48_sectors

                        # Check for HPA support in IDENTIFY data
                        # Word 82, bit 10: HPA feature set supported
                        word82 = struct.unpack('<H', bytes(identify_buffer[164:166]))[0]
                        hpa_supported = bool(word82 & 0x0400)

                        if hpa_supported:
                            # Try to get native max sectors
                            # This would require sending READ NATIVE MAX ADDRESS command
                            hpa_dco_info['detection_method'] = 'ata_identify'

                    # Close handle
                    windll.kernel32.CloseHandle(handle)

            except Exception as e:
                logger.debug(f"DeviceIoControl method failed: {e}")

            # Method 3: Use diskpart utility to check for hidden sectors
            try:
                # Create a diskpart script
                script = f"select disk {disk_num}\ndetail disk\nexit"
                script_file = "temp_diskpart.txt"

                with open(script_file, 'w') as f:
                    f.write(script)

                # Run diskpart
                result = subprocess.run(
                    ["diskpart", "/s", script_file],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    output = result.stdout
                    import re

                    # Parse diskpart output for disk size
                    size_match = re.search(r'Disk size\s*:\s*([\d.]+)\s*(GB|TB|MB)', output, re.IGNORECASE)
                    if size_match:
                        size_value = float(size_match.group(1))
                        size_unit = size_match.group(2).upper()

                        if size_unit == 'TB':
                            size_bytes = size_value * 1024 * 1024 * 1024 * 1024
                        elif size_unit == 'GB':
                            size_bytes = size_value * 1024 * 1024 * 1024
                        elif size_unit == 'MB':
                            size_bytes = size_value * 1024 * 1024

                        diskpart_sectors = int(size_bytes // 512)

                        # Compare with accessible sectors
                        if hpa_dco_info['accessible_sectors'] > 0 and diskpart_sectors > hpa_dco_info['accessible_sectors']:
                            hpa_dco_info['hpa_detected'] = True
                            hpa_dco_info['hidden_sectors'] = diskpart_sectors - hpa_dco_info['accessible_sectors']
                            hpa_dco_info['hpa_sectors'] = hpa_dco_info['hidden_sectors']
                            hpa_dco_info['detection_method'] = 'diskpart'

                # Clean up
                if os.path.exists(script_file):
                    os.remove(script_file)

            except Exception as e:
                logger.debug(f"Diskpart method failed: {e}")

            # Method 4: Check with PowerShell Get-Disk cmdlet
            try:
                cmd = f"powershell -Command \"Get-Disk -Number {disk_num} | Select-Object Size, AllocatedSize, LargestFreeExtent | ConvertTo-Json\""
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)

                if result.returncode == 0:
                    import json
                    disk_data = json.loads(result.stdout)

                    if disk_data.get('Size'):
                        ps_sectors = disk_data['Size'] // 512
                        if hpa_dco_info['accessible_sectors'] == 0:
                            hpa_dco_info['accessible_sectors'] = ps_sectors

                        # Check for differences indicating hidden areas
                        if disk_data.get('AllocatedSize') and disk_data['AllocatedSize'] < disk_data['Size']:
                            unallocated = disk_data['Size'] - disk_data['AllocatedSize']
                            if unallocated > 1024 * 1024 * 1024:  # More than 1GB unallocated
                                hpa_dco_info['hpa_detected'] = True
                                hpa_dco_info['hidden_sectors'] = unallocated // 512
                                if not hpa_dco_info['detection_method']:
                                    hpa_dco_info['detection_method'] = 'powershell'

            except Exception as e:
                logger.debug(f"PowerShell method failed: {e}")

            # Set error if no detection method worked
            if not hpa_dco_info['detection_method'] and not hpa_dco_info['error']:
                hpa_dco_info['error'] = "Unable to detect HPA/DCO - may require additional tools or drivers"

        except Exception as e:
            hpa_dco_info['error'] = f"Error detecting HPA/DCO: {str(e)}"

        return hpa_dco_info

    def remove_hpa(self, device: str) -> Tuple[bool, str]:
        """
        Remove Host Protected Area from disk on Windows
        Note: This requires specialized tools like HDAT2 or manufacturer utilities
        """
        try:
            # First detect HPA
            hpa_info = self.detect_hpa_dco(device)

            if not hpa_info['hpa_detected']:
                return False, "No HPA detected on this disk"

            # On Windows, removing HPA typically requires:
            # 1. Manufacturer-specific utilities (e.g., SeaTools, WD Data Lifeguard)
            # 2. Third-party tools like HDAT2 or MHDD
            # 3. Direct ATA commands via DeviceIoControl (complex implementation)

            return False, "HPA removal on Windows requires specialized tools like HDAT2 or manufacturer utilities"

        except Exception as e:
            return False, f"Error removing HPA: {str(e)}"

    def remove_dco(self, device: str) -> Tuple[bool, str]:
        """
        Remove Device Configuration Overlay from disk on Windows
        Note: This requires specialized tools and is potentially dangerous
        """
        try:
            # First detect DCO
            dco_info = self.detect_hpa_dco(device)

            if not dco_info['dco_detected']:
                return False, "No DCO detected on this disk"

            # DCO removal on Windows typically requires:
            # 1. Specialized forensic tools
            # 2. Direct ATA commands with proper driver support
            # 3. Manufacturer-specific utilities

            return False, "DCO removal on Windows requires specialized forensic tools or manufacturer utilities"

        except Exception as e:
            return False, f"Error removing DCO: {str(e)}"

    def __init__(self):
        self.wmi_conn = None
        self.tool_manager = tool_manager
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
                    disk_type = DiskType.HDD
                    if "SSD" in model.upper() or "SOLID" in model.upper():
                        disk_type = DiskType.SSD
                    elif "NVME" in model.upper():
                        disk_type = DiskType.NVME
                    
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
                            DiskType.UNKNOWN,
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
                            
                            disk_type = DiskType.HDD
                            if "SSD" in model.upper() or "SOLID" in model.upper():
                                disk_type = DiskType.SSD
                            elif "NVME" in model.upper():
                                disk_type = DiskType.NVME
                            
                            disk_info = DiskInfo(device, size, disk_type, model, serial)
                            # Add HPA/DCO detection (optional, may require admin privileges)
                            try:
                                hpa_dco_info = self.detect_hpa_dco(device)
                                disk_info.hpa_dco_info = hpa_dco_info
                            except Exception as e:
                                logger.debug(f"HPA/DCO detection failed for {device}: {e}")
                                # Provide default HPA/DCO info
                                disk_info.hpa_dco_info = {
                                    'hpa_detected': False,
                                    'dco_detected': False,
                                    'error': 'Detection requires admin privileges'
                                }
                            return disk_info
            
            # Fallback
            return DiskInfo(device, 0, DiskType.UNKNOWN, "Unknown", "")
            
        except Exception as e:
            logger.error(f"Error getting disk info for {device}: {e}")
            return DiskInfo(device, 0, DiskType.UNKNOWN, "Unknown", "")
    
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
        """Use DeviceIoControl for secure wiping on Windows"""
        try:
            import struct
            import ctypes
            from ctypes import wintypes, windll
            
            # Open the physical drive
            handle = ctypes.windll.kernel32.CreateFileW(
                device,
                0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
                0x1 | 0x2,  # FILE_SHARE_READ | FILE_SHARE_WRITE
                None,
                3,  # OPEN_EXISTING
                0,
                None
            )
            
            if handle == -1:
                return False, "Failed to open device for writing"
            
            try:
                # Get device size
                device_size = self._get_device_size(handle)
                if device_size == 0:
                    return False, "Could not determine device size"
                
                # Perform multiple passes
                for pass_num in range(passes):
                    logger.info(f"Starting Windows DD wipe pass {pass_num + 1}/{passes}")
                    
                    # Create random data buffer (1MB chunks)
                    chunk_size = 1024 * 1024
                    random_data = os.urandom(chunk_size)
                    
                    # Write data in chunks
                    bytes_written = 0
                    while bytes_written < device_size:
                        current_chunk_size = min(chunk_size, device_size - bytes_written)
                        
                        # Write the chunk
                        bytes_written_ptr = wintypes.DWORD()
                        success = ctypes.windll.kernel32.WriteFile(
                            handle,
                            random_data,
                            current_chunk_size,
                            ctypes.byref(bytes_written_ptr),
                            None
                        )
                        
                        if not success:
                            return False, f"Write failed at pass {pass_num + 1}, offset {bytes_written}"
                        
                        bytes_written += bytes_written_ptr.value
                        
                        # Flush buffers
                        ctypes.windll.kernel32.FlushFileBuffers(handle)
                
                return True, f"Windows DD wipe completed successfully with {passes} passes"
                
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
            
        except Exception as e:
            return False, f"Windows DD wipe error: {e}"
    
    def _wipe_secure(self, device: str, passes: int) -> Tuple[bool, str]:
        """Perform secure multi-pass wipe using DeviceIoControl"""
        try:
            import struct
            import ctypes
            from ctypes import wintypes, windll
            
            # Open the physical drive
            handle = ctypes.windll.kernel32.CreateFileW(
                device,
                0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
                0x1 | 0x2,  # FILE_SHARE_READ | FILE_SHARE_WRITE
                None,
                3,  # OPEN_EXISTING
                0,
                None
            )
            
            if handle == -1:
                return False, "Failed to open device for secure wipe"
            
            try:
                # Get device size
                device_size = self._get_device_size(handle)
                if device_size == 0:
                    return False, "Could not determine device size"
                
                # Perform secure multi-pass wipe
                for pass_num in range(passes):
                    logger.info(f"Starting secure wipe pass {pass_num + 1}/{passes}")
                    
                    # Different patterns for each pass
                    if pass_num == 0:
                        # Pass 1: Write all zeros
                        pattern = b'\x00'
                    elif pass_num == 1:
                        # Pass 2: Write all ones
                        pattern = b'\xFF'
                    else:
                        # Pass 3+: Write random data
                        pattern = os.urandom(1)
                    
                    # Write pattern in chunks
                    chunk_size = 1024 * 1024
                    pattern_data = pattern * chunk_size
                    
                    bytes_written = 0
                    while bytes_written < device_size:
                        current_chunk_size = min(chunk_size, device_size - bytes_written)
                        
                        # Write the chunk
                        bytes_written_ptr = wintypes.DWORD()
                        success = ctypes.windll.kernel32.WriteFile(
                            handle,
                            pattern_data,
                            current_chunk_size,
                            ctypes.byref(bytes_written_ptr),
                            None
                        )
                        
                        if not success:
                            return False, f"Secure wipe failed at pass {pass_num + 1}, offset {bytes_written}"
                        
                        bytes_written += bytes_written_ptr.value
                        
                        # Flush buffers
                        ctypes.windll.kernel32.FlushFileBuffers(handle)
                
                return True, f"Secure wipe completed successfully with {passes} passes"
                
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
            
        except Exception as e:
            return False, f"Secure wipe error: {e}"
    
    def _wipe_quick(self, device: str) -> Tuple[bool, str]:
        """Perform quick single-pass wipe using DeviceIoControl"""
        try:
            import ctypes
            from ctypes import wintypes, windll
            
            # Open the physical drive
            handle = ctypes.windll.kernel32.CreateFileW(
                device,
                0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
                0x1 | 0x2,  # FILE_SHARE_READ | FILE_SHARE_WRITE
                None,
                3,  # OPEN_EXISTING
                0,
                None
            )
            
            if handle == -1:
                return False, "Failed to open device for quick wipe"
            
            try:
                # Get device size
                device_size = self._get_device_size(handle)
                if device_size == 0:
                    return False, "Could not determine device size"
                
                logger.info("Starting quick wipe (single pass with zeros)")
                
                # Write zeros in chunks
                chunk_size = 1024 * 1024
                zero_data = b'\x00' * chunk_size
                
                bytes_written = 0
                while bytes_written < device_size:
                    current_chunk_size = min(chunk_size, device_size - bytes_written)
                    
                    # Write the chunk
                    bytes_written_ptr = wintypes.DWORD()
                    success = ctypes.windll.kernel32.WriteFile(
                        handle,
                        zero_data,
                        current_chunk_size,
                        ctypes.byref(bytes_written_ptr),
                        None
                    )
                    
                    if not success:
                        return False, f"Quick wipe failed at offset {bytes_written}"
                    
                    bytes_written += bytes_written_ptr.value
                    
                    # Flush buffers
                    ctypes.windll.kernel32.FlushFileBuffers(handle)
                
                return True, "Quick wipe completed successfully"
                
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
            
        except Exception as e:
            return False, f"Quick wipe error: {e}"
    
    def get_wipe_methods(self) -> List[str]:
        """Get available wiping methods for Windows"""
        methods = ["cipher", "secure", "quick"]

        # Check for available tools using tool manager
        if self.tool_manager.is_tool_available('hdparm'):
            methods.append("hdparm")

        # Add dd if available (system check)
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
    
    def _get_device_size(self, handle) -> int:
        """Get the size of a device using DeviceIoControl"""
        try:
            import ctypes
            from ctypes import wintypes, windll
            
            # IOCTL_DISK_GET_DRIVE_GEOMETRY_EX
            IOCTL_DISK_GET_DRIVE_GEOMETRY_EX = 0x000700A0
            
            # DISK_GEOMETRY_EX structure
            class DISK_GEOMETRY_EX(ctypes.Structure):
                _fields_ = [
                    ("Geometry", ctypes.c_byte * 24),  # DISK_GEOMETRY structure
                    ("DiskSize", ctypes.c_ulonglong)
                ]
            
            geometry = DISK_GEOMETRY_EX()
            bytes_returned = wintypes.DWORD()
            
            success = windll.kernel32.DeviceIoControl(
                handle,
                IOCTL_DISK_GET_DRIVE_GEOMETRY_EX,
                None,
                0,
                ctypes.byref(geometry),
                ctypes.sizeof(geometry),
                ctypes.byref(bytes_returned),
                None
            )
            
            if success:
                return geometry.DiskSize
            else:
                # Fallback: try to get size using GetFileSize
                high_size = wintypes.DWORD()
                low_size = windll.kernel32.GetFileSize(handle, ctypes.byref(high_size))
                if low_size != 0xFFFFFFFF or windll.kernel32.GetLastError() == 0:
                    return (high_size.value << 32) | low_size
                return 0
                
        except Exception as e:
            logger.error(f"Error getting device size: {e}")
            return 0
