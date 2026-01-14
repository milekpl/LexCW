"""
Audio file validation utilities.
Provides functions to validate audio files for pronunciation uploads.
"""

import os
import mimetypes
from typing import Optional, Tuple
from pathlib import Path


def validate_audio_file(file_path: str) -> bool:
    """
    Validate that a file is a valid audio file.
    
    Args:
        file_path: Path to the audio file to validate
        
    Returns:
        bool: True if the file is a valid audio file, False otherwise
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return False
        
        # Check file size (not empty, not too large)
        file_size = os.path.getsize(file_path)
        if file_size == 0 or file_size > 10 * 1024 * 1024:  # 10MB max
            return False
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type or not mime_type.startswith('audio/'):
            # Try to validate by file extension
            allowed_extensions = {'.mp3', '.wav', '.ogg', '.opus', '.m4a'}
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in allowed_extensions:
                return False
        
        # Basic file header validation
        if not _validate_audio_header(file_path):
            return False
        
        return True
        
    except Exception:
        return False


def _validate_audio_header(file_path: str) -> bool:
    """
    Validate audio file by checking file headers/magic bytes.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        bool: True if the file has valid audio headers
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)  # Read first 16 bytes
        
        # MP3 file validation
        if header.startswith(b'ID3') or header.startswith(b'\xff\xfb') or header.startswith(b'\xff\xf3'):
            return True
        
        # WAV file validation
        if header.startswith(b'RIFF') and b'WAVE' in header:
            return True
        
        # OGG file validation
        if header.startswith(b'OggS'):
            return True
        
        # M4A/AAC file validation
        if b'ftyp' in header or header[4:8] == b'ftyp':
            return True
        
        # If we can't identify the format but it has a reasonable size, accept it
        # (Some audio files might not have standard headers)
        file_size = os.path.getsize(file_path)
        return file_size > 1000  # At least 1KB
        
    except Exception:
        return False


def get_audio_info(file_path: str) -> Optional[Tuple[str, int, Optional[str]]]:
    """
    Get audio file information.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple of (filename, file_size, mime_type) or None if invalid
    """
    try:
        if not validate_audio_file(file_path):
            return None
        
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return filename, file_size, mime_type
        
    except Exception:
        return None


def is_audio_file_extension(filename: str) -> bool:
    """
    Check if a filename has a valid audio file extension.
    
    Args:
        filename: The filename to check
        
    Returns:
        bool: True if the filename has a valid audio extension
    """
    allowed_extensions = {'.mp3', '.wav', '.ogg', '.opus', '.m4a'}
    return Path(filename).suffix.lower() in allowed_extensions
