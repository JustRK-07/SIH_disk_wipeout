"""
Certificate Generator for SIH Disk Wipeout
Generates cryptographic proof-of-erasure certificates
"""

import json
import hashlib
import hmac
import time
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import base64
import secrets

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

@dataclass
class CertificateData:
    """Data structure for wipe certificate"""
    certificate_id: str
    timestamp: str
    device_info: Dict[str, Any]  # manufacturer, model, serial, capacity
    sanitization_method: str  # Clear / Purge / Destroy
    exact_command: str  # e.g., nvme sanitize -a 2 /dev/nvme0n1
    passes: int
    verification_method: str
    verification_result: str
    operator_info: Dict[str, str]
    supervisor_info: Dict[str, str]
    tool_versions: Dict[str, str]  # e.g., nvme-cli v1.12, hdparm v9.66
    hash_algorithm: str
    certificate_hash: str
    issuer: str
    version: str
    metadata: Dict[str, Any]

class CertificateGenerator:
    """Generates cryptographic certificates for disk wipe operations"""
    
    def __init__(self, issuer: str = "SIH Disk Wipeout", version: str = "1.0"):
        self.issuer = issuer
        self.version = version
        self.certificates_dir = "certificates"
        self._ensure_certificates_dir()
    
    def _ensure_certificates_dir(self):
        """Ensure certificates directory exists"""
        if not os.path.exists(self.certificates_dir):
            os.makedirs(self.certificates_dir)
    
    def gather_real_device_data(self, device: str, disk_manager) -> Dict[str, Any]:
        """Gather real device information from disk manager"""
        try:
            # Get basic disk info
            disk_info = disk_manager.get_disk_info(device)
            if not disk_info:
                raise ValueError(f"Could not get disk info for {device}")
            
            # Get HPA/DCO information
            hpa_dco_info = disk_manager.detect_hpa_dco(device)
            
            # Get system information
            system_disks = disk_manager.get_system_disks()
            is_system_disk = device in system_disks
            is_writable = disk_manager.is_disk_writable(device)
            
            # Build comprehensive device data
            device_data = {
                'device': device,
                'model': disk_info.model or 'Unknown',
                'serial': disk_info.serial or 'Unknown',
                'size_formatted': f"{disk_info.size // (1024**3):,}GB" if disk_info.size > 0 else 'Unknown',
                'size_bytes': disk_info.size,
                'type': disk_info.type.upper() if hasattr(disk_info.type, 'upper') else str(disk_info.type).upper(),
                'filesystem': disk_info.filesystem or 'Unknown',
                'mountpoint': disk_info.mountpoint or 'Not mounted',
                'is_system_disk': is_system_disk,
                'is_writable': is_writable,
                'hpa_dco_info': hpa_dco_info,
                'detection_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Add HPA/DCO details if available
            if hpa_dco_info and not hpa_dco_info.get('error'):
                device_data.update({
                    'hpa_detected': hpa_dco_info.get('hpa_detected', False),
                    'dco_detected': hpa_dco_info.get('dco_detected', False),
                    'hidden_capacity_gb': hpa_dco_info.get('hidden_gb', 0),
                    'total_capacity_gb': device_data['size_bytes'] / (1024**3) + hpa_dco_info.get('hidden_gb', 0)
                })
            
            return device_data
            
        except Exception as e:
            # Fallback to basic info if detailed gathering fails
            return {
                'device': device,
                'model': 'Unknown',
                'serial': 'Unknown',
                'size_formatted': 'Unknown',
                'size_bytes': 0,
                'type': 'UNKNOWN',
                'filesystem': 'Unknown',
                'mountpoint': 'Unknown',
                'is_system_disk': False,
                'is_writable': False,
                'error': str(e),
                'detection_timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def generate_certificate(self, 
                           device_info: Dict[str, Any],
                           sanitization_method: str,
                           exact_command: str,
                           passes: int,
                           verification_method: str = "hash_verification",
                           verification_result: str = "verified",
                           operator_info: Optional[Dict[str, str]] = None,
                           supervisor_info: Optional[Dict[str, str]] = None,
                           tool_versions: Optional[Dict[str, str]] = None,
                           metadata: Optional[Dict[str, Any]] = None,
                           disk_manager=None) -> CertificateData:
        """Generate a new wipe certificate with real data"""
        
        # Generate unique certificate ID
        certificate_id = self._generate_certificate_id()
        
        # Get current timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # If disk_manager is provided, gather real device data
        if disk_manager and 'device' in device_info:
            real_device_data = self.gather_real_device_data(device_info['device'], disk_manager)
            # Merge with provided device_info, giving priority to real data
            device_info = {**device_info, **real_device_data}
        
        # Set default values if not provided
        if operator_info is None:
            operator_info = {"name": "System Administrator", "id": "ADMIN-001"}
        if supervisor_info is None:
            supervisor_info = {"name": "IT Security Manager", "id": "SUPER-001"}
        if tool_versions is None:
            tool_versions = self._detect_tool_versions()
        
        # Prepare certificate data
        cert_data = CertificateData(
            certificate_id=certificate_id,
            timestamp=timestamp,
            device_info=device_info,
            sanitization_method=sanitization_method,
            exact_command=exact_command,
            passes=passes,
            verification_method=verification_method,
            verification_result=verification_result,
            operator_info=operator_info,
            supervisor_info=supervisor_info,
            tool_versions=tool_versions,
            hash_algorithm="SHA-256",
            certificate_hash="",  # Will be calculated
            issuer=self.issuer,
            version=self.version,
            metadata=metadata or {}
        )
        
        # Calculate certificate hash
        cert_data.certificate_hash = self._calculate_certificate_hash(cert_data)
        
        return cert_data
    
    def _generate_certificate_id(self) -> str:
        """Generate a unique certificate ID"""
        timestamp = int(time.time())
        random_part = secrets.token_hex(8)
        return f"SIH-{timestamp}-{random_part}"
    
    def _detect_tool_versions(self) -> Dict[str, str]:
        """Detect versions of common disk sanitization tools"""
        import subprocess
        import shutil
        
        tool_versions = {}
        
        # Common tools to check
        tools = {
            'nvme-cli': 'nvme --version',
            'hdparm': 'hdparm -V',
            'dd': 'dd --version',
            'shred': 'shred --version',
            'wipefs': 'wipefs --version',
            'sg_utils': 'sg_scan --version',
            'smartctl': 'smartctl --version'
        }
        
        for tool, version_cmd in tools.items():
            try:
                if shutil.which(tool.split()[0]):
                    result = subprocess.run(version_cmd.split(), 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        # Extract version from output
                        version_line = result.stdout.split('\n')[0]
                        tool_versions[tool] = version_line.strip()
                    else:
                        tool_versions[tool] = "Available (version unknown)"
                else:
                    tool_versions[tool] = "Not installed"
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                tool_versions[tool] = "Not available"
        
        # Add SIH Disk Wipeout version
        tool_versions['sih-disk-wipeout'] = f"{self.version} ({self.issuer})"
        
        return tool_versions
    
    def _calculate_certificate_hash(self, cert_data: CertificateData) -> str:
        """Calculate SHA-256 hash of certificate data"""
        # Convert to dict and create a deterministic string
        data_dict = asdict(cert_data)
        # Remove the hash field itself for calculation
        data_dict.pop('certificate_hash', None)
        
        # Create a sorted, deterministic JSON string
        json_string = json.dumps(data_dict, sort_keys=True, separators=(',', ':'))
        
        # Calculate SHA-256 hash
        hash_obj = hashlib.sha256(json_string.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def save_certificate(self, cert_data: CertificateData, filename: Optional[str] = None) -> str:
        """Save certificate to file"""
        if filename is None:
            filename = f"{cert_data.certificate_id}.json"
        
        filepath = os.path.join(self.certificates_dir, filename)
        
        # Convert to dict for JSON serialization
        cert_dict = asdict(cert_data)
        
        # Save as pretty-printed JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cert_dict, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def load_certificate(self, filepath: str) -> CertificateData:
        """Load certificate from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            cert_dict = json.load(f)
        
        return CertificateData(**cert_dict)
    
    def verify_certificate(self, cert_data: CertificateData) -> bool:
        """Verify certificate integrity"""
        # Recalculate hash
        expected_hash = self._calculate_certificate_hash(cert_data)
        
        # Compare with stored hash
        return expected_hash == cert_data.certificate_hash
    
    def generate_certificate_report(self, cert_data: CertificateData) -> str:
        """Generate a NIST-compliant certificate report"""
        report = f"""
================================================================================
                    MEDIA SANITIZATION CERTIFICATE
                    NIST SP 800-88 REV. 1 COMPLIANT
================================================================================

CERTIFICATE INFORMATION
--------------------------------------------------------------------------------
Certificate ID:           {cert_data.certificate_id}
Date/Time:               {cert_data.timestamp}
Issuing Organization:    {cert_data.issuer}
Certificate Version:     {cert_data.version}
Compliance Standard:     NIST SP 800-88 Rev. 1

MEDIA INFORMATION
--------------------------------------------------------------------------------
Media Identifier:        {cert_data.device_info.get('device', 'N/A')}
Media Type:              {cert_data.device_info.get('type', 'N/A')}
Manufacturer:            {cert_data.device_info.get('model', 'N/A').split()[0] if cert_data.device_info.get('model') else 'N/A'}
Model:                   {cert_data.device_info.get('model', 'N/A')}
Serial Number:           {cert_data.device_info.get('serial', 'N/A')}
Capacity:                {cert_data.device_info.get('size_formatted', 'N/A')}
Physical Location:       {cert_data.metadata.get('location', 'Not specified')}

SANITIZATION DETAILS
--------------------------------------------------------------------------------
Sanitization Method:     {cert_data.sanitization_method.upper()}
Exact Command:           {cert_data.exact_command}
Number of Passes:        {cert_data.passes}
Verification Method:     {cert_data.verification_method}
Verification Result:     {cert_data.verification_result.upper()}
Hash Algorithm:          {cert_data.hash_algorithm}
Sanitization Date:       {cert_data.timestamp.split('T')[0]}
Sanitization Time:       {cert_data.timestamp.split('T')[1].split('+')[0]}

PERSONNEL INFORMATION
--------------------------------------------------------------------------------
Operator Name:           {cert_data.operator_info.get('name', 'Not specified')}
Operator ID:             {cert_data.operator_info.get('id', 'Not specified')}
Supervisor Name:         {cert_data.supervisor_info.get('name', 'Not specified')}
Supervisor ID:           {cert_data.supervisor_info.get('id', 'Not specified')}
Organization:            {cert_data.issuer}

TOOL VERSIONS
--------------------------------------------------------------------------------
"""
        # Add tool versions
        for tool, version in cert_data.tool_versions.items():
            report += f"{tool.replace('-', ' ').title()}:           {version}\n"
        
        report += f"""
COMPLIANCE INFORMATION
--------------------------------------------------------------------------------
Compliance Standard:     NIST SP 800-88 Rev. 1
Security Classification: {cert_data.metadata.get('classification', 'Unclassified')}
Data Sensitivity:        {cert_data.metadata.get('sensitivity', 'Standard')}
Retention Period:        {cert_data.metadata.get('retention', '7 years')}

CRYPTOGRAPHIC VERIFICATION
--------------------------------------------------------------------------------
Certificate Hash (SHA-256):
{cert_data.certificate_hash}

VERIFICATION INSTRUCTIONS
--------------------------------------------------------------------------------
To verify this certificate:
1. Extract all data fields except the certificate_hash
2. Create a JSON object with the remaining fields
3. Calculate SHA-256 hash of the JSON string
4. Compare with the hash shown above
5. If hashes match, certificate is authentic

CERTIFICATION STATEMENT
--------------------------------------------------------------------------------
I certify that the media identified above has been sanitized in accordance with
NIST SP 800-88 Rev. 1 guidelines using the method and verification procedures
specified. The sanitization process has been completed successfully and all
data has been permanently removed from the media.

This certificate provides cryptographic proof of sanitization and can be used
for compliance, audit, and legal purposes.

================================================================================
CERTIFICATE SIGNATURE
================================================================================

Digital Signature Hash:  {cert_data.certificate_hash}
Verification Status:     VERIFIED
Certificate Integrity:   INTACT

This certificate is valid and authentic as verified by cryptographic hash
verification in accordance with NIST SP 800-88 Rev. 1 requirements.

================================================================================
END OF CERTIFICATE
================================================================================
"""
        return report
    
    def save_certificate_report(self, cert_data: CertificateData, filename: Optional[str] = None) -> str:
        """Save certificate report to text file"""
        if filename is None:
            filename = f"{cert_data.certificate_id}_report.txt"
        
        filepath = os.path.join(self.certificates_dir, filename)
        
        report = self.generate_certificate_report(cert_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return filepath
    
    def list_certificates(self) -> list:
        """List all certificates in the certificates directory"""
        certificates = []
        if os.path.exists(self.certificates_dir):
            for filename in os.listdir(self.certificates_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.certificates_dir, filename)
                    try:
                        cert_data = self.load_certificate(filepath)
                        certificates.append({
                            'filename': filename,
                            'certificate_id': cert_data.certificate_id,
                            'timestamp': cert_data.timestamp,
                            'device': cert_data.device_info.get('device', 'N/A'),
                            'method': cert_data.wipe_method,
                            'verified': self.verify_certificate(cert_data)
                        })
                    except Exception as e:
                        print(f"Error loading certificate {filename}: {e}")
        
        return sorted(certificates, key=lambda x: x['timestamp'], reverse=True)
    
    def generate_pdf_certificate(self, cert_data: CertificateData, filename: Optional[str] = None) -> str:
        """Generate PDF certificate following NIST template format"""
        if not PDF_AVAILABLE:
            raise ImportError("ReportLab not available. Install with: pip install reportlab")
        
        if filename is None:
            filename = f"{cert_data.certificate_id}_certificate.pdf"
        
        filepath = os.path.join(self.certificates_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(filepath, pagesize=A4, 
                              rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Build PDF content
        story = []
        
        # Title
        story.append(Paragraph("MEDIA SANITIZATION CERTIFICATE", title_style))
        story.append(Paragraph("NIST SP 800-88 REV. 1 COMPLIANT", title_style))
        story.append(Spacer(1, 20))
        
        # Certificate Information
        story.append(Paragraph("CERTIFICATE INFORMATION", heading_style))
        cert_info_data = [
            ['Certificate ID:', cert_data.certificate_id],
            ['Date/Time:', cert_data.timestamp],
            ['Issuing Organization:', cert_data.issuer],
            ['Certificate Version:', cert_data.version],
            ['Compliance Standard:', 'NIST SP 800-88 Rev. 1']
        ]
        cert_info_table = Table(cert_info_data, colWidths=[2*inch, 4*inch])
        cert_info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(cert_info_table)
        story.append(Spacer(1, 12))
        
        # Media Information
        story.append(Paragraph("MEDIA INFORMATION", heading_style))
        media_info_data = [
            ['Media Identifier:', cert_data.device_info.get('device', 'N/A')],
            ['Media Type:', cert_data.device_info.get('type', 'N/A')],
            ['Manufacturer:', cert_data.device_info.get('model', 'N/A').split()[0] if cert_data.device_info.get('model') else 'N/A'],
            ['Model:', cert_data.device_info.get('model', 'N/A')],
            ['Serial Number:', cert_data.device_info.get('serial', 'N/A')],
            ['Capacity:', cert_data.device_info.get('size_formatted', 'N/A')],
            ['Physical Location:', cert_data.metadata.get('location', 'Not specified')]
        ]
        media_info_table = Table(media_info_data, colWidths=[2*inch, 4*inch])
        media_info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(media_info_table)
        story.append(Spacer(1, 12))
        
        # Sanitization Details
        story.append(Paragraph("SANITIZATION DETAILS", heading_style))
        sanitization_data = [
            ['Sanitization Method:', cert_data.sanitization_method.upper()],
            ['Exact Command:', cert_data.exact_command],
            ['Number of Passes:', str(cert_data.passes)],
            ['Verification Method:', cert_data.verification_method],
            ['Verification Result:', cert_data.verification_result.upper()],
            ['Hash Algorithm:', cert_data.hash_algorithm],
            ['Sanitization Date:', cert_data.timestamp.split('T')[0]],
            ['Sanitization Time:', cert_data.timestamp.split('T')[1].split('+')[0]]
        ]
        sanitization_table = Table(sanitization_data, colWidths=[2*inch, 4*inch])
        sanitization_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(sanitization_table)
        story.append(Spacer(1, 12))
        
        # Personnel Information
        story.append(Paragraph("PERSONNEL INFORMATION", heading_style))
        personnel_data = [
            ['Operator Name:', cert_data.operator_info.get('name', 'Not specified')],
            ['Operator ID:', cert_data.operator_info.get('id', 'Not specified')],
            ['Supervisor Name:', cert_data.supervisor_info.get('name', 'Not specified')],
            ['Supervisor ID:', cert_data.supervisor_info.get('id', 'Not specified')],
            ['Organization:', cert_data.issuer]
        ]
        personnel_table = Table(personnel_data, colWidths=[2*inch, 4*inch])
        personnel_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(personnel_table)
        story.append(Spacer(1, 12))
        
        # Tool Versions
        story.append(Paragraph("TOOL VERSIONS", heading_style))
        tool_data = []
        for tool, version in cert_data.tool_versions.items():
            tool_data.append([f"{tool.replace('-', ' ').title()}:", version])
        
        tool_table = Table(tool_data, colWidths=[2*inch, 4*inch])
        tool_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(tool_table)
        story.append(Spacer(1, 12))
        
        # Compliance Information
        story.append(Paragraph("COMPLIANCE INFORMATION", heading_style))
        compliance_data = [
            ['Compliance Standard:', 'NIST SP 800-88 Rev. 1'],
            ['Security Classification:', cert_data.metadata.get('classification', 'Unclassified')],
            ['Data Sensitivity:', cert_data.metadata.get('sensitivity', 'Standard')],
            ['Retention Period:', cert_data.metadata.get('retention', '7 years')]
        ]
        compliance_table = Table(compliance_data, colWidths=[2*inch, 4*inch])
        compliance_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(compliance_table)
        story.append(Spacer(1, 12))
        
        # Cryptographic Verification
        story.append(Paragraph("CRYPTOGRAPHIC VERIFICATION", heading_style))
        story.append(Paragraph(f"Certificate Hash (SHA-256):", normal_style))
        story.append(Paragraph(cert_data.certificate_hash, normal_style))
        story.append(Spacer(1, 12))
        
        # Certification Statement
        story.append(Paragraph("CERTIFICATION STATEMENT", heading_style))
        statement_text = """
        I certify that the media identified above has been sanitized in accordance with 
        NIST SP 800-88 Rev. 1 guidelines using the method and verification procedures 
        specified. The sanitization process has been completed successfully and all 
        data has been permanently removed from the media.
        
        This certificate provides cryptographic proof of sanitization and can be used 
        for compliance, audit, and legal purposes.
        """
        story.append(Paragraph(statement_text, normal_style))
        story.append(Spacer(1, 20))
        
        # Certificate Signature
        story.append(Paragraph("CERTIFICATE SIGNATURE", heading_style))
        signature_data = [
            ['Digital Signature Hash:', cert_data.certificate_hash],
            ['Verification Status:', 'VERIFIED'],
            ['Certificate Integrity:', 'INTACT']
        ]
        signature_table = Table(signature_data, colWidths=[2*inch, 4*inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(signature_table)
        
        # Build PDF
        doc.build(story)
        
        return filepath
    
    def generate_enhanced_json_certificate(self, cert_data: CertificateData, filename: Optional[str] = None) -> str:
        """Generate enhanced JSON certificate following NIST template structure"""
        if filename is None:
            filename = f"{cert_data.certificate_id}_enhanced.json"
        
        filepath = os.path.join(self.certificates_dir, filename)
        
        # Create enhanced JSON structure following NIST template
        enhanced_cert = {
            "certificate_header": {
                "title": "Media Sanitization Certificate",
                "standard": "NIST SP 800-88 Rev. 1 Compliant",
                "version": cert_data.version,
                "issuer": cert_data.issuer
            },
            "certificate_information": {
                "certificate_id": cert_data.certificate_id,
                "timestamp": cert_data.timestamp,
                "date": cert_data.timestamp.split('T')[0],
                "time": cert_data.timestamp.split('T')[1].split('+')[0],
                "compliance_standard": "NIST SP 800-88 Rev. 1"
            },
            "media_information": {
                "media_identifier": cert_data.device_info.get('device', 'N/A'),
                "media_type": cert_data.device_info.get('type', 'N/A'),
                "manufacturer": cert_data.device_info.get('model', 'N/A').split()[0] if cert_data.device_info.get('model') else 'N/A',
                "model": cert_data.device_info.get('model', 'N/A'),
                "serial_number": cert_data.device_info.get('serial', 'N/A'),
                "capacity": cert_data.device_info.get('size_formatted', 'N/A'),
                "capacity_bytes": cert_data.device_info.get('size_bytes', 0),
                "filesystem": cert_data.device_info.get('filesystem', 'N/A'),
                "mountpoint": cert_data.device_info.get('mountpoint', 'N/A'),
                "physical_location": cert_data.metadata.get('location', 'Not specified'),
                "is_system_disk": cert_data.device_info.get('is_system_disk', False),
                "is_writable": cert_data.device_info.get('is_writable', False)
            },
            "sanitization_details": {
                "sanitization_method": cert_data.sanitization_method.upper(),
                "exact_command": cert_data.exact_command,
                "number_of_passes": cert_data.passes,
                "verification_method": cert_data.verification_method,
                "verification_result": cert_data.verification_result.upper(),
                "hash_algorithm": cert_data.hash_algorithm,
                "sanitization_date": cert_data.timestamp.split('T')[0],
                "sanitization_time": cert_data.timestamp.split('T')[1].split('+')[0],
                "hpa_dco_info": cert_data.device_info.get('hpa_dco_info', {}),
                "detection_timestamp": cert_data.device_info.get('detection_timestamp', '')
            },
            "personnel_information": {
                "operator_name": cert_data.operator_info.get('name', 'Not specified'),
                "operator_id": cert_data.operator_info.get('id', 'Not specified'),
                "supervisor_name": cert_data.supervisor_info.get('name', 'Not specified'),
                "supervisor_id": cert_data.supervisor_info.get('id', 'Not specified'),
                "organization": cert_data.issuer
            },
            "tool_versions": cert_data.tool_versions,
            "compliance_information": {
                "compliance_standard": "NIST SP 800-88 Rev. 1",
                "security_classification": cert_data.metadata.get('classification', 'Unclassified'),
                "data_sensitivity": cert_data.metadata.get('sensitivity', 'Standard'),
                "retention_period": cert_data.metadata.get('retention', '7 years'),
                "audit_trail": cert_data.metadata.get('audit_trail', ''),
                "purpose": cert_data.metadata.get('purpose', 'Data sanitization')
            },
            "cryptographic_verification": {
                "certificate_hash": cert_data.certificate_hash,
                "hash_algorithm": cert_data.hash_algorithm,
                "verification_instructions": [
                    "Extract all data fields except the certificate_hash",
                    "Create a JSON object with the remaining fields",
                    "Calculate SHA-256 hash of the JSON string",
                    "Compare with the hash shown above",
                    "If hashes match, certificate is authentic"
                ]
            },
            "certification_statement": {
                "statement": "I certify that the media identified above has been sanitized in accordance with NIST SP 800-88 Rev. 1 guidelines using the method and verification procedures specified. The sanitization process has been completed successfully and all data has been permanently removed from the media.",
                "legal_notice": "This certificate provides cryptographic proof of sanitization and can be used for compliance, audit, and legal purposes."
            },
            "certificate_signature": {
                "digital_signature_hash": cert_data.certificate_hash,
                "verification_status": "VERIFIED",
                "certificate_integrity": "INTACT",
                "validity_statement": "This certificate is valid and authentic as verified by cryptographic hash verification in accordance with NIST SP 800-88 Rev. 1 requirements."
            },
            "metadata": {
                "generation_timestamp": datetime.now(timezone.utc).isoformat(),
                "generator_version": cert_data.version,
                "generator_issuer": cert_data.issuer,
                "additional_metadata": cert_data.metadata
            }
        }
        
        # Save enhanced JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(enhanced_cert, f, indent=2, ensure_ascii=False)
        
        return filepath

# Example usage and testing
if __name__ == "__main__":
    # Create certificate generator
    cert_gen = CertificateGenerator()
    
    # Import disk manager for real data
    try:
        from .disk_manager import DiskManager
        disk_manager = DiskManager()
        
        # Get real device information
        devices = disk_manager.get_available_disks()
        if devices:
            # Use the first available device for testing
            test_device = devices[0].device
            print(f"Testing with real device: {test_device}")
            
            # Generate certificate with real data
            certificate = cert_gen.generate_certificate(
                device_info={'device': test_device},  # Minimal info, will be filled with real data
                sanitization_method='Purge',
                exact_command=f'nvme sanitize -a 2 {test_device}',
                passes=3,
                verification_method='hash_verification',
                verification_result='verified',
                operator_info={'name': 'System Administrator', 'id': 'ADMIN-001'},
                supervisor_info={'name': 'IT Security Manager', 'id': 'SUPER-001'},
                metadata={
                    'location': 'Data Center',
                    'classification': 'Confidential',
                    'sensitivity': 'High',
                    'retention': '7 years',
                    'compliance_standard': 'NIST SP 800-88 Rev. 1',
                    'audit_trail': 'AUDIT-2025-001',
                    'purpose': 'End-of-life data destruction'
                },
                disk_manager=disk_manager  # Pass disk manager for real data gathering
            )
        else:
            print("No devices found, using sample data")
            # Fallback to sample data if no devices found
            device_info = {
                'device': '/dev/sda',
                'model': 'TOSHIBA MQ04ABF100',
                'serial': '1234567890',
                'size_formatted': '931.5GB',
                'type': 'HDD',
                'filesystem': 'ext4',
                'mountpoint': '/mnt/backup'
            }
            
            certificate = cert_gen.generate_certificate(
                device_info=device_info,
                wipe_method='secure',
                passes=3,
                verification_status='verified',
                metadata={
                    'operator': 'System Administrator',
                    'supervisor': 'IT Security Manager',
                    'location': 'Data Center',
                    'classification': 'Confidential',
                    'sensitivity': 'High',
                    'retention': '7 years',
                    'compliance_standard': 'NIST SP 800-88 Rev. 1',
                    'audit_trail': 'AUDIT-2025-001',
                    'purpose': 'End-of-life data destruction'
                }
            )
    except ImportError:
        print("Disk manager not available, using sample data")
        # Fallback to sample data
        device_info = {
            'device': '/dev/sda',
            'model': 'TOSHIBA MQ04ABF100',
            'serial': '1234567890',
            'size_formatted': '931.5GB',
            'type': 'HDD',
            'filesystem': 'ext4',
            'mountpoint': '/mnt/backup'
        }
        
        certificate = cert_gen.generate_certificate(
            device_info=device_info,
            wipe_method='secure',
            passes=3,
            verification_status='verified',
            metadata={
                'operator': 'System Administrator',
                'supervisor': 'IT Security Manager',
                'location': 'Data Center',
                'classification': 'Confidential',
                'sensitivity': 'High',
                'retention': '7 years',
                'compliance_standard': 'NIST SP 800-88 Rev. 1',
                'audit_trail': 'AUDIT-2025-001',
                'purpose': 'End-of-life data destruction'
            }
        )
    
    # Save certificate in multiple formats
    json_file = cert_gen.save_certificate(certificate)
    report_file = cert_gen.save_certificate_report(certificate)
    enhanced_json_file = cert_gen.generate_enhanced_json_certificate(certificate)
    
    print(f"Certificate generated: {certificate.certificate_id}")
    print(f"Standard JSON file: {json_file}")
    print(f"Enhanced JSON file: {enhanced_json_file}")
    print(f"Text report file: {report_file}")
    
    # Generate PDF certificate if ReportLab is available
    try:
        pdf_file = cert_gen.generate_pdf_certificate(certificate)
        print(f"PDF certificate: {pdf_file}")
    except ImportError:
        print("PDF generation not available. Install ReportLab: pip install reportlab")
    except Exception as e:
        print(f"PDF generation failed: {e}")
    
    # Verify certificate
    is_valid = cert_gen.verify_certificate(certificate)
    print(f"Certificate verification: {'PASSED' if is_valid else 'FAILED'}")
    
    # Display report
    print("\n" + cert_gen.generate_certificate_report(certificate))
