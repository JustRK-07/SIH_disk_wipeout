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
        self.hpa_dco_info = None  # HPA/DCO detection results

    def __str__(self):
        base_str = f"{self.device} ({self.size // (1024**3)}GB) - {self.type.upper()}"
        if self.hpa_dco_info:
            if self.hpa_dco_info.get('hpa_detected'):
                hidden_gb = (self.hpa_dco_info.get('hpa_sectors', 0) * 512) // (1024**3)
                base_str += f" [HPA: {hidden_gb}GB hidden]"
            if self.hpa_dco_info.get('dco_detected'):
                dco_gb = (self.hpa_dco_info.get('dco_sectors', 0) * 512) // (1024**3)
                base_str += f" [DCO: {dco_gb}GB hidden]"
        return base_str
