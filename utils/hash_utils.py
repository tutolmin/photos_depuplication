# utils/hash_utils.py
"""
Utility functions for MD5 validation and JPEG detection/dimension extraction.
"""

import hashlib
from pathlib import Path
from typing import Optional, Tuple

def extract_md5_from_filename(filename: str) -> Optional[str]:
    """Return the MD5 hash from a filename by removing the '.jpg' extension.

    Validates that the hash is exactly 32 hexadecimal characters.
    """
    if not filename.lower().endswith('.jpg'):
        return None
    name = filename[:-4]
    if len(name) != 32:
        return None
    if not all(c in '0123456789abcdefABCDEF' for c in name):
        return None
    return name.lower()  # normalise to lowercase

def is_jpeg(filepath: Path) -> bool:
    """Check if a file is a JPEG by looking for the SOI marker (FF D8)."""
    try:
        with open(filepath, 'rb') as f:
            return f.read(2) == b'\xff\xd8'
    except Exception:
        return False

def get_jpeg_dimensions(filepath: Path) -> Optional[Tuple[int, int]]:
    """Return (width, height) of a JPEG image by parsing its markers.

    Supports SOF0..SOF3 markers. Returns None on failure.
    """
    try:
        with open(filepath, 'rb') as f:
            # First two bytes are already checked as 0xFF 0xD8
            f.seek(2)
            while True:
                byte = f.read(1)
                if byte != b'\xff':
                    continue  # should not happen in valid JPEG
                # skip padding 0xFF bytes
                while byte == b'\xff':
                    byte = f.read(1)
                marker = byte[0]
                if marker == 0xD8:  # SOI (shouldn't appear again)
                    continue
                if marker == 0xD9:  # EOI
                    break
                if 0xC0 <= marker <= 0xC3:  # SOF0 - SOF3
                    length = int.from_bytes(f.read(2), 'big')
                    precision = f.read(1)[0]
                    height = int.from_bytes(f.read(2), 'big')
                    width = int.from_bytes(f.read(2), 'big')
                    return width, height
                else:
                    # skip other markers by reading length
                    length_bytes = f.read(2)
                    if len(length_bytes) < 2:
                        break
                    length = int.from_bytes(length_bytes, 'big')
                    f.seek(length - 2, 1)  # skip the rest of the segment
        return None
    except Exception:
        return None
