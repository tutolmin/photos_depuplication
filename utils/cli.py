# utils/cli.py
"""
Command-line interface parser for the photo registry.
"""

import argparse

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Photo registry - deduplication and management for a single person"
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('add', help='Add new photos from src/ directory')
    subparsers.add_parser('dedup', help='Find and mark perceptual duplicates')
    subparsers.add_parser('dups', help='List all original photos that have duplicates (JSON)')
    subparsers.add_parser('stats', help='Show registry statistics')
    subparsers.add_parser('cleanup', help='Sync filesystem with current database after manual rollback')

    return parser
