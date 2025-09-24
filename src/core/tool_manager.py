"""
Tool Manager for handling bundled and system tools
Supports both Lite and Complete editions
"""

import os
import platform
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class ToolManager:
    """Manages tool detection and path resolution for bundled and system tools"""

    def __init__(self):
        self.system = platform.system().lower()
        self.architecture = self._detect_architecture()
        self.tools_dir = self._get_tools_directory()
        self.is_complete_edition = self._check_complete_edition()

        # Initialize tool paths
        self.tool_paths = {}
        self._initialize_tool_paths()

        logger.info(f"ToolManager initialized - System: {self.system}, "
                   f"Architecture: {self.architecture}, "
                   f"Complete Edition: {self.is_complete_edition}")

    def _detect_architecture(self) -> str:
        """Detect system architecture"""
        arch = platform.machine().lower()
        if arch in ['x86_64', 'amd64']:
            return 'x86_64'
        elif arch in ['i386', 'i686']:
            return 'x86'
        elif arch in ['arm64', 'aarch64']:
            return 'arm64'
        elif arch.startswith('arm'):
            return 'arm'
        else:
            return arch

    def _get_tools_directory(self) -> Optional[Path]:
        """Get the tools directory path"""
        # Check relative to the main script
        script_dir = Path(__file__).parent.parent.parent
        tools_dir = script_dir / "tools"

        if tools_dir.exists():
            return tools_dir

        # Check in current working directory
        cwd_tools = Path.cwd() / "tools"
        if cwd_tools.exists():
            return cwd_tools

        return None

    def _check_complete_edition(self) -> bool:
        """Check if this is the complete edition with bundled tools"""
        return self.tools_dir is not None and self.tools_dir.exists()

    def _initialize_tool_paths(self):
        """Initialize tool paths for the current platform"""
        if self.system == "linux":
            self._init_linux_tools()
        elif self.system == "windows":
            self._init_windows_tools()
        elif self.system == "darwin":  # macOS
            self._init_macos_tools()
        else:
            logger.warning(f"Unsupported system: {self.system}")

    def _init_linux_tools(self):
        """Initialize Linux tool paths"""
        tools = ['hdparm', 'smartctl', 'nvme', 'blkdiscard']

        for tool in tools:
            bundled_path = None
            if self.is_complete_edition:
                bundled_path = self.tools_dir / "linux" / self.architecture / tool
                if not bundled_path.exists():
                    # Fallback to generic linux folder
                    bundled_path = self.tools_dir / "linux" / tool
                    if not bundled_path.exists():
                        bundled_path = None

            self.tool_paths[tool] = {
                'bundled': str(bundled_path) if bundled_path else None,
                'system': tool,  # System command name
                'available': False,
                'path': None
            }

    def _init_windows_tools(self):
        """Initialize Windows tool paths"""
        tools = ['hdparm.exe', 'smartctl.exe']

        for tool in tools:
            bundled_path = None
            if self.is_complete_edition:
                bundled_path = self.tools_dir / "windows" / tool
                if not bundled_path.exists():
                    bundled_path = None

            tool_name = tool.replace('.exe', '')
            self.tool_paths[tool_name] = {
                'bundled': str(bundled_path) if bundled_path else None,
                'system': tool,  # System command name with .exe
                'available': False,
                'path': None
            }

    def _init_macos_tools(self):
        """Initialize macOS tool paths (similar to Linux)"""
        tools = ['hdparm', 'smartctl']

        for tool in tools:
            bundled_path = None
            if self.is_complete_edition:
                bundled_path = self.tools_dir / "macos" / self.architecture / tool
                if not bundled_path.exists():
                    bundled_path = self.tools_dir / "macos" / tool
                    if not bundled_path.exists():
                        bundled_path = None

            self.tool_paths[tool] = {
                'bundled': str(bundled_path) if bundled_path else None,
                'system': tool,
                'available': False,
                'path': None
            }

    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """
        Get the path to a tool, preferring bundled over system

        Returns:
            Path to tool or None if not available
        """
        if tool_name not in self.tool_paths:
            logger.warning(f"Unknown tool: {tool_name}")
            return None

        tool_info = self.tool_paths[tool_name]

        # Return cached path if available
        if tool_info['available'] and tool_info['path']:
            return tool_info['path']

        # Check bundled tool first (Complete Edition)
        if tool_info['bundled']:
            bundled_path = Path(tool_info['bundled'])
            if bundled_path.exists() and os.access(bundled_path, os.X_OK):
                tool_info['available'] = True
                tool_info['path'] = str(bundled_path)
                logger.debug(f"Using bundled {tool_name}: {tool_info['path']}")
                return tool_info['path']

        # Check system tool (Lite Edition or fallback)
        if self._check_system_tool(tool_info['system']):
            tool_info['available'] = True
            tool_info['path'] = tool_info['system']
            logger.debug(f"Using system {tool_name}: {tool_info['path']}")
            return tool_info['path']

        # Tool not available
        logger.debug(f"Tool {tool_name} not available")
        return None

    def _check_system_tool(self, command: str) -> bool:
        """Check if a system tool is available"""
        try:
            if self.system == "windows":
                # Use 'where' command on Windows
                result = subprocess.run(["where", command],
                                      capture_output=True,
                                      text=True,
                                      timeout=5)
            else:
                # Use 'which' command on Unix-like systems
                result = subprocess.run(["which", command],
                                      capture_output=True,
                                      text=True,
                                      timeout=5)

            return result.returncode == 0

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False

    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available (bundled or system)"""
        return self.get_tool_path(tool_name) is not None

    def get_available_tools(self) -> List[str]:
        """Get list of all available tools"""
        available = []
        for tool_name in self.tool_paths:
            if self.is_tool_available(tool_name):
                available.append(tool_name)
        return available

    def get_missing_tools(self) -> List[str]:
        """Get list of missing tools with installation suggestions"""
        missing = []
        for tool_name in self.tool_paths:
            if not self.is_tool_available(tool_name):
                missing.append(tool_name)
        return missing

    def get_tool_info(self) -> Dict:
        """Get comprehensive tool information"""
        info = {
            'system': self.system,
            'architecture': self.architecture,
            'is_complete_edition': self.is_complete_edition,
            'tools_directory': str(self.tools_dir) if self.tools_dir else None,
            'tools': {}
        }

        for tool_name, tool_data in self.tool_paths.items():
            info['tools'][tool_name] = {
                'available': self.is_tool_available(tool_name),
                'path': self.get_tool_path(tool_name),
                'bundled_path': tool_data['bundled'],
                'system_command': tool_data['system']
            }

        return info

    def get_installation_suggestions(self) -> Dict[str, str]:
        """Get installation suggestions for missing tools"""
        suggestions = {}
        missing = self.get_missing_tools()

        if not missing:
            return suggestions

        if self.system == "linux":
            # Detect Linux distribution for specific commands
            distro_commands = {
                'ubuntu': 'sudo apt-get install',
                'debian': 'sudo apt-get install',
                'fedora': 'sudo dnf install',
                'centos': 'sudo yum install',
                'rhel': 'sudo yum install',
                'arch': 'sudo pacman -S',
                'manjaro': 'sudo pacman -S'
            }

            # Default to apt-get
            install_cmd = distro_commands.get('ubuntu', 'sudo apt-get install')

            if 'hdparm' in missing:
                suggestions['hdparm'] = f"{install_cmd} hdparm"
            if 'smartctl' in missing:
                suggestions['smartctl'] = f"{install_cmd} smartmontools"
            if 'nvme' in missing:
                suggestions['nvme'] = f"{install_cmd} nvme-cli"
            if 'blkdiscard' in missing:
                suggestions['blkdiscard'] = f"{install_cmd} util-linux"

        elif self.system == "windows":
            base_msg = "Download from official website or use package manager:"
            if 'hdparm' in missing:
                suggestions['hdparm'] = f"{base_msg} winget install hdparm"
            if 'smartctl' in missing:
                suggestions['smartctl'] = f"{base_msg} winget install smartmontools"

        elif self.system == "darwin":  # macOS
            if 'hdparm' in missing:
                suggestions['hdparm'] = "brew install hdparm"
            if 'smartctl' in missing:
                suggestions['smartctl'] = "brew install smartmontools"

        return suggestions

# Global instance
tool_manager = ToolManager()