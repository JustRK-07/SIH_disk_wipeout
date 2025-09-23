"""
Logging configuration for Disk Wipeout application
"""

import logging
import os
from pathlib import Path
from datetime import datetime

def setup_logger(log_level=logging.INFO, log_file=None):
    """
    Setup logging configuration for the application
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Optional log file path (default: auto-generated)
    """
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Generate log file name if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"disk_wipeout_{timestamp}.log"
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Disk Wipeout logging initialized - Log file: {log_file}")
    
    return logger
