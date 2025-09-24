"""
Core disk management functionality
Handles cross-platform disk detection and wiping operations
"""

import os
import platform
import logging
import psutil
import json
import fnmatch
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod
from pathlib import Path

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
        self.safety_config = self._load_safety_config()
        
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
            # CRITICAL SAFETY CHECK - Block protected devices
            if self.is_device_protected(device):
                error_msg = f"CRITICAL SAFETY ERROR: Device {device} is PROTECTED and cannot be wiped!"
                logger.error(error_msg)
                return False, error_msg
            
            # Additional safety check - ensure device is writable
            if not self.is_disk_writable(device):
                error_msg = f"Device {device} is not writable or is protected"
                logger.error(error_msg)
                return False, error_msg
            
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
        """Check if a disk is writable (not mounted, system disk, or protected)"""
        # First check if device is protected
        if self.is_device_protected(device):
            return False
        
        # Then check platform-specific writability
        return self.handler.is_disk_writable(device)
    
    def _load_safety_config(self) -> Dict:
        """Load safety configuration from file"""
        config_path = Path(__file__).parent.parent.parent / "safety_config.json"
        default_config = {
            "protected_devices": [],
            "protected_patterns": [],
            "additional_safety_checks": True,
            "require_multiple_confirmations": True,
            "block_system_disks": True,
            "log_all_attempts": True,
            "emergency_override": False
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded safety configuration from {config_path}")
                    return {**default_config, **config}
            else:
                logger.info("No safety config found, using defaults")
                return default_config
        except Exception as e:
            logger.error(f"Error loading safety config: {e}")
            return default_config
    
    def get_system_disks(self) -> List[str]:
        """Get list of system disks that should not be wiped"""
        system_disks = self.handler.get_system_disks()
        
        # Add configured protected devices
        if self.safety_config.get("protected_devices"):
            system_disks.extend(self.safety_config["protected_devices"])
        
        # Add devices matching protected patterns
        if self.safety_config.get("protected_patterns"):
            all_disks = self.get_available_disks()
            for disk in all_disks:
                for pattern in self.safety_config["protected_patterns"]:
                    if fnmatch.fnmatch(disk.device, pattern):
                        if disk.device not in system_disks:
                            system_disks.append(disk.device)
        
        return list(set(system_disks))  # Remove duplicates
    
    def is_device_protected(self, device: str) -> bool:
        """Check if a device is protected from wiping"""
        system_disks = self.get_system_disks()
        return device in system_disks

    def detect_hpa_dco(self, device: str) -> Dict:
        """
        Detect Host Protected Area (HPA) and Device Configuration Overlay (DCO)

        Returns:
            Dict containing HPA/DCO detection results
        """
        try:
            return self.handler.detect_hpa_dco(device)
        except Exception as e:
            logger.error(f"Error detecting HPA/DCO for {device}: {e}")
            return {
                'hpa_detected': False,
                'dco_detected': False,
                'error': str(e)
            }

    def remove_hpa(self, device: str) -> Tuple[bool, str]:
        """
        Remove Host Protected Area from disk
        WARNING: This exposes hidden disk areas that may contain sensitive data

        Args:
            device: Disk device path

        Returns:
            Tuple of (success, message)
        """
        try:
            # Safety check
            if self.is_device_protected(device):
                return False, f"Cannot remove HPA from protected device {device}"

            logger.warning(f"Attempting to remove HPA from {device}")
            return self.handler.remove_hpa(device)
        except AttributeError:
            return False, "HPA removal not implemented for this platform"
        except Exception as e:
            error_msg = f"Error removing HPA from {device}: {e}"
            logger.error(error_msg)
            return False, error_msg

    def remove_dco(self, device: str) -> Tuple[bool, str]:
        """
        Remove Device Configuration Overlay from disk
        WARNING: This is dangerous and can damage the disk

        Args:
            device: Disk device path

        Returns:
            Tuple of (success, message)
        """
        try:
            # Safety check
            if self.is_device_protected(device):
                return False, f"Cannot remove DCO from protected device {device}"

            logger.warning(f"Attempting to remove DCO from {device} - THIS IS DANGEROUS")
            return self.handler.remove_dco(device)
        except AttributeError:
            return False, "DCO removal not implemented for this platform"
        except Exception as e:
            error_msg = f"Error removing DCO from {device}: {e}"
            logger.error(error_msg)
            return False, error_msg

    def wipe_with_hpa_dco_removal(self, device: str, method: str = "secure",
                                  passes: int = 3, verify: bool = True,
                                  remove_hpa: bool = False, remove_dco: bool = False) -> Tuple[bool, str]:
        """
        Wipe disk with optional HPA/DCO removal

        Args:
            device: Disk device path
            method: Wiping method
            passes: Number of passes for secure wipe
            verify: Whether to verify the wipe
            remove_hpa: Whether to remove HPA before wiping
            remove_dco: Whether to remove DCO before wiping

        Returns:
            Tuple of (success, message)
        """
        messages = []

        # Detect HPA/DCO
        hpa_dco_info = self.detect_hpa_dco(device)

        if hpa_dco_info.get('hpa_detected'):
            hidden_gb = (hpa_dco_info.get('hpa_sectors', 0) * 512) // (1024**3)
            messages.append(f"HPA detected: {hidden_gb}GB hidden")

            if remove_hpa:
                success, msg = self.remove_hpa(device)
                if success:
                    messages.append(f"HPA removed: {msg}")
                else:
                    messages.append(f"Failed to remove HPA: {msg}")
                    if not self.safety_config.get('emergency_override'):
                        return False, "\n".join(messages)

        if hpa_dco_info.get('dco_detected'):
            dco_gb = (hpa_dco_info.get('dco_sectors', 0) * 512) // (1024**3)
            messages.append(f"DCO detected: {dco_gb}GB hidden")

            if remove_dco:
                success, msg = self.remove_dco(device)
                if success:
                    messages.append(f"DCO removed: {msg}")
                else:
                    messages.append(f"Failed to remove DCO: {msg}")
                    if not self.safety_config.get('emergency_override'):
                        return False, "\n".join(messages)

        # Perform the wipe
        success, wipe_msg = self.wipe_disk(device, method, passes, verify)
        messages.append(wipe_msg)

        return success, "\n".join(messages)
