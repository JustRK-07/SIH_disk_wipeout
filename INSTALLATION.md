# Installation Guide - Disk Wipeout

## Quick Start

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd disk_wipeout
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the installation**
   ```bash
   python test_app.py
   ```

4. **Run the application**
   ```bash
   # GUI mode (default)
   python main.py
   
   # CLI mode
   python main.py --cli list
   ```

## Platform-Specific Setup

### Windows

**Basic Installation:**
- Python 3.7+ required
- No additional tools needed for basic functionality

**Advanced Features:**
- Administrator privileges required for low-level disk access
- WMI support (usually pre-installed on Windows)

**Optional Tools:**
- `dd` for Windows (if available) for additional wipe methods

### Linux

**Required Tools:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install hdparm nvme-cli util-linux

# CentOS/RHEL/Fedora
sudo yum install hdparm nvme-cli util-linux
# or
sudo dnf install hdparm nvme-cli util-linux

# Arch Linux
sudo pacman -S hdparm nvme-cli util-linux
```

**Permissions:**
- Root/sudo access required for most wipe operations
- User must be in appropriate groups for disk access

### Android

**For Rooted Devices:**
- Device must be rooted
- `su` command must be available
- Root access required for block device operations

**For Non-Rooted Devices:**
- Uses Storage Access Framework
- Limited to user-accessible storage areas
- Some features may not be available

## Dependencies

### Core Dependencies
- `psutil>=5.9.0` - Cross-platform system information
- `cryptography>=41.0.0` - Cryptographic functions

### Platform-Specific Dependencies
- `WMI>=1.5.1` (Windows only) - Windows Management Instrumentation
- `pywin32>=306` (Windows only) - Windows API access
- `jnius` (Android only) - Java Native Interface for Python

## Verification

After installation, verify everything works:

```bash
# Run the test suite
python test_app.py

# Test CLI functionality
python main.py --cli list
python main.py --cli methods

# Test GUI (if tkinter is available)
python main.py
```

## Troubleshooting

### Common Issues

**Import Errors:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.7+)

**Permission Errors:**
- On Linux: Use `sudo` for disk operations
- On Windows: Run as Administrator
- On Android: Ensure device is rooted for advanced features

**Missing Tools:**
- Install platform-specific tools (hdparm, nvme-cli, etc.)
- Check if tools are in PATH: `which hdparm`

**GUI Issues:**
- Ensure tkinter is installed: `python -m tkinter`
- On Linux: Install tkinter: `sudo apt-get install python3-tk`

### Getting Help

1. Check the logs in the `logs/` directory
2. Run with verbose output: `python main.py --cli --verbose list`
3. Check system requirements and installed tools
4. Review the README.md for detailed usage instructions

## Security Notes

- **Administrator/Root Access**: Required for most wipe operations
- **Data Loss**: Wiping is irreversible - ensure you have backups
- **System Disks**: The application prevents wiping of system/boot disks
- **Verification**: Always verify wipe completion for sensitive data

## Development Setup

For developers wanting to contribute:

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
python test_app.py

# Check code style (if tools are available)
flake8 src/
pylint src/
```

## Uninstallation

To remove the application:

```bash
# Remove Python packages
pip uninstall psutil WMI pywin32 cryptography

# Remove application files
rm -rf disk_wipeout/
rm -rf logs/
rm -rf proofs/
```
