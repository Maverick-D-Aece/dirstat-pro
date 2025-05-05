"""Storage optimization utilities for folder-summary."""

import hashlib
import mimetypes
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .advanced_filters import (
    FileFilter,
    ParallelProcessor,
    ResultsCache,
    create_file_key,
)


class ChangeMonitor(FileSystemEventHandler):
    """Monitor file system changes."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def on_modified(self, event):
        """Handle file modification event."""
        if not event.is_directory:
            self.callback(Path(event.src_path))

    def on_created(self, event):
        """Handle file creation event."""
        if not event.is_directory:
            self.callback(Path(event.src_path))

    def on_deleted(self, event):
        """Handle file deletion event."""
        if not event.is_directory:
            self.callback(Path(event.src_path))


class StorageOptimizer:
    """Analyze and optimize storage usage."""

    # File patterns that might indicate temporary or cache files
    TEMP_PATTERNS = [
        r'.*\.tmp$',
        r'.*\.temp$',
        r'.*\.cache$',
        r'.*\.log$',
        r'\.DS_Store$',
        r'Thumbs\.db$',
        r'\.pytest_cache',
        r'__pycache__',
        r'node_modules',
        r'\.git/objects',
    ]

    # File extensions that are typically good candidates for compression
    COMPRESSIBLE_EXTENSIONS = {
        '.txt', '.log', '.csv', '.json', '.xml', '.html', '.md',
        '.yml', '.yaml', '.conf', '.config', '.ini'
    }

    def __init__(self, root_path: Path, enable_monitoring: bool = False):
        self.root_path = root_path
        self.duplicate_files: Dict[str, List[Path]] = {}
        self.large_files: List[Tuple[Path, int]] = []
        self.temp_files: List[Path] = []
        self.compression_candidates: List[Tuple[Path, int]] = []
        self.old_backups: List[Path] = []
        self.byte_counts: DefaultDict[int, int] = defaultdict(int)

        # Initialize advanced features
        self.file_filter = FileFilter()
        self.cache = ResultsCache(root_path)
        self.parallel_processor = ParallelProcessor()

        # Set up change monitoring if enabled
        self.enable_monitoring = enable_monitoring
        self._monitor: Optional[ChangeMonitor] = None
        self._observer: Optional[Observer] = None
        if enable_monitoring:
            self._setup_monitoring()

    def _setup_monitoring(self) -> None:
        """Set up file system monitoring."""
        if self._monitor is None:
            self._monitor = Observer()
            event_handler = FileSystemEventHandler()
            event_handler.on_modified = self._on_file_modified
            event_handler.on_created = self._on_file_created
            event_handler.on_deleted = self._on_file_deleted
            self._monitor.schedule(
                event_handler,
                str(self.root_path),
                recursive=True
            )

    def _handle_file_change(self, changed_path: Path) -> None:
        """Handle a file change event."""
        # Invalidate relevant cache entries
        self.cache.invalidate(str(changed_path))

        # Update analysis for the changed file
        if self.file_filter.matches(changed_path):
            self._update_analysis(changed_path)

    def _update_analysis(self, file_path: Path, size: Optional[int] = None) -> None:
        """Update storage analysis for a single file."""
        if size is None:
            try:
                size = file_path.stat().st_size
            except (OSError, FileNotFoundError):
                return

        # Update byte count distribution
        size_bucket = (size // 1024) * 1024  # Round to nearest KB
        self.byte_counts[size_bucket] = (
            self.byte_counts.get(size_bucket, 0) + 1
        )

        # Check for large files
        if size > self.large_file_threshold:
            self.large_files.append((file_path, size))

        # Check for duplicates using hash
        if size > 0:
            try:
                file_hash = self._compute_file_hash(file_path)
                if file_hash in self.file_hashes:
                    self.duplicate_files[file_hash] = [
                        p for p in self.duplicate_files[file_hash]
                        if p.exists()
                    ]
                    if file_path not in self.duplicate_files[file_hash]:
                        self.duplicate_files[file_hash].append(file_path)
                else:
                    self.file_hashes[file_hash] = file_path
            except (OSError, IOError):
                pass

    def _compute_file_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """Compute SHA-256 hash of a file in chunks."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def set_filters(self,
                   min_age: Optional[int] = None,
                   max_age: Optional[int] = None,
                   min_size: Optional[int] = None,
                   max_size: Optional[int] = None,
                   include_patterns: Optional[List[str]] = None,
                   exclude_patterns: Optional[List[str]] = None) -> None:
        """Set up filtering criteria."""
        if min_age is not None:
            self.file_filter.set_age_filter(min_age, older_than=True)
        if max_age is not None:
            self.file_filter.set_age_filter(max_age, older_than=False)

        if min_size is not None or max_size is not None:
            self.file_filter.set_size_range(min_size, max_size)

        if include_patterns or exclude_patterns:
            self.file_filter.set_patterns(include_patterns, exclude_patterns)

    def find_duplicate_files(self, min_size: int = 1024) -> Dict[str, List[Path]]:
        """Find duplicate files based on content hash."""
        cache_key = f"duplicates:{min_size}:{create_file_key(self.root_path)}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.duplicate_files = {
                h: [Path(p) for p in paths]
                for h, paths in cached_result.items()
            }
            return self.duplicate_files

        def process_file(file_path: Path) -> Optional[Tuple[str, Path]]:
            file_hash = self._compute_file_hash(file_path)
            return (file_hash, file_path) if file_hash else None

        # Process files in parallel
        results = self.parallel_processor.process_directory(
            self.root_path,
            process_file,
            self.file_filter
        )

        # Group results by hash
        hash_dict: Dict[str, List[Path]] = {}
        for result in results:
            if result:
                file_hash, file_path = result
                if file_hash in hash_dict:
                    hash_dict[file_hash].append(file_path)
                else:
                    hash_dict[file_hash] = [file_path]

        # Keep only entries with duplicates
        self.duplicate_files = {
            h: paths for h, paths in hash_dict.items()
            if len(paths) > 1
        }

        # Cache the results
        self.cache.set(
            cache_key,
            {h: [str(p) for p in paths] for h, paths in self.duplicate_files.items()}
        )
        return self.duplicate_files

    def find_large_files(self, min_size_mb: int = 100) -> List[Tuple[Path, int]]:
        """Find files larger than the specified size."""
        cache_key = f"large_files:{min_size_mb}:{create_file_key(self.root_path)}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.large_files = [(Path(p), s) for p, s in cached_result]
            return self.large_files

        min_size = min_size_mb * 1024 * 1024  # Convert to bytes
        self.file_filter.set_size_range(min_size=min_size)

        def process_file(file_path: Path) -> Optional[Tuple[Path, int]]:
            try:
                # Skip cache files
                if '.folder_summary_cache' in str(file_path):
                    return None
                size = file_path.stat().st_size
                if size >= min_size:
                    return (file_path, size)
                return None
            except (IOError, PermissionError):
                return None

        # Process files in parallel
        results = self.parallel_processor.process_directory(
            self.root_path,
            process_file,
            self.file_filter
        )

        # Filter and sort results
        self.large_files = sorted(
            [r for r in results if r is not None],
            key=lambda x: x[1],
            reverse=True
        )

        # Cache the results
        self.cache.set(cache_key, [(str(p), s) for p, s in self.large_files])
        return self.large_files

    def find_temp_files(self, max_age_days: int = 30) -> List[Path]:
        """Find temporary and cache files."""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        for file_path in self.root_path.rglob("*"):
            try:
                if file_path.is_file():
                    # Check if file matches temp patterns
                    if any(re.match(pattern, str(file_path)) for pattern in self.TEMP_PATTERNS):
                        # Check if file is older than cutoff
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if mtime < cutoff_time:
                            self.temp_files.append(file_path)
            except (IOError, PermissionError):
                continue

        return self.temp_files

    def find_compression_candidates(self, min_size: int = 1024) -> List[Tuple[Path, int]]:
        """Find files that could benefit from compression."""
        for file_path in self.root_path.rglob("*"):
            if file_path.is_file():
                try:
                    if file_path.suffix.lower() in self.COMPRESSIBLE_EXTENSIONS:
                        size = file_path.stat().st_size
                        if size >= min_size:
                            # Check if file has good compression potential
                            if self._check_compression_potential(file_path):
                                self.compression_candidates.append((file_path, size))
                except (IOError, PermissionError):
                    continue

        self.compression_candidates.sort(key=lambda x: x[1], reverse=True)
        return self.compression_candidates

    def find_old_backups(self, backup_patterns: Optional[List[str]] = None) -> List[Path]:
        """Find potential backup files."""
        if backup_patterns is None:
            backup_patterns = [
                r'.*\.bak$',
                r'.*\.backup$',
                r'.*\.old$',
                r'.*\.\d{8}$',  # Date-stamped files
                r'.*~$',  # Vim/Emacs backup files
            ]

        for file_path in self.root_path.rglob("*"):
            try:
                if file_path.is_file():
                    if any(re.match(pattern, str(file_path)) for pattern in backup_patterns):
                        self.old_backups.append(file_path)
            except (IOError, PermissionError):
                continue

        return self.old_backups

    def _check_compression_potential(self, file_path: Path, sample_size: int = 4096) -> bool:
        """Check if a file has good compression potential."""
        try:
            # Read a sample of the file
            with open(file_path, 'rb') as f:
                content = f.read(sample_size)

            # Check if the content is text-based
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type.startswith('text/'):
                return True

            # Check for high repetition in binary files
            if len(content) > 0:
                # Calculate entropy as a simple compression potential indicator
                byte_counts = {}
                for byte in content:
                    byte_counts[byte] = byte_counts.get(byte, 0) + 1

                entropy = sum(
                    (count / len(content)) * (count / len(content))
                    for count in byte_counts.values()
                )

                # Lower entropy suggests better compression potential
                return entropy < 0.5

        except (IOError, PermissionError):
            pass

        return False

    def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate a storage optimization report."""
        total_size = sum(
            size * count for size, count in self.byte_counts.items()
        )
        duplicate_size = sum(
            os.path.getsize(str(file))
            for file, _ in self.duplicate_files.items()
        )
        large_files_size = sum(
            size for _, size in self.large_files
        )
        old_backups_size = sum(
            os.path.getsize(str(file))
            for file in self.old_backups
        )

        return {
            'total_size': total_size,
            'duplicate_files': {
                'count': len(self.duplicate_files),
                'size': duplicate_size,
                'files': sorted(str(f) for f, _ in self.duplicate_files.items())
            },
            'large_files': {
                'count': len(self.large_files),
                'size': large_files_size,
                'threshold': self.large_file_threshold,
                'files': sorted(
                    (str(f), s) for f, s in self.large_files
                )
            },
            'old_backups': {
                'count': len(self.old_backups),
                'size': old_backups_size,
                'files': sorted(str(f) for f in self.old_backups)
            },
            'size_distribution': dict(sorted(
                self.byte_counts.items()
            ))
        }

    def estimate_savings(self) -> Dict[str, int]:
        """Estimate potential space savings."""
        savings = {
            'duplicates': 0,
            'temp_files': 0,
            'compression': 0,
            'old_backups': 0
        }

        # Calculate duplicate file savings
        for paths in self.duplicate_files.values():
            if paths:
                # Subtract one copy that we'd keep
                savings['duplicates'] += sum(p.stat().st_size for p in paths[1:])

        # Calculate temp file savings
        savings['temp_files'] = sum(f.stat().st_size for f in self.temp_files)

        # Estimate compression savings (assume 50% compression ratio)
        savings['compression'] = sum(
            size // 2 for _, size in self.compression_candidates
        )

        # Calculate backup file savings
        savings['old_backups'] = sum(f.stat().st_size for f in self.old_backups)

        return savings

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._observer:
            self._observer.stop()
            self._observer.join()

        if self.cache:
            self.cache.cache.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()