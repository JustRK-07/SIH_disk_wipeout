"""
Intelligent Disk Analysis System
Advanced disk detection, classification, and safety assessment
"""

import os
import re
import subprocess
import logging
import psutil
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class DiskRole(Enum):
    """Disk role classification"""
    SYSTEM_BOOT = "system_boot"      # Primary system boot disk
    SYSTEM_DATA = "system_data"      # System data partitions
    EXTERNAL_STORAGE = "external"    # External/USB storage
    REMOVABLE_MEDIA = "removable"    # Removable media (USB, SD)
    NETWORK_STORAGE = "network"      # Network attached storage
    OPTICAL_MEDIA = "optical"        # CD/DVD drives
    VIRTUAL_DISK = "virtual"         # Virtual disks/containers
    UNKNOWN = "unknown"

class DiskInterface(Enum):
    """Disk interface types"""
    SATA = "sata"
    NVME = "nvme"
    USB = "usb"
    SCSI = "scsi"
    IDE = "ide"
    SAS = "sas"
    FIBRE_CHANNEL = "fc"
    NETWORK = "network"
    VIRTUAL = "virtual"
    UNKNOWN = "unknown"

class DiskSafetyLevel(Enum):
    """Disk safety levels for wiping"""
    SAFE_TO_WIPE = "safe"           # Safe to wipe (external, removable)
    WARNING_REQUIRED = "warning"    # Requires warning (data disk)
    DANGEROUS = "dangerous"         # Dangerous (system disk)
    CRITICAL = "critical"           # Critical (boot disk)
    UNKNOWN = "unknown"

@dataclass
class DiskAnalysis:
    """Comprehensive disk analysis result"""
    device: str
    role: DiskRole
    interface: DiskInterface
    safety_level: DiskSafetyLevel
    is_readable: bool
    is_writable: bool
    is_mounted: bool
    is_system_disk: bool
    is_boot_disk: bool
    is_removable: bool
    is_external: bool
    mount_points: List[str]
    partitions: List[str]
    filesystems: List[str]
    boot_priority: int  # 0 = not bootable, 1 = primary boot, 2+ = secondary
    confidence_score: float  # 0.0 to 1.0
    warnings: List[str]
    recommendations: List[str]
    metadata: Dict[str, any]

