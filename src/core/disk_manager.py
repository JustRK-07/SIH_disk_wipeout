"""
Core disk management functionality
Handles cross-platform disk detection and wiping operations
"""

import os
import platform
import logging
import psutil
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod

from .models import DiskInfo
from .platforms.windows_disk_handler import WindowsDiskHandler
from .platforms.linux_disk_handler import LinuxDiskHandler
from .platforms.android_disk_handler import AndroidDiskHandler
from .verification import VerificationManager

logger = logging.getLogger(__name__)

class DiskManager:
    """Main disk management class"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.handler = self._get_platform_handler()
        self.verification_manager = VerificationManager()
        
    def _get_platform_handler(self):
        """Get the appropriate platform handler"""
        if self.system == "windows":
            return WindowsDiskHandler()
        elif self.system == "linux":
            return LinuxDiskHandler()
        elif self.system == "android":
            return AndroidDiskHandler()
        else:
            raise NotImplementedError(f"Platform {self.system} not supported")
    
    def get_available_disks(self) -> List[DiskInfo]:
        """Get list of available disks for wiping"""
        try:
            return self.handler.get_available_disks()
        except Exception as e:
            logger.error(f"Error getting available disks: {e}")
            return []
    
    def get_disk_info(self, device: str) -> Optional[DiskInfo]:
        """Get detailed information about a specific disk"""
        try:
            return self.handler.get_disk_info(device)
        except Exception as e:
            logger.error(f"Error getting disk info for {device}: {e}")
            return None
    
    def wipe_disk(self, device: str, method: str = "secure", 
                  passes: int = 3, verify: bool = True) -> Tuple[bool, str]:
        """
        Wipe a disk using specified method
        
        Args:
            device: Disk device path
            method: Wiping method ('secure', 'quick', 'cipher', 'dd', 'nvme')
            passes: Number of passes for secure wipe
            verify: Whether to verify the wipe
            
        Returns:
            Tuple of (success, message)
        """
        try:
            logger.info(f"Starting wipe of {device} using {method} method")
            
            # Perform the wipe
            success, message = self.handler.wipe_disk(device, method, passes)
            
            if success and verify:
                # Verify the wipe
                verification_success, verification_message = self.verification_manager.verify_wipe(device)
                if not verification_success:
                    logger.warning(f"Wipe verification failed: {verification_message}")
                    message += f" (Warning: {verification_message})"
            
            return success, message
            
        except Exception as e:
            error_msg = f"Error wiping disk {device}: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_wipe_methods(self) -> List[str]:
        """Get available wiping methods for current platform"""
        return self.handler.get_wipe_methods()
    
    def is_disk_writable(self, device: str) -> bool:
        """Check if a disk is writable (not mounted or system disk)"""
        return self.handler.is_disk_writable(device)
    
    def get_system_disks(self) -> List[str]:
        """Get list of system disks that should not be wiped"""
        return self.handler.get_system_disks()
