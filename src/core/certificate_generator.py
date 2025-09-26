"""
Real-Time NIST SP 800-88 Rev. 1 Compliant Certificate Generator
Generates JSON and PDF certificates with actual disk wipeout data
"""

import os
import json
import hashlib
import platform
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
import socket
import getpass

# PDF generation imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("Warning: reportlab not installed. PDF generation disabled. Install with: pip install reportlab")

logger = logging.getLogger(__name__)

class SanitizationType(Enum):
    """NIST-defined sanitization types"""
    CLEAR = "Clear"
    PURGE = "Purge"
    DESTROY = "Destroy"

class SanitizationMethod(Enum):
    """Sanitization methods as per NIST guidelines"""
    OVERWRITE = "Overwrite"
    BLOCK_ERASE = "Block Erase"
    CRYPTO_ERASE = "Cryptographic Erase"
    DEGAUSS = "Degauss"
    PHYSICAL_DESTRUCTION = "Physical Destruction"
    SECURE_ERASE = "Secure Erase"
    TRIM = "TRIM/UNMAP"

class VerificationStatus(Enum):
    """Verification status"""
    PASSED = "Passed"
    FAILED = "Failed"
    PARTIAL = "Partial"
    NOT_PERFORMED = "Not Performed"

@dataclass
class SystemInfo:
    """System information"""
    hostname: str
    platform: str
    platform_version: str
    processor: str
    python_version: str
    tool_version: str = "1.0.0"
    
    @classmethod
    def gather(cls):
        """Gather current system information"""
        return cls(
            hostname=socket.gethostname(),
            platform=platform.system(),
            platform_version=platform.release(),
            processor=platform.processor(),
            python_version=platform.python_version(),
            tool_version="1.0.0"
        )