class IntelligentDiskAnalyzer:
    """Advanced disk analysis and classification system"""
    
    def __init__(self):
        self.system_info = self._gather_system_info()
        self.boot_info = self._analyze_boot_configuration()
        self.mount_info = self._analyze_mount_points()
        
    def _gather_system_info(self) -> Dict:
        """Gather comprehensive system information"""
        info = {
            'platform': os.uname().sysname.lower(),
            'architecture': os.uname().machine,
            'boot_device': None,
            'root_device': None,
            'efi_device': None,
            'system_partitions': set(),
            'boot_partitions': set(),
            'removable_devices': set(),
            'usb_devices': set()
        }
        
        try:
            # Get root filesystem
            root_stat = os.stat('/')
            info['root_device'] = self._get_device_from_stat(root_stat)
            
            # Analyze /proc/mounts for system partitions
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        device, mountpoint, fstype = parts[0], parts[1], parts[2]
                        if mountpoint in ['/', '/boot', '/boot/efi', '/var', '/usr', '/home']:
                            info['system_partitions'].add(device)
                        if mountpoint in ['/boot', '/boot/efi']:
                            info['boot_partitions'].add(device)
            
            # Get boot device from /proc/cmdline
            try:
                with open('/proc/cmdline', 'r') as f:
                    cmdline = f.read()
                    boot_match = re.search(r'root=([^\s]+)', cmdline)
                    if boot_match:
                        info['boot_device'] = boot_match.group(1)
            except FileNotFoundError:
                pass
            
            # Detect removable devices
            info['removable_devices'] = self._detect_removable_devices()
            info['usb_devices'] = self._detect_usb_devices()
            
        except Exception as e:
            logger.error(f"Error gathering system info: {e}")
        
        return info
    
    def _get_device_from_stat(self, stat_result) -> Optional[str]:
        """Get device path from stat result"""
        try:
            major = os.major(stat_result.st_dev)
            minor = os.minor(stat_result.st_dev)
            # This is a simplified approach - in practice, you'd need to map major:minor to device
            return f"/dev/block/{major}:{minor}"
        except Exception:
            return None
    
    def _detect_removable_devices(self) -> Set[str]:
        """Detect removable devices using sysfs"""
        removable = set()
        try:
            for device_dir in Path('/sys/block').iterdir():
                if device_dir.is_dir():
                    removable_file = device_dir / 'removable'
                    if removable_file.exists():
                        with open(removable_file, 'r') as f:
                            if f.read().strip() == '1':
                                device_name = device_dir.name
                                removable.add(f"/dev/{device_name}")
        except Exception as e:
            logger.debug(f"Error detecting removable devices: {e}")
        return removable
    
    def _detect_usb_devices(self) -> Set[str]:
        """Detect USB devices using sysfs"""
        usb_devices = set()
        try:
            for device_dir in Path('/sys/block').iterdir():
                if device_dir.is_dir():
                    # Check if device is connected via USB
                    device_path = device_dir / 'device'
                    if device_path.exists():
                        try:
                            # Check if it's a USB device by looking at the device path
                            real_path = device_path.resolve()
                            if 'usb' in str(real_path).lower():
                                device_name = device_dir.name
                                usb_devices.add(f"/dev/{device_name}")
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Error detecting USB devices: {e}")
        return usb_devices
    
    def _analyze_boot_configuration(self) -> Dict:
        """Analyze boot configuration"""
        boot_info = {
            'efi_system': False,
            'legacy_boot': False,
            'boot_order': [],
            'efi_partitions': set(),
            'boot_partitions': set()
        }
        
        try:
            # Check for EFI system
            if os.path.exists('/sys/firmware/efi'):
                boot_info['efi_system'] = True
            
            # Check for EFI partitions
            for partition in psutil.disk_partitions():
                if partition.mountpoint == '/boot/efi':
                    boot_info['efi_partitions'].add(partition.device)
                elif partition.mountpoint == '/boot':
                    boot_info['boot_partitions'].add(partition.device)
            
            # Try to get boot order from efibootmgr
            try:
                result = subprocess.run(['efibootmgr'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('BootOrder:'):
                            boot_info['boot_order'] = line.split(':')[1].strip().split(',')
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
                
        except Exception as e:
            logger.debug(f"Error analyzing boot configuration: {e}")
        
        return boot_info
    
    def _analyze_mount_points(self) -> Dict:
        """Analyze mount points and their purposes"""
        mount_info = {
            'system_mounts': set(),
            'user_mounts': set(),
            'media_mounts': set(),
            'network_mounts': set(),
            'special_mounts': set()
        }
        
        try:
            for partition in psutil.disk_partitions():
                mountpoint = partition.mountpoint
                device = partition.device
                
                if mountpoint.startswith('/media/'):
                    mount_info['media_mounts'].add(device)
                elif mountpoint.startswith('/mnt/'):
                    mount_info['user_mounts'].add(device)
                elif mountpoint.startswith('/home/'):
                    mount_info['user_mounts'].add(device)
                elif mountpoint in ['/', '/boot', '/boot/efi', '/var', '/usr', '/tmp']:
                    mount_info['system_mounts'].add(device)
                elif 'nfs' in partition.fstype or 'cifs' in partition.fstype:
                    mount_info['network_mounts'].add(device)
                else:
                    mount_info['special_mounts'].add(device)
                    
        except Exception as e:
            logger.debug(f"Error analyzing mount points: {e}")
        
        return mount_info
    
    def analyze_disk(self, device: str) -> DiskAnalysis:
        """Perform comprehensive disk analysis"""
        logger.info(f"Analyzing disk: {device}")
        
        # Initialize analysis result
        analysis = DiskAnalysis(
            device=device,
            role=DiskRole.UNKNOWN,
            interface=DiskInterface.UNKNOWN,
            safety_level=DiskSafetyLevel.UNKNOWN,
            is_readable=False,
            is_writable=False,
            is_mounted=False,
            is_system_disk=False,
            is_boot_disk=False,
            is_removable=False,
            is_external=False,
            mount_points=[],
            partitions=[],
            filesystems=[],
            boot_priority=0,
            confidence_score=0.0,
            warnings=[],
            recommendations=[],
            metadata={}
        )
        
        try:
            # Basic device checks
            analysis.is_readable = self._check_readability(device)
            analysis.is_mounted = self._check_mount_status(device)
            analysis.is_removable = device in self.system_info['removable_devices']
            analysis.is_external = device in self.system_info['usb_devices']
            
            # Determine interface type
            analysis.interface = self._determine_interface(device)
            
            # Analyze partitions and mount points
            analysis.partitions = self._get_partitions(device)
            analysis.mount_points = self._get_mount_points(device)
            analysis.filesystems = self._get_filesystems(device)
            
            # Determine if it's a system disk (must be done before role determination)
            analysis.is_system_disk = self._is_system_disk(device, analysis)
            
            # Determine if it's a boot disk (must be done before role determination)
            analysis.is_boot_disk = self._is_boot_disk(device, analysis)
            
            # Determine disk role (after system and boot disk determination)
            analysis.role = self._determine_role(device, analysis)
            
            # Determine boot priority
            analysis.boot_priority = self._get_boot_priority(device, analysis)
            
            # Determine writability
            analysis.is_writable = self._determine_writability(device, analysis)
            
            # Determine safety level
            analysis.safety_level = self._determine_safety_level(analysis)
            
            # Generate warnings and recommendations
            analysis.warnings = self._generate_warnings(analysis)
            analysis.recommendations = self._generate_recommendations(analysis)
            
            # Calculate confidence score
            analysis.confidence_score = self._calculate_confidence(analysis)
            
            # Gather additional metadata
            analysis.metadata = self._gather_metadata(device, analysis)
            
        except Exception as e:
            logger.error(f"Error analyzing disk {device}: {e}")
            analysis.warnings.append(f"Analysis error: {e}")
            analysis.confidence_score = 0.0
        
        return analysis
    
    def _check_readability(self, device: str) -> bool:
        """Check if device is readable"""
        try:
            if not os.path.exists(device):
                return False
            
            # Try to read device info
            with open(device, 'rb') as f:
                f.read(1)
            return True
        except (PermissionError, OSError):
            return False
    
    def _check_mount_status(self, device: str) -> bool:
        """Check if device or its partitions are mounted"""
        try:
            for partition in psutil.disk_partitions():
                if partition.device.startswith(device):
                    return True
            return False
        except Exception:
            return False
    
    def _determine_interface(self, device: str) -> DiskInterface:
        """Determine disk interface type"""
        device_name = os.path.basename(device).lower()
        
        if 'nvme' in device_name:
            return DiskInterface.NVME
        elif device_name.startswith('sd') or device_name.startswith('hd'):
            # Check if it's USB
            if device in self.system_info['usb_devices']:
                return DiskInterface.USB
            else:
                return DiskInterface.SATA
        elif device_name.startswith('scsi'):
            return DiskInterface.SCSI
        elif device_name.startswith('ide'):
            return DiskInterface.IDE
        else:
            return DiskInterface.UNKNOWN
    
    def _get_partitions(self, device: str) -> List[str]:
        """Get list of partitions for the device"""
        partitions = []
        try:
            device_name = os.path.basename(device)
            for partition in psutil.disk_partitions():
                if partition.device.startswith(device):
                    partitions.append(partition.device)
        except Exception:
            pass
        return partitions
    
    def _get_mount_points(self, device: str) -> List[str]:
        """Get mount points for device partitions"""
        mount_points = []
        try:
            for partition in psutil.disk_partitions():
                if partition.device.startswith(device):
                    mount_points.append(partition.mountpoint)
        except Exception:
            pass
        return mount_points
    
    def _get_filesystems(self, device: str) -> List[str]:
        """Get filesystem types for device partitions"""
        filesystems = []
        try:
            for partition in psutil.disk_partitions():
                if partition.device.startswith(device):
                    filesystems.append(partition.fstype)
        except Exception:
            pass
        return filesystems
    
    def _determine_role(self, device: str, analysis: DiskAnalysis) -> DiskRole:
        """Determine disk role based on comprehensive analysis"""
        # Check if it's a system boot disk
        if analysis.is_boot_disk and analysis.is_system_disk:
            return DiskRole.SYSTEM_BOOT
        
        # Check if it's system data
        if analysis.is_system_disk and not analysis.is_boot_disk:
            return DiskRole.SYSTEM_DATA
        
        # Check if it's external storage
        if analysis.is_external or analysis.is_removable:
            if any(mp.startswith('/media/') for mp in analysis.mount_points):
                return DiskRole.REMOVABLE_MEDIA
            else:
                return DiskRole.EXTERNAL_STORAGE
        
        # Check for network storage
        if any('nfs' in fs or 'cifs' in fs for fs in analysis.filesystems):
            return DiskRole.NETWORK_STORAGE
        
        # Check for optical media
        if 'cdrom' in device.lower() or 'dvd' in device.lower():
            return DiskRole.OPTICAL_MEDIA
        
        # Check for virtual disks
        if device.startswith('/dev/loop') or device.startswith('/dev/dm-'):
            return DiskRole.VIRTUAL_DISK
        
        return DiskRole.UNKNOWN
    
    def _is_system_disk(self, device: str, analysis: DiskAnalysis) -> bool:
        """Determine if disk is a system disk"""
        # Check if any partitions are mounted at system locations
        system_mounts = ['/', '/boot', '/boot/efi', '/var', '/usr', '/home']
        for mount_point in analysis.mount_points:
            if mount_point in system_mounts:
                return True
        
        # Check if it's the root device
        if device == self.system_info.get('root_device'):
            return True
        
        # Check if it contains system partitions
        for partition in analysis.partitions:
            if partition in self.system_info['system_partitions']:
                return True
        
        return False
    
    def _is_boot_disk(self, device: str, analysis: DiskAnalysis) -> bool:
        """Determine if disk is a boot disk"""
        # Check if it's the boot device
        if device == self.system_info.get('boot_device'):
            return True
        
        # Check if it contains boot partitions
        for partition in analysis.partitions:
            if partition in self.system_info['boot_partitions']:
                return True
        
        # Check if it has EFI or boot partitions mounted
        boot_mounts = ['/boot', '/boot/efi']
        for mount_point in analysis.mount_points:
            if mount_point in boot_mounts:
                return True
        
        return False
    
    def _get_boot_priority(self, device: str, analysis: DiskAnalysis) -> int:
        """Get boot priority (0 = not bootable, 1 = primary, 2+ = secondary)"""
        if not analysis.is_boot_disk:
            return 0
        
        # Primary boot disk
        if device == self.system_info.get('boot_device'):
            return 1
        
        # Secondary boot disk
        if analysis.is_boot_disk:
            return 2
        
        return 0
    
    def _determine_writability(self, device: str, analysis: DiskAnalysis) -> bool:
        """Determine if disk is writable with proper context"""
        # System disks are not writable for safety
        if analysis.is_system_disk:
            return False
        
        # Mounted disks are not writable (need to unmount first)
        if analysis.is_mounted:
            return False
        
        # Check if device exists and is accessible
        if not analysis.is_readable:
            # For raw devices, assume writable with proper permissions
            if os.path.exists(device):
                return True
            return False
        
        # If readable and not system/mounted, assume writable
        return True
    
    def _determine_safety_level(self, analysis: DiskAnalysis) -> DiskSafetyLevel:
        """Determine safety level for wiping"""
        # Critical: Boot disk
        if analysis.is_boot_disk and analysis.boot_priority == 1:
            return DiskSafetyLevel.CRITICAL
        
        # Dangerous: System disk
        if analysis.is_system_disk:
            return DiskSafetyLevel.DANGEROUS
        
        # Warning: Data disk with important data
        if analysis.role in [DiskRole.SYSTEM_DATA, DiskRole.EXTERNAL_STORAGE]:
            return DiskSafetyLevel.WARNING_REQUIRED
        
        # Safe: Removable media, external storage
        if analysis.role in [DiskRole.REMOVABLE_MEDIA, DiskRole.EXTERNAL_STORAGE]:
            return DiskSafetyLevel.SAFE_TO_WIPE
        
        return DiskSafetyLevel.UNKNOWN
    
    def _generate_warnings(self, analysis: DiskAnalysis) -> List[str]:
        """Generate appropriate warnings"""
        warnings = []
        
        if analysis.safety_level == DiskSafetyLevel.CRITICAL:
            warnings.append("CRITICAL: This is the primary boot disk!")
            warnings.append("Wiping this disk will make the system unbootable!")
        
        elif analysis.safety_level == DiskSafetyLevel.DANGEROUS:
            warnings.append("DANGEROUS: This is a system disk!")
            warnings.append("Wiping this disk may damage the operating system!")
        
        elif analysis.safety_level == DiskSafetyLevel.WARNING_REQUIRED:
            warnings.append("WARNING: This disk may contain important data!")
            warnings.append("Ensure you have backups before proceeding!")
        
        if analysis.is_mounted:
            warnings.append("Disk is currently mounted - unmount before wiping!")
        
        if not analysis.is_readable:
            warnings.append("Cannot read disk - may require elevated permissions!")
        
        if analysis.interface == DiskInterface.USB:
            warnings.append("USB device detected - ensure it's not the boot device!")
        
        return warnings
    
    def _generate_recommendations(self, analysis: DiskAnalysis) -> List[str]:
        """Generate recommendations for safe wiping"""
        recommendations = []
        
        if analysis.safety_level == DiskSafetyLevel.SAFE_TO_WIPE:
            recommendations.append("This disk appears safe to wipe")
            recommendations.append("Consider using 'quick' method for faster wiping")
        
        elif analysis.safety_level == DiskSafetyLevel.WARNING_REQUIRED:
            recommendations.append("Verify this is the correct disk before wiping")
            recommendations.append("Consider using 'secure' method for sensitive data")
        
        if analysis.is_mounted:
            recommendations.append("Unmount all partitions before wiping")
            recommendations.append("Use 'umount' command to unmount partitions")
        
        if analysis.interface == DiskInterface.NVME:
            recommendations.append("NVMe detected - consider using 'nvme' method for optimal performance")
        
        elif analysis.interface == DiskInterface.USB:
            recommendations.append("USB device - consider using 'dd' method for reliability")
        
        if analysis.is_removable:
            recommendations.append("Removable device - ensure it's not needed for system operation")
        
        return recommendations
    
    def _calculate_confidence(self, analysis: DiskAnalysis) -> float:
        """Calculate confidence score for the analysis"""
        score = 0.0
        
        # Base score for successful analysis
        if analysis.is_readable:
            score += 0.3
        
        # Role determination confidence
        if analysis.role != DiskRole.UNKNOWN:
            score += 0.2
        
        # Interface determination confidence
        if analysis.interface != DiskInterface.UNKNOWN:
            score += 0.1
        
        # Safety level determination confidence
        if analysis.safety_level != DiskSafetyLevel.UNKNOWN:
            score += 0.2
        
        # System information availability
        if self.system_info.get('root_device'):
            score += 0.1
        
        if self.boot_info.get('efi_system') is not None:
            score += 0.1
        
        return min(score, 1.0)
    
    def _gather_metadata(self, device: str, analysis: DiskAnalysis) -> Dict:
        """Gather additional metadata"""
        metadata = {
            'device_name': os.path.basename(device),
            'analysis_timestamp': str(psutil.boot_time()),
            'system_platform': self.system_info['platform'],
            'efi_system': self.boot_info['efi_system'],
            'removable_detected': analysis.is_removable,
            'usb_detected': analysis.is_external,
            'partition_count': len(analysis.partitions),
            'mount_count': len(analysis.mount_points)
        }
        
        return metadata
