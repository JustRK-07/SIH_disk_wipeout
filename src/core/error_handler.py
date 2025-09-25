"""
Enhanced error handling system for disk wipeout application
Provides comprehensive error management and user feedback
"""

import logging
import traceback
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories"""
    DISK_ACCESS = "disk_access"
    PERMISSION = "permission"
    VALIDATION = "validation"
    SAFETY = "safety"
    OPERATION = "operation"
    SYSTEM = "system"
    NETWORK = "network"
    CONFIGURATION = "configuration"

@dataclass
class ErrorInfo:
    """Comprehensive error information"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    details: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    recoverable: bool = True
    user_action_required: bool = False
    original_exception: Optional[Exception] = None
    traceback_info: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "details": self.details,
            "context": self.context,
            "suggestions": self.suggestions,
            "recoverable": self.recoverable,
            "user_action_required": self.user_action_required,
            "traceback_info": self.traceback_info
        }

class ErrorHandler:
    """Enhanced error handling system"""
    
    def __init__(self):
        self.error_history: List[ErrorInfo] = []
        self.error_callbacks: List[Callable[[ErrorInfo], None]] = []
        self.max_history_size = 1000
        
    def register_callback(self, callback: Callable[[ErrorInfo], None]):
        """Register an error callback"""
        self.error_callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[ErrorInfo], None]):
        """Unregister an error callback"""
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None, 
                    severity: ErrorSeverity = ErrorSeverity.ERROR,
                    category: ErrorCategory = ErrorCategory.SYSTEM) -> ErrorInfo:
        """Handle an error and create comprehensive error information"""
        
        error_id = f"err_{int(datetime.now().timestamp())}"
        context = context or {}
        
        # Generate error information
        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            message=str(error),
            details=self._get_error_details(error),
            context=context,
            suggestions=self._get_suggestions(error, category),
            recoverable=self._is_recoverable(error, category),
            user_action_required=self._requires_user_action(error, category),
            original_exception=error,
            traceback_info=traceback.format_exc()
        )
        
        # Add to history
        self.error_history.append(error_info)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)
        
        # Log the error
        self._log_error(error_info)
        
        # Notify callbacks
        for callback in self.error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
        
        return error_info
    
    def handle_disk_error(self, error: Exception, device: str, operation: str = "") -> ErrorInfo:
        """Handle disk-specific errors"""
        context = {
            "device": device,
            "operation": operation,
            "error_type": type(error).__name__
        }
        
        # Determine category and severity based on error type
        if "Permission denied" in str(error) or "Access denied" in str(error):
            category = ErrorCategory.PERMISSION
            severity = ErrorSeverity.ERROR
        elif "No such file or directory" in str(error) or "Device not found" in str(error):
            category = ErrorCategory.DISK_ACCESS
            severity = ErrorSeverity.ERROR
        elif "Device or resource busy" in str(error):
            category = ErrorCategory.DISK_ACCESS
            severity = ErrorSeverity.WARNING
        else:
            category = ErrorCategory.DISK_ACCESS
            severity = ErrorSeverity.ERROR
        
        return self.handle_error(error, context, severity, category)
    
    def handle_safety_error(self, error: Exception, device: str, safety_violation: str) -> ErrorInfo:
        """Handle safety-related errors"""
        context = {
            "device": device,
            "safety_violation": safety_violation,
            "error_type": type(error).__name__
        }
        
        return self.handle_error(error, context, ErrorSeverity.CRITICAL, ErrorCategory.SAFETY)
    
    def handle_validation_error(self, error: Exception, validation_details: Dict[str, Any]) -> ErrorInfo:
        """Handle validation errors"""
        context = {
            "validation_details": validation_details,
            "error_type": type(error).__name__
        }
        
        return self.handle_error(error, context, ErrorSeverity.WARNING, ErrorCategory.VALIDATION)
    
    def _get_error_details(self, error: Exception) -> str:
        """Get detailed error information"""
        error_type = type(error).__name__
        error_message = str(error)
        
        details = f"Error Type: {error_type}\n"
        details += f"Error Message: {error_message}\n"
        
        # Add specific details based on error type
        if hasattr(error, 'errno'):
            details += f"Error Number: {error.errno}\n"
        
        if hasattr(error, 'filename'):
            details += f"Filename: {error.filename}\n"
        
        return details.strip()
    
    def _get_suggestions(self, error: Exception, category: ErrorCategory) -> List[str]:
        """Get suggestions for resolving the error"""
        suggestions = []
        
        if category == ErrorCategory.PERMISSION:
            suggestions.extend([
                "Run the application with administrator/root privileges",
                "Check file and directory permissions",
                "Ensure the user has access to the device"
            ])
        elif category == ErrorCategory.DISK_ACCESS:
            suggestions.extend([
                "Verify the device path is correct",
                "Check if the device is connected and recognized",
                "Ensure the device is not in use by another process",
                "Try unmounting the device if it's mounted"
            ])
        elif category == ErrorCategory.SAFETY:
            suggestions.extend([
                "Review safety configuration settings",
                "Verify the device is not a system disk",
                "Check if the device is protected",
                "Contact system administrator if needed"
            ])
        elif category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Check input parameters",
                "Verify configuration settings",
                "Ensure all required fields are provided"
            ])
        elif category == ErrorCategory.OPERATION:
            suggestions.extend([
                "Retry the operation",
                "Check system resources",
                "Verify device status",
                "Review operation parameters"
            ])
        
        return suggestions
    
    def _is_recoverable(self, error: Exception, category: ErrorCategory) -> bool:
        """Determine if the error is recoverable"""
        if category == ErrorCategory.SAFETY:
            return False  # Safety errors are generally not recoverable
        elif category == ErrorCategory.PERMISSION:
            return True  # Permission errors can be resolved
        elif category == ErrorCategory.DISK_ACCESS:
            return True  # Disk access errors can often be resolved
        else:
            return True  # Default to recoverable
    
    def _requires_user_action(self, error: Exception, category: ErrorCategory) -> bool:
        """Determine if user action is required"""
        if category in [ErrorCategory.SAFETY, ErrorCategory.PERMISSION]:
            return True
        elif "user" in str(error).lower() or "confirm" in str(error).lower():
            return True
        else:
            return False
    
    def _log_error(self, error_info: ErrorInfo):
        """Log the error with appropriate level"""
        log_message = f"[{error_info.error_id}] {error_info.message}"
        if error_info.context:
            log_message += f" | Context: {error_info.context}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.ERROR:
            logger.error(log_message)
        elif error_info.severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Log traceback for errors and critical issues
        if error_info.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            logger.debug(f"Traceback for {error_info.error_id}:\n{error_info.traceback_info}")
    
    def get_error_history(self, limit: int = None) -> List[ErrorInfo]:
        """Get error history"""
        if limit:
            return self.error_history[-limit:]
        return self.error_history.copy()
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorInfo]:
        """Get errors by category"""
        return [error for error in self.error_history if error.category == category]
    
    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[ErrorInfo]:
        """Get errors by severity"""
        return [error for error in self.error_history if error.severity == severity]
    
    def clear_history(self):
        """Clear error history"""
        self.error_history.clear()
        logger.info("Error history cleared")
    
    def export_errors(self, filepath: str):
        """Export error history to file"""
        try:
            errors_data = [error.to_dict() for error in self.error_history]
            with open(filepath, 'w') as f:
                json.dump(errors_data, f, indent=2)
            logger.info(f"Exported {len(errors_data)} errors to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export errors: {e}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary statistics"""
        total_errors = len(self.error_history)
        if total_errors == 0:
            return {"total": 0}
        
        summary = {
            "total": total_errors,
            "by_severity": {},
            "by_category": {},
            "recoverable": 0,
            "user_action_required": 0,
            "recent_errors": []
        }
        
        # Count by severity
        for severity in ErrorSeverity:
            count = len(self.get_errors_by_severity(severity))
            summary["by_severity"][severity.value] = count
        
        # Count by category
        for category in ErrorCategory:
            count = len(self.get_errors_by_category(category))
            summary["by_category"][category.value] = count
        
        # Count recoverable and user action required
        summary["recoverable"] = sum(1 for error in self.error_history if error.recoverable)
        summary["user_action_required"] = sum(1 for error in self.error_history if error.user_action_required)
        
        # Get recent errors (last 10)
        summary["recent_errors"] = [
            {
                "id": error.error_id,
                "timestamp": error.timestamp.isoformat(),
                "severity": error.severity.value,
                "category": error.category.value,
                "message": error.message
            }
            for error in self.error_history[-10:]
        ]
        
        return summary

# Global error handler instance
error_handler = ErrorHandler()
