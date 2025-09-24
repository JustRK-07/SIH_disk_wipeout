# Disk Wipeout - Hybrid Edition Guide

## Overview

Disk Wipeout now comes in **two editions** to meet different user needs:

- **🪶 Lite Edition** (5MB) - For technical users who prefer manual setup
- **📦 Complete Edition** (50MB) - For beginners and offline use with everything included

Both editions use the **same codebase** and have identical functionality. The only difference is whether tools are bundled or not.

## Which Edition Should I Choose?

### Choose **Lite Edition** if you:
- ✅ Are comfortable with command line
- ✅ Already have or can install hdparm, smartctl, etc.
- ✅ Want the smallest download
- ✅ Have a reliable internet connection
- ✅ Prefer to manage dependencies yourself

### Choose **Complete Edition** if you:
- ✅ Are new to disk forensics/wiping
- ✅ Work in offline environments
- ✅ Want everything to "just work" immediately
- ✅ Don't want to install dependencies manually
- ✅ Use multiple different systems

## Download Links

| Edition | Size | Best For | Download |
|---------|------|----------|----------|
| **Lite** | ~5MB | Technical users | `disk_wipeout_lite_v1.0.tar.gz` |
| **Complete** | ~50MB | Beginners, offline use | `disk_wipeout_complete_v1.0.tar.gz` |

## Feature Comparison

| Feature | Lite Edition | Complete Edition |
|---------|--------------|------------------|
| HPA/DCO Detection | ✅ (requires tools) | ✅ (bundled) |
| Cross-platform | ✅ | ✅ |
| Offline usage | ❌ (needs internet for tools) | ✅ |
| Tool management | Manual | Automatic |
| Disk wiping | ✅ | ✅ |
| GUI interface | ✅ | ✅ |
| CLI interface | ✅ | ✅ |

## Installation & Usage

### Lite Edition Setup

1. **Download and extract:**
   ```bash
   wget disk_wipeout_lite_v1.0.tar.gz
   tar -xzf disk_wipeout_lite_v1.0.tar.gz
   cd disk_wipeout_lite
   ```

2. **Install dependencies:**
   ```bash
   # Linux (Ubuntu/Debian)
   sudo apt-get install hdparm smartmontools nvme-cli

   # Linux (Fedora/RHEL)
   sudo dnf install hdparm smartmontools nvme-cli

   # Windows (with winget)
   winget install hdparm smartmontools

   # macOS (with Homebrew)
   brew install hdparm smartmontools
   ```

3. **Check tool availability:**
   ```bash
   python main.py tools
   ```

4. **Start using:**
   ```bash
   sudo python main.py detect-hpa /dev/sdb
   ```

### Complete Edition Setup

1. **Download and extract:**
   ```bash
   wget disk_wipeout_complete_v1.0.tar.gz
   tar -xzf disk_wipeout_complete_v1.0.tar.gz
   cd disk_wipeout_complete
   ```

2. **No additional setup needed!** All tools are bundled.

3. **Verify bundled tools:**
   ```bash
   python main.py tools
   ```

4. **Start using immediately:**
   ```bash
   sudo python main.py detect-hpa /dev/sdb
   ```

## Tool Availability Check

Both editions include a tool checker:

```bash
python main.py tools
```

**Lite Edition Output:**
```
🔧 Tool Availability Report
=================================
System: Linux
Architecture: x86_64
Edition: Lite

Tool Status:
hdparm       ❌ Missing
smartctl     ✅ Available
             Path: /usr/sbin/smartctl (System)

💡 Installation Suggestions:
hdparm: sudo apt-get install hdparm
```

**Complete Edition Output:**
```
🔧 Tool Availability Report
=================================
System: Linux
Architecture: x86_64
Edition: Complete
Tools Directory: /path/to/tools

Tool Status:
hdparm       ✅ Available
             Path: ./tools/linux/x86_64/hdparm (Bundled)
smartctl     ✅ Available
             Path: ./tools/linux/x86_64/smartctl (Bundled)

✅ All tools available!
```

## Usage Examples

### HPA/DCO Detection
```bash
# Both editions - same command
python main.py detect-hpa /dev/sdb

# Output shows if HPA/DCO found
⚠️  HPA DETECTED!
Hidden Sectors: 2,048,576
Hidden Size: 1.00 GB
Can Remove: Yes
```

### Tool-Aware Wiping
```bash
# Automatically uses best available tools
python main.py wipe-full /dev/sdb --remove-hpa --method secure
```

### Migration from Lite to Complete

If you started with Lite Edition and want Complete Edition:

1. Download Complete Edition
2. Copy your data/config files
3. No other changes needed - same commands work

## Building from Source

### Build Both Editions
```bash
python build.py --both
```

### Build Specific Edition
```bash
python build.py --lite      # Lite only
python build.py --complete  # Complete only
```

### Build Output
```
📊 Build Summary:
✓ Lite Edition:     4.8 MB
✓ Complete Edition: 52.3 MB
✓ Size difference:  47.5 MB

📦 Created archives:
• disk_wipeout_lite_v1.0.tar.gz (4.2 MB)
• disk_wipeout_complete_v1.0.tar.gz (48.1 MB)
```

## Technical Details

### How Tool Detection Works

The **ToolManager** class handles both editions:

1. **Complete Edition**: Checks `tools/` directory first
2. **Lite Edition**: Falls back to system tools
3. **Automatic fallback**: Complete edition falls back to system if bundled tools fail

```python
# Automatic tool resolution
hdparm_path = tool_manager.get_tool_path('hdparm')
# Returns: ./tools/linux/x86_64/hdparm (Complete)
# Returns: hdparm (Lite with system install)
# Returns: None (Lite without system install)
```

### Directory Structure

**Lite Edition:**
```
disk_wipeout_lite/
├── src/
├── main.py
├── requirements.txt
└── README.md
```

**Complete Edition:**
```
disk_wipeout_complete/
├── src/
├── tools/                  # ← Additional bundled tools
│   ├── linux/
│   │   ├── x86_64/
│   │   └── arm64/
│   ├── windows/
│   └── macos/
├── main.py
├── requirements.txt
└── README.md
```

## Troubleshooting

### Lite Edition Issues

**"hdparm not available"**
```bash
# Install missing tools
sudo apt-get install hdparm

# Or switch to Complete Edition
```

**"Permission denied"**
```bash
# Run with appropriate privileges
sudo python main.py detect-hpa /dev/sdb
```

### Complete Edition Issues

**"Bundled tools not found"**
- Check if `tools/` directory exists
- Verify correct architecture folder
- Re-download Complete Edition if corrupted

**"Operation timed out"**
- USB adapters may not support ATA commands
- Try with direct SATA connection

### General Issues

**"No disks found"**
- Run with sudo/administrator privileges
- Check if disks are properly connected
- Use `python main.py list` to see available disks

## Platform-Specific Notes

### Linux
- **Lite**: Requires `sudo apt-get install hdparm smartmontools`
- **Complete**: Works immediately with bundled tools
- Both require `sudo` for disk access

### Windows
- **Lite**: Requires manual tool installation or winget
- **Complete**: Includes Windows binaries
- Both require "Run as Administrator"

### Android
- **Lite**: Requires root + manual hdparm installation
- **Complete**: Includes ARM binaries for rooted devices
- Both require root access

### macOS
- **Lite**: Use `brew install hdparm smartmontools`
- **Complete**: Includes macOS binaries (x86_64 + Apple Silicon)
- Both may require SIP adjustments for low-level disk access

## Migration Guide

### From Lite to Complete
1. Download Complete Edition
2. Copy any custom configurations
3. Same commands work - no changes needed

### From Complete to Lite
1. Install system tools manually
2. Remove `tools/` directory
3. Verify with `python main.py tools`

## FAQ

**Q: Can I use both editions on the same system?**
A: Yes, they can coexist in different directories.

**Q: Does Complete Edition use bundled tools even if system tools exist?**
A: Yes, bundled tools take priority for consistency.

**Q: Can I add my own tools to Complete Edition?**
A: Yes, add them to the appropriate `tools/platform/arch/` directory.

**Q: Which edition is more secure?**
A: Both are identical in security. Complete Edition reduces attack surface by not requiring internet for tool installation.

**Q: Can I contribute tools to Complete Edition?**
A: Yes! Submit pull requests with properly licensed tool binaries.

---

## Support

- **Documentation**: See `HPA_DCO_DOCUMENTATION.md`
- **Issues**: Report on GitHub
- **Tool Problems**: Run `python main.py tools` for diagnostics

**Choose the edition that fits your needs - both provide the same powerful HPA/DCO detection and removal capabilities!**