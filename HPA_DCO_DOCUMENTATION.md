# HPA/DCO Detection and Removal - Technical Documentation

## Overview

This document describes the Host Protected Area (HPA) and Device Configuration Overlay (DCO) detection and removal functionality implemented in the Disk Wipeout application. The implementation provides cross-platform support for Windows, Linux, and Android.

## What are HPA and DCO?

### Host Protected Area (HPA)
- A hidden area at the end of a hard drive that is not normally visible to the OS
- Created using the SET MAX ADDRESS command (ATA-4 specification)
- Can store data that survives normal disk wiping operations
- Often used by manufacturers for system recovery or diagnostics
- Can be misused to hide malicious data

### Device Configuration Overlay (DCO)
- A more advanced hiding mechanism than HPA
- Modifies the apparent characteristics of the drive
- Can hide capacity and modify drive identification
- More difficult to detect and remove than HPA
- Requires specialized tools for removal

## Implementation Details

### Platform Support

#### Linux
- **Primary Method**: hdparm utility
- **Secondary Methods**: smartctl, kernel sysfs
- **Requirements**:
  - hdparm package (`sudo apt-get install hdparm`)
  - smartmontools package (`sudo apt-get install smartmontools`)
  - Root/sudo access

#### Windows
- **Primary Methods**: WMI, DeviceIoControl API
- **Secondary Methods**: diskpart, PowerShell Get-Disk
- **Requirements**:
  - Administrator privileges
  - WMI access (optional but recommended)
  - For removal: Specialized tools like HDAT2

#### Android
- **Primary Method**: hdparm (if available)
- **Secondary Methods**: blockdev, /sys/block analysis
- **Requirements**:
  - Root access
  - hdparm via Termux or custom ROM (optional)

## Usage

### Command Line Interface

#### Detect HPA/DCO
```bash
# Linux/Mac
sudo python main.py detect-hpa /dev/sdb

# Windows (Run as Administrator)
python main.py detect-hpa \\.\PhysicalDrive1
```

#### Remove HPA
```bash
# Linux (requires hdparm)
sudo python main.py remove-hpa /dev/sdb --force

# Windows (limited support)
python main.py remove-hpa \\.\PhysicalDrive1
```

#### Remove DCO
```bash
# Linux (requires hdparm --dco-restore)
sudo python main.py remove-dco /dev/sdb --force

# Windows (requires specialized tools)
python main.py remove-dco \\.\PhysicalDrive1
```

#### Full Wipe with HPA/DCO Removal
```bash
# Wipe disk and remove hidden areas
sudo python main.py wipe-full /dev/sdb --remove-hpa --method secure --passes 3
```

### Python API

```python
from src.core.disk_manager import DiskManager

# Initialize manager
disk_manager = DiskManager()

# Detect HPA/DCO
device = "/dev/sdb"
hpa_dco_info = disk_manager.detect_hpa_dco(device)

if hpa_dco_info['hpa_detected']:
    print(f"HPA detected: {hpa_dco_info['hpa_sectors']} hidden sectors")

    # Remove HPA
    success, message = disk_manager.remove_hpa(device)
    if success:
        print(f"HPA removed: {message}")

# Full wipe with HPA/DCO removal
success, message = disk_manager.wipe_with_hpa_dco_removal(
    device=device,
    method="secure",
    passes=3,
    verify=True,
    remove_hpa=True,
    remove_dco=False  # DCO removal is dangerous
)
```

## Detection Methods

### Linux Detection Process

1. **hdparm -I**: Get drive identification data
2. **hdparm -N**: Check native max vs current max sectors
3. **hdparm --dco-identify**: Query DCO information
4. **smartctl -i**: Cross-verify with SMART data
5. **/sys/block**: Compare kernel-reported size

### Windows Detection Process

1. **WMI Win32_DiskDrive**: Query disk properties
2. **DeviceIoControl**: Send ATA IDENTIFY command
3. **diskpart detail disk**: Check for size discrepancies
4. **PowerShell Get-Disk**: Verify allocated vs total size

