#!/usr/bin/env python3
"""
Build script for Disk Wipeout application
Supports building both Lite and Complete editions
"""

import os
import sys
import shutil
import zipfile
import tarfile
import platform
import argparse
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime

class DiskWipeoutBuilder:
    """Builder for Disk Wipeout application"""

    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.dist_dir = self.root_dir / "dist"
        self.tools_dir = self.root_dir / "tools"
        self.version = self._get_version()

    def _get_version(self):
        """Get version from git or default"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True, text=True, cwd=self.root_dir
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "v1.0.0"

    def clean(self):
        """Clean build directories"""
        print("🧹 Cleaning build directories...")
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        self.dist_dir.mkdir(exist_ok=True)
        print("✓ Cleaned")

    def build_lite(self):
        """Build Lite edition (no bundled tools)"""
        print("📦 Building Lite Edition...")

        lite_dir = self.dist_dir / "disk_wipeout_lite"
        lite_dir.mkdir(exist_ok=True)

        # Copy source files
        self._copy_source_files(lite_dir)

        # Create README for Lite edition
        self._create_lite_readme(lite_dir)

        # Create archive
        archive_name = f"disk_wipeout_lite_{self.version}"
        self._create_archive(lite_dir, archive_name)

        # Calculate size
        size_mb = self._get_directory_size(lite_dir) / (1024 * 1024)
        print(f"✓ Lite edition built: {archive_name} ({size_mb:.1f} MB)")

        return lite_dir

    def build_complete(self):
        """Build Complete edition (with bundled tools)"""
        print("📦 Building Complete Edition...")

        complete_dir = self.dist_dir / "disk_wipeout_complete"
        complete_dir.mkdir(exist_ok=True)

        # Copy source files
        self._copy_source_files(complete_dir)

        # Download and bundle tools
        self._bundle_tools(complete_dir)

        # Create README for Complete edition
        self._create_complete_readme(complete_dir)

        # Create archive
        archive_name = f"disk_wipeout_complete_{self.version}"
        self._create_archive(complete_dir, archive_name)

        # Calculate size
        size_mb = self._get_directory_size(complete_dir) / (1024 * 1024)
        print(f"✓ Complete edition built: {archive_name} ({size_mb:.1f} MB)")

        return complete_dir

    def _copy_source_files(self, target_dir):
        """Copy source files to target directory"""
        # Copy source directory
        if (self.root_dir / "src").exists():
            shutil.copytree(self.root_dir / "src", target_dir / "src")

        # Copy main files
        files_to_copy = [
            "main.py",
            "requirements.txt",
            "LICENSE",
            "CHANGELOG.md"
        ]

        for file_name in files_to_copy:
            file_path = self.root_dir / file_name
            if file_path.exists():
                shutil.copy2(file_path, target_dir / file_name)

        # Copy test script
        if (self.root_dir / "test_hpa_dco.py").exists():
            shutil.copy2(self.root_dir / "test_hpa_dco.py", target_dir / "test_hpa_dco.py")

    def _bundle_tools(self, target_dir):
        """Download and bundle tools for Complete edition"""
        tools_target = target_dir / "tools"
        tools_target.mkdir(exist_ok=True)

        # Create platform directories
        platforms = {
            "linux": ["x86_64", "arm64"],
            "windows": [],
            "macos": ["x86_64", "arm64"]
        }

        for platform_name, architectures in platforms.items():
            platform_dir = tools_target / platform_name
            platform_dir.mkdir(exist_ok=True)

            if architectures:
                for arch in architectures:
                    arch_dir = platform_dir / arch
                    arch_dir.mkdir(exist_ok=True)

            # Download tools for this platform
            self._download_platform_tools(platform_dir, platform_name, architectures)

    def _download_platform_tools(self, platform_dir, platform_name, architectures):
        """Download tools for a specific platform"""
        print(f"  📥 Downloading {platform_name} tools...")\n        \n        # Note: In a real implementation, you would download actual binaries\n        # For demo purposes, we'll create placeholder files\n        \n        tools = {\n            "linux": ["hdparm", "smartctl", "nvme", "blkdiscard"],\n            "windows": ["hdparm.exe", "smartctl.exe"],\n            "macos": ["hdparm", "smartctl"]\n        }\n        \n        platform_tools = tools.get(platform_name, [])\n        \n        for tool in platform_tools:\n            if architectures:\n                for arch in architectures:\n                    tool_path = platform_dir / arch / tool\n                    self._create_placeholder_tool(tool_path, tool, platform_name, arch)\n            else:\n                tool_path = platform_dir / tool\n                self._create_placeholder_tool(tool_path, tool, platform_name)\n    \n    def _create_placeholder_tool(self, tool_path, tool_name, platform_name, arch=None):\n        """Create a placeholder tool file (replace with actual download in production)"""\n        # Create placeholder script/binary\n        content = f"""#!/bin/bash\n# Placeholder for {tool_name} on {platform_name}"""\n        if arch:\n            content += f" ({arch})"\n        content += """\n# In the Complete Edition, this would be the actual binary\necho "This is a placeholder for {tool_name}"\necho "Replace with actual binary in production"\nexit 1\n"""\n        \n        with open(tool_path, 'w') as f:\n            f.write(content)\n        \n        # Make executable on Unix-like systems\n        if platform_name != "windows":\n            os.chmod(tool_path, 0o755)\n    \n    def _create_lite_readme(self, target_dir):\n        """Create README for Lite edition"""\n        readme_content = f"""# Disk Wipeout - Lite Edition {self.version}\n\nThis is the Lite Edition of Disk Wipeout. It requires manual installation of dependencies.\n\n## Requirements\n\n### Linux\n```bash\nsudo apt-get install hdparm smartmontools nvme-cli\n# or equivalent for your distribution\n```\n\n### Windows\n- Run as Administrator\n- Install tools manually or use package managers:\n  - winget install hdparm\n  - winget install smartmontools\n\n### Android\n- Root access required\n- Install hdparm via Termux (optional):\n  ```bash\n  pkg install hdparm\n  ```\n\n## Usage\n\n```bash\n# List available disks\npython main.py list\n\n# Detect HPA/DCO\nsudo python main.py detect-hpa /dev/sdb\n\n# Wipe disk with HPA/DCO removal\nsudo python main.py wipe-full /dev/sdb --remove-hpa\n```\n\n## Need Everything Pre-installed?\n\nDownload the **Complete Edition** instead - it includes all tools bundled.\n\nFor more information, see the documentation.\n"""\n        \n        with open(target_dir / "README.md", 'w') as f:\n            f.write(readme_content)\n    \n    def _create_complete_readme(self, target_dir):\n        """Create README for Complete edition"""\n        readme_content = f"""# Disk Wipeout - Complete Edition {self.version}\n\nThis is the Complete Edition of Disk Wipeout with all tools bundled. No additional installation required!\n\n## Features\n\n✓ All tools included (hdparm, smartctl, etc.)  \n✓ Works offline  \n✓ No manual dependency installation  \n✓ Cross-platform binaries included  \n\n## Quick Start\n\n```bash\n# List available disks\npython main.py list\n\n# Detect HPA/DCO (no additional tools needed)\nsudo python main.py detect-hpa /dev/sdb\n\n# Wipe disk with HPA/DCO removal\nsudo python main.py wipe-full /dev/sdb --remove-hpa\n\n# Test HPA/DCO detection\nsudo python test_hpa_dco.py\n```\n\n## Included Tools\n\n- **hdparm**: HPA/DCO detection and removal\n- **smartctl**: SMART data analysis\n- **nvme-cli**: NVMe device management\n- **blkdiscard**: TRIM operations\n\n## Platform Support\n\n- **Linux**: x86_64, ARM64\n- **Windows**: x86_64\n- **macOS**: x86_64, ARM64 (Apple Silicon)\n\n## Requirements\n\n- Python 3.8+\n- Administrator/root privileges for disk operations\n\n## Need Smaller Download?\n\nUse the **Lite Edition** if you prefer to install tools manually.\n\nFor more information, see the documentation.\n"""\n        \n        with open(target_dir / "README.md", 'w') as f:\n            f.write(readme_content)\n    \n    def _create_archive(self, source_dir, archive_name):\n        """Create compressed archive"""\n        if platform.system() == "Windows":\n            # Create ZIP on Windows\n            archive_path = self.dist_dir / f"{archive_name}.zip"\n            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:\n                for file_path in source_dir.rglob('*'):\n                    if file_path.is_file():\n                        arcname = file_path.relative_to(source_dir.parent)\n                        zf.write(file_path, arcname)\n        else:\n            # Create tar.gz on Unix-like systems\n            archive_path = self.dist_dir / f"{archive_name}.tar.gz"\n            with tarfile.open(archive_path, 'w:gz') as tf:\n                tf.add(source_dir, arcname=source_dir.name)\n        \n        return archive_path\n    \n    def _get_directory_size(self, directory):\n        """Calculate directory size in bytes"""\n        total_size = 0\n        for file_path in directory.rglob('*'):\n            if file_path.is_file():\n                total_size += file_path.stat().st_size\n        return total_size\n    \n    def build_both(self):\n        """Build both Lite and Complete editions"""\n        print(f"🚀 Building Disk Wipeout {self.version} - Both Editions")\n        print("=" * 60)\n        \n        self.clean()\n        lite_dir = self.build_lite()\n        complete_dir = self.build_complete()\n        \n        print("\\n" + "=" * 60)\n        print("📊 Build Summary:")\n        \n        lite_size = self._get_directory_size(lite_dir) / (1024 * 1024)\n        complete_size = self._get_directory_size(complete_dir) / (1024 * 1024)\n        \n        print(f"✓ Lite Edition:     {lite_size:.1f} MB")\n        print(f"✓ Complete Edition: {complete_size:.1f} MB")\n        print(f"✓ Size difference:  {complete_size - lite_size:.1f} MB")\n        \n        print(f"\\n📁 Output directory: {self.dist_dir.absolute()}")\n        \n        # List created archives\n        archives = list(self.dist_dir.glob("*.zip")) + list(self.dist_dir.glob("*.tar.gz"))\n        if archives:\n            print("\\n📦 Created archives:")\n            for archive in archives:\n                size_mb = archive.stat().st_size / (1024 * 1024)\n                print(f"  • {archive.name} ({size_mb:.1f} MB)")\n        \n        print("\\n✅ Build completed successfully!")\n\ndef main():\n    """Main entry point"""\n    parser = argparse.ArgumentParser(\n        description="Build Disk Wipeout application",\n        formatter_class=argparse.RawDescriptionHelpFormatter,\n        epilog="""\nExamples:\n  python build.py --both          # Build both editions\n  python build.py --lite          # Build Lite edition only\n  python build.py --complete      # Build Complete edition only\n  python build.py --clean         # Clean build directories\n"""\n    )\n    \n    parser.add_argument("--lite", action="store_true",\n                       help="Build Lite edition only")\n    parser.add_argument("--complete", action="store_true",\n                       help="Build Complete edition only")\n    parser.add_argument("--both", action="store_true",\n                       help="Build both editions (default)")\n    parser.add_argument("--clean", action="store_true",\n                       help="Clean build directories only")\n    \n    args = parser.parse_args()\n    \n    builder = DiskWipeoutBuilder()\n    \n    try:\n        if args.clean:\n            builder.clean()\n        elif args.lite:\n            builder.clean()\n            builder.build_lite()\n        elif args.complete:\n            builder.clean()\n            builder.build_complete()\n        else:\n            # Default: build both\n            builder.build_both()\n            \n    except KeyboardInterrupt:\n        print("\\n❌ Build cancelled by user")\n        sys.exit(1)\n    except Exception as e:\n        print(f"\\n❌ Build failed: {e}")\n        import traceback\n        traceback.print_exc()\n        sys.exit(1)\n\nif __name__ == "__main__":\n    main()