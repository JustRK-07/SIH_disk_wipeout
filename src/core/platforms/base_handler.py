"""
Base class for platform-specific disk handlers
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict
from ..models import DiskInfo

class BaseDiskHandler(ABC):
    """Abstract base class for platform-specific disk handlers"""
    
    @abstractmethod
    def get_available_disks(self) -> List[DiskInfo]:
        """Get list of available disks for wiping"""
        pass
    
    @abstractmethod
    def get_disk_info(self, device: str) -> DiskInfo:
        """Get detailed information about a specific disk"""
        pass
    
    @abstractmethod
    def wipe_disk(self, device: str, method: str, passes: int) -> Tuple[bool, str]:
        """Wipe a disk using specified method"""
        pass
    
    @abstractmethod
    def get_wipe_methods(self) -> List[str]:
        """Get available wiping methods for current platform"""
        pass
    
    @abstractmethod
    def is_disk_writable(self, device: str) -> bool:
        """Check if a disk is writable"""
        pass
    
    @abstractmethod
    def get_system_disks(self) -> List[str]:
        """Get list of system disks that should not be wiped"""
        pass
    
    def detect_hpa_dco(self, device: str) -> Dict:
        """Detect Host Protected Area (HPA) and Device Configuration Overlay (DCO)"""
        return {
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
            'error': 'HPA/DCO detection not implemented for this platform'
        }
    
    def remove_hpa(self, device: str) -> Tuple[bool, str]:
        """Remove Host Protected Area from disk"""
        return False, "HPA removal not implemented for this platform"
    
    def remove_dco(self, device: str) -> Tuple[bool, str]:
        """Remove Device Configuration Overlay from disk"""
        return False, "DCO removal not implemented for this platform"
