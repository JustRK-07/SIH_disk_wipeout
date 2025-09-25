"""
Enhanced data models for the disk wiping application
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import datetime

class DiskType(Enum):
    """Enumeration of disk types"""
    HDD = "hdd"
    SSD = "ssd"
    NVME = "nvme"
    REMOVABLE = "removable"
    UNKNOWN = "unknown"

class DiskStatus(Enum):
    """Enumeration of disk statuses"""
    AVAILABLE = "available"
    PROTECTED = "protected"
    READ_ONLY = "read_only"
    IN_USE = "in_use"
    ERROR = "error"

class WipeMethod(Enum):
    """Enumeration of wipe methods"""
    SECURE = "secure"
    QUICK = "quick"
    DD = "dd"
    CIPHER = "cipher"
    HDPARM = "hdparm"
    NVME = "nvme"
    BLKDISCARD = "blkdiscard"
    SAF = "saf"

@dataclass
class HPADCOInfo:
    """Information about HPA/DCO detection results"""
    hpa_detected: bool = False
    dco_detected: bool = False
    current_max_sectors: int = 0
    native_max_sectors: int = 0
    accessible_sectors: int = 0
    hpa_sectors: int = 0
    dco_sectors: int = 0
    can_remove_hpa: bool = False
    can_remove_dco: bool = False
    detection_method: str = ""
    error: Optional[str] = None
    
    @property
    def hidden_gb(self) -> float:
        """Calculate hidden capacity in GB"""
        total_hidden = self.hpa_sectors + self.dco_sectors
        return (total_hidden * 512) / (1024**3)
    
    @property
    def hpa_gb(self) -> float:
        """Calculate HPA capacity in GB"""
        return (self.hpa_sectors * 512) / (1024**3)
    
    @property
    def dco_gb(self) -> float:
        """Calculate DCO capacity in GB"""
        return (self.dco_sectors * 512) / (1024**3)

@dataclass
class DiskHealth:
    """Disk health information"""
    temperature: Optional[float] = None
    power_on_hours: Optional[int] = None
    bad_sectors: Optional[int] = None
    reallocated_sectors: Optional[int] = None
    health_status: str = "unknown"  # good, warning, critical, unknown
    last_checked: Optional[datetime.datetime] = None

@dataclass
class WipeOperation:
    """Information about a wipe operation"""
    device: str
    method: WipeMethod
    passes: int
    verify: bool
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    progress: float = 0.0
    status: str = "pending"  # pending, running, completed, failed, cancelled
    speed_mbps: float = 0.0
    eta_seconds: int = 0
    error_message: Optional[str] = None
    verification_result: Optional[bool] = None

@dataclass
class DiskInfo:
    """Enhanced data class for disk information"""
    device: str
    size: int
    type: DiskType
    model: str = ""
    serial: str = ""
    mountpoint: str = ""
    filesystem: str = ""
    hpa_dco_info: Optional[HPADCOInfo] = None
    health: Optional[DiskHealth] = None
    status: DiskStatus = DiskStatus.AVAILABLE
    is_writable: bool = True
    is_system_disk: bool = False
    last_updated: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    @property
    def size_gb(self) -> float:
        """Get size in GB"""
        return self.size / (1024**3)
    
    @property
    def size_formatted(self) -> str:
        """Get formatted size string"""
        if self.size_gb >= 1024:
            return f"{self.size_gb / 1024:.1f}TB"
        else:
            return f"{self.size_gb:.1f}GB"
    
    @property
    def has_hidden_areas(self) -> bool:
        """Check if disk has hidden areas (HPA/DCO)"""
        if not self.hpa_dco_info:
            return False
        return self.hpa_dco_info.hpa_detected or self.hpa_dco_info.dco_detected
    
    @property
    def hidden_capacity_gb(self) -> float:
        """Get hidden capacity in GB"""
        if not self.hpa_dco_info:
            return 0.0
        return self.hpa_dco_info.hidden_gb
    
    @property
    def total_capacity_gb(self) -> float:
        """Get total capacity including hidden areas"""
        return self.size_gb + self.hidden_capacity_gb
    
    @property
    def status_icon(self) -> str:
        """Get status icon for display"""
        if self.is_system_disk:
            return "🔒"
        elif self.status == DiskStatus.AVAILABLE:
            return "✅"
        elif self.status == DiskStatus.READ_ONLY:
            return "🔒"
        elif self.status == DiskStatus.IN_USE:
            return "🔄"
        else:
            return "❌"
    
    @property
    def type_icon(self) -> str:
        """Get type icon for display"""
        icons = {
            DiskType.HDD: "💾",
            DiskType.SSD: "⚡",
            DiskType.NVME: "🚀",
            DiskType.REMOVABLE: "💿",
            DiskType.UNKNOWN: "❓"
        }
        return icons.get(self.type, "❓")
    
    def get_detailed_info(self) -> Dict[str, Any]:
        """Get detailed information as dictionary"""
        info = {
            "device": self.device,
            "size": self.size_formatted,
            "size_bytes": self.size,
            "type": self.type.value.upper(),
            "type_icon": self.type_icon,
            "model": self.model,
            "serial": self.serial,
            "mountpoint": self.mountpoint or "Not mounted",
            "filesystem": self.filesystem or "Unknown",
            "status": self.status.value,
            "status_icon": self.status_icon,
            "is_writable": self.is_writable,
            "is_system_disk": self.is_system_disk,
            "has_hidden_areas": self.has_hidden_areas,
            "hidden_capacity": f"{self.hidden_capacity_gb:.1f}GB" if self.has_hidden_areas else "None",
            "total_capacity": f"{self.total_capacity_gb:.1f}GB",
            "last_updated": self.last_updated.isoformat()
        }
        
        if self.hpa_dco_info:
            info.update({
                "hpa_detected": self.hpa_dco_info.hpa_detected,
                "dco_detected": self.hpa_dco_info.dco_detected,
                "hpa_capacity": f"{self.hpa_dco_info.hpa_gb:.1f}GB",
                "dco_capacity": f"{self.hpa_dco_info.dco_gb:.1f}GB",
                "can_remove_hpa": self.hpa_dco_info.can_remove_hpa,
                "can_remove_dco": self.hpa_dco_info.can_remove_dco
            })
        
        if self.health:
            info.update({
                "health_status": self.health.health_status,
                "temperature": self.health.temperature,
                "power_on_hours": self.health.power_on_hours,
                "bad_sectors": self.health.bad_sectors
            })
        
        return info

    def __str__(self):
        base_str = f"{self.device} ({self.size_formatted}) - {self.type.value.upper()}"
        if self.has_hidden_areas:
            base_str += f" [Hidden: {self.hidden_capacity_gb:.1f}GB]"
        return base_str
