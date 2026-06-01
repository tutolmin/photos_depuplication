# utils/file_utils.py
"""
File system operations: moving, deleting, listing files.
"""

import os
import shutil
from pathlib import Path
from typing import List, Set

def ensure_directory(path: Path) -> None:
    """Create directory if it doesn't exist (though the spec says they pre-exist)."""
    path.mkdir(parents=True, exist_ok=True)

def move_file(src: Path, dst: Path) -> None:
    """Move a file, overwriting if necessary."""
    try:
        shutil.move(str(src), str(dst))
    except PermissionError as e:
        print(f"Permission denied while moving {src} -> {dst}: {e}")
        raise SystemExit(1)
    except Exception as e:
        print(f"Error moving {src}: {e}")
        raise SystemExit(1)

def delete_file(path: Path) -> None:
    """Delete a file permanently."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except PermissionError as e:
        print(f"Permission denied while deleting {path}: {e}")
        raise SystemExit(1)

def list_jpg_files(directory: Path) -> List[str]:
    """Return sorted list of .jpg filenames (with extension) in the directory."""
    if not directory.is_dir():
        return []
    return sorted(f.name for f in directory.glob('*.jpg'))

def get_file_size(path: Path) -> int:
    """Return file size in bytes."""
    return path.stat().st_size

def cleanup_sync(files_dir: Path, dups_dir: Path, db_hashes: dict) -> None:
    """
    Remove files from files/ and dups/ that are not present in the database.
    db_hashes: dict mapping md5_hash -> True if original (should be in files/),
               False if duplicate (should be in dups/).
    """
    # Collect expected files
    expected_files = set()
    expected_dups = set()
    for md5, is_original in db_hashes.items():
        if is_original:
            expected_files.add(f"{md5}.jpg")
        else:
            expected_dups.add(f"{md5}.jpg")

    # Clean files/ directory
    for fname in list_jpg_files(files_dir):
        if fname not in expected_files:
            file_path = files_dir / fname
            print(f"Removing orphaned file: {file_path}")
            delete_file(file_path)

    # Clean dups/ directory
    for fname in list_jpg_files(dups_dir):
        if fname not in expected_dups:
            file_path = dups_dir / fname
            print(f"Removing orphaned duplicate: {file_path}")
            delete_file(file_path)
