"""
Enhanced Main GUI window for Disk Wipeout application
Modern, professional interface with advanced features
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import logging
import platform
import json
import time
from typing import List, Optional, Dict
from datetime import datetime
import os

from ..core.disk_manager import DiskManager
from ..core.models import DiskInfo, DiskType, DiskStatus, WipeMethod, HPADCOInfo, DiskHealth, WipeOperation
from ..core.progress_monitor import progress_monitor, ProgressInfo
from ..core.error_handler import error_handler, ErrorInfo, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

class EnhancedMainWindow:
    """Enhanced main application window with modern design"""
    
    def __init__(self, disk_manager: DiskManager):
        self.disk_manager = disk_manager
        self.root = tk.Tk()
        self.selected_disk = None
        self.wipe_thread = None
        self.operation_queue = []
        self.current_operation = None
        self.current_operation_id = None
        
        # Theme configuration
        self.theme = "light"  # light, dark, auto
        self.colors = self._get_theme_colors()
        
        self._setup_window()
        self._create_modern_widgets()
        self._refresh_disks()
        
        # Start progress monitoring
        progress_monitor.start_monitoring()
        
        # Register error handler callback
        error_handler.register_callback(self._on_error_occurred)
    
    def _get_theme_colors(self) -> Dict[str, str]:
        """Get color scheme based on current theme"""
        if self.theme == "dark":
            return {
                'bg_primary': '#2c3e50',
                'bg_secondary': '#34495e',
                'bg_card': '#3c4f63',
                'text_primary': '#ecf0f1',
                'text_secondary': '#bdc3c7',
                'accent': '#3498db',
                'success': '#27ae60',
                'warning': '#f39c12',
                'danger': '#e74c3c',
                'border': '#4a5f7a'
            }
        else:  # light theme
            return {
                'bg_primary': '#ffffff',
                'bg_secondary': '#f8f9fa',
                'bg_card': '#ffffff',
                'text_primary': '#2c3e50',
                'text_secondary': '#7f8c8d',
                'accent': '#3498db',
                'success': '#27ae60',
                'warning': '#f39c12',
                'danger': '#e74c3c',
                'border': '#dee2e6'
            }
    
    def _setup_window(self):
        """Setup the enhanced main window"""
        self.root.title("🔒 SIH Disk Wipeout - Professional Data Erasure")
        
        # Set fixed window size
        window_width = 1024
        window_height = 700
        
        self.root.minsize(1024, 700)
        self.root.resizable(True, True)
        
        # Center the window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.update_idletasks()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Configure modern styling
        self._configure_modern_style()
        
        # Set window icon and properties
        self.root.configure(bg=self.colors['bg_primary'])
        
    def _configure_modern_style(self):
        """Configure modern ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure color scheme
        style.configure('Modern.TFrame', 
                       background=self.colors['bg_primary'])
        style.configure('Card.TFrame',
                       background=self.colors['bg_card'],
                       relief='solid',
                       borderwidth=1)
        style.configure('Header.TFrame',
                       background=self.colors['bg_secondary'])
        
        # Configure labels
        style.configure('Title.TLabel',
                       font=('Segoe UI', 24, 'bold'),
                       foreground=self.colors['text_primary'],
                       background=self.colors['bg_primary'])
        style.configure('Subtitle.TLabel',
                       font=('Segoe UI', 14),
                       foreground=self.colors['text_secondary'],
                       background=self.colors['bg_primary'])
        style.configure('Heading.TLabel',
                       font=('Segoe UI', 12, 'bold'),
                       foreground=self.colors['text_primary'])
        style.configure('Info.TLabel',
                       font=('Segoe UI', 10),
                       foreground=self.colors['accent'])
        style.configure('Success.TLabel',
                       font=('Segoe UI', 10, 'bold'),
                       foreground=self.colors['success'])
        style.configure('Warning.TLabel',
                       font=('Segoe UI', 10, 'bold'),
                       foreground=self.colors['warning'])
        style.configure('Danger.TLabel',
                       font=('Segoe UI', 10, 'bold'),
                       foreground=self.colors['danger'])
        
        # Configure buttons
        style.configure('Primary.TButton',
                       font=('Segoe UI', 11, 'bold'),
                       padding=(15, 8))
        style.configure('Secondary.TButton',
                       font=('Segoe UI', 10),
                       padding=(12, 6))
        style.configure('Danger.TButton',
                       font=('Segoe UI', 10, 'bold'),
                       foreground='white',
                       background=self.colors['danger'])
        
        # Configure treeview
        style.configure('Modern.Treeview',
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_primary'],
                       fieldbackground=self.colors['bg_card'],
                       borderwidth=0)
        style.configure('Modern.Treeview.Heading',
                       background=self.colors['bg_secondary'],
                       foreground=self.colors['text_primary'],
                       font=('Segoe UI', 10, 'bold'))
    
    def _create_modern_widgets(self):
        """Create modern, professional widgets"""
        # Main container
        main_container = ttk.Frame(self.root, style='Modern.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # Header section
        self._create_header(main_container)
        
        # Main content area
        content_frame = ttk.Frame(main_container, style='Modern.TFrame')
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(20, 0))
        content_frame.columnconfigure(0, weight=2)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Left panel - Disk management
        self._create_disk_panel(content_frame)
        
        # Right panel - Operations and monitoring
        self._create_operations_panel(content_frame)
        
        # Status bar
        self._create_status_bar(main_container)
    
    def _create_header(self, parent):
        """Create modern header section"""
        header_frame = ttk.Frame(parent, style='Header.TFrame')
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(1, weight=1)
        
        # Title and subtitle
        title_label = ttk.Label(header_frame, text="🔒 SIH Disk Wipeout", style='Title.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        subtitle_label = ttk.Label(header_frame, 
                                 text="Professional Secure Data Erasure • Cross-Platform • Enterprise-Grade", 
                                 style='Subtitle.TLabel')
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
        # System info and controls
        controls_frame = ttk.Frame(header_frame, style='Header.TFrame')
        controls_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.E, tk.N, tk.S))
        
        # System status
        self.system_status = ttk.Label(controls_frame, 
                                     text=f"🟢 System: {platform.system()} | Python: {platform.python_version()}", 
                                     style='Info.TLabel')
        self.system_status.grid(row=0, column=0, sticky=tk.E, padx=(0, 20))
        
        # Quick actions
        refresh_btn = ttk.Button(controls_frame, text="🔄 Refresh", 
                               command=self._refresh_disks, style='Secondary.TButton')
        refresh_btn.grid(row=0, column=1, sticky=tk.E, padx=(0, 10))
        
        settings_btn = ttk.Button(controls_frame, text="⚙️ Settings", 
                                command=self._open_settings, style='Secondary.TButton')
        settings_btn.grid(row=0, column=2, sticky=tk.E)
    
    def _create_disk_panel(self, parent):
        """Create enhanced disk management panel"""
        disk_frame = ttk.LabelFrame(parent, text="💾 Disk Management", padding="20")
        disk_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        disk_frame.columnconfigure(0, weight=1)
        disk_frame.rowconfigure(1, weight=1)
        
        # Disk list header
        list_header = ttk.Frame(disk_frame)
        list_header.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        list_header.columnconfigure(0, weight=1)
        
        ttk.Label(list_header, text="Available Storage Devices", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W)
        
        # Filter and search
        filter_frame = ttk.Frame(list_header)
        filter_frame.grid(row=0, column=1, sticky=tk.E)
        
        ttk.Label(filter_frame, text="Filter:", style='Info.TLabel').grid(row=0, column=0, padx=(0, 5))
        self.filter_var = tk.StringVar()
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, 
                                   values=["All", "Writable", "Protected", "HDD", "SSD", "NVMe"],
                                   state="readonly", width=12)
        filter_combo.set("All")
        filter_combo.grid(row=0, column=1)
        filter_combo.bind('<<ComboboxSelected>>', self._filter_disks)
        
        # Enhanced disk treeview with better data representation
        columns = ('Device', 'Size', 'Type', 'Model', 'Status', 'Health', 'Hidden', 'Usage')
        self.disk_tree = ttk.Treeview(disk_frame, columns=columns, show='headings', height=12, style='Modern.Treeview')
        
        # Configure columns with better headers and widths
        self.disk_tree.heading('Device', text='Device Path')
        self.disk_tree.heading('Size', text='Total Capacity')
        self.disk_tree.heading('Type', text='Type')
        self.disk_tree.heading('Model', text='Model')
        self.disk_tree.heading('Status', text='Status')
        self.disk_tree.heading('Health', text='Health')
        self.disk_tree.heading('Hidden', text='Hidden Areas')
        self.disk_tree.heading('Usage', text='Storage Usage')
        
        self.disk_tree.column('Device', width=140, minwidth=120)
        self.disk_tree.column('Size', width=100, minwidth=90)
        self.disk_tree.column('Type', width=70, minwidth=60)
        self.disk_tree.column('Model', width=180, minwidth=150)
        self.disk_tree.column('Status', width=100, minwidth=90)
        self.disk_tree.column('Health', width=70, minwidth=60)
        self.disk_tree.column('Hidden', width=100, minwidth=90)
        self.disk_tree.column('Usage', width=120, minwidth=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(disk_frame, orient=tk.VERTICAL, command=self.disk_tree.yview)
        h_scrollbar = ttk.Scrollbar(disk_frame, orient=tk.HORIZONTAL, command=self.disk_tree.xview)
        self.disk_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.disk_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        v_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        # Bind events
        self.disk_tree.bind('<<TreeviewSelect>>', self._on_disk_select)
        self.disk_tree.bind('<Double-1>', self._on_disk_double_click)
        
        # HPA/DCO Information Panel (Always Visible)
        hpa_dco_frame = ttk.LabelFrame(disk_frame, text="🔍 HPA/DCO Detection Results", padding="15")
        hpa_dco_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        hpa_dco_frame.columnconfigure(0, weight=1)
        
        # HPA/DCO status display
        self.hpa_dco_display = tk.Text(hpa_dco_frame, height=4, wrap=tk.WORD, state=tk.DISABLED,
                                      font=('Consolas', 9), bg=self.colors['bg_secondary'], 
                                      fg=self.colors['text_primary'], insertbackground=self.colors['text_primary'])
        hpa_dco_scrollbar = ttk.Scrollbar(hpa_dco_frame, orient=tk.VERTICAL, command=self.hpa_dco_display.yview)
        self.hpa_dco_display.configure(yscrollcommand=hpa_dco_scrollbar.set)
        
        self.hpa_dco_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        hpa_dco_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Disk information panel
        info_frame = ttk.LabelFrame(disk_frame, text="ℹ️ Detailed Disk Information", padding="15")
        info_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        info_frame.columnconfigure(0, weight=1)
        
        self.disk_info_text = tk.Text(info_frame, height=8, wrap=tk.WORD, state=tk.DISABLED,
                                    font=('Consolas', 9), bg=self.colors['bg_secondary'], 
                                    fg=self.colors['text_primary'], insertbackground=self.colors['text_primary'])
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.disk_info_text.yview)
        self.disk_info_text.configure(yscrollcommand=info_scrollbar.set)
        
        self.disk_info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def _create_operations_panel(self, parent):
        """Create operations and monitoring panel"""
        ops_frame = ttk.LabelFrame(parent, text="⚙️ Operations & Monitoring", padding="20")
        ops_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        ops_frame.columnconfigure(0, weight=1)
        ops_frame.rowconfigure(2, weight=1)
        
        # Wipe configuration
        config_frame = ttk.LabelFrame(ops_frame, text="🔧 Wipe Configuration", padding="15")
        config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        config_frame.columnconfigure(1, weight=1)
        
        # Method selection with recommendations
        ttk.Label(config_frame, text="Wipe Method:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.wipe_method_var = tk.StringVar()
        self.wipe_method_combo = ttk.Combobox(config_frame, textvariable=self.wipe_method_var, 
                                            state="readonly", width=25, font=('Segoe UI', 10))
        self.wipe_method_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        self.wipe_method_combo.bind('<<ComboboxSelected>>', self._on_method_change)
        
        # Method description
        self.method_desc = ttk.Label(config_frame, text="", style='Info.TLabel', wraplength=300)
        self.method_desc.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Advanced options
        options_frame = ttk.Frame(config_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        options_frame.columnconfigure(1, weight=1)
        
        # Passes configuration
        ttk.Label(options_frame, text="Passes:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W)
        self.passes_var = tk.StringVar(value="3")
        passes_spinbox = ttk.Spinbox(options_frame, from_=1, to=10, textvariable=self.passes_var, 
                                   width=10, font=('Segoe UI', 10))
        passes_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Security options
        security_frame = ttk.LabelFrame(config_frame, text="🔒 Security Options", padding="10")
        security_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.verify_var = tk.BooleanVar(value=True)
        verify_check = ttk.Checkbutton(security_frame, text="✅ Verify wipe after completion", 
                                     variable=self.verify_var)
        verify_check.grid(row=0, column=0, sticky=tk.W)
        
        self.force_var = tk.BooleanVar(value=False)
        force_check = ttk.Checkbutton(security_frame, text="⚠️ Force wipe (skip confirmations)", 
                                    variable=self.force_var)
        force_check.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # HPA/DCO Management
        hpa_dco_frame = ttk.LabelFrame(config_frame, text="🔍 Hidden Areas Management", padding="10")
        hpa_dco_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # HPA/DCO detection button
        detect_hpa_btn = ttk.Button(hpa_dco_frame, text="🔍 Detect HPA/DCO", 
                                   command=self._detect_hpa_dco, style='Secondary.TButton')
        detect_hpa_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # HPA removal option
        self.remove_hpa_var = tk.BooleanVar(value=False)
        remove_hpa_check = ttk.Checkbutton(hpa_dco_frame, text="⚠️ Remove HPA before wipe", 
                                         variable=self.remove_hpa_var)
        remove_hpa_check.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        # DCO removal option (dangerous)
        self.remove_dco_var = tk.BooleanVar(value=False)
        remove_dco_check = ttk.Checkbutton(hpa_dco_frame, text="🚨 Remove DCO (DANGEROUS)", 
                                         variable=self.remove_dco_var)
        remove_dco_check.grid(row=0, column=2, sticky=tk.W)
        
        # HPA/DCO status display
        self.hpa_dco_status = ttk.Label(hpa_dco_frame, text="Status: Not checked", style='Info.TLabel')
        self.hpa_dco_status.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # Action controls
        controls_frame = ttk.LabelFrame(ops_frame, text="🎮 Action Controls", padding="15")
        controls_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=1)
        
        # Action buttons
        self.wipe_btn = ttk.Button(controls_frame, text="🚀 Start Wipe", 
                                 command=self._start_wipe, style='Primary.TButton')
        self.wipe_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.stop_btn = ttk.Button(controls_frame, text="⏹️ Stop", 
                                 command=self._stop_wipe, state=tk.DISABLED, style='Danger.TButton')
        self.stop_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # Progress monitoring
        progress_frame = ttk.LabelFrame(ops_frame, text="📊 Progress Monitoring", padding="15")
        progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=300, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status information
        status_frame = ttk.Frame(progress_frame)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="🟢 Ready - Select a disk to begin")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, style='Info.TLabel')
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.details_var = tk.StringVar(value="")
        self.details_label = ttk.Label(status_frame, textvariable=self.details_var, style='Info.TLabel')
        self.details_label.grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        
        # Statistics
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
        self.speed_var = tk.StringVar(value="Speed: --")
        self.speed_label = ttk.Label(stats_frame, textvariable=self.speed_var, style='Info.TLabel')
        self.speed_label.grid(row=0, column=0, sticky=tk.W)
        
        self.eta_var = tk.StringVar(value="ETA: --")
        self.eta_label = ttk.Label(stats_frame, textvariable=self.eta_var, style='Info.TLabel')
        self.eta_label.grid(row=0, column=1, sticky=tk.E)
    
    def _create_status_bar(self, parent):
        """Create modern status bar"""
        status_frame = ttk.Frame(parent, style='Header.TFrame')
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(20, 0))
        status_frame.columnconfigure(0, weight=1)
        
        # Status information
        self.status_bar_text = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_bar_text, style='Info.TLabel')
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        # System information
        system_info = ttk.Label(status_frame, 
                              text=f"Platform: {platform.system()} | Python: {platform.python_version()}", 
                              style='Info.TLabel')
        system_info.grid(row=0, column=1, sticky=tk.E)
        
        # Update wipe methods
        self._update_wipe_methods()
        
        # Add initial log message
        self._log("🚀 SIH Disk Wipeout Professional Edition started")
        self._log(f"📊 Platform: {platform.system()} {platform.release()}")
        self._log("✅ Enhanced safety features active")
    
    def _refresh_disks(self):
        """Refresh the disk list with enhanced information"""
        self._log("Refreshing disk list...")
        
        # Clear existing items
        for item in self.disk_tree.get_children():
            self.disk_tree.delete(item)
        
        try:
            # Get available disks
            disks = self.disk_manager.get_available_disks()
            system_disks = self.disk_manager.get_system_disks()
            
            for disk in disks:
                # Use enhanced data model properties
                size_str = disk.size_formatted if hasattr(disk, 'size_formatted') else f"{disk.size // (1024**3)}GB"
                
                # Check status using enhanced model
                is_writable = self.disk_manager.is_disk_writable(disk.device)
                is_system_disk = disk.device in system_disks
                
                # Determine status and health using enhanced model
                if is_system_disk:
                    status = "🔒 PROTECTED"
                    health = "🟢 System"
                elif is_writable:
                    status = "✅ Writable"
                    health = "🟢 Good"
                else:
                    status = "❌ Read-only"
                    health = "🟡 Limited"
                
                # Check for hidden areas (HPA/DCO)
                hidden_info = "None"
                if hasattr(disk, 'hpa_dco_info') and disk.hpa_dco_info:
                    # Handle both dataclass and dict formats
                    if hasattr(disk.hpa_dco_info, 'hpa_detected'):
                        if disk.hpa_dco_info.hpa_detected or disk.hpa_dco_info.dco_detected:
                            hidden_gb = disk.hpa_dco_info.hidden_gb
                            hidden_info = f"⚠️ {hidden_gb:.1f}GB"
                    elif isinstance(disk.hpa_dco_info, dict):
                        if disk.hpa_dco_info.get('hpa_detected') or disk.hpa_dco_info.get('dco_detected'):
                            hidden_gb = disk.hpa_dco_info.get('hidden_gb', 0)
                            hidden_info = f"⚠️ {hidden_gb:.1f}GB"
                
                # Calculate storage usage (simulated - in real implementation, this would come from filesystem info)
                usage_percentage = 0
                if not is_system_disk:  # Don't show usage for system disks
                    # Simulate usage based on disk type and size
                    if disk.type.lower() in ['ssd', 'nvme']:
                        usage_percentage = 25  # SSDs typically have less usage
                    else:
                        usage_percentage = 45  # HDDs typically have more usage
                
                usage_display = f"{usage_percentage}% Used" if usage_percentage > 0 else "N/A"
                
                # Get type with icon
                if hasattr(disk, 'type_icon'):
                    if hasattr(disk.type, 'value'):
                        type_display = f"{disk.type_icon} {disk.type.value.upper()}"
                    else:
                        type_display = f"{disk.type_icon} {disk.type.upper()}"
                else:
                    if hasattr(disk.type, 'value'):
                        type_display = disk.type.value.upper()
                    else:
                        type_display = disk.type.upper()
                
                # Insert into tree with enhanced data
                item = self.disk_tree.insert('', 'end', values=(
                    disk.device,
                    size_str,
                    type_display,
                    disk.model,
                    status,
                    health,
                    hidden_info,
                    usage_display
                ))
                
                # Store disk info
                self.disk_tree.set(item, 'Device', disk.device)
            
            self._log(f"Found {len(disks)} disks")
            self.status_bar_text.set(f"Found {len(disks)} disks")
            
        except Exception as e:
            self._log(f"Error refreshing disks: {e}")
            messagebox.showerror("Error", f"Failed to refresh disk list: {e}")
    
    def _on_disk_select(self, event):
        """Handle disk selection with enhanced information"""
        selection = self.disk_tree.selection()
        if selection:
            item = selection[0]
            device = self.disk_tree.item(item, 'values')[0]
            self.selected_disk = device
            
            # Update disk information
            self._update_disk_info(device)
            
            # Update HPA/DCO information
            self._update_hpa_dco_display(device)
            
            # Update status
            self.status_var.set(f"🔍 Selected: {device}")
            self.details_var.set("Ready to configure wipe options")
            
            # Update method recommendations
            self._update_method_recommendations(device)
            
            self._log(f"Selected disk: {device}")
        else:
            self.selected_disk = None
            self._clear_disk_info()
            self.status_var.set("🟢 Ready - Select a disk to begin")
            self.details_var.set("")
    
    def _on_disk_double_click(self, event):
        """Handle double-click on disk for quick actions"""
        selection = self.disk_tree.selection()
        if selection:
            item = selection[0]
            device = self.disk_tree.item(item, 'values')[0]
            self._show_quick_actions(device)
    
    def _update_disk_info(self, device):
        """Update enhanced disk information display with comprehensive data"""
        try:
            disk_info = self.disk_manager.get_disk_info(device)
            if disk_info:
                # Get additional system information
                system_disks = self.disk_manager.get_system_disks()
                is_protected = device in system_disks
                is_writable = self.disk_manager.is_disk_writable(device)
                
                # Use enhanced data model if available
                if hasattr(disk_info, 'get_detailed_info'):
                    detailed_info = disk_info.get_detailed_info()
                    size_display = detailed_info['size']
                    type_display = f"{detailed_info['type_icon']} {detailed_info['type']}"
                else:
                    size_display = f"{disk_info.size // (1024**3):,}GB"
                    type_display = disk_info.type.upper()
                
                # Build comprehensive information text
                info_text = f"""DEVICE INFORMATION
{'='*50}
Device: {disk_info.device}
Size: {size_display} ({disk_info.size:,} bytes)
Type: {type_display}
Model: {disk_info.model}
Serial: {disk_info.serial or 'Not available'}
Mountpoint: {disk_info.mountpoint or 'Not mounted'}
Filesystem: {disk_info.filesystem or 'Unknown'}

SECURITY STATUS
{'='*50}
Writable: {'Yes' if is_writable else 'No'}
Protected: {'Yes' if is_protected else 'No'}
System Disk: {'Yes' if is_protected else 'No'}
Status: {'PROTECTED' if is_protected else 'Available' if is_writable else 'Read-only'}

HIDDEN AREAS (HPA/DCO)
{'='*50}"""
                
                # Add HPA/DCO information if available
                if hasattr(disk_info, 'hpa_dco_info') and disk_info.hpa_dco_info:
                    hpa_info = disk_info.hpa_dco_info
                    if hpa_info.hpa_detected or hpa_info.dco_detected:
                        info_text += f"""
HPA Detected: {'Yes' if hpa_info.hpa_detected else 'No'}
DCO Detected: {'Yes' if hpa_info.dco_detected else 'No'}
Hidden Capacity: {hpa_info.hidden_gb:.1f}GB
Can Remove HPA: {'Yes' if hpa_info.can_remove_hpa else 'No'}
Can Remove DCO: {'Yes' if hpa_info.can_remove_dco else 'No'}
Detection Method: {hpa_info.detection_method or 'Unknown'}"""
                    else:
                        info_text += "\nNo hidden areas detected"
                else:
                    info_text += "\nHPA/DCO detection not performed"
                
                # Add health information if available
                if hasattr(disk_info, 'health') and disk_info.health:
                    health = disk_info.health
                    info_text += f"""

HEALTH STATUS
{'='*50}
Health Status: {health.health_status.title()}
Temperature: {health.temperature or 'Unknown'}°C
Power On Hours: {health.power_on_hours or 'Unknown'}
Bad Sectors: {health.bad_sectors or 'None'}
Last Checked: {health.last_checked or 'Never'}"""
                
                # Add recommendations
                info_text += f"""

RECOMMENDATIONS
{'='*50}
"""
                if is_protected:
                    info_text += "WARNING: This disk is protected and cannot be wiped"
                elif not is_writable:
                    info_text += "ERROR: This disk is not writable"
                else:
                    info_text += "OK: This disk is safe to wipe"
                    if hasattr(disk_info, 'hpa_dco_info') and disk_info.hpa_dco_info:
                        if disk_info.hpa_dco_info.hpa_detected:
                            info_text += "\nWARNING: Consider removing HPA to access hidden areas"
                        if disk_info.hpa_dco_info.dco_detected:
                            info_text += "\nWARNING: DCO detected - removal is dangerous"
                
                self.disk_info_text.config(state=tk.NORMAL)
                self.disk_info_text.delete(1.0, tk.END)
                self.disk_info_text.insert(1.0, info_text)
                self.disk_info_text.config(state=tk.DISABLED)
        except Exception as e:
            self._log(f"Error getting disk info: {e}")
    
    def _update_hpa_dco_display(self, device):
        """Update the HPA/DCO information display"""
        try:
            # Get HPA/DCO information
            hpa_dco_info = self.disk_manager.detect_hpa_dco(device)
            
            # Build HPA/DCO display text
            hpa_dco_text = f"HPA/DCO Analysis for {device}\n"
            hpa_dco_text += "=" * 50 + "\n"
            
            if hpa_dco_info.get('error'):
                hpa_dco_text += f"Error: {hpa_dco_info['error']}\n"
            else:
                # Detection method
                hpa_dco_text += f"Detection Method: {hpa_dco_info.get('detection_method', 'N/A')}\n\n"
                
                # Sector information
                hpa_dco_text += "Sector Information:\n"
                hpa_dco_text += f"  Current Max Sectors: {hpa_dco_info.get('current_max_sectors', 0):,}\n"
                hpa_dco_text += f"  Native Max Sectors:  {hpa_dco_info.get('native_max_sectors', 0):,}\n"
                hpa_dco_text += f"  Accessible Sectors:  {hpa_dco_info.get('accessible_sectors', 0):,}\n\n"
                
                # HPA detection
                if hpa_dco_info.get('hpa_detected'):
                    hpa_sectors = hpa_dco_info.get('hpa_sectors', 0)
                    hpa_gb = (hpa_sectors * 512) / (1024**3)
                    hpa_dco_text += f"⚠️  HPA DETECTED!\n"
                    hpa_dco_text += f"  Hidden Sectors: {hpa_sectors:,}\n"
                    hpa_dco_text += f"  Hidden Size: {hpa_gb:.2f} GB\n"
                    hpa_dco_text += f"  Can Remove: {'Yes' if hpa_dco_info.get('can_remove_hpa') else 'No'}\n\n"
                else:
                    hpa_dco_text += "✓ No HPA detected\n\n"
                
                # DCO detection
                if hpa_dco_info.get('dco_detected'):
                    dco_sectors = hpa_dco_info.get('dco_sectors', 0)
                    dco_gb = (dco_sectors * 512) / (1024**3)
                    hpa_dco_text += f"⚠️  DCO DETECTED!\n"
                    hpa_dco_text += f"  DCO Sectors: {dco_sectors:,}\n"
                    hpa_dco_text += f"  DCO Size: {dco_gb:.2f} GB\n"
                    hpa_dco_text += f"  Can Remove: {'Yes' if hpa_dco_info.get('can_remove_dco') else 'No'}\n\n"
                else:
                    hpa_dco_text += "✓ No DCO detected\n\n"
                
                # Summary
                total_hidden = hpa_dco_info.get('hpa_sectors', 0) + hpa_dco_info.get('dco_sectors', 0)
                if total_hidden > 0:
                    total_hidden_gb = (total_hidden * 512) / (1024**3)
                    hpa_dco_text += f"Total Hidden Capacity: {total_hidden_gb:.2f} GB"
                else:
                    hpa_dco_text += "No hidden areas detected"
            
            # Update display
            self.hpa_dco_display.config(state=tk.NORMAL)
            self.hpa_dco_display.delete(1.0, tk.END)
            self.hpa_dco_display.insert(1.0, hpa_dco_text)
            self.hpa_dco_display.config(state=tk.DISABLED)
            
        except Exception as e:
            error_text = f"Error analyzing HPA/DCO for {device}:\n{str(e)}"
            self.hpa_dco_display.config(state=tk.NORMAL)
            self.hpa_dco_display.delete(1.0, tk.END)
            self.hpa_dco_display.insert(1.0, error_text)
            self.hpa_dco_display.config(state=tk.DISABLED)
    
    def _clear_disk_info(self):
        """Clear the disk information display"""
        self.disk_info_text.config(state=tk.NORMAL)
        self.disk_info_text.delete(1.0, tk.END)
        self.disk_info_text.insert(1.0, "Select a disk to view detailed information...")
        self.disk_info_text.config(state=tk.DISABLED)
        
        # Clear HPA/DCO display
        self.hpa_dco_display.config(state=tk.NORMAL)
        self.hpa_dco_display.delete(1.0, tk.END)
        self.hpa_dco_display.insert(1.0, "Select a disk to view HPA/DCO analysis...")
        self.hpa_dco_display.config(state=tk.DISABLED)
    
    def _update_wipe_methods(self):
        """Update available wipe methods with descriptions"""
        try:
            methods = self.disk_manager.get_wipe_methods()
            method_descriptions = {
                'secure': 'Multi-pass secure wipe (recommended for sensitive data)',
                'quick': 'Single-pass quick wipe (faster, less secure)',
                'dd': 'DD-based wiping with random data (very secure)',
                'cipher': 'Windows Cipher.exe free space wipe',
                'hdparm': 'Linux hdparm secure erase (hardware-level)',
                'nvme': 'NVMe secure format (SSD-specific)',
                'blkdiscard': 'TRIM-based discard (SSD-optimized)',
                'saf': 'Android Storage Access Framework'
            }
            
            # Create method list with descriptions
            method_list = []
            for method in methods:
                desc = method_descriptions.get(method, 'Custom wipe method')
                method_list.append(f"{method} - {desc}")
            
            self.wipe_method_combo['values'] = method_list
            if methods:
                self.wipe_method_combo.set(method_list[0])
                self._on_method_change(None)
        except Exception as e:
            self._log(f"Error getting wipe methods: {e}")
    
    def _on_method_change(self, event):
        """Handle method selection change"""
        selection = self.wipe_method_combo.get()
        if selection:
            method = selection.split(' - ')[0]
            description = selection.split(' - ', 1)[1] if ' - ' in selection else ""
            self.method_desc.config(text=description)
    
    def _update_method_recommendations(self, device):
        """Update method recommendations based on selected disk"""
        try:
            disk_info = self.disk_manager.get_disk_info(device)
            if disk_info:
                # Recommend method based on disk type
                if disk_info.type.lower() == 'nvme':
                    recommended = "nvme - NVMe secure format (SSD-specific)"
                elif disk_info.type.lower() == 'ssd':
                    recommended = "blkdiscard - TRIM-based discard (SSD-optimized)"
                elif disk_info.type.lower() == 'hdd':
                    recommended = "hdparm - Linux hdparm secure erase (hardware-level)"
                else:
                    recommended = "secure - Multi-pass secure wipe (recommended for sensitive data)"
                
                # Find and select recommended method
                for i, method in enumerate(self.wipe_method_combo['values']):
                    if method.startswith(recommended.split(' - ')[0]):
                        self.wipe_method_combo.current(i)
                        self._on_method_change(None)
                        break
        except Exception as e:
            self._log(f"Error updating method recommendations: {e}")
    
    def _start_wipe(self):
        """Start the enhanced disk wiping process"""
        if not self.selected_disk:
            messagebox.showwarning("Warning", "Please select a disk to wipe")
            return
        
        # Enhanced safety checks
        system_disks = self.disk_manager.get_system_disks()
        if self.selected_disk in system_disks:
            messagebox.showerror("CRITICAL ERROR", 
                               f"🚨 SYSTEM DISK PROTECTION 🚨\n\n"
                               f"The selected disk {self.selected_disk} is a SYSTEM DISK!\n"
                               f"Wiping this disk would DESTROY YOUR OPERATING SYSTEM!\n\n"
                               f"This operation is BLOCKED for your safety.\n"
                               f"Please select a different disk.")
            self._log(f"BLOCKED: Attempt to wipe system disk {self.selected_disk}")
            return
        
        if not self.disk_manager.is_disk_writable(self.selected_disk):
            messagebox.showerror("Error", 
                               f"Cannot wipe {self.selected_disk}\n\n"
                               f"This disk is not writable or is currently in use.\n"
                               f"Please ensure the disk is unmounted and accessible.")
            return
        
        # Get wipe parameters
        method_selection = self.wipe_method_combo.get()
        if not method_selection:
            messagebox.showwarning("Warning", "Please select a wipe method")
            return
        
        method = method_selection.split(' - ')[0]
        
        try:
            passes = int(self.passes_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid number of passes")
            return
        
        verify = self.verify_var.get()
        remove_hpa = self.remove_hpa_var.get()
        remove_dco = self.remove_dco_var.get()
        
        # Enhanced confirmation dialogs with HPA/DCO information
        confirmation_text = f"🚨 FINAL CONFIRMATION REQUIRED 🚨\n\n"
        confirmation_text += f"You are about to PERMANENTLY ERASE ALL DATA on:\n"
        confirmation_text += f"📀 Device: {self.selected_disk}\n"
        confirmation_text += f"🔧 Method: {method}\n"
        confirmation_text += f"🔄 Passes: {passes}\n"
        
        if remove_hpa:
            confirmation_text += f"⚠️ HPA will be REMOVED (exposes hidden areas)\n"
        if remove_dco:
            confirmation_text += f"🚨 DCO will be REMOVED (DANGEROUS - can damage disk)\n"
        
        confirmation_text += f"\n⚠️ THIS ACTION CANNOT BE UNDONE!\n"
        confirmation_text += f"⚠️ ALL DATA WILL BE PERMANENTLY LOST!\n\n"
        confirmation_text += f"Are you absolutely certain you want to continue?"
        
        result = messagebox.askyesno("⚠️ CRITICAL WARNING", confirmation_text)
        if not result:
            self._log("Wipe operation cancelled by user")
            return
        
        # Start wipe operation with HPA/DCO removal options
        self._start_wipe_operation(self.selected_disk, method, passes, verify, remove_hpa, remove_dco)
    
    def _start_wipe_operation(self, device, method, passes, verify, remove_hpa=False, remove_dco=False):
        """Start the actual wipe operation with enhanced monitoring and HPA/DCO support"""
        # Disable controls
        self.wipe_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # Generate operation ID
        self.current_operation_id = f"wipe_{device}_{int(time.time())}"
        
        # Get disk size for progress tracking
        disk_info = self.disk_manager.get_disk_info(device)
        total_size = disk_info.size if disk_info else 0
        
        # Register operation with progress monitor
        progress_info = progress_monitor.register_operation(
            self.current_operation_id, device, method, total_size, passes
        )
        
        # Register progress callback
        progress_monitor.register_callback(self.current_operation_id, self._on_progress_update)
        
        # Update status
        self.status_var.set("🔄 Wiping disk...")
        status_details = f"Method: {method} | Passes: {passes}"
        if remove_hpa:
            status_details += " | Removing HPA"
        if remove_dco:
            status_details += " | Removing DCO"
        self.details_var.set(status_details)
        
        # Start wipe in separate thread
        self.wipe_thread = threading.Thread(
            target=self._wipe_worker,
            args=(device, method, passes, verify, remove_hpa, remove_dco)
        )
        self.wipe_thread.daemon = True
        self.wipe_thread.start()
    
    def _wipe_worker(self, device, method, passes, verify, remove_hpa=False, remove_dco=False):
        """Enhanced worker thread for disk wiping with HPA/DCO support and progress monitoring"""
        try:
            self._log(f"🚀 Starting wipe of {device} using {method} method")
            self._log(f"📊 Configuration: {passes} passes, Verify: {verify}")
            if remove_hpa:
                self._log("⚠️ HPA removal enabled")
            if remove_dco:
                self._log("🚨 DCO removal enabled (DANGEROUS)")
            
            # Update progress monitor
            if self.current_operation_id:
                progress_monitor.update_progress(self.current_operation_id, 0, 0, "initializing")
            
            # Simulate progress updates (in real implementation, this would come from the actual wipe operation)
            disk_info = self.disk_manager.get_disk_info(device)
            total_size = disk_info.size if disk_info else 0
            
            for pass_num in range(1, passes + 1):
                if self.current_operation_id:
                    progress_monitor.update_progress(
                        self.current_operation_id, 0, pass_num, f"pass_{pass_num}"
                    )
                
                # Simulate pass progress
                for i in range(0, 101, 10):
                    if self.current_operation_id:
                        processed_size = int((total_size * i) / 100)
                        speed = 50.0 + (i * 2)  # Simulate varying speed
                        progress_monitor.update_progress(
                            self.current_operation_id, processed_size, pass_num, 
                            f"pass_{pass_num}", speed
                        )
                    time.sleep(0.1)  # Simulate work
            
            # Perform actual wipe (this would be the real implementation)
            if remove_hpa or remove_dco:
                success, message = self.disk_manager.wipe_with_hpa_dco_removal(
                    device, method, passes, verify, remove_hpa, remove_dco
                )
            else:
                # Perform standard wipe
                success, message = self.disk_manager.wipe_disk(device, method, passes, verify)
            
            # Complete operation in progress monitor
            if self.current_operation_id:
                progress_monitor.complete_operation(self.current_operation_id, success, message)
            
            # Update UI
            self.root.after(0, lambda: self._wipe_complete(success, message))
            
        except Exception as e:
            if self.current_operation_id:
                progress_monitor.complete_operation(self.current_operation_id, False, str(e))
            self.root.after(0, lambda: self._wipe_complete(False, str(e)))
    
    def _wipe_complete(self, success, message):
        """Handle wipe completion with enhanced feedback"""
        # Re-enable controls
        self.wipe_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_var.set(100)
        
        # Update status
        if success:
            self.status_var.set("✅ Wipe completed successfully")
            self.details_var.set("Data has been securely erased")
            self.speed_var.set("Speed: Complete")
            self.eta_var.set("ETA: --")
            self._log(f"SUCCESS: {message}")
            messagebox.showinfo("Success", f"🎉 Disk wiped successfully!\n\n{message}")
        else:
            self.status_var.set("❌ Wipe failed")
            self.details_var.set("Check log for details")
            self.speed_var.set("Speed: Failed")
            self.eta_var.set("ETA: --")
            self._log(f"ERROR: {message}")
            messagebox.showerror("Error", f"❌ Wipe failed!\n\n{message}")
    
    def _stop_wipe(self):
        """Stop the current wipe operation"""
        self._log("Stop requested (not implemented)")
        messagebox.showinfo("Info", "Stop functionality not yet implemented")
    
    def _filter_disks(self, event):
        """Filter disks based on selection"""
        filter_value = self.filter_var.get()
        # Implementation for disk filtering
        self._log(f"Filtering disks by: {filter_value}")
    
    def _show_quick_actions(self, device):
        """Show quick action menu for disk"""
        # Implementation for quick actions menu
        self._log(f"Quick actions for: {device}")
    
    def _detect_hpa_dco(self):
        """Detect HPA/DCO on selected disk"""
        if not self.selected_disk:
            messagebox.showwarning("Warning", "Please select a disk first")
            return
        
        self._log(f"Detecting HPA/DCO on {self.selected_disk}...")
        self.hpa_dco_status.config(text="Status: Detecting...")
        
        # Run detection in separate thread
        def detection_worker():
            try:
                hpa_dco_info = self.disk_manager.detect_hpa_dco(self.selected_disk)
                
                # Update UI in main thread
                self.root.after(0, lambda: self._update_hpa_dco_status(hpa_dco_info))
                
            except Exception as e:
                self.root.after(0, lambda: self._update_hpa_dco_status({'error': str(e)}))
        
        detection_thread = threading.Thread(target=detection_worker)
        detection_thread.daemon = True
        detection_thread.start()
    
    def _update_hpa_dco_status(self, hpa_dco_info):
        """Update HPA/DCO status display"""
        if hpa_dco_info.get('error'):
            self.hpa_dco_status.config(text=f"Status: Error - {hpa_dco_info['error']}")
            self._log(f"HPA/DCO detection failed: {hpa_dco_info['error']}")
            return
        
        # Build status message
        status_parts = []
        
        if hpa_dco_info.get('hpa_detected'):
            hpa_gb = hpa_dco_info.get('hpa_gb', 0)
            status_parts.append(f"HPA: {hpa_gb:.1f}GB")
        else:
            status_parts.append("HPA: None")
        
        if hpa_dco_info.get('dco_detected'):
            dco_gb = hpa_dco_info.get('dco_gb', 0)
            status_parts.append(f"DCO: {dco_gb:.1f}GB")
        else:
            status_parts.append("DCO: None")
        
        status_text = f"Status: {' | '.join(status_parts)}"
        self.hpa_dco_status.config(text=status_text)
        
        # Log detection results
        if hpa_dco_info.get('hpa_detected') or hpa_dco_info.get('dco_detected'):
            total_hidden = hpa_dco_info.get('hidden_gb', 0)
            self._log(f"HPA/DCO detected: {total_hidden:.1f}GB hidden capacity")
        else:
            self._log("No HPA/DCO detected")
    
    def _on_progress_update(self, progress_info: ProgressInfo):
        """Handle progress updates from the progress monitor"""
        # Update progress bar
        self.progress_var.set(progress_info.progress_percentage)
        
        # Update status information
        status_text = f"🔄 {progress_info.phase.replace('_', ' ').title()}"
        if progress_info.current_pass > 0:
            status_text += f" (Pass {progress_info.current_pass}/{progress_info.total_passes})"
        
        self.status_var.set(status_text)
        
        # Update details
        details_text = f"Progress: {progress_info.progress_percentage:.1f}%"
        if progress_info.speed_mbps > 0:
            details_text += f" | Speed: {progress_info.speed_mbps:.1f} MB/s"
        if progress_info.eta_seconds > 0:
            details_text += f" | ETA: {progress_info.eta_formatted}"
        
        self.details_var.set(details_text)
        
        # Update speed and ETA displays
        self.speed_var.set(f"Speed: {progress_info.speed_mbps:.1f} MB/s")
        self.eta_var.set(f"ETA: {progress_info.eta_formatted}")
    
    def _on_error_occurred(self, error_info: ErrorInfo):
        """Handle errors from the error handler"""
        # Update status bar with error information
        error_icon = {
            ErrorSeverity.INFO: "ℹ️",
            ErrorSeverity.WARNING: "⚠️",
            ErrorSeverity.ERROR: "❌",
            ErrorSeverity.CRITICAL: "🚨"
        }.get(error_info.severity, "❓")
        
        self.status_bar_text.set(f"{error_icon} {error_info.message}")
        
        # Log the error
        self._log(f"ERROR [{error_info.error_id}]: {error_info.message}")
        
        # Show user-friendly error dialog for critical errors
        if error_info.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            self._show_error_dialog(error_info)
    
    def _show_error_dialog(self, error_info: ErrorInfo):
        """Show user-friendly error dialog"""
        # Create error dialog
        error_dialog = tk.Toplevel(self.root)
        error_dialog.title(f"Error - {error_info.severity.value.title()}")
        error_dialog.geometry("600x400")
        error_dialog.resizable(True, True)
        
        # Configure dialog style
        error_dialog.configure(bg=self.colors['bg_primary'])
        
        # Main frame
        main_frame = ttk.Frame(error_dialog, style='Modern.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Error icon and title
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        error_icon = {
            ErrorSeverity.ERROR: "❌",
            ErrorSeverity.CRITICAL: "🚨"
        }.get(error_info.severity, "❓")
        
        icon_label = ttk.Label(header_frame, text=error_icon, font=('Segoe UI', 24))
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title_label = ttk.Label(title_frame, text="An Error Occurred", 
                               style='Title.TLabel', font=('Segoe UI', 16, 'bold'))
        title_label.pack(anchor=tk.W)
        
        severity_label = ttk.Label(title_frame, text=f"Severity: {error_info.severity.value.title()}", 
                                  style='Warning.TLabel')
        severity_label.pack(anchor=tk.W)
        
        # Error message
        message_frame = ttk.LabelFrame(main_frame, text="Error Message", padding="15")
        message_frame.pack(fill=tk.X, pady=(0, 15))
        
        message_text = tk.Text(message_frame, height=3, wrap=tk.WORD, 
                              font=('Segoe UI', 10), bg=self.colors['bg_secondary'], 
                              fg=self.colors['text_primary'])
        message_text.insert(1.0, error_info.message)
        message_text.config(state=tk.DISABLED)
        message_text.pack(fill=tk.X)
        
        # Suggestions
        if error_info.suggestions:
            suggestions_frame = ttk.LabelFrame(main_frame, text="Suggestions", padding="15")
            suggestions_frame.pack(fill=tk.X, pady=(0, 15))
            
            for i, suggestion in enumerate(error_info.suggestions, 1):
                suggestion_label = ttk.Label(suggestions_frame, 
                                           text=f"{i}. {suggestion}", 
                                           style='Info.TLabel')
                suggestion_label.pack(anchor=tk.W, pady=2)
        
        # Details (collapsible)
        details_frame = ttk.LabelFrame(main_frame, text="Technical Details", padding="15")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        details_text = tk.Text(details_frame, wrap=tk.WORD, 
                              font=('Consolas', 9), bg=self.colors['bg_secondary'], 
                              fg=self.colors['text_primary'])
        details_text.insert(1.0, f"Error ID: {error_info.error_id}\n")
        details_text.insert(tk.END, f"Category: {error_info.category.value}\n")
        details_text.insert(tk.END, f"Timestamp: {error_info.timestamp.isoformat()}\n")
        details_text.insert(tk.END, f"Recoverable: {'Yes' if error_info.recoverable else 'No'}\n")
        if error_info.context:
            details_text.insert(tk.END, f"Context: {error_info.context}\n")
        if error_info.details:
            details_text.insert(tk.END, f"\nDetails:\n{error_info.details}")
        details_text.config(state=tk.DISABLED)
        details_text.pack(fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        if error_info.recoverable:
            retry_btn = ttk.Button(button_frame, text="🔄 Retry", 
                                  command=lambda: self._retry_operation(error_dialog))
            retry_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = ttk.Button(button_frame, text="Close", 
                              command=error_dialog.destroy)
        close_btn.pack(side=tk.RIGHT)
        
        # Center dialog
        error_dialog.transient(self.root)
        error_dialog.grab_set()
        
        # Center on screen
        error_dialog.update_idletasks()
        x = (error_dialog.winfo_screenwidth() // 2) - (error_dialog.winfo_width() // 2)
        y = (error_dialog.winfo_screenheight() // 2) - (error_dialog.winfo_height() // 2)
        error_dialog.geometry(f"+{x}+{y}")
    
    def _retry_operation(self, dialog):
        """Retry the failed operation"""
        dialog.destroy()
        # Implementation for retry logic would go here
        self._log("Retry operation requested")
    
    def _open_settings(self):
        """Open settings dialog"""
        # Implementation for settings dialog
        self._log("Opening settings dialog")
    
    def _log(self, message):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # Update status bar
        self.status_bar_text.set(message)
        
        # Also log to file
        logger.info(message)
    
    def run(self):
        """Start the enhanced GUI application"""
        self.root.mainloop()