### Android Detection Process

1. **hdparm** (if available): Standard ATA commands
2. **/sys/block/*/size**: Kernel-reported sectors
3. **/proc/partitions**: Partition table analysis
4. **blockdev --getsize64**: Block device size
5. **eMMC RPMB**: Check for hardware-protected areas

## Safety Features

### Protection Mechanisms
- System disk detection prevents accidental OS damage
- Multiple confirmation prompts for dangerous operations
- Verification after HPA/DCO removal
- Configurable safety overrides via safety_config.json

### Warning Levels
- **INFO**: Normal detection results
- **WARNING**: HPA detected, removable
- **DANGER**: DCO detected, removal risky
- **CRITICAL**: System disk or protected device

## Technical Details

### HPA Detection Formula
```
HPA Present = (Native Max Sectors > Current Max Sectors)
HPA Size = Native Max Sectors - Current Max Sectors
```

### DCO Detection Formula
```
DCO Present = (Physical Sectors > Native Max Sectors)
DCO Size = Physical Sectors - Native Max Sectors
```

### Sector to GB Conversion
```python
size_gb = (sectors * 512) / (1024**3)
```

## Limitations

### General Limitations
- Some drives don't support HPA/DCO commands
- Firmware bugs may report incorrect values
- USB adapters may not pass through ATA commands

### Platform-Specific Limitations

#### Linux
- Requires hdparm for full functionality
- Some NVMe drives don't support HPA/DCO
- RAID controllers may block direct disk access

#### Windows
- Limited native support for HPA/DCO removal
- Requires third-party tools for complete functionality
- Some drivers block low-level disk access

#### Android
- Root access absolutely required
- Limited tool availability
- eMMC devices use different protection mechanisms

## Security Considerations

### Data Recovery Risk
- Removing HPA/DCO exposes previously hidden data
- Hidden areas may contain sensitive information
- Proper wiping should include HPA/DCO areas

### Forensic Implications
- HPA/DCO are common hiding places for malware
- Forensic tools specifically check these areas
- Complete disk sanitization requires HPA/DCO removal

## Troubleshooting

### Common Issues

#### "hdparm not available"
- **Solution**: Install hdparm package
- Linux: `sudo apt-get install hdparm`
- Android: Install via Termux or custom ROM

#### "Operation timed out"
- **Cause**: Drive not responding to ATA commands
- **Solution**: Check connection, try different interface

#### "Permission denied"
- **Solution**: Run with appropriate privileges
- Linux: Use sudo
- Windows: Run as Administrator
- Android: Ensure root access

#### "No HPA/DCO detected" (when expected)
- **Causes**:
  - Drive doesn't support HPA/DCO
  - USB adapter blocking commands
  - Already removed by previous operation

## Testing

### Test Script Usage
```bash
# Run comprehensive HPA/DCO test
sudo python test_hpa_dco.py

# Check specific device
sudo python main.py detect-hpa /dev/sdb
```

### Manual Testing with hdparm
```bash
# Check current vs native max
sudo hdparm -N /dev/sdb

# Get detailed drive info
sudo hdparm -I /dev/sdb

# Check DCO
sudo hdparm --dco-identify /dev/sdb
```

## Best Practices

1. **Always detect before removal**: Check for HPA/DCO before wiping
2. **Backup important data**: HPA removal is irreversible
3. **Use appropriate tools**: Platform-specific tools work best
4. **Verify after removal**: Ensure HPA/DCO successfully removed
5. **Document findings**: Keep records for forensic purposes

## References

- ATA/ATAPI Command Set (ATA8-ACS)
- hdparm documentation: https://linux.die.net/man/8/hdparm
- NIST SP 800-88r1: Guidelines for Media Sanitization
- DCO and HPA: Forensic Implications and Detection

## Support

For issues or questions regarding HPA/DCO functionality:
1. Check the troubleshooting section
2. Run the test script for diagnostics
3. Enable debug logging for detailed output
4. Report issues with platform and device details