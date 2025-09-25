# Building Windows Executable (.exe) for SIH Disk Wipeout

## 🖥️ **Windows Executable Creation**

Since we're currently on Linux, we cannot directly create a Windows .exe file. Here are the instructions to create a Windows executable:

## 📋 **Method 1: Build on Windows Machine**

### **Requirements:**
- Windows 10/11
- Python 3.8+ installed
- All dependencies installed

### **Steps:**

1. **Copy the project to Windows machine**
2. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Create Windows executable:**
   ```cmd
   pyinstaller --onefile --windowed --name "SIH_Disk_Wipeout" --add-data "src;src" --add-data "safety_config.json;." --add-data "requirements.txt;." --add-data "README.md;." --add-data "LICENSE;." --hidden-import tkinter --hidden-import tkinter.ttk --hidden-import tkinter.messagebox --hidden-import tkinter.filedialog --hidden-import psutil --hidden-import reportlab --hidden-import cryptography main.py
   ```

4. **The .exe file will be created in `dist/` folder**

## 📋 **Method 2: Cross-Compilation (Advanced)**

### **Using Wine (Linux to Windows):**
```bash
# Install Wine
sudo apt install wine

# Install Python in Wine
wine python-3.x.x.exe

# Install dependencies in Wine
wine pip install -r requirements.txt
wine pip install pyinstaller

# Build Windows executable
wine pyinstaller --onefile --windowed main.py
```

## 📋 **Method 3: GitHub Actions (Recommended)**

Create a `.github/workflows/build.yml` file:

```yaml
name: Build Executables

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller
    - name: Build Windows executable
      run: |
        pyinstaller --onefile --windowed --name "SIH_Disk_Wipeout" --add-data "src;src" --add-data "safety_config.json;." --add-data "requirements.txt;." --add-data "README.md;." --add-data "LICENSE;." --hidden-import tkinter --hidden-import tkinter.ttk --hidden-import tkinter.messagebox --hidden-import tkinter.filedialog --hidden-import psutil --hidden-import reportlab --hidden-import cryptography main.py
    - name: Upload Windows executable
      uses: actions/upload-artifact@v3
      with:
        name: SIH_Disk_Wipeout_Windows
        path: dist/SIH_Disk_Wipeout.exe
```

## 🎯 **Current Status**

**✅ Available:**
- Linux executable (322MB)
- Windows batch launcher script
- Complete source code

**⏳ Pending:**
- Windows .exe file (requires Windows machine or Wine)

## 📦 **Distribution Package for Windows**

When you have the Windows .exe file, create this package:

```
SIH_Disk_Wipeout_Windows/
├── SIH_Disk_Wipeout.exe          # Main executable
├── run_sih_disk_wipeout.bat      # Windows launcher
├── EXECUTABLE_README.md          # User instructions
├── README.md                     # Full documentation
└── LICENSE                       # Software license
```

## 🚀 **Quick Start for Windows Users**

1. **Download the Windows package**
2. **Extract to a folder**
3. **Double-click `SIH_Disk_Wipeout.exe`** or **`run_sih_disk_wipeout.bat`**
4. **No installation required!**

## ⚠️ **Important Notes**

- **Administrative Rights**: Some operations may require "Run as Administrator"
- **Antivirus**: Some antivirus software may flag the .exe file (false positive)
- **Windows Defender**: May need to add exception for the executable
- **UAC**: User Account Control may prompt for permissions

## 🔧 **Troubleshooting**

### **If .exe doesn't run:**
1. Right-click → "Run as Administrator"
2. Check Windows Defender exclusions
3. Verify all dependencies are included
4. Check Windows version compatibility

### **If GUI doesn't appear:**
1. Try running from Command Prompt
2. Check for error messages
3. Verify tkinter is working
4. Run with `--cli` flag for command line mode
