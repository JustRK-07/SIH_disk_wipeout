# Disk Wipeout - Secure Data Erasure Tool

A comprehensive, cross-platform data wiping application that ensures complete data erasure and provides cryptographic proof of erasure. Supports Windows, Linux, and Android platforms.

## Features

- **Cross-Platform Support**: Works on Windows, Linux, and Android
- **Multiple Wipe Methods**: 
  - Windows: Cipher.exe, DeviceIoControl, secure multi-pass
  - Linux: hdparm, nvme-cli, blkdiscard, dd
  - Android: Storage Access Framework, root-level commands
- **Verification & Proof**: Cryptographic verification and certificate generation
- **User-Friendly Interface**: Both GUI and CLI interfaces
- **Safety Features**: System disk protection, confirmation prompts

## Installation

### Prerequisites

- Python 3.7 or higher
- Platform-specific tools (see below)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Platform-Specific Setup

#### Windows
- No additional setup required for basic functionality
- For advanced features, ensure you have administrator privileges

#### Linux
Install required tools:
```bash
# Ubuntu/Debian
sudo apt-get install hdparm nvme-cli util-linux

# CentOS/RHEL/Fedora
sudo yum install hdparm nvme-cli util-linux
```

#### Android
- For root features: Device must be rooted
- For non-root usage: Uses Storage Access Framework

## Usage

### GUI Mode (Default)
```bash
python main.py
```

### CLI Mode
```bash
python main.py --cli
```

### CLI Examples

List available disks:
```bash
python main.py --cli list
```

Show disk information:
```bash
python main.py --cli info /dev/sdb
```

Wipe a disk:
```bash
python main.py --cli wipe /dev/sdb --method secure --passes 3
```

Show available wipe methods:
```bash
python main.py --cli methods
```

## Wipe Methods

### Windows
- **cipher**: Uses Windows Cipher.exe for free space wiping
- **secure**: Multi-pass secure wipe (requires DeviceIoControl implementation)
- **quick**: Single-pass quick wipe

### Linux
- **hdparm**: Hardware secure erase for HDDs
- **nvme**: NVMe secure format for SSDs
- **blkdiscard**: TRIM-based discard for SSDs
- **dd**: Multi-pass wiping with random data
- **secure**: Alias for dd with multiple passes
- **quick**: Single-pass dd wipe

### Android
- **dd**: Root-level dd wiping
- **secure**: Multi-pass secure wipe
- **quick**: Single-pass wipe
- **saf**: Storage Access Framework (requires app integration)

## Verification

The application provides cryptographic verification of data erasure:

- **Sample Analysis**: Reads and analyzes disk samples
- **Pattern Detection**: Identifies incomplete wipes
- **Entropy Calculation**: Measures data randomness
- **Certificate Generation**: Creates verifiable proof documents

## Safety Features

- **System Disk Protection**: Prevents wiping of system/boot disks
- **Confirmation Prompts**: Requires explicit confirmation for destructive operations
- **Writable Check**: Verifies disk is writable before attempting wipe
- **Progress Monitoring**: Real-time progress updates

## File Structure

```
disk_wipeout/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── src/
│   ├── core/              # Core functionality
│   │   ├── disk_manager.py
│   │   ├── verification.py
│   │   └── platforms/     # Platform-specific implementations
│   ├── gui/               # GUI interface
│   │   └── main_window.py
│   ├── cli/               # CLI interface
│   │   └── cli_interface.py
│   └── utils/             # Utilities
│       └── logger.py
├── logs/                  # Log files
└── proofs/                # Verification certificates
```

## Security Considerations

- **Administrator/Root Access**: Some wipe methods require elevated privileges
- **Data Recovery**: Proper wiping makes data recovery extremely difficult
- **Verification**: Always verify wipe completion for sensitive data
- **Backup**: Ensure you have backups of important data before wiping

## Limitations

- **DeviceIoControl**: Windows low-level access requires additional implementation
- **Android SAF**: Storage Access Framework integration requires app development
- **Hardware Support**: Some methods depend on hardware capabilities
- **Performance**: Secure wiping can take significant time for large disks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is provided "as is" without warranty. Users are responsible for ensuring compliance with applicable laws and regulations regarding data destruction. The authors are not liable for any data loss or other damages resulting from the use of this software.

## Support

For issues, questions, or contributions, please use the GitHub issue tracker.