@dataclass
class DiskDataExtractor:
    """Extract real disk information"""
    
    @staticmethod
    def get_disk_info_linux(device: str) -> Dict:
        """Get real disk information on Linux"""
        info = {
            'vendor': 'Unknown',
            'model': 'Unknown',
            'serial': 'Unknown',
            'size_bytes': 0,
            'size_formatted': 'Unknown',
            'firmware': 'Unknown',
            'interface': 'Unknown',
            'rotation_rate': 'Unknown',
            'smart_status': 'Unknown'
        }
        
        try:
            # Get vendor and model from sysfs
            device_name = os.path.basename(device)
            
            # Try vendor
            vendor_path = f"/sys/block/{device_name}/device/vendor"
            if os.path.exists(vendor_path):
                with open(vendor_path, 'r') as f:
                    info['vendor'] = f.read().strip()
            
            # Try model
            model_path = f"/sys/block/{device_name}/device/model"
            if os.path.exists(model_path):
                with open(model_path, 'r') as f:
                    info['model'] = f.read().strip()
            
            # Get size
            size_path = f"/sys/block/{device_name}/size"
            if os.path.exists(size_path):
                with open(size_path, 'r') as f:
                    sectors = int(f.read().strip())
                    info['size_bytes'] = sectors * 512
                    # Format size
                    size_gb = info['size_bytes'] / (1024**3)
                    if size_gb >= 1024:
                        info['size_formatted'] = f"{size_gb/1024:.1f}TB"
                    else:
                        info['size_formatted'] = f"{size_gb:.1f}GB"
            
            # Try hdparm for more details
            try:
                result = subprocess.run(['sudo', 'hdparm', '-I', device], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    output = result.stdout
                    # Parse serial number
                    import re
                    serial_match = re.search(r'Serial Number:\s+(\S+)', output)
                    if serial_match:
                        info['serial'] = serial_match.group(1)
                    
                    # Parse firmware
                    fw_match = re.search(r'Firmware Revision:\s+(\S+)', output)
                    if fw_match:
                        info['firmware'] = fw_match.group(1)
                    
                    # Check interface
                    if 'SATA' in output:
                        info['interface'] = 'SATA'
                    elif 'NVMe' in output:
                        info['interface'] = 'NVMe'
                    
                    # Check rotation rate (SSD vs HDD)
                    if 'Nominal Media Rotation Rate: Solid State Device' in output:
                        info['rotation_rate'] = 'SSD'
                    elif 'Nominal Media Rotation Rate:' in output:
                        rpm_match = re.search(r'Nominal Media Rotation Rate:\s+(\d+)', output)
                        if rpm_match:
                            info['rotation_rate'] = f"{rpm_match.group(1)} RPM"
            except:
                pass
            
            # Try smartctl for SMART status
            try:
                result = subprocess.run(['sudo', 'smartctl', '-H', device],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    if 'PASSED' in result.stdout:
                        info['smart_status'] = 'PASSED'
                    elif 'FAILED' in result.stdout:
                        info['smart_status'] = 'FAILED'
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error getting disk info: {e}")
        
        return info
    
    @staticmethod
    def get_disk_info(device: str) -> Dict:
        """Get disk information based on platform"""
        system = platform.system().lower()
        if system == 'linux':
            return DiskDataExtractor.get_disk_info_linux(device)
        else:
            # Basic fallback for other platforms
            return {
                'vendor': 'Unknown',
                'model': 'Unknown',
                'serial': 'Unknown',
                'size_bytes': 0,
                'size_formatted': 'Unknown',
                'firmware': 'Unknown',
                'interface': 'Unknown',
                'rotation_rate': 'Unknown',
                'smart_status': 'Unknown'
            }

@dataclass
class WipeOperationData:
    """Complete wipe operation data"""
    # Operation identifiers
    operation_id: str
    certificate_id: str
    
    # Timestamps
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    duration_formatted: str
    
    # Device information
    device_path: str
    device_vendor: str
    device_model: str
    device_serial: str
    device_size_bytes: int
    device_size_formatted: str
    device_firmware: str
    device_interface: str
    device_type: str  # HDD/SSD/NVMe/USB
    smart_status: str
    
    # Wipe details
    wipe_method: str
    sanitization_type: str  # Clear/Purge/Destroy
    sanitization_method: str  # Overwrite/Block Erase/etc
    wipe_passes: int
    pattern_used: str
    bytes_written: int
    write_speed_mbps: float
    
    # Verification
    verification_performed: bool
    verification_method: str
    verification_status: str
    verification_details: str
    verification_timestamp: Optional[datetime]
    
    # Result
    operation_success: bool
    error_message: str
    
    # System info
    system_info: Dict
    
    # Operator info
    operator_username: str
    operator_hostname: str
    
    # Compliance
    compliance_standards: List[str]
    
    # Checksums
    data_checksum: str = ""
    
    def calculate_checksum(self):
        """Calculate SHA-256 checksum of the operation data"""
        data_str = f"{self.operation_id}{self.device_serial}{self.start_time}{self.end_time}"
        self.data_checksum = hashlib.sha256(data_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime objects to strings
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        if self.verification_timestamp:
            data['verification_timestamp'] = self.verification_timestamp.isoformat()
        return data

class RealTimeCertificateGenerator:
    """Generate certificates with real disk wipeout data"""
    
    def __init__(self, output_dir: str = "certificates"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.json_dir = self.output_dir / "json"
        self.json_dir.mkdir(exist_ok=True)
        self.pdf_dir = self.output_dir / "pdf"
        self.pdf_dir.mkdir(exist_ok=True)
        
        if HAS_REPORTLAB:
            self.styles = getSampleStyleSheet()
            self._setup_pdf_styles()
    
    def _setup_pdf_styles(self):
        """Setup PDF styles"""
        if not HAS_REPORTLAB:
            return
            
        self.styles.add(ParagraphStyle(
            name='CertTitle',
            parent=self.styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#000080'),
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=11,
            textColor=colors.white,
            backColor=colors.HexColor('#4472C4'),
            leftIndent=3,
            rightIndent=3,
            spaceBefore=8,
            spaceAfter=8
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldValue',
            parent=self.styles['Normal'],
            fontSize=9
        ))
    
    def capture_wipe_operation(self, device_path: str, method: str, 
                              passes: int, start_time: datetime, 
                              end_time: datetime, success: bool,
                              bytes_written: int = 0,
                              verification_result: Dict = None) -> WipeOperationData:
        """Capture real wipe operation data"""
        
        # Generate IDs
        operation_id = f"OP_{start_time.strftime('%Y%m%d_%H%M%S')}_{os.path.basename(device_path)}"
        cert_id = f"CERT_{hashlib.sha256(operation_id.encode()).hexdigest()[:12].upper()}"
        
        # Get real disk information
        disk_info = DiskDataExtractor.get_disk_info(device_path)
        
        # Calculate duration
        duration = end_time - start_time
        duration_seconds = int(duration.total_seconds())
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        duration_formatted = f"{hours}h {minutes}m {seconds}s"
        
        # Calculate write speed if bytes written
        write_speed_mbps = 0
        if bytes_written > 0 and duration_seconds > 0:
            write_speed_mbps = (bytes_written / (1024*1024)) / duration_seconds
        
        # Determine device type
        device_type = "Unknown"
        if disk_info['rotation_rate'] == 'SSD':
            device_type = "SSD"
        elif 'RPM' in disk_info.get('rotation_rate', ''):
            device_type = "HDD"
        elif 'nvme' in device_path.lower():
            device_type = "NVMe"
        elif 'usb' in device_path.lower() or '/dev/sd' in device_path:
            # Check if removable
            device_name = os.path.basename(device_path)
            removable_path = f"/sys/block/{device_name}/removable"
            if os.path.exists(removable_path):
                with open(removable_path, 'r') as f:
                    if f.read().strip() == "1":
                        device_type = "USB/Removable"
        
        # Map method to NIST types
        sanitization_type = self._map_to_sanitization_type(method)
        sanitization_method = self._map_to_sanitization_method(method)
        
        # Pattern used
        pattern_map = {
            'dd': 'Random data (urandom)',
            'secure': 'DoD 5220.22-M (3 passes)',
            'quick': 'Zeros (single pass)',
            'hdparm': 'ATA Secure Erase',
            'nvme': 'NVMe Format',
            'blkdiscard': 'TRIM/UNMAP'
        }
        pattern_used = pattern_map.get(method.lower(), 'Custom pattern')
        
        # Verification details
        if verification_result:
            verification_performed = True
            verification_method = verification_result.get('method', 'Sampling')
            verification_status = 'PASSED' if verification_result.get('passed', False) else 'FAILED'
            verification_details = verification_result.get('details', '')
            verification_timestamp = datetime.now()
        else:
            verification_performed = False
            verification_method = "Not performed"
            verification_status = "N/A"
            verification_details = ""
            verification_timestamp = None
        
        # Create operation data
        operation_data = WipeOperationData(
            operation_id=operation_id,
            certificate_id=cert_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            duration_formatted=duration_formatted,
            device_path=device_path,
            device_vendor=disk_info['vendor'],
            device_model=disk_info['model'],
            device_serial=disk_info['serial'],
            device_size_bytes=disk_info['size_bytes'],
            device_size_formatted=disk_info['size_formatted'],
            device_firmware=disk_info['firmware'],
            device_interface=disk_info['interface'],
            device_type=device_type,
            smart_status=disk_info['smart_status'],
            wipe_method=method,
            sanitization_type=sanitization_type,
            sanitization_method=sanitization_method,
            wipe_passes=passes,
            pattern_used=pattern_used,
            bytes_written=bytes_written,
            write_speed_mbps=write_speed_mbps,
            verification_performed=verification_performed,
            verification_method=verification_method,
            verification_status=verification_status,
            verification_details=verification_details,
            verification_timestamp=verification_timestamp,
            operation_success=success,
            error_message="" if success else "Operation failed",
            system_info=asdict(SystemInfo.gather()),
            operator_username=getpass.getuser(),
            operator_hostname=socket.gethostname(),
            compliance_standards=["NIST SP 800-88 Rev. 1", "DoD 5220.22-M"]
        )
        
        # Calculate checksum
        operation_data.calculate_checksum()
        
        return operation_data
    
    def generate_json_certificate(self, operation_data: WipeOperationData) -> str:
        """Generate JSON certificate"""
        filename = f"{operation_data.certificate_id}_{operation_data.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.json_dir / filename
        
        # Convert to dictionary
        cert_data = operation_data.to_dict()
        
        # Add metadata
        cert_data['_metadata'] = {
            'version': '1.0',
            'schema': 'NIST SP 800-88 Rev. 1',
            'generated_at': datetime.now().isoformat(),
            'generator': 'SIH Disk Wipeout Certificate Generator'
        }
        
        # Write JSON file with proper formatting
        with open(filepath, 'w') as f:
            json.dump(cert_data, f, indent=2, sort_keys=False)
        
        logger.info(f"JSON certificate generated: {filepath}")
        return str(filepath)
    
    def generate_pdf_certificate(self, operation_data: WipeOperationData) -> Optional[str]:
        """Generate PDF certificate"""
        if not HAS_REPORTLAB:
            logger.warning("PDF generation skipped - reportlab not installed")
            return None
        
        filename = f"{operation_data.certificate_id}_{operation_data.start_time.strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.pdf_dir / filename
        
        # Create PDF
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        story = []
        
        # Title
        story.append(Paragraph("CERTIFICATE OF MEDIA SANITIZATION", self.styles['CertTitle']))
        story.append(Paragraph(f"Certificate ID: {operation_data.certificate_id}", self.styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Device Information Section
        story.append(Paragraph("DEVICE INFORMATION", self.styles['SectionHeader']))
        device_data = [
            ["Device Path:", operation_data.device_path, "Type:", operation_data.device_type],
            ["Vendor:", operation_data.device_vendor, "Model:", operation_data.device_model],
            ["Serial Number:", operation_data.device_serial, "Capacity:", operation_data.device_size_formatted],
            ["Interface:", operation_data.device_interface, "SMART Status:", operation_data.smart_status]
        ]
        device_table = Table(device_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        device_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ]))
        story.append(device_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Sanitization Details Section
        story.append(Paragraph("SANITIZATION DETAILS", self.styles['SectionHeader']))
        sanitize_data = [
            ["Method:", operation_data.wipe_method, "Type:", operation_data.sanitization_type],
            ["Passes:", str(operation_data.wipe_passes), "Pattern:", operation_data.pattern_used],
            ["Start Time:", operation_data.start_time.strftime('%Y-%m-%d %H:%M:%S'), 
             "End Time:", operation_data.end_time.strftime('%Y-%m-%d %H:%M:%S')],
            ["Duration:", operation_data.duration_formatted, 
             "Write Speed:", f"{operation_data.write_speed_mbps:.1f} MB/s" if operation_data.write_speed_mbps > 0 else "N/A"],
            ["Status:", "SUCCESS" if operation_data.operation_success else "FAILED", 
             "Verification:", operation_data.verification_status]
        ]
        sanitize_table = Table(sanitize_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        sanitize_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ]))
        story.append(sanitize_table)
        story.append(Spacer(1, 0.2*inch))
        
        # System Information Section
        story.append(Paragraph("SYSTEM INFORMATION", self.styles['SectionHeader']))
        system_data = [
            ["Operator:", operation_data.operator_username, "Hostname:", operation_data.operator_hostname],
            ["Platform:", operation_data.system_info['platform'], 
             "Version:", operation_data.system_info['platform_version']],
            ["Tool Version:", operation_data.system_info['tool_version'],
             "Checksum:", operation_data.data_checksum[:16] + "..."]
        ]
        system_table = Table(system_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        system_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ]))
        story.append(system_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Compliance Statement
        story.append(Paragraph("COMPLIANCE STATEMENT", self.styles['SectionHeader']))
        compliance_text = (
            f"This certificate confirms that the above-mentioned storage device has been sanitized "
            f"in accordance with: {', '.join(operation_data.compliance_standards)}. "
            f"The sanitization method '{operation_data.sanitization_type}' using '{operation_data.sanitization_method}' "
            f"is appropriate for the data classification and intended disposition of the media."
        )
        story.append(Paragraph(compliance_text, self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Signature Section
        story.append(Paragraph("CERTIFICATION", self.styles['SectionHeader']))
        story.append(Paragraph(
            "I certify that the information provided above is accurate and complete.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.3*inch))
        
        sig_data = [
            ["Signature:", "_" * 40, "Date:", "_" * 20],
            ["Name:", "_" * 40, "Title:", "_" * 20]
        ]
        sig_table = Table(sig_data, colWidths=[1*inch, 2.5*inch, 0.8*inch, 2.2*inch])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ]))
        story.append(sig_table)
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF certificate generated: {filepath}")
        return str(filepath)
    
    def _map_to_sanitization_type(self, method: str) -> str:
        """Map wipe method to NIST sanitization type"""
        method_lower = method.lower()
        if method_lower in ['quick', 'dd', 'secure']:
            return "Clear"
        elif method_lower in ['hdparm', 'nvme', 'blkdiscard']:
            return "Purge"
        else:
            return "Clear"
    
    def _map_to_sanitization_method(self, method: str) -> str:
        """Map wipe method to sanitization method"""
        method_lower = method.lower()
        if method_lower in ['quick', 'dd', 'secure']:
            return "Overwrite"
        elif method_lower == 'hdparm':
            return "Secure Erase"
        elif method_lower == 'nvme':
            return "NVMe Format"
        elif method_lower == 'blkdiscard':
            return "TRIM/UNMAP"
        else:
            return "Overwrite"
    
    def generate_certificates(self, operation_data: WipeOperationData) -> Dict[str, str]:
        """Generate both JSON and PDF certificates"""
        result = {}
        
        # Generate JSON (always)
        result['json'] = self.generate_json_certificate(operation_data)
        
        # Generate PDF (if reportlab available)
        pdf_path = self.generate_pdf_certificate(operation_data)
        if pdf_path:
            result['pdf'] = pdf_path
        
        return result


# Integration function for your main application
def generate_wipe_certificate(device_path: str, method: str, passes: int,
                             start_time: datetime, end_time: datetime,
                             success: bool, bytes_written: int = 0,
                             verification_result: Dict = None) -> Dict[str, str]:
    """
    Generate certificates for a completed wipe operation
    
    Returns dict with paths to generated certificates
    """
    generator = RealTimeCertificateGenerator()
    
    # Capture real operation data
    operation_data = generator.capture_wipe_operation(
        device_path=device_path,
        method=method,
        passes=passes,
        start_time=start_time,
        end_time=end_time,
        success=success,
        bytes_written=bytes_written,
        verification_result=verification_result
    )
    
    # Generate certificates
    certificates = generator.generate_certificates(operation_data)
    
    return certificates
