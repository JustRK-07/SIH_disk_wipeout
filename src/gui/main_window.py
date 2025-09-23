"""
Main GUI window for Disk Wipeout application
Provides an easy-to-use interface for disk wiping operations
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import logging
import platform
from typing import List, Optional

from ..core.disk_manager import DiskManager
from ..core.models import DiskInfo

logger = logging.getLogger(__name__)

class MainWindow:
    """Main application window"""
    
    def __init__(self, disk_manager: DiskManager):
        self.disk_manager = disk_manager
        self.root = tk.Tk()
        self.selected_disk = None
        self.wipe_thread = None
        
        self._setup_window()
        self._create_widgets()
        self._refresh_disks()
    
    def _setup_window(self):
        """Setup the main window"""
        self.root.title("Disk Wipeout - Secure Data Erasure Tool")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        self.root.resizable(True, True)
        
        # Center the window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"1200x800+{x}+{y}")
        
        # Configure style with modern look
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure modern colors and fonts
        style.configure('Title.TLabel', 
                       font=('Segoe UI', 20, 'bold'),
                       foreground='#2c3e50',
                       background='#ecf0f1')
        
        style.configure('Heading.TLabel', 
                       font=('Segoe UI', 12, 'bold'),
                       foreground='#34495e')
        
        style.configure('Subheading.TLabel',
                       font=('Segoe UI', 10, 'bold'),
                       foreground='#7f8c8d')
        
        style.configure('Warning.TLabel', 
                       foreground='#e74c3c',
                       font=('Segoe UI', 10, 'bold'))
        
        style.configure('Success.TLabel', 
                       foreground='#27ae60',
                       font=('Segoe UI', 10, 'bold'))
        
        style.configure('Info.TLabel',
                       foreground='#3498db',
                       font=('Segoe UI', 10))
        
        # Configure button styles
        style.configure('Action.TButton',
                       font=('Segoe UI', 10, 'bold'),
                       padding=(10, 5))
        
        style.configure('Danger.TButton',
                       font=('Segoe UI', 10, 'bold'),
                       foreground='white',
                       background='#e74c3c')
        
        # Configure frame styles
        style.configure('Card.TFrame',
                       background='#ffffff',
                       relief='solid',
                       borderwidth=1)
        
        style.configure('Header.TFrame',
                       background='#ecf0f1')
    
    def _create_widgets(self):
        """Create and layout GUI widgets"""
        # Configure root grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Main container with padding
        main_container = ttk.Frame(self.root, style='Header.TFrame')
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=15, pady=15)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # Header section
        header_frame = ttk.Frame(main_container, style='Header.TFrame')
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)
        
        # Title and subtitle
        title_label = ttk.Label(header_frame, text="🔒 Disk Wipeout", style='Title.TLabel')
        title_label.grid(row=0, column=0, pady=(0, 5))
        
        subtitle_label = ttk.Label(header_frame, text="Secure Data Erasure Tool - Cross-Platform", 
                                 style='Subheading.TLabel')
        subtitle_label.grid(row=1, column=0)
        
        # Main content area
        content_frame = ttk.Frame(main_container)
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Left column - Disk selection
        left_frame = ttk.Frame(content_frame, style='Card.TFrame')
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        # Disk selection frame
        disk_frame = ttk.LabelFrame(left_frame, text="💾 Available Disks", padding="15")
        disk_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        disk_frame.columnconfigure(0, weight=1)
        
        # Disk list header
        disk_header = ttk.Frame(disk_frame)
        disk_header.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        disk_header.columnconfigure(0, weight=1)
        
        ttk.Label(disk_header, text="Select a disk to wipe:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W)
        refresh_btn = ttk.Button(disk_header, text="🔄 Refresh", command=self._refresh_disks, style='Action.TButton')
        refresh_btn.grid(row=0, column=1, sticky=tk.E)
        
        # Create treeview for disk list with better styling
        columns = ('Device', 'Size', 'Type', 'Model', 'Status')
        self.disk_tree = ttk.Treeview(disk_frame, columns=columns, show='headings', height=8)
        
        # Configure columns with better widths
        self.disk_tree.heading('Device', text='Device Path')
        self.disk_tree.heading('Size', text='Size')
        self.disk_tree.heading('Type', text='Type')
        self.disk_tree.heading('Model', text='Model')
        self.disk_tree.heading('Status', text='Status')
        
        self.disk_tree.column('Device', width=180, minwidth=150)
        self.disk_tree.column('Size', width=100, minwidth=80)
        self.disk_tree.column('Type', width=80, minwidth=60)
        self.disk_tree.column('Model', width=200, minwidth=150)
        self.disk_tree.column('Status', width=100, minwidth=80)
        
        # Scrollbar for disk list
        disk_scrollbar = ttk.Scrollbar(disk_frame, orient=tk.VERTICAL, command=self.disk_tree.yview)
        self.disk_tree.configure(yscrollcommand=disk_scrollbar.set)
        
        self.disk_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        disk_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S), pady=(0, 10))
        
        # Bind selection event
        self.disk_tree.bind('<<TreeviewSelect>>', self._on_disk_select)
        
        # Disk info frame
        info_frame = ttk.LabelFrame(left_frame, text="ℹ️ Disk Information", padding="15")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_frame.columnconfigure(0, weight=1)
        
        self.disk_info_text = tk.Text(info_frame, height=6, wrap=tk.WORD, state=tk.DISABLED,
                                    font=('Consolas', 9), bg='#f8f9fa', fg='#2c3e50')
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.disk_info_text.yview)
        self.disk_info_text.configure(yscrollcommand=info_scrollbar.set)
        
        self.disk_info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Right column - Wipe options and controls
        right_frame = ttk.Frame(content_frame, style='Card.TFrame')
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        
        # Wipe options frame
        options_frame = ttk.LabelFrame(right_frame, text="⚙️ Wipe Configuration", padding="15")
        options_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        options_frame.columnconfigure(1, weight=1)
        
        # Wipe method selection
        ttk.Label(options_frame, text="Wipe Method:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.wipe_method_var = tk.StringVar()
        self.wipe_method_combo = ttk.Combobox(options_frame, textvariable=self.wipe_method_var, 
                                            state="readonly", width=25, font=('Segoe UI', 10))
        self.wipe_method_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Passes configuration
        passes_frame = ttk.Frame(options_frame)
        passes_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        passes_frame.columnconfigure(1, weight=1)
        
        ttk.Label(passes_frame, text="Number of Passes:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W)
        self.passes_var = tk.StringVar(value="3")
        passes_spinbox = ttk.Spinbox(passes_frame, from_=1, to=10, textvariable=self.passes_var, 
                                   width=10, font=('Segoe UI', 10))
        passes_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Security options
        security_frame = ttk.LabelFrame(options_frame, text="🔒 Security Options", padding="10")
        security_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.verify_var = tk.BooleanVar(value=True)
        verify_check = ttk.Checkbutton(security_frame, text="✅ Verify wipe after completion", 
                                     variable=self.verify_var, style='Info.TLabel')
        verify_check.grid(row=0, column=0, sticky=tk.W)
        
        self.force_var = tk.BooleanVar(value=False)
        force_check = ttk.Checkbutton(security_frame, text="⚠️ Force wipe (skip confirmations)", 
                                    variable=self.force_var, style='Warning.TLabel')
        force_check.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Action controls frame
        controls_frame = ttk.LabelFrame(right_frame, text="🎮 Action Controls", padding="15")
        controls_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.rowconfigure(1, weight=1)
        
        # Action buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        
        # Wipe button
        self.wipe_btn = ttk.Button(button_frame, text="🚀 Start Wipe", command=self._start_wipe, 
                                 style='Action.TButton')
        self.wipe_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # Stop button
        self.stop_btn = ttk.Button(button_frame, text="⏹️ Stop", command=self._stop_wipe, 
                                 state=tk.DISABLED, style='Danger.TButton')
        self.stop_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # Progress section
        progress_frame = ttk.LabelFrame(controls_frame, text="📊 Progress", padding="10")
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar with better styling
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=300, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status and details
        status_frame = ttk.Frame(progress_frame)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="🟢 Ready - Select a disk to begin")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, style='Info.TLabel')
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.details_var = tk.StringVar(value="")
        self.details_label = ttk.Label(status_frame, textvariable=self.details_var, style='Subheading.TLabel')
        self.details_label.grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        
        # Bottom panel - Log and system info
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.rowconfigure(0, weight=1)
        main_container.rowconfigure(2, weight=1)
        
        # Log frame with better styling
        log_frame = ttk.LabelFrame(bottom_frame, text="📝 Operation Log", padding="15")
        log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text widget with better styling
        self.log_text = tk.Text(log_frame, height=6, wrap=tk.WORD, 
                              font=('Consolas', 9), bg='#2c3e50', fg='#ecf0f1',
                              insertbackground='#ecf0f1', selectbackground='#3498db')
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Log controls
        log_controls = ttk.Frame(log_frame)
        log_controls.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        log_controls.columnconfigure(0, weight=1)
        
        clear_log_btn = ttk.Button(log_controls, text="🗑️ Clear Log", command=self._clear_log, 
                                 style='Action.TButton')
        clear_log_btn.grid(row=0, column=0, sticky=tk.W)
        
        # System info
        system_info = ttk.Label(log_controls, text=f"Platform: {platform.system()} | Python: {platform.python_version()}", 
                              style='Subheading.TLabel')
        system_info.grid(row=0, column=1, sticky=tk.E)
        
        # Update wipe methods
        self._update_wipe_methods()
        
        # Add initial log message
        self._log("🚀 Disk Wipeout application started")
        self._log(f"📊 Platform: {platform.system()} {platform.release()}")
        self._log("✅ Ready to detect and wipe disks")
    
    def _refresh_disks(self):
        """Refresh the list of available disks"""
        self._log("Refreshing disk list...")
        
        # Clear existing items
        for item in self.disk_tree.get_children():
            self.disk_tree.delete(item)
        
        try:
            # Get available disks
            disks = self.disk_manager.get_available_disks()
            
            for disk in disks:
                # Format size
                size_str = f"{disk.size // (1024**3)}GB" if disk.size > 0 else "Unknown"
                
                # Check if writable
                is_writable = self.disk_manager.is_disk_writable(disk.device)
                status = "Writable" if is_writable else "Read-only"
                
                # Insert into tree
                item = self.disk_tree.insert('', 'end', values=(
                    disk.device,
                    size_str,
                    disk.type.upper(),
                    disk.model,
                    status
                ))
                
                # Store disk info in item
                self.disk_tree.set(item, 'Device', disk.device)
            
            self._log(f"Found {len(disks)} disks")
            
        except Exception as e:
            self._log(f"Error refreshing disks: {e}")
            messagebox.showerror("Error", f"Failed to refresh disk list: {e}")
    
    def _on_disk_select(self, event):
        """Handle disk selection"""
        selection = self.disk_tree.selection()
        if selection:
            item = selection[0]
            device = self.disk_tree.item(item, 'values')[0]
            self.selected_disk = device
            
            # Update disk information display
            self._update_disk_info(device)
            
            # Update status
            self.status_var.set(f"🔍 Selected: {device}")
            self.details_var.set("Ready to configure wipe options")
            
            self._log(f"Selected disk: {device}")
        else:
            self.selected_disk = None
            self._clear_disk_info()
            self.status_var.set("🟢 Ready - Select a disk to begin")
            self.details_var.set("")
    
    def _update_disk_info(self, device):
        """Update the disk information display"""
        try:
            disk_info = self.disk_manager.get_disk_info(device)
            if disk_info:
                info_text = f"""Device: {disk_info.device}
