"""
Base class for platform-specific disk handlers
"""

from abc import ABC, abstractmethod
from typing import List, Tuple
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
