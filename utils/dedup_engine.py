# utils/dedup_engine.py
"""
Wrapper around imagededup for perceptual duplicate detection.

Uses perceptual hash (phash) to avoid heavy TensorFlow dependency.
"""

from pathlib import Path
from typing import List, Dict, Set, Tuple, Any
from imagededup.methods import PHash

def find_duplicate_groups(files_dir: Path) -> Tuple[List[List[str]], Dict[str, Any]]:
    """
    Scan the given directory for perceptually similar images using phash.

    Returns:
        groups: list of lists, each inner list contains filenames (with extension)
                that are considered duplicates of each other.
        encodings: dict mapping filename -> hash (binary array) for later score calculation.
    """
    if not files_dir.exists():
        return [], {}

    phasher = PHash()
    # Generate encodings for all JPEG files in the directory
    encodings = phasher.encode_images(image_dir=str(files_dir))

    if not encodings:
        return [], {}

    # Use imagededup's built-in method to find duplicates (max distance threshold 10)
    duplicates_dict = phasher.find_duplicates(encoding_map=encodings,
                                              max_distance_threshold=10)

    # Build graph to find connected components (groups)
    # duplicates_dict: filename -> [list of duplicate filenames]
    graph = {}
    for filename, dup_list in duplicates_dict.items():
        if filename not in graph:
            graph[filename] = set()
        for dup in dup_list:
            graph[filename].add(dup)
            if dup not in graph:
                graph[dup] = set()
            graph[dup].add(filename)

    visited = set()
    groups = []
    for node in graph:
        if node not in visited:
            component = set()
            stack = [node]
            while stack:
                current = stack.pop()
                if current not in visited:
                    visited.add(current)
                    component.add(current)
                    stack.extend(graph[current] - visited)
            if len(component) > 1:  # only groups with more than one file are relevant
                groups.append(list(component))

    return groups, encodings
