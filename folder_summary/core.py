"""Core functionality for folder metadata processing."""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import humanize

from .git_utils import GitInfo


class FileStats:
    """Statistics for a file type."""
    def __init__(self, count: int = 0, total_size: int = 0):
        self.count = count
        self.total_size = total_size


class DirectoryMetadata:
    """Class to hold and process directory metadata."""

    def __init__(self, path: Path):
        self.path = path
        self.total_files = 0
        self.total_subdirs = 0
        self.total_size = 0
        self.extension_stats: Dict[str, FileStats] = defaultdict(FileStats)
        self.largest_files: List[Tuple[Path, int]] = []
        self.timestamp = datetime.now()
        self.git_info: Optional[GitInfo] = None
        self.git_tracked_files = 0
        self.git_modified_files = 0
        self.git_untracked_files = 0

    def process_directory(
        self,
        include_hidden: bool = False,
        git_integration: bool = False,
        git_only: bool = False
    ) -> None:
        """Process the directory and collect metadata."""
        if git_integration:
            self.git_info = GitInfo(self.path)
            if git_only and not self.git_info.is_git_repo:
                return

        for item in self.path.iterdir():
            # Skip hidden files/directories if not included
            if not include_hidden and item.name.startswith('.'):
                continue

            # Skip .git directory by default in git mode
            if git_integration and item.name == '.git':
                continue

            # Skip non-git files in git-only mode
            if git_only and self.git_info and item.is_file():
                if item not in self.git_info.get_tracked_files():
                    continue

            if item.is_file():
                self._process_file(item, git_integration)
            elif item.is_dir():
                self.total_subdirs += 1

    def _process_file(self, file_path: Path, git_integration: bool = False) -> None:
        """Process a single file and update statistics."""
        try:
            file_size = file_path.stat().st_size
            self.total_files += 1
            self.total_size += file_size

            # Update extension statistics
            ext = file_path.suffix.lower() if file_path.suffix else '(no extension)'
            current_stats = self.extension_stats[ext]
            self.extension_stats[ext] = FileStats(
                current_stats.count + 1,
                current_stats.total_size + file_size
            )

            # Update largest files list
            self.largest_files.append((file_path, file_size))
            self.largest_files.sort(key=lambda x: x[1], reverse=True)
            self.largest_files = self.largest_files[:5]

            # Process git information if enabled
            if git_integration and self.git_info and self.git_info.is_git_repo:
                status = self.git_info.get_file_status(file_path)
                if status == "??":
                    self.git_untracked_files += 1
                elif status != "  ":
                    self.git_modified_files += 1
                else:
                    self.git_tracked_files += 1

        except (PermissionError, OSError):
            pass

    def _format_size(self, size: int, human_readable: bool = True) -> str:
        """Format file size in a human-readable format."""
        if human_readable:
            return humanize.naturalsize(size)
        return str(size)

    def _format_count(self, count: int) -> str:
        """Format count in a human-readable format."""
        if count > 1000:
            return humanize.intcomma(count)
        return str(count)

    def generate_summary(self, human_readable: bool = True, git_integration: bool = False) -> str:
        """Generate a formatted summary of the directory metadata."""
        summary = [
            f"📁 Directory Summary for: {self.path}",
            f"📅 Generated on: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 50,
            "📊 Statistics:",
            f"  • Total Files: {self._format_count(self.total_files)}",
            f"  • Total Subdirectories: {self.total_subdirs}",
            f"  • Total Size: {self._format_size(self.total_size, human_readable)}",
        ]

        # Add Git information if available
        if git_integration and self.git_info and self.git_info.is_git_repo:
            summary.extend([
                "\n🔄 Git Status:",
                f"  • Tracked (unchanged): {self.git_tracked_files} files",
                f"  • Modified/Staged: {self.git_modified_files} files",
                f"  • Untracked: {self.git_untracked_files} files",
            ])

        # Add extension statistics
        summary.extend(["\n📋 Files by Extension:"])
        sorted_extensions = sorted(
            self.extension_stats.items(),
            key=lambda x: x[1].total_size,
            reverse=True
        )
        for ext, stats in sorted_extensions:
            ext_name = ext if ext else "(no extension)"
            size = self._format_size(stats.total_size, human_readable)
            count = self._format_count(stats.count)
            summary.append(f"  • {ext_name:<15} {count:>8} files {size:>10}")

        # Add largest files
        if self.largest_files:
            summary.extend(["\n📦 Largest Files:"])
            for file_path, size in self.largest_files:
                size_str = self._format_size(size, human_readable)
                status = ""
                if git_integration and self.git_info and self.git_info.is_git_repo:
                    git_status = self.git_info.get_file_status(file_path)
                    if git_status != "  ":
                        status = f" [{git_status}]"
                summary.append(f"  • {file_path.name}: {size_str}{status}")

        return "\n".join(summary)


def process_directory(
    root_path: Path,
    depth: Optional[int] = None,
    include_hidden: bool = False,
    output_name: str = ".folder_summary.txt",
    dry_run: bool = False,
    human_readable: bool = True,
    git_integration: bool = False,
    git_only: bool = False,
) -> Dict[Path, DirectoryMetadata]:
    """
    Recursively process directories and generate metadata summaries.

    Args:
        root_path: Starting directory path
        depth: Maximum depth to traverse (None for unlimited)
        include_hidden: Whether to include hidden files/directories
        output_name: Name of the summary file to create
        dry_run: If True, don't write files
        human_readable: Use human-readable file sizes
        git_integration: Enable Git integration features
        git_only: Only process Git-tracked files

    Returns:
        Dictionary mapping directory paths to their metadata
    """
    results: Dict[Path, DirectoryMetadata] = {}

    def _process_recursive(current_path: Path, current_depth: int) -> None:
        if depth is not None and current_depth > depth:
            return

        metadata = DirectoryMetadata(current_path)
        metadata.process_directory(
            include_hidden=include_hidden,
            git_integration=git_integration,
            git_only=git_only
        )
        results[current_path] = metadata

        if not dry_run:
            summary_path = current_path / output_name
            try:
                summary_path.write_text(metadata.generate_summary(
                    human_readable=human_readable,
                    git_integration=git_integration
                ))
            except (PermissionError, OSError):
                pass

        # Process subdirectories
        for item in current_path.iterdir():
            if item.is_dir():
                if include_hidden or not item.name.startswith('.'):
                    if not (git_integration and item.name == '.git'):
                        _process_recursive(item, current_depth + 1)

    _process_recursive(root_path, 0)
    return results