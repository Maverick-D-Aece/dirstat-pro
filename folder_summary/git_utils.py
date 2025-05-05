"""Git integration utilities for folder-summary."""

import subprocess
from pathlib import Path
from typing import Dict, Optional, Set


class GitInfo:
    """Class to handle Git-related information."""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self._git_root: Optional[Path] = None
        self._tracked_files: Optional[Set[Path]] = None
        self._status_cache: Dict[Path, str] = {}

    @property
    def is_git_repo(self) -> bool:
        """Check if the directory is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.root_path,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    @property
    def git_root(self) -> Optional[Path]:
        """Get the root directory of the git repository."""
        if self._git_root is None and self.is_git_repo:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.root_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self._git_root = Path(result.stdout.strip())
        return self._git_root

    def get_tracked_files(self) -> Set[Path]:
        """Get a set of all tracked files in the repository."""
        if self._tracked_files is None:
            self._tracked_files = set()
            if self.is_git_repo and self.git_root is not None:
                result = subprocess.run(
                    ["git", "ls-files"],
                    cwd=self.root_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    self._tracked_files = {
                        self.git_root / Path(f)
                        for f in result.stdout.splitlines()
                    }
        return self._tracked_files

    def get_file_status(self, file_path: Path) -> str:
        """Get the git status of a file."""
        if file_path not in self._status_cache and self.is_git_repo:
            git_root = self.git_root
            if git_root is not None:
                try:
                    abs_file_path = file_path.resolve()
                    abs_git_root = git_root.resolve()
                    rel_path = abs_file_path.relative_to(abs_git_root)
                    result = subprocess.run(
                        ["git", "status", "--porcelain", str(rel_path)],
                        cwd=git_root,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        status_line = result.stdout.strip()
                        if status_line:
                            self._status_cache[file_path] = status_line[:2]
                        else:
                            self._status_cache[file_path] = "  "  # Tracked, unchanged
                    else:
                        self._status_cache[file_path] = "??"  # Untracked
                except ValueError:
                    self._status_cache[file_path] = "??"  # Untracked

        return self._status_cache.get(file_path, "??")

    def is_ignored(self, file_path: Path) -> bool:
        """Check if a file is ignored by git."""
        if not self.is_git_repo:
            return False

        result = subprocess.run(
            ["git", "check-ignore", "-q", str(file_path)],
            cwd=self.root_path,
            capture_output=True,
        )
        return result.returncode == 0