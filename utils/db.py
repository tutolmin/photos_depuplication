# utils/db.py
"""
Database operations for the photo registry.

Uses sqlite3 from the standard library.
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

def get_connection(db_path: Path) -> sqlite3.Connection:
    """Return a connection to the SQLite database.

    Enables foreign keys and row factory for dict-like access.
    """
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Error opening database: {e}")
        raise SystemExit(1)

def photo_exists(conn: sqlite3.Connection, md5_hash: str) -> bool:
    """Check if a photo with the given MD5 hash already exists."""
    cur = conn.execute("SELECT 1 FROM photos WHERE md5_hash = ?", (md5_hash,))
    return cur.fetchone() is not None

def add_photo(conn: sqlite3.Connection, md5_hash: str,
              file_size: int, width: int, height: int) -> int:
    """Insert a new photo record and return its id."""
    added_at = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    cur = conn.execute(
        "INSERT INTO photos (md5_hash, file_size, width, height, added_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (md5_hash, file_size, width, height, added_at)
    )
    conn.commit()
    return cur.lastrowid

def set_as_duplicate(conn: sqlite3.Connection, duplicate_id: int,
                     original_id: int, score: float) -> None:
    """Mark a photo as a duplicate of an original."""
    conn.execute(
        "UPDATE photos SET original_id = ?, score = ? WHERE id = ?",
        (original_id, score, duplicate_id)
    )
    conn.commit()

def get_unclassified_photos(conn: sqlite3.Connection) -> List[Dict]:
    """Return all photos that are not yet marked as duplicates.

    These are files in the `files/` directory (original_id IS NULL).
    """
    cur = conn.execute(
        "SELECT id, md5_hash, file_size, width, height, added_at "
        "FROM photos WHERE original_id IS NULL"
    )
    return [dict(row) for row in cur.fetchall()]

def get_photo_by_hash(conn: sqlite3.Connection, md5_hash: str) -> Optional[Dict]:
    """Retrieve a single photo record by its MD5 hash."""
    cur = conn.execute(
        "SELECT id, md5_hash, original_id, file_size, width, height, added_at "
        "FROM photos WHERE md5_hash = ?",
        (md5_hash,)
    )
    row = cur.fetchone()
    return dict(row) if row else None

def get_duplicate_groups(conn: sqlite3.Connection) -> List[Dict]:
    """Return originals and their duplicates for the 'dups' command."""
    # Find distinct original_ids that have duplicates
    cur = conn.execute(
        "SELECT DISTINCT original_id FROM photos WHERE original_id IS NOT NULL"
    )
    original_ids = [row[0] for row in cur.fetchall()]

    groups = []
    for orig_id in original_ids:
        # fetch original
        orig = conn.execute(
            "SELECT id, md5_hash, width, height, file_size, added_at FROM photos WHERE id = ?",
            (orig_id,)
        ).fetchone()
        if not orig:
            continue
        original = dict(orig)
        # fetch duplicates
        dups = conn.execute(
            "SELECT id, md5_hash, width, height, file_size, score, added_at FROM photos WHERE original_id = ?",
            (orig_id,)
        ).fetchall()
        groups.append({
            "original_id": original["id"],
            "original_width": original["width"],
            "original_height": original["height"],
            "original_file_size": original["file_size"],
            "original_path": f"files/{original['md5_hash']}.jpg",
            "original_added_at": original["added_at"].replace(" ", "T"),
            "duplicates": [
                {
                    "id": d["id"],
                    "width": d["width"],
                    "height": d["height"],
                    "file_size": d["file_size"],
                    "score": d["score"],
                    "path": f"dups/{d['md5_hash']}.jpg",
                    "added_at": d["added_at"].replace(" ", "T")
                }
                for d in dups
            ]
        })

    return groups

def get_stats(conn: sqlite3.Connection) -> Dict:
    """Collect statistics for the registry."""
    total = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
    originals = conn.execute(
        "SELECT COUNT(*) FROM photos WHERE original_id IS NULL"
    ).fetchone()[0]
    duplicates = total - originals
    last_addition = conn.execute(
        "SELECT MAX(added_at) FROM photos"
    ).fetchone()[0]
    dup_groups = conn.execute(
        "SELECT COUNT(DISTINCT original_id) FROM photos WHERE original_id IS NOT NULL"
    ).fetchone()[0]
    total_size = conn.execute(
        "SELECT COALESCE(SUM(file_size), 0) FROM photos"
    ).fetchone()[0]

    return {
        "total": total,
        "originals": originals,
        "duplicates": duplicates,
        "last_addition": last_addition,
        "duplicate_groups": dup_groups,
        "total_size": total_size,
    }

def get_all_photos_with_status(conn: sqlite3.Connection) -> Dict[str, bool]:
    """Return a mapping from md5_hash to True if original (in files/), False if duplicate (in dups/)."""
    cur = conn.execute("SELECT md5_hash, original_id FROM photos")
    result = {}
    for row in cur.fetchall():
        result[row[0]] = (row[1] is None)  # True = original -> files/
    return result

def backup_database(db_dir: Path) -> None:
    """Create a timestamped backup of registry.db in the same directory."""
    src = db_dir / "registry.db"
    if not src.exists():
        print("No database to backup.")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = db_dir / f"registry_{timestamp}.db"
    shutil.copy2(src, dst)
    print(f"Database backed up to {dst}")
