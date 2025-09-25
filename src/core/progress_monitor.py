"""
Progress monitoring system for disk wipe operations
Provides real-time feedback and progress tracking
"""

import time
import threading
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProgressInfo:
    """Information about operation progress"""
    operation_id: str
    device: str
    method: str
    total_size: int = 0
    processed_size: int = 0
    current_pass: int = 0
    total_passes: int = 1
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    speed_mbps: float = 0.0
    status: str = "pending"  # pending, running, completed, failed, cancelled
    error_message: Optional[str] = None
    phase: str = "initializing"  # initializing, wiping, verifying, completed
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_size == 0:
            return 0.0
        return (self.processed_size / self.total_size) * 100
    
    @property
    def elapsed_time(self) -> timedelta:
        """Get elapsed time since start"""
        if not self.start_time:
            return timedelta(0)
        return datetime.now() - self.start_time
    
    @property
    def eta_seconds(self) -> int:
        """Get estimated time to completion in seconds"""
        if not self.estimated_completion:
            return 0
        remaining = self.estimated_completion - datetime.now()
        return max(0, int(remaining.total_seconds()))
    
    @property
    def eta_formatted(self) -> str:
        """Get formatted ETA string"""
        eta_sec = self.eta_seconds
        if eta_sec == 0:
            return "Unknown"
        
        hours = eta_sec // 3600
        minutes = (eta_sec % 3600) // 60
        seconds = eta_sec % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

class ProgressMonitor:
    """Progress monitoring system for disk operations"""
    
    def __init__(self):
        self.active_operations: Dict[str, ProgressInfo] = {}
        self.callbacks: Dict[str, Callable[[ProgressInfo], None]] = {}
        self.monitor_thread: Optional[threading.Thread] = None
        self.running = False
        self.update_interval = 1.0  # seconds
        
    def start_monitoring(self):
        """Start the progress monitoring thread"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Progress monitoring started")
    
    def stop_monitoring(self):
        """Stop the progress monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("Progress monitoring stopped")
    
    def register_operation(self, operation_id: str, device: str, method: str, 
                          total_size: int, total_passes: int = 1) -> ProgressInfo:
        """Register a new operation for monitoring"""
        progress_info = ProgressInfo(
            operation_id=operation_id,
            device=device,
            method=method,
            total_size=total_size,
            total_passes=total_passes,
            start_time=datetime.now()
        )
        
        self.active_operations[operation_id] = progress_info
        logger.info(f"Registered operation {operation_id} for {device}")
        return progress_info
    
    def update_progress(self, operation_id: str, processed_size: int, 
                       current_pass: int = None, phase: str = None, 
                       speed_mbps: float = None):
        """Update progress for an operation"""
        if operation_id not in self.active_operations:
            logger.warning(f"Unknown operation ID: {operation_id}")
            return
        
        progress_info = self.active_operations[operation_id]
        progress_info.processed_size = processed_size
        progress_info.status = "running"
        
        if current_pass is not None:
            progress_info.current_pass = current_pass
        
        if phase is not None:
            progress_info.phase = phase
        
        if speed_mbps is not None:
            progress_info.speed_mbps = speed_mbps
            # Update ETA based on current speed
            if speed_mbps > 0 and progress_info.total_size > 0:
                remaining_bytes = progress_info.total_size - processed_size
                remaining_mb = remaining_bytes / (1024 * 1024)
                eta_seconds = remaining_mb / speed_mbps
                progress_info.estimated_completion = datetime.now() + timedelta(seconds=eta_seconds)
    
    def complete_operation(self, operation_id: str, success: bool = True, 
                          error_message: str = None):
        """Mark an operation as completed"""
        if operation_id not in self.active_operations:
            return
        
        progress_info = self.active_operations[operation_id]
        progress_info.status = "completed" if success else "failed"
        progress_info.phase = "completed"
        progress_info.processed_size = progress_info.total_size
        progress_info.error_message = error_message
        
        if success:
            logger.info(f"Operation {operation_id} completed successfully")
        else:
            logger.error(f"Operation {operation_id} failed: {error_message}")
    
    def cancel_operation(self, operation_id: str):
        """Cancel an operation"""
        if operation_id not in self.active_operations:
            return
        
        progress_info = self.active_operations[operation_id]
        progress_info.status = "cancelled"
        progress_info.phase = "cancelled"
        
        logger.info(f"Operation {operation_id} cancelled")
    
    def get_progress(self, operation_id: str) -> Optional[ProgressInfo]:
        """Get progress information for an operation"""
        return self.active_operations.get(operation_id)
    
    def register_callback(self, operation_id: str, callback: Callable[[ProgressInfo], None]):
        """Register a callback for progress updates"""
        self.callbacks[operation_id] = callback
    
    def unregister_callback(self, operation_id: str):
        """Unregister a callback"""
        self.callbacks.pop(operation_id, None)
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                for operation_id, progress_info in list(self.active_operations.items()):
                    # Call registered callbacks
                    if operation_id in self.callbacks:
                        try:
                            self.callbacks[operation_id](progress_info)
                        except Exception as e:
                            logger.error(f"Error in progress callback for {operation_id}: {e}")
                    
                    # Clean up completed operations
                    if progress_info.status in ["completed", "failed", "cancelled"]:
                        # Keep completed operations for a short time for final callbacks
                        if progress_info.elapsed_time > timedelta(seconds=5):
                            self.active_operations.pop(operation_id, None)
                            self.callbacks.pop(operation_id, None)
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in progress monitoring loop: {e}")
                time.sleep(self.update_interval)
    
    def get_all_operations(self) -> Dict[str, ProgressInfo]:
        """Get all active operations"""
        return self.active_operations.copy()
    
    def clear_completed_operations(self):
        """Clear all completed operations"""
        completed_ids = [
            op_id for op_id, info in self.active_operations.items()
            if info.status in ["completed", "failed", "cancelled"]
        ]
        
        for op_id in completed_ids:
            self.active_operations.pop(op_id, None)
            self.callbacks.pop(op_id, None)
        
        logger.info(f"Cleared {len(completed_ids)} completed operations")

# Global progress monitor instance
progress_monitor = ProgressMonitor()
