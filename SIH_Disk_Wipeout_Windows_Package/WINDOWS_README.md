# SIH Disk Wipeout - Windows Package

## 🖥️ **Windows Executable Status**

### **Current Status:**
- ✅ **Linux Executable**: Available (322MB)
- ⏳ **Windows Executable**: Pending (requires Windows machine to build)

### **What's Included:**
- **run_sih_disk_wipeout.bat** - Windows launcher script
- **WINDOWS_BUILD_INSTRUCTIONS.md** - How to create the .exe file
- **EXECUTABLE_README.md** - User instructions
- **README.md** - Full documentation
- **LICENSE** - Software license

## 🚀 **How to Get Windows Executable**

### **Option 1: Build Yourself (Recommended)**
1. **Copy this project to a Windows machine**
2. **Follow instructions in `WINDOWS_BUILD_INSTRUCTIONS.md`**
3. **Run the build command to create the .exe file**

### **Option 2: Use Python Directly**
If you have Python installed on Windows:
```cmd
pip install -r requirements.txt
python main.py
```

### **Option 3: Wait for Pre-built Version**
- Check the GitHub releases for pre-built Windows executables
- Or request a Windows build from the developer

## 📋 **Windows Build Command**

When you have a Windows machine with Python installed:

```cmd
pyinstaller --onefile --windowed --name "SIH_Disk_Wipeout" --add-data "src;src" --add-data "safety_config.json;." --add-data "requirements.txt;." --add-data "README.md;." --add-data "LICENSE;." --hidden-import tkinter --hidden-import tkinter.ttk --hidden-import tkinter.messagebox --hidden-import tkinter.filedialog --hidden-import psutil --hidden-import reportlab --hidden-import cryptography main.py
```

## 🎯 **Expected Result**

After building, you should have:
- **SIH_Disk_Wipeout.exe** (300-400MB)
- **No Python installation required**
- **No dependency management needed**
- **Double-click to run**

## ⚠️ **Windows-Specific Notes**

### **Administrative Rights:**
- Some disk operations require "Run as Administrator"
- Right-click the .exe file → "Run as Administrator"

### **Antivirus Software:**
- Some antivirus may flag the .exe file (false positive)
- Add exception in your antivirus software
- Windows Defender may need exclusion

### **User Account Control (UAC):**
- UAC may prompt for permissions
- This is normal for disk management software

## 🔧 **Troubleshooting**

### **If .exe doesn't run:**
1. **Right-click → "Run as Administrator"**
2. **Check Windows Defender exclusions**
3. **Verify Windows version compatibility**
4. **Try running from Command Prompt**

### **If GUI doesn't appear:**
1. **Run from Command Prompt to see errors**
2. **Check if tkinter is working**
3. **Try command line mode: `SIH_Disk_Wipeout.exe --cli`**

## 📞 **Support**

For Windows-specific issues:
1. Check `WINDOWS_BUILD_INSTRUCTIONS.md`
2. Verify all dependencies are included
3. Ensure Windows version compatibility
4. Contact support with error messages

## 🎉 **Ready When Built!**

Once you have the Windows .exe file, users can:
1. **Download the package**
2. **Double-click `SIH_Disk_Wipeout.exe`**
3. **Start securely wiping disks immediately**

**No Python, no dependencies, no installation required!** 🚀
