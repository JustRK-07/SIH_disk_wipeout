"""
Data models for the disk wiping application
"""

class DiskInfo:
    """Data class for disk information"""
    def __init__(self, device: str, size: int, type: str, model: str = "", serial: str = ""):
        self.device = device
        self.size = size
        self.type = type  # 'hdd', 'ssd', 'nvme', 'removable'
        self.model = model
        self.serial = serial
        self.mountpoint = ""
        self.filesystem = ""
    
    def __str__(self):
        return f"{self.device} ({self.size // (1024**3)}GB) - {self.type.upper()}"
