import os
import re
import logging
from pathlib import Path
from typing import Union, Optional

def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a standard logger instance.
    
    Args:
        name: Name of the logger.
        log_file: Path to the log file. If None, logs to console only.
        level: Logging level (default: INFO).
    """
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler (if requested)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(str(log_path), encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

def format_bytes(size: float) -> str:
    """
    Converts raw bytes to human-readable string (e.g., 12.5 MB).
    """
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels.get(n, '')}B"

def sanitize_filename(name: str) -> str:
    """
    Removes illegal characters from filesystem paths.
    """
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def get_app_data_path(app_name: str) -> Path:
    """
    Returns the standard configuration path for the current OS.
    """
    if os.name == 'nt':
        base_path = Path(os.getenv('APPDATA', '.'))
    else:
        base_path = Path.home() / ".config"
    
    full_path = base_path / app_name
    full_path.mkdir(exist_ok=True)
    return full_path
