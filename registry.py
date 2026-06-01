# registry.py
#!/usr/bin/env python3
"""
Photo Registry – main entry point.

Manages a single-person photo archive with MD5-based filenames and perceptual
deduplication.
"""

import sys
import json
from pathlib import Path

from utils.cli import create_parser
from utils.db import (
    get_connection, photo_exists, add_photo, set_as_duplicate,
    get_unclassified_photos, get_photo_by_hash, get_duplicate_groups,
    get_stats, get_all_photos_with_status, backup_database
)
from utils.hash_utils import extract_md5_from_filename, is_jpeg, get_jpeg_dimensions
from utils.dedup_engine import find_duplicate_groups
from utils.file_utils import move_file, delete_file, list_jpg_files, get_file_size, cleanup_sync

# Assume the script is run from the work_dir
WORK_DIR = Path.cwd()
FILES_DIR = WORK_DIR / "files"
DUPS_DIR = WORK_DIR / "dups"
DB_DIR = WORK_DIR / "db"
SRC_DIR = WORK_DIR / "src"
DB_PATH = DB_DIR / "registry.db"

def cmd_add():
    """Add new photos from src/ directory."""
    if not SRC_DIR.is_dir():
        print("Source directory 'src' does not exist. Nothing to add.")
        return

    # Backup database
    backup_database(DB_DIR)

    conn = get_connection(DB_PATH)
    try:
        jpg_files = list_jpg_files(SRC_DIR)
        if not jpg_files:
            print("No JPEG files found in src/")
            return

        for filename in jpg_files:
            filepath = SRC_DIR / filename
            # Verify JPEG signature
            if not is_jpeg(filepath):
                print(f"Skipping non-JPEG file: {filename}")
                continue

            md5 = extract_md5_from_filename(filename)
            if md5 is None:
                print(f"Skipping file with invalid MD5 name: {filename}")
                continue

            # Check existence in DB
            if photo_exists(conn, md5):
                print(f"Hash {md5} already exists in registry. Deleting source file.")
                delete_file(filepath)
                continue

            # Extract image dimensions
            dims = get_jpeg_dimensions(filepath)
            if dims is None:
                print(f"Unable to read dimensions from {filename}. Skipping.")
                continue
            width, height = dims
            file_size = get_file_size(filepath)

            # Move to files/
            dest = FILES_DIR / f"{md5}.jpg"
            move_file(filepath, dest)
            print(f"Added: {md5}.jpg ({width}x{height}, {file_size} bytes)")

            # Insert into DB
            add_photo(conn, md5, file_size, width, height)

    finally:
        conn.close()

def select_original(photos, encodings):
    """
    Given a list of photo dicts (must include md5_hash, width, height, file_size)
    and the encodings map, select the best candidate as the original following the policy:
    1. Maximum resolution (width * height)
    2. Maximum file size
    3. При равенстве — любой (например, первый)
    Returns the photo dict of the chosen original.
    """
    return max(photos, key=lambda p: (
        p.get('width', 0) * p.get('height', 0),
        p.get('file_size', 0)
    ))

def cmd_dedup():
    """Find and mark perceptual duplicates in files/ directory."""
    conn = get_connection(DB_PATH)
    try:
        # Run imagededup on the entire files/ directory
        groups, encodings = find_duplicate_groups(FILES_DIR)

        if not groups:
            print("No duplicate groups found.")
            return

        for group in groups:
            # group is a list of filenames like "abc123...jpg"
            # Retrieve their DB records
            photos = []
            for fname in group:
                md5 = fname.replace('.jpg', '')
                rec = get_photo_by_hash(conn, md5)
                if rec:
                    photos.append(rec)
                else:
                    # Should not happen for files in files/
                    print(f"Warning: file {fname} not found in DB, skipping.")
                    continue

            if not photos:
                continue

            # Select original among them
            original = select_original(photos, encodings)
            original_md5 = original['md5_hash']
            original_id = original['id']

            # For the others, mark as duplicates and move
            for photo in photos:
                if photo['id'] == original_id:
                    # This one stays in files/ (already there)
                    # Ensure it is marked as original (original_id NULL)
                    if photo['original_id'] is not None:
                        # Just in case, set it to NULL
                        conn.execute("UPDATE photos SET original_id=NULL, score=NULL WHERE id=?",
                                     (original_id,))
                        conn.commit()
                    continue

                # Compute similarity score using hamming distance of phash
                # encodings is dict with filenames as keys
                original_enc = encodings.get(original_md5 + '.jpg')
                duplicate_enc = encodings.get(photo['md5_hash'] + '.jpg')
                if original_enc is not None and duplicate_enc is not None:
                    # Compute hamming distance
                    dist = sum(o != d for o, d in zip(original_enc, duplicate_enc))
                    score = max(0.0, 1.0 - (dist / 64.0))
                else:
                    score = 0.0

                # Move the duplicate file from files/ to dups/
                src_path = FILES_DIR / f"{photo['md5_hash']}.jpg"
                dst_path = DUPS_DIR / f"{photo['md5_hash']}.jpg"
                move_file(src_path, dst_path)
                print(f"Moved duplicate: {photo['md5_hash']}.jpg -> dups/ (score: {score:.3f})")

                # Update DB
                set_as_duplicate(conn, photo['id'], original_id, score)

        conn.commit()
    finally:
        conn.close()

def cmd_dups():
    """Output JSON with all originals that have duplicates."""
    conn = get_connection(DB_PATH)
    try:
        groups = get_duplicate_groups(conn)
        output = {
            "total_duplicate_groups": len(groups),
            "groups": groups
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    finally:
        conn.close()

def human_readable_size(size_bytes: int) -> str:
    """Convert bytes to a human-readable string (e.g., 1.2 GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"

def cmd_stats():
    """Print registry statistics."""
    conn = get_connection(DB_PATH)
    try:
        stats = get_stats(conn)
        last = stats['last_addition'] or 'N/A'
        print("=== Statistics ===")
        print(f"Total photos in database: {stats['total']}")
        print(f"  - Originals (in files/): {stats['originals']}")
        print(f"  - Duplicates (in dups/): {stats['duplicates']}")
        print(f"Last addition: {last}")
        print(f"Duplicate groups: {stats['duplicate_groups']}")
        print(f"Total disk usage: {human_readable_size(stats['total_size'])}")
    finally:
        conn.close()

def cmd_cleanup():
    """Remove files from files/ and dups/ that are not in the current database."""
    conn = get_connection(DB_PATH)
    try:
        hashes = get_all_photos_with_status(conn)
        cleanup_sync(FILES_DIR, DUPS_DIR, hashes)
        print("Cleanup complete.")
    finally:
        conn.close()

def main():
    parser = create_parser()
    args = parser.parse_args()

    # Dispatch command
    if args.command == 'add':
        cmd_add()
    elif args.command == 'dedup':
        cmd_dedup()
    elif args.command == 'dups':
        cmd_dups()
    elif args.command == 'stats':
        cmd_stats()
    elif args.command == 'cleanup':
        cmd_cleanup()

if __name__ == "__main__":
    main()