Size: {disk_info.size // (1024**3):,}GB ({disk_info.size:,} bytes)
Type: {disk_info.type.upper()}
Model: {disk_info.model}
Serial: {disk_info.serial}
Mountpoint: {disk_info.mountpoint or 'Not mounted'}
Filesystem: {disk_info.filesystem or 'Unknown'}
Writable: {'Yes' if self.disk_manager.is_disk_writable(device) else 'No'}"""
                
                self.disk_info_text.config(state=tk.NORMAL)
                self.disk_info_text.delete(1.0, tk.END)
                self.disk_info_text.insert(1.0, info_text)
                self.disk_info_text.config(state=tk.DISABLED)
        except Exception as e:
            self._log(f"Error getting disk info: {e}")
    
    def _clear_disk_info(self):
        """Clear the disk information display"""
        self.disk_info_text.config(state=tk.NORMAL)
        self.disk_info_text.delete(1.0, tk.END)
        self.disk_info_text.insert(1.0, "Select a disk to view detailed information...")
        self.disk_info_text.config(state=tk.DISABLED)
    
    def _update_wipe_methods(self):
        """Update available wipe methods"""
        try:
            methods = self.disk_manager.get_wipe_methods()
            self.wipe_method_combo['values'] = methods
            if methods:
                self.wipe_method_combo.set(methods[0])
        except Exception as e:
            self._log(f"Error getting wipe methods: {e}")
    
    def _start_wipe(self):
        """Start the disk wiping process"""
        if not self.selected_disk:
            messagebox.showwarning("Warning", "Please select a disk to wipe")
            return
        
        # Confirm wipe operation
        result = messagebox.askyesno("Confirm Wipe", 
                                   f"Are you sure you want to wipe {self.selected_disk}?\n\n"
                                   "This action cannot be undone!")
        if not result:
            return
        
        # Get wipe parameters
        method = self.wipe_method_var.get()
        if not method:
            messagebox.showwarning("Warning", "Please select a wipe method")
            return
        
        try:
            passes = int(self.passes_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid number of passes")
            return
        
        verify = self.verify_var.get()
        
        # Disable controls
        self.wipe_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # Start wipe in separate thread
        self.wipe_thread = threading.Thread(
            target=self._wipe_worker,
            args=(self.selected_disk, method, passes, verify)
        )
        self.wipe_thread.daemon = True
        self.wipe_thread.start()
    
    def _wipe_worker(self, device: str, method: str, passes: int, verify: bool):
        """Worker thread for disk wiping"""
        try:
            self._log(f"🚀 Starting wipe of {device} using {method} method")
            self._log(f"📊 Configuration: {passes} passes, Verify: {verify}")
            
            # Update status with progress
            self.root.after(0, lambda: self.status_var.set("🔄 Wiping disk..."))
            self.root.after(0, lambda: self.details_var.set(f"Method: {method} | Passes: {passes}"))
            self.root.after(0, lambda: self.progress_var.set(10))
            
            # Simulate progress updates (in real implementation, this would come from the wipe operation)
            for i in range(1, 6):
                import time
                time.sleep(0.5)  # Simulate work
                progress = 10 + (i * 15)
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda p=progress: self.details_var.set(f"Progress: {p}% - Wiping..."))
            
            # Perform wipe
            success, message = self.disk_manager.wipe_disk(device, method, passes, verify)
            
            # Update UI
            self.root.after(0, lambda: self._wipe_complete(success, message))
            
        except Exception as e:
            self.root.after(0, lambda: self._wipe_complete(False, str(e)))
    
    def _wipe_complete(self, success: bool, message: str):
        """Handle wipe completion"""
        # Re-enable controls
        self.wipe_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_var.set(100)
        
        # Update status with better styling
        if success:
            self.status_var.set("✅ Wipe completed successfully")
            self.details_var.set("Data has been securely erased")
            self._log(f"SUCCESS: {message}")
            messagebox.showinfo("Success", f"🎉 Disk wiped successfully!\n\n{message}")
        else:
            self.status_var.set("❌ Wipe failed")
            self.details_var.set("Check log for details")
            self._log(f"ERROR: {message}")
            messagebox.showerror("Error", f"❌ Wipe failed!\n\n{message}")
    
    def _stop_wipe(self):
        """Stop the current wipe operation"""
        # This would require implementing cancellation in the disk manager
        self._log("Stop requested (not implemented)")
        messagebox.showinfo("Info", "Stop functionality not yet implemented")
    
    def _log(self, message: str):
        """Add message to log"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # Also log to file
        logger.info(message)
    
    def _clear_log(self):
        """Clear the log text"""
        self.log_text.delete(1.0, tk.END)
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()
