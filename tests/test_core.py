"""Tests for the core functionality."""

import os
from pathlib import Path
import tempfile
import time
from datetime import datetime, timedelta
import pytest

from folder_summary.core import DirectoryMetadata, process_directory
from folder_summary.storage_utils import StorageOptimizer
from folder_summary.advanced_filters import FileFilter


@pytest.fixture
def temp_directory():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test directory structure
        root = Path(tmpdir)

        # Create some files in root
        (root / "file1.txt").write_text("Hello")
        (root / "file2.py").write_text("print('test')")

        # Create a large file (2MB)
        large_file = root / "large_file.dat"
        large_file.write_bytes(b'0' * (2 * 1024 * 1024))

        # Create a subdirectory with files
        subdir = root / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("Test file")
        (subdir / "file4.json").write_text('{"test": true}')

        # Create duplicate files
        (subdir / "duplicate1.txt").write_text("duplicate content")
        (subdir / "duplicate2.txt").write_text("duplicate content")

        # Create a hidden directory and file
        (root / ".hidden_file").write_text("hidden")
        hidden_dir = root / ".hidden_dir"
        hidden_dir.mkdir()
        (hidden_dir / "hidden_content.txt").write_text("secret")

        # Create temp files
        temp_file = root / "temp.tmp"
        temp_file.write_text("temporary")
        # Set old modification time
        old_time = time.time() - (31 * 24 * 3600)  # 31 days old
        os.utime(temp_file, (old_time, old_time))

        yield root


def test_directory_metadata(temp_directory):
    """Test DirectoryMetadata class functionality."""
    metadata = DirectoryMetadata(temp_directory)
    metadata.process_directory(include_hidden=False)

    # Test basic stats
    assert metadata.total_files == 4  # Only non-hidden files in root
    assert metadata.total_subdirs == 1  # Only non-hidden subdirectory

    # Test with hidden files
    metadata = DirectoryMetadata(temp_directory)
    metadata.process_directory(include_hidden=True)
    assert metadata.total_files == 5  # Including hidden file
    assert metadata.total_subdirs == 2  # Including hidden directory


def test_process_directory(temp_directory):
    """Test process_directory function."""
    # Test without hidden files
    results = process_directory(
        temp_directory,
        depth=None,
        include_hidden=False,
        output_name="test_summary.txt",
        dry_run=True
    )

    assert len(results) == 2  # Root and one visible subdirectory

    # Test with depth limit
    results = process_directory(
        temp_directory,
        depth=0,
        include_hidden=False,
        output_name="test_summary.txt",
        dry_run=True
    )

    assert len(results) == 1  # Only root directory

    # Test with hidden files
    results = process_directory(
        temp_directory,
        depth=None,
        include_hidden=True,
        output_name="test_summary.txt",
        dry_run=True
    )

    assert len(results) == 3  # Root, visible subdir, and hidden subdir


def test_storage_optimizer(temp_directory):
    """Test StorageOptimizer functionality."""
    optimizer = StorageOptimizer(temp_directory)

    # Test duplicate file detection
    duplicates = optimizer.find_duplicate_files()
    assert len(duplicates) == 1  # One set of duplicates
    assert len(next(iter(duplicates.values()))) == 2  # Two files in the set

    # Test large file detection
    large_files = optimizer.find_large_files(min_size_mb=1)
    assert len(large_files) == 1  # One large file

    # Test temp file detection
    temp_files = optimizer.find_temp_files()
    assert len(temp_files) == 1  # One temp file


def test_file_filter(temp_directory):
    """Test FileFilter functionality."""
    file_filter = FileFilter()

    # Test age filter
    file_filter.set_age_filter(days=30, older_than=True)
    old_file = temp_directory / "temp.tmp"
    new_file = temp_directory / "file1.txt"
    assert file_filter.matches(old_file)  # Should match old file
    assert not file_filter.matches(new_file)  # Should not match new file

    # Test size filter
    file_filter = FileFilter()
    file_filter.set_size_range(min_size=1024*1024)  # 1MB
    large_file = temp_directory / "large_file.dat"
    small_file = temp_directory / "file1.txt"
    assert file_filter.matches(large_file)  # Should match large file
    assert not file_filter.matches(small_file)  # Should not match small file

    # Test pattern matching
    file_filter = FileFilter()
    file_filter.set_patterns(
        include_patterns=["*.txt"],
        exclude_patterns=["temp.*"]
    )
    assert file_filter.matches(temp_directory / "file1.txt")  # Should match .txt
    assert not file_filter.matches(temp_directory / "temp.tmp")  # Should not match temp.*


def test_summary_file_creation(temp_directory):
    """Test that summary files are created correctly."""
    output_name = "test_summary.txt"

    # Process directory and create summary files
    process_directory(
        temp_directory,
        depth=None,
        include_hidden=False,
        output_name=output_name,
        dry_run=False
    )

    # Check that summary files exist
    assert (temp_directory / output_name).exists()
    assert (temp_directory / "subdir" / output_name).exists()

    # Check summary file content
    summary_content = (temp_directory / output_name).read_text()
    assert "Directory Summary for:" in summary_content
    assert "Statistics:" in summary_content
    assert "Files by Extension:" in summary_content


def test_parallel_processing(temp_directory):
    """Test parallel processing functionality."""
    optimizer = StorageOptimizer(temp_directory)
    optimizer.parallel_processor.n_jobs = 2  # Use 2 jobs for testing

    # Test parallel duplicate file detection
    duplicates = optimizer.find_duplicate_files()
    assert len(duplicates) == 1  # Should find the same duplicates

    # Test parallel large file detection
    large_files = optimizer.find_large_files(min_size_mb=1)
    assert len(large_files) == 1  # Should find the same large file


def test_caching(temp_directory):
    """Test caching functionality."""
    optimizer = StorageOptimizer(temp_directory)

    # First run should cache results
    first_run = optimizer.find_large_files(min_size_mb=1)  # Set threshold to 1MB

    # Second run should use cache
    second_run = optimizer.find_large_files(min_size_mb=1)

    assert first_run == second_run  # Results should be identical

    # Modify a file and check cache invalidation
    large_file = temp_directory / "large_file.dat"
    large_file.write_bytes(b'1' * 2 * 1024 * 1024)  # 2MB file

    # Should detect the change
    third_run = optimizer.find_large_files(min_size_mb=1)
    assert len(third_run) == 1
    assert third_run[0][1] == 2 * 1024 * 1024  # New file should be exactly 2MB