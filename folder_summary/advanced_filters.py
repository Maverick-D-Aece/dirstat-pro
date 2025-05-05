"""Advanced filtering and performance optimization utilities."""

import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import humanize
import pathspec
from diskcache import Cache
from joblib import Parallel, delayed
from watchdog.events import FileSystemEventHandler


class FileFilter:
    """Advanced file filtering capabilities."""

    def __init__(self) -> None:
        self.size_min: Optional[int] = None
        self.size_max: Optional[int] = None
        self.age_min: Optional[timedelta] = None
        self.age_max: Optional[timedelta] = None
        self.extensions: Optional[Set[str]] = None
        self.exclude_patterns: Set[str] = set()
        self.include_patterns: List[str] = []
        self._spec: Optional[pathspec.PathSpec] = None
        self.exclude_spec: Optional[pathspec.PathSpec] = None

    def set_size_range(
        self,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None
    ) -> None:
        """Set size range filter."""
        self.size_min = min_size
        self.size_max = max_size

    def set_age_filter(self, days: int, older_than: bool = True) -> None:
        """Set age filter in days."""
        if older_than:
            self.age_min = timedelta(days=days)
        else:
            self.age_max = timedelta(days=days)

    def set_age_range(self, min_age: Optional[str] = None, max_age: Optional[str] = None) -> None:
        """Set age range filter using human-readable time spans."""
        if min_age:
            self.age_min = self._parse_age(min_age)
        if max_age:
            self.age_max = self._parse_age(max_age)

    def set_extensions(self, extensions: List[str]) -> None:
        """Set allowed file extensions."""
        self.extensions = {ext.lower() for ext in extensions}

    def add_exclude_pattern(self, pattern: str) -> None:
        """Add a pattern to exclude from results."""
        self.exclude_patterns.add(pattern)

    def set_patterns(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> None:
        """Set include and exclude patterns for file filtering."""
        if include_patterns is not None:
            self.include_patterns = [re.compile(pattern) for pattern in include_patterns]
        if exclude_patterns is not None:
            self.exclude_patterns = [re.compile(pattern) for pattern in exclude_patterns]

    def set_size_constraints(
        self,
        min_size: Optional[str] = None,
        max_size: Optional[str] = None
    ) -> None:
        """Set minimum and maximum size constraints for file filtering."""
        self.min_size = self._parse_size(min_size) if min_size else None
        self.max_size = self._parse_size(max_size) if max_size else None

    def set_date_constraints(
        self,
        min_age: Optional[str] = None,
        max_age: Optional[str] = None
    ) -> None:
        """Set minimum and maximum age constraints for file filtering."""
        self.min_age = self._parse_duration(min_age) if min_age else None
        self.max_age = self._parse_duration(max_age) if max_age else None

    def _parse_duration(self, duration_str: Optional[str]) -> Optional[float]:
        """Parse a duration string into seconds."""
        if not duration_str:
            return None

        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800,
            'M': 2592000,  # 30 days
            'y': 31536000  # 365 days
        }

        match = re.match(r'^(\d+)([smhdwMy])$', duration_str)
        if not match:
            raise ValueError(
                f"Invalid duration format: {duration_str}. "
                "Use format: <number><unit> (s=seconds, m=minutes, h=hours, "
                "d=days, w=weeks, M=months, y=years)"
            )

        value, unit = match.groups()
        return int(value) * units[unit]

    def matches(self, file_path: Path) -> bool:
        """Check if a file matches all filter criteria."""
        try:
            stats = file_path.stat()

            # Check size constraints
            if self.size_min is not None and stats.st_size < self.size_min:
                return False
            if self.size_max is not None and stats.st_size > self.size_max:
                return False

            # Check age constraints
            file_age = datetime.now().timestamp() - stats.st_mtime
            if self.age_min and file_age < self.age_min.total_seconds():
                return False
            if self.age_max and file_age > self.age_max.total_seconds():
                return False

            # Check extension
            if self.extensions and file_path.suffix.lower() not in self.extensions:
                return False

            # Check exclude patterns
            if any(pattern in str(file_path) for pattern in self.exclude_patterns):
                return False

            # Check patterns
            str_path = str(file_path)
            if self.exclude_spec and self.exclude_spec.match_file(str_path):
                return False
            if self._spec is not None:
                return self._spec.match_file(str_path)

            return True
        except (OSError, PermissionError):
            return False

    def _parse_age(self, age_str: str) -> timedelta:
        """Parse a human-readable age string into a timedelta."""
        units: Dict[str, int] = {
            'd': 1,
            'w': 7,
            'm': 30,
            'y': 365
        }

        value = int(''.join(filter(str.isdigit, age_str)))
        unit = ''.join(filter(str.isalpha, age_str)).lower()

        if unit not in units:
            raise ValueError(f"Invalid age unit: {unit}")

        return timedelta(days=value * units[unit])

    def generate_report(self) -> Dict[str, Any]:
        """Generate a report of the current filter settings."""
        report: Dict[str, Any] = {}

        if self.size_min:
            report['min_size'] = humanize.naturalsize(self.size_min)
        if self.size_max:
            report['max_size'] = humanize.naturalsize(self.size_max)

        if self.age_min:
            report['min_age'] = str(self.age_min)
        if self.age_max:
            report['max_age'] = str(self.age_max)

        if self.extensions:
            report['extensions'] = list(self.extensions)

        if self.exclude_patterns:
            report['exclude_patterns'] = list(self.exclude_patterns)

        return report


class ChangeMonitor(FileSystemEventHandler):
    """Monitor file system changes for incremental updates."""

    def __init__(self, callback):
        self.callback = callback
        self.changes: Set[Path] = set()
        self._last_event_time = time.time()
        self._debounce_interval = 1.0  # seconds

    def on_any_event(self, event):
        """Handle any file system event."""
        if event.is_directory:
            return

        current_time = time.time()
        if current_time - self._last_event_time >= self._debounce_interval:
            path = Path(event.src_path)
            self.changes.add(path)
            self.callback(path)
            self._last_event_time = current_time


class ResultsCache:
    """Cache for storing analysis results."""

    def __init__(self, cache_dir: Path):
        self.cache = Cache(str(cache_dir / '.folder_summary_cache'))
        self.max_age = 3600  # 1 hour default cache lifetime

    def get(self, key: str) -> Optional[Any]:
        """Get cached result."""
        try:
            value, timestamp = self.cache.get(key, default=(None, None))
            if value is not None and time.time() - timestamp <= self.max_age:
                return value
        except Exception:
            pass
        return None

    def set(self, key: str, value: Any) -> None:
        """Cache a result."""
        try:
            self.cache.set(key, (value, time.time()))
        except Exception:
            pass

    def invalidate(self, pattern: str = None) -> None:
        """Invalidate cache entries."""
        if pattern:
            keys = [k for k in self.cache.iterkeys() if pattern in k]
            for key in keys:
                self.cache.delete(key)
        else:
            self.cache.clear()


class ParallelProcessor:
    """Handle parallel processing of large directories."""

    def __init__(self, n_jobs: int = -1, batch_size: int = 100):
        self.n_jobs = n_jobs
        self.batch_size = batch_size

    def process_directory(
        self,
        root_path: Path,
        processor_func,
        file_filter: FileFilter
    ) -> List[Any]:
        """Process directory in parallel."""
        all_files = [
            f for f in root_path.rglob("*")
            if f.is_file() and file_filter.matches(f)
        ]

        # Split files into batches
        batches = [
            all_files[i:i + self.batch_size]
            for i in range(0, len(all_files), self.batch_size)
        ]

        # Process batches in parallel
        with Parallel(n_jobs=self.n_jobs) as parallel:
            results = parallel(
                delayed(self._process_batch)(batch, processor_func)
                for batch in batches
            )

        # Flatten results
        return [item for batch_result in results for item in batch_result]

    @staticmethod
    def _process_batch(files: List[Path], processor_func) -> List[Any]:
        """Process a batch of files."""
        return [processor_func(f) for f in files]


def create_file_key(file_path: Path) -> str:
    """Create a unique key for a file based on path and metadata."""
    try:
        stat = file_path.stat()
        return f"{file_path}:{stat.st_size}:{stat.st_mtime}"
    except (OSError, PermissionError):
        return str(file_path)