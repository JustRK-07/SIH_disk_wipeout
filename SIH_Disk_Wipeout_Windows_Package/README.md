# SIH Disk Wipeout - Secure Data Erasure Tool

Professional-grade, cross-platform data wiping application with cryptographic verification and enterprise safety features.

## Features

- **Cross-Platform**: Windows, Linux, Android support
- **Multiple Wipe Methods**: Hardware and software-level erasure
- **Safety Protection**: System disk protection with multi-layer safety
- **Verification**: Cryptographic proof-of-erasure certificates
- **Dual Interface**: Professional GUI and CLI modes

## Installation

```bash
pip install -r requirements.txt
```

### Linux Setup
```bash
sudo apt-get install hdparm nvme-cli util-linux
```

## Usage

### GUI Mode
```bash
python main.py                    # Professional GUI with all features
```

### CLI Mode
```bash
python main.py --cli list         # List disks
python main.py --cli info /dev/sdb # Disk info
python main.py --cli wipe /dev/sdb --method secure --passes 3
```

## Wipe Methods

- **Linux**: hdparm, nvme, blkdiscard, dd, secure, quick
- **Windows**: cipher, secure, quick
- **Android**: dd, secure, quick, saf

## Safety Features

- **System Disk Protection**: Multi-layer protection prevents accidental system disk wiping
- **Verification**: Cryptographic proof-of-erasure certificates
- **Confirmation Prompts**: Multiple confirmation dialogs for destructive operations

## License

MIT License - see LICENSE file for details.
