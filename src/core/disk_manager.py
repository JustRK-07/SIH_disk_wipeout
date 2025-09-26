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
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod
from pathlib import Path

from .models import DiskInfo, DiskType
from .platforms.windows_disk_handler import WindowsDiskHandler
from .platforms.linux_disk_handler import LinuxDiskHandler
from .platforms.android_disk_handler import AndroidDiskHandler
from .verification import VerificationManager
from .intelligent_disk_analyzer import IntelligentDiskAnalyzer, DiskRole, DiskInterface, DiskSafetyLevel
from .sudo_manager import SudoManager
from .certificate_generator import generate_wipe_certificate

logger = logging.getLogger(__name__)

class DiskManager:
    """Main disk management class"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.handler = self._get_platform_handler()
        self.verification_manager = VerificationManager()
        self.safety_config = self._load_safety_config()
        self.intelligent_analyzer = IntelligentDiskAnalyzer()
        self.sudo_manager = SudoManager()
        
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
    
    def get_intelligent_disk_analysis(self, device: str):
        """Get comprehensive intelligent disk analysis"""
        try:
            return self.intelligent_analyzer.analyze_disk(device)
        except Exception as e:
            logger.error(f"Error getting intelligent disk analysis for {device}: {e}")
            return None
    
    def wipe_disk_with_sudo(self, device: str, method: str = "dd", 
                           passes: int = 1, verify: bool = True, 
                           generate_certificate: bool = True) -> Tuple[bool, str]:
        """
        Wipe a disk with automatic sudo permission handling
        
        Args:
            device: Disk device path
            method: Wiping method ('dd', 'quick', 'secure')
            passes: Number of passes for secure wipe
            verify: Whether to verify the wipe
            generate_certificate: Whether to generate NIST-compliant certificate
            
        Returns:
            Tuple of (success, message)
        """
        start_time = datetime.now()
        bytes_written = 0
        verification_result = None
        
        try:
            # CRITICAL SAFETY CHECK - Block protected devices
            if self.is_device_protected(device):
                error_msg = f"CRITICAL SAFETY ERROR: Device {device} is PROTECTED and cannot be wiped!"
                logger.error(error_msg)
                return False, error_msg
            
            # For removable devices, force unmount first
            disk_info = self.get_disk_info(device)
            if disk_info and disk_info.is_removable:
                logger.info(f"USB device detected, force unmounting all partitions...")
                
                # Find all partitions
                import glob
                partitions = glob.glob(f"{device}*")
                for partition in partitions:
                    if partition != device:  # Don't unmount the base device
                        self.sudo_manager.run_with_sudo(['umount', '-f', partition], f"force unmount {partition}")
                
                # Also unmount the base device if mounted
                self.sudo_manager.run_with_sudo(['umount', '-f', device], f"force unmount {device}")
                
                # Use USB-optimized method for quick wipe
                if method == "quick":
                    logger.info("Using USB-optimized quick wipe method")
                    # Quick wipe should only clear partition table
                    success, stdout, stderr = self.sudo_manager.run_with_sudo(
                        ['dd', 'if=/dev/zero', f'of={device}', 'bs=1M', 'count=10'],
                        "USB quick wipe"
                    )
                    if success:
                        bytes_written = 10 * 1024 * 1024  # 10MB
                        end_time = datetime.now()
                        
                        # Generate certificate if requested
                        if generate_certificate:
                            try:
                                certificates = generate_wipe_certificate(
                                    device_path=device,
                                    method=method,
                                    passes=passes,
                                    start_time=start_time,
                                    end_time=end_time,
                                    success=True,
                                    bytes_written=bytes_written,
                                    verification_result=verification_result
                                )
                                logger.info(f"Generated certificates: {certificates}")
                            except Exception as e:
                                logger.warning(f"Certificate generation failed: {e}")
                        
                        return True, "USB device quick wiped (partition table cleared)"
                    else:
                        end_time = datetime.now()
                        
                        # Generate certificate for failed operation
                        if generate_certificate:
                            try:
                                certificates = generate_wipe_certificate(
                                    device_path=device,
                                    method=method,
                                    passes=passes,
                                    start_time=start_time,
                                    end_time=end_time,
                                    success=False,
                                    bytes_written=0,
                                    verification_result=verification_result
                                )
                                logger.info(f"Generated certificates for failed operation: {certificates}")
                            except Exception as e:
                                logger.warning(f"Certificate generation failed: {e}")
                        
                        return False, f"USB quick wipe failed: {stderr}"
            
            # Check if device exists and is accessible
            access_ok, access_msg = self.sudo_manager.check_disk_access(device)
            if not access_ok:
                return False, f"Cannot access device {device}: {access_msg}"
            
            logger.info(f"Starting sudo-enabled wipe of {device} using {method} method with {passes} passes")
            
            # Use sudo manager for seamless wiping
            success, message = self.sudo_manager.wipe_disk_with_sudo(device, method, passes)
            
            end_time = datetime.now()
            
            # Estimate bytes written based on device size
            if success and disk_info:
                bytes_written = disk_info.size
            
            # Perform verification if requested
            if success and verify:
                logger.info("Starting wipe verification...")
                verification_success, verification_message = self.verification_manager.verify_wipe(device)
                verification_result = {
                    'method': 'Sampling',
                    'passed': verification_success,
                    'details': verification_message
                }
                if not verification_success:
                    logger.warning(f"Wipe verification failed: {verification_message}")
                    message += f" (Warning: {verification_message})"
                else:
                    logger.info("Wipe verification successful")
                    message += " (Verified: Wipe successful)"
            
            # Generate certificate if requested
            if generate_certificate:
                try:
                    certificates = generate_wipe_certificate(
                        device_path=device,
                        method=method,
                        passes=passes,
                        start_time=start_time,
                        end_time=end_time,
                        success=success,
                        bytes_written=bytes_written,
                        verification_result=verification_result
                    )
                    logger.info(f"Generated certificates: {certificates}")
                    message += f" | Certificates: {list(certificates.keys())}"
                except Exception as e:
                    logger.warning(f"Certificate generation failed: {e}")
            
            if success:
                logger.info(f"Wipe completed successfully: {message}")
            else:
                logger.error(f"Wipe failed: {message}")
            
            return success, message
            
        except Exception as e:
            end_time = datetime.now()
            error_msg = f"Error during sudo-enabled wipe operation: {str(e)}"
            logger.error(error_msg)
            
            # Generate certificate for failed operation
            if generate_certificate:
                try:
                    certificates = generate_wipe_certificate(
                        device_path=device,
                        method=method,
                        passes=passes,
                        start_time=start_time,
                        end_time=end_time,
                        success=False,
                        bytes_written=0,
                        verification_result=verification_result
                    )
                    logger.info(f"Generated certificates for failed operation: {certificates}")
                except Exception as cert_e:
                    logger.warning(f"Certificate generation failed: {cert_e}")
            
            return False, error_msg
    
    def wipe_disk(self, device: str, method: str = "secure", 
                  passes: int = 3, verify: bool = True) -> Tuple[bool, str]:
        """
        Wipe a disk using specified method with enhanced error recovery
        
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
            
            # Check device access using sudo manager
            access_ok, access_msg = self.sudo_manager.check_disk_access(device)
            if not access_ok:
                error_msg = f"Device Access Error: {access_msg}"
                logger.error(error_msg)
                return False, error_msg
            
            # Validate wipe operation with warnings
            is_valid, warnings = self.validate_wipe_operation(device, method, passes)
            if not is_valid:
                error_msg = f"Validation failed: {'; '.join(warnings)}"
                logger.error(error_msg)
                return False, error_msg
            
            # Log warnings if any
            if warnings:
                for warning in warnings:
                    logger.warning(f"Wipe warning: {warning}")
            
            logger.info(f"Starting wipe of {device} using {method} method with {passes} passes")
            
            # Perform the wipe with retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    success, message = self.handler.wipe_disk(device, method, passes)
                    
                    if success:
                        logger.info(f"Wipe completed successfully on attempt {attempt + 1}")
                        break
                    else:
                        logger.warning(f"Wipe attempt {attempt + 1} failed: {message}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying wipe operation (attempt {attempt + 2}/{max_retries})")
                            time.sleep(2)  # Wait before retry
                        else:
                            return False, f"Wipe failed after {max_retries} attempts: {message}"
                            
                except Exception as e:
                    logger.error(f"Wipe attempt {attempt + 1} failed with exception: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying wipe operation (attempt {attempt + 2}/{max_retries})")
                        time.sleep(2)  # Wait before retry
                    else:
                        return False, f"Wipe failed after {max_retries} attempts: {e}"
            
            # Verify the wipe if requested
            if success and verify:
                logger.info("Starting wipe verification...")
                verification_success, verification_message = self.verification_manager.verify_wipe(device)
                if not verification_success:
                    logger.warning(f"Wipe verification failed: {verification_message}")
                    message += f" (Warning: {verification_message})"
                else:
                    logger.info("Wipe verification successful")
                    message += " (Verified: Wipe successful)"
            
            return success, message
            
        except Exception as e:
            error_msg = f"Unexpected error wiping disk {device}: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_wipe_methods(self) -> List[str]:
        """Get available wiping methods for current platform"""
        return self.handler.get_wipe_methods()

    def auto_detect_best_wipe_method(self, device: str) -> Tuple[str, str]:
        """
        Auto-detect the best wipeout method for a given disk

        Returns:
            Tuple of (method, reason)
        """
        try:
            # Get disk information
            disk_info = self.get_disk_info(device)
            if not disk_info:
                return "dd", "Default method - unable to detect disk type"

            # Get intelligent analysis
            analysis = self.intelligent_analyzer.analyze_disk(device)

            # Get available methods
            available_methods = self.get_wipe_methods()

            # Decision logic for best method
            # 1. NVMe drives: Use nvme-cli if available
            if disk_info.type == DiskType.NVME:
                if "nvme" in available_methods:
                    return "nvme", "NVMe drive detected - using native NVMe secure format for optimal performance"
                else:
                    return "blkdiscard" if "blkdiscard" in available_methods else "dd", "NVMe drive - using TRIM discard or fallback method"

            # 2. SSDs: Use blkdiscard (TRIM) if available
            elif disk_info.type == DiskType.SSD or disk_info.is_ssd:
                if "blkdiscard" in available_methods:
                    return "blkdiscard", "SSD detected - using TRIM for fast and SSD-friendly wiping"
                elif "hdparm" in available_methods:
                    return "hdparm", "SSD detected - using ATA secure erase"
                else:
                    return "quick", "SSD detected - using quick wipe to minimize wear"

            # 3. USB/Removable drives: Use dd for reliability
            elif disk_info.type == DiskType.REMOVABLE or disk_info.is_removable:
                if analysis.interface == DiskInterface.USB:
                    return "dd", "USB device detected - using dd for maximum compatibility"
                else:
                    return "quick", "Removable device - using quick wipe for speed"

            # 4. HDDs: Use hdparm if available, otherwise secure multi-pass
            elif disk_info.type == DiskType.HDD:
                if "hdparm" in available_methods:
                    return "hdparm", "HDD detected - using ATA secure erase for thorough wiping"
                else:
                    return "secure", "HDD detected - using multi-pass secure wipe"

            # 5. Unknown or special cases
            else:
                # Check if it's a virtual disk
                if analysis.role == DiskRole.VIRTUAL_DISK:
                    return "quick", "Virtual disk detected - using quick wipe"
                # Default to dd for unknown types
                else:
                    return "dd", "Unknown disk type - using dd for compatibility"

        except Exception as e:
            logger.error(f"Error auto-detecting best wipe method for {device}: {e}")
            return "dd", f"Error in detection: {e} - using default dd method"
    
    def is_disk_writable(self, device: str) -> bool:
        """Check if a disk is writable (not mounted, system disk, or protected)"""
        # First check if device is protected
        if self.is_device_protected(device):
            return False
        
        # Then check platform-specific writability
        return self.handler.is_disk_writable(device)
    
    def get_disk_status_safe(self, device: str) -> Dict[str, any]:
        """Get intelligent disk status information using advanced analysis"""
        try:
            # Use intelligent analyzer for comprehensive analysis
            analysis = self.intelligent_analyzer.analyze_disk(device)
            
            # Map analysis results to status format
            status_map = {
                DiskSafetyLevel.CRITICAL: 'CRITICAL',
                DiskSafetyLevel.DANGEROUS: 'PROTECTED', 
                DiskSafetyLevel.WARNING_REQUIRED: 'WARNING',
                DiskSafetyLevel.SAFE_TO_WIPE: 'AVAILABLE',
                DiskSafetyLevel.UNKNOWN: 'UNKNOWN'
            }
            
            return {
                'is_protected': analysis.safety_level in [DiskSafetyLevel.CRITICAL, DiskSafetyLevel.DANGEROUS],
                'is_mounted': analysis.is_mounted,
                'is_writable': analysis.is_writable,
                'is_system_disk': analysis.is_system_disk,
                'is_boot_disk': analysis.is_boot_disk,
                'is_removable': analysis.is_removable,
                'is_external': analysis.is_external,
                'role': analysis.role.value,
                'interface': analysis.interface.value,
                'safety_level': analysis.safety_level.value,
                'boot_priority': analysis.boot_priority,
                'confidence_score': analysis.confidence_score,
                'warnings': analysis.warnings,
                'recommendations': analysis.recommendations,
                'status': status_map.get(analysis.safety_level, 'UNKNOWN')
            }
        except Exception as e:
            logger.error(f"Error getting intelligent disk status for {device}: {e}")
            # Fallback to basic analysis
            return self._get_basic_disk_status(device)
    
    def _get_basic_disk_status(self, device: str) -> Dict[str, any]:
        """Fallback basic disk status when intelligent analysis fails"""
        try:
            is_protected = self.is_device_protected(device)
            is_mounted = self._is_disk_mounted(device)
            
            # Basic writability check
            is_writable = False
            if not is_protected and not is_mounted and os.path.exists(device):
                try:
                    with open(device, 'rb') as f:
                        f.read(1)
                    is_writable = True
                except PermissionError:
                    is_writable = True  # Assume writable with proper permissions
                except OSError:
                    is_writable = False
            
            return {
                'is_protected': is_protected,
                'is_mounted': is_mounted,
                'is_writable': is_writable,
                'is_system_disk': is_protected,
                'is_boot_disk': False,
                'is_removable': False,
                'is_external': False,
                'role': 'unknown',
                'interface': 'unknown',
                'safety_level': 'dangerous' if is_protected else 'safe' if is_writable else 'unknown',
                'boot_priority': 0,
                'confidence_score': 0.5,
                'warnings': ['Basic analysis only - intelligent analysis failed'],
                'recommendations': ['Use with caution - limited analysis available'],
                'status': 'PROTECTED' if is_protected else 'MOUNTED' if is_mounted else 'AVAILABLE' if is_writable else 'READ_ONLY'
            }
        except Exception as e:
            logger.error(f"Error getting basic disk status for {device}: {e}")
            return {
                'is_protected': True,
                'is_mounted': False,
                'is_writable': False,
                'is_system_disk': True,
                'is_boot_disk': False,
                'is_removable': False,
                'is_external': False,
                'role': 'unknown',
                'interface': 'unknown',
                'safety_level': 'unknown',
                'boot_priority': 0,
                'confidence_score': 0.0,
                'warnings': ['Analysis failed - assume protected'],
                'recommendations': ['Contact administrator'],
                'status': 'ERROR'
            }
    
    
    def _load_safety_config(self) -> Dict:
        """Load enhanced safety configuration from file"""
        config_path = Path(__file__).parent.parent.parent / "safety_config.json"
        default_config = {
            "protected_devices": [],
            "protected_patterns": [],
            "additional_safety_checks": True,
            "require_multiple_confirmations": True,
            "block_system_disks": True,
            "log_all_attempts": True,
            "emergency_override": False,
            "safety_warnings": {
                "show_hpa_dco_warnings": True,
                "warn_about_hidden_areas": True,
                "require_hpa_dco_confirmation": True,
                "show_disk_health_warnings": True,
                "warn_about_ssd_wear": True
            },
            "confirmation_levels": {
                "standard_wipe": 2,
                "hpa_removal": 3,
                "dco_removal": 4,
                "system_disk_attempt": 5
            },
            "logging": {
                "log_safety_violations": True,
                "log_confirmation_attempts": True,
                "log_hpa_dco_operations": True,
                "log_file_retention_days": 30
            },
            "advanced_protection": {
                "check_disk_mount_status": True,
                "verify_disk_ownership": True,
                "check_for_active_processes": True,
                "validate_wipe_parameters": True
            }
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded enhanced safety configuration from {config_path}")
                    # Deep merge configuration
                    merged_config = self._deep_merge_config(default_config, config)
                    return merged_config
            else:
                logger.info("No safety config found, using enhanced defaults")
                return default_config
        except Exception as e:
            logger.error(f"Error loading safety config: {e}")
            return default_config
    
    def _deep_merge_config(self, default: Dict, user: Dict) -> Dict:
        """Deep merge user configuration with defaults"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
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
        # First check if it's a removable/USB device - these should never be protected
        disk_info = self.get_disk_info(device)
        if disk_info and (disk_info.is_removable or disk_info.type == DiskType.REMOVABLE):
            return False  # Never protect removable devices
        
        system_disks = self.get_system_disks()
        return device in system_disks
    
    def validate_wipe_operation(self, device: str, method: str, passes: int, 
                              remove_hpa: bool = False, remove_dco: bool = False) -> Tuple[bool, List[str]]:
        """
        Enhanced validation for wipe operations
        
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        
        # Basic protection check
        if self.is_device_protected(device):
            return False, [f"Device {device} is protected and cannot be wiped"]
        
        # Check if device is writable
        if not self.is_disk_writable(device):
            return False, [f"Device {device} is not writable"]
        
        # Advanced protection checks
        if self.safety_config.get("advanced_protection", {}).get("check_disk_mount_status", True):
            if self._is_disk_mounted(device):
                warnings.append(f"Device {device} appears to be mounted")
        
        if self.safety_config.get("advanced_protection", {}).get("validate_wipe_parameters", True):
            if passes < 1 or passes > 10:
                warnings.append(f"Unusual number of passes: {passes}")
            
            if method not in self.get_wipe_methods():
                warnings.append(f"Unknown wipe method: {method}")
        
        # USB-specific warnings and recommendations
        disk_info = self.get_disk_info(device)
        if disk_info and disk_info.type.value == 'removable':
            warnings.append("💿 USB/Removable device detected")
            warnings.append("💡 USB Wiping Recommendations:")
            warnings.append("   • Ensure the USB device is not mounted")
            warnings.append("   • Use 'dd' or 'secure' method for USB drives")
            warnings.append("   • USB drives may have limited write cycles")
            warnings.append("   • Consider using 'quick' method for large USB drives")
            warnings.append("   • Verify the wipe was successful after completion")
            
            # Check for USB-specific issues
            if disk_info.size_gb > 64:
                warnings.append("⚠️ Large USB device detected - wiping may take considerable time")
            
            if method == 'hdparm' and disk_info.type.value == 'removable':
                warnings.append("⚠️ hdparm method may not work optimally with USB devices")
                warnings.append("💡 Consider using 'dd' or 'secure' method instead")
        
        # HPA/DCO specific warnings
        if self.safety_config.get("safety_warnings", {}).get("warn_about_hidden_areas", True):
            hpa_dco_info = self.detect_hpa_dco(device)
            if hpa_dco_info.get('hpa_detected') and not remove_hpa:
                warnings.append(f"HPA detected: {hpa_dco_info.get('hpa_gb', 0):.1f}GB hidden")
            if hpa_dco_info.get('dco_detected') and not remove_dco:
                warnings.append(f"DCO detected: {hpa_dco_info.get('dco_gb', 0):.1f}GB hidden")
        
        # Enhanced DCO removal warnings
        if remove_dco and self.safety_config.get("safety_warnings", {}).get("require_hpa_dco_confirmation", True):
            warnings.append("⚠️ CRITICAL WARNING: DCO removal is EXTREMELY DANGEROUS")
            warnings.append("⚠️ DCO removal can PERMANENTLY DAMAGE the disk hardware")
            warnings.append("⚠️ This operation should only be performed by experienced professionals")
            warnings.append("⚠️ Ensure you have proper backup and recovery procedures")
            
            # Check if emergency override is required
            if not self.safety_config.get('emergency_override', False):
                warnings.append("🚨 DCO removal requires emergency override to be enabled in safety configuration")
        
        return True, warnings
    
    def _is_disk_mounted(self, device: str) -> bool:
        """Check if a disk is currently mounted"""
        try:
            import psutil
            for partition in psutil.disk_partitions():
                if partition.device.startswith(device):
                    return True
            return False
        except Exception:
            return False

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
        WARNING: This is EXTREMELY DANGEROUS and can permanently damage the disk

        Args:
            device: Disk device path

        Returns:
            Tuple of (success, message)
        """
        try:
            # Enhanced safety checks
            if self.is_device_protected(device):
                return False, f"Cannot remove DCO from protected device {device}"

            # Check if device is mounted
            if self._is_disk_mounted(device):
                return False, f"Cannot remove DCO from mounted device {device}. Please unmount first."

            # Get disk information for additional safety checks
            disk_info = self.get_disk_info(device)
            if disk_info:
                # Check if it's a system-critical disk type
                if disk_info.type.value in ['nvme', 'ssd']:
                    logger.critical(f"DCO removal attempted on {disk_info.type.value.upper()} device {device}")
                    return False, f"DCO removal on {disk_info.type.value.upper()} devices is EXTREMELY RISKY and may cause permanent damage"

            # Log critical safety warning
            logger.critical(f"CRITICAL: DCO removal attempted on {device} - THIS CAN PERMANENTLY DAMAGE THE DISK")
            
            # Additional safety check - require emergency override
            if not self.safety_config.get('emergency_override', False):
                return False, ("DCO removal requires emergency override to be enabled in safety configuration. "
                             "This operation can PERMANENTLY DAMAGE the disk and should only be performed "
                             "by experienced professionals with proper backup procedures.")

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
