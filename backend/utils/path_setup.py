"""
Path setup utilities for the backend.
This module provides functions to set up Python paths without hardcoding.
"""

import sys
from pathlib import Path


def setup_backend_path():
    """
    Set up the backend directory in Python path.
    This function determines the backend directory dynamically and adds it to sys.path.
    """
    # Get the current file's directory
    current_file = Path(__file__)
    
    # Navigate to the backend directory (utils -> backend)
    backend_dir = current_file.parent.parent
    
    # Add to Python path if not already there
    backend_dir_str = str(backend_dir)
    if backend_dir_str not in sys.path:
        sys.path.insert(0, backend_dir_str)
    
    return backend_dir


def get_backend_dir():
    """
    Get the backend directory path.
    Returns the Path object for the backend directory.
    """
    current_file = Path(__file__)
    return current_file.parent.parent 