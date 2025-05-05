"""Command-line interface for directory analysis and storage optimization."""

from pathlib import Path
from typing import List, Optional, Dict, Any

import typer
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from . import __version__
from .core import process_directory
from .exporters import (
    BaseExporter,
    CSVExporter,
    HTMLExporter,
    JSONExporter,
    MarkdownExporter,
    create_exporter
)
from .storage_utils import StorageOptimizer

# Default values for CLI arguments
DEFAULT_PATH = "."
DEFAULT_FORMAT = "text"
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def get_exporter(format_type: str, metadata: Dict[Path, Any]) -> BaseExporter:
    """Get the appropriate exporter based on format type."""
    exporters = {
        'text': MarkdownExporter(metadata),
        'json': JSONExporter(metadata),
        'yaml': JSONExporter(metadata),  # Use JSON exporter for YAML for now
        'html': HTMLExporter(metadata)
    }
    return exporters.get(format_type, MarkdownExporter(metadata))

# Create Typer app with custom formatting
class ModernTyper(typer.Typer):
    def get_help(self, *args, **kwargs):
        self.info_name = "dirstat"
        return self._get_formatted_help()

    def _get_formatted_help(self) -> str:
        console = Console()

        # Create main help panel
        help_text = [
            "# 🚀 DirStat Pro",
            "A powerful directory analysis and storage optimization tool.\n",
            "## Usage",
            "```bash",
            "$ dirstat [OPTIONS] [PATH]",
            "```\n"
        ]

        # Create options table
        table = Table(
            title="⚙️ Options",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            title_style="bold blue",
        )
        table.add_column("Option", style="bold green")
        table.add_column("Description", style="white")
        table.add_column("Default", style="dim")

        # Directory Processing
        table.add_row("", "[bold yellow]Directory Processing[/bold yellow]", "")
        table.add_row("PATH", "Root directory to process", ".")
        table.add_row("-d, --depth", "Maximum directory depth", "None")
        table.add_row("-o, --output-name", "Output filename", ".folder_summary.txt")
        table.add_row("-n, --top-n", "Number of largest files to show", "5")
        table.add_row("-i, --include-hidden", "Include hidden files/directories", "False")
        table.add_row("-h, --human-readable", "Show human-readable sizes", "True")
        table.add_row("--dry-run", "Preview without writing files", "False")
        table.add_row("-v, --verbose", "Enable verbose output", "False")

        # Git Integration
        table.add_row("", "[bold yellow]Git Integration[/bold yellow]", "")
        table.add_row("-g, --git", "Enable Git integration", "False")
        table.add_row("--git-only", "Only process Git-tracked files", "False")

        # Advanced Filtering
        table.add_row("", "[bold yellow]Advanced Filtering[/bold yellow]", "")
        table.add_row("--min-age", "Only include files older than N days", "None")
        table.add_row("--max-age", "Only include files newer than N days", "None")
        table.add_row("--min-size", "Minimum file size (e.g., '1MB')", "None")
        table.add_row("--max-size", "Maximum file size (e.g., '1GB')", "None")
        table.add_row("--include", "Include files matching pattern", "None")
        table.add_row("--exclude", "Exclude files matching pattern", "None")

        # Performance
        table.add_row("", "[bold yellow]Performance[/bold yellow]", "")
        table.add_row("--parallel/--no-parallel", "Enable/disable parallel processing", "True")
        table.add_row("-j, --jobs", "Number of parallel jobs (-1 for auto)", "-1")
        table.add_row("--cache/--no-cache", "Enable/disable result caching", "True")
        table.add_row("-m, --monitor", "Enable real-time monitoring", "False")

        # Other
        table.add_row("", "[bold yellow]Other[/bold yellow]", "")
        table.add_row("--version", "Show version information", "")
        table.add_row("--help", "Show this help message", "")

        # Examples section
        examples = """
        ## 📋 Examples

        Basic directory analysis:
        ```bash
        $ dirstat .
        ```

        Advanced filtering with Git integration:
        ```bash
        $ dirstat . --git --min-size 100MB --include "*.{py,js}" --exclude "test_*"
        ```

        Performance optimization:
        ```bash
        $ dirstat . --parallel --jobs 4 --cache --monitor
        ```
        """

        # Render help content
        console = Console(record=True)
        console.print(Markdown("\n".join(help_text)))
        console.print(table)
        console.print(Markdown(examples))

        return console.export_text()


app = ModernTyper(
    help="A powerful directory analysis and storage optimization tool.",
    add_completion=False,
)

console = Console()

# Default argument values
DEFAULT_PATH = typer.Argument(
    ".",
    help="Root directory to process",
    exists=True,
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
)

DEFAULT_INCLUDE_PATTERN = typer.Option(
    None,
    "--include",
    help="Include files matching pattern (can be specified multiple times)",
)

DEFAULT_EXCLUDE_PATTERN = typer.Option(
    None,
    "--exclude",
    help="Exclude files matching pattern (can be specified multiple times)",
)

# Default values for CLI arguments
DEFAULT_FORMAT = "text"
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def version_callback(value: bool):
    """Print version information."""
    if value:
        console.print(Panel(
            "[bold blue]DirStat Pro[/bold blue] "
            f"[white]version[/white] [green]{__version__}[/green]",
            subtitle="🚀 Directory Analysis & Storage Optimization",
            style="bold",
        ))
        raise typer.Exit()


@app.command()
def main(
    path: Path = DEFAULT_PATH,
    depth: Optional[int] = typer.Option(
        None,
        "--depth",
        "-d",
        help="Maximum directory depth to process (0 = root only, None = unlimited)",
    ),
    output_name: str = typer.Option(
        ".folder_summary.txt",
        "--output-name",
        "-o",
        help="Name of the summary file to create in each directory",
    ),
    top_n: int = typer.Option(
        5,
        "--top-n",
        "-n",
        help="Number of largest files to show",
    ),
    include_hidden: bool = typer.Option(
        False,
        "--include-hidden",
        "-i",
        help="Include hidden files and directories",
    ),
    human_readable: bool = typer.Option(
        True,
        "--human-readable/--bytes",
        "-h/-b",
        help="Show file sizes in human-readable format",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview actions without writing files",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    git_integration: bool = typer.Option(
        False,
        "--git",
        "-g",
        help="Enable Git integration features",
    ),
    git_only: bool = typer.Option(
        False,
        "--git-only",
        help="Only process Git-tracked files (implies --git)",
    ),
    # Advanced filtering options
    min_age: Optional[int] = typer.Option(
        None,
        "--min-age",
        help="Only include files older than N days",
    ),
    max_age: Optional[int] = typer.Option(
        None,
        "--max-age",
        help="Only include files newer than N days",
    ),
    min_size: Optional[str] = typer.Option(
        None,
        "--min-size",
        help="Only include files larger than SIZE (e.g., '1MB', '500KB')",
    ),
    max_size: Optional[str] = typer.Option(
        None,
        "--max-size",
        help="Only include files smaller than SIZE (e.g., '1GB', '10MB')",
    ),
    include_pattern: Optional[List[str]] = DEFAULT_INCLUDE_PATTERN,
    exclude_pattern: Optional[List[str]] = DEFAULT_EXCLUDE_PATTERN,
    # Performance options
    parallel: bool = typer.Option(
        True,
        "--parallel/--no-parallel",
        help="Enable/disable parallel processing",
    ),
    jobs: int = typer.Option(
        -1,
        "--jobs",
        "-j",
        help="Number of parallel jobs (-1 for auto)",
    ),
    enable_cache: bool = typer.Option(
        True,
        "--cache/--no-cache",
        help="Enable/disable result caching",
    ),
    monitor: bool = typer.Option(
        False,
        "--monitor",
        "-m",
        help="Enable real-time monitoring for changes",
    ),
    version: bool = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version information and exit",
    ),
):
    """Generate metadata summaries for directories and their contents."""
    try:
        # If git-only is enabled, ensure git integration is also enabled
        if git_only:
            git_integration = True

        # Parse size strings
        def parse_size(size_str: Optional[str]) -> Optional[int]:
            if not size_str:
                return None
            units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
            size_str = size_str.upper()
            for unit, multiplier in units.items():
                if size_str.endswith(unit):
                    try:
                        return int(float(size_str[:-len(unit)]) * multiplier)
                    except ValueError:
                        return None
            return None

        min_size_bytes = parse_size(min_size)
        max_size_bytes = parse_size(max_size)

        # Show initial message
        console.print(
            Panel(
                "[bold blue]🔍 Processing directory: {path}[/bold blue]\n"
                "[dim]Depth: {depth_str} | "
                "Include hidden: {include_hidden} | "
                "Output: {output_name} | "
                "Git integration: {git_status}\n"
                "Advanced filters: {filter_status} | "
                "Parallel processing: {parallel_status} | "
                "Caching: {cache_status} | "
                "Monitoring: {monitor_status}[/dim]".format(
                    path=path,
                    depth_str='unlimited' if depth is None else depth,
                    include_hidden=include_hidden,
                    output_name=output_name,
                    git_status='enabled' if git_integration else 'disabled',
                    filter_status='configured' if any([
                        min_age, max_age, min_size, max_size,
                        include_pattern, exclude_pattern
                    ]) else 'none',
                    parallel_status='enabled' if parallel else 'disabled',
                    cache_status='enabled' if enable_cache else 'disabled',
                    monitor_status='enabled' if monitor else 'disabled'
                )
            )
        )

        # Initialize storage optimizer with advanced features
        optimizer = StorageOptimizer(path, enable_monitoring=monitor)

        # Configure filters
        optimizer.set_filters(
            min_age=min_age,
            max_age=max_age,
            min_size=min_size_bytes,
            max_size=max_size_bytes,
            include_patterns=include_pattern,
            exclude_patterns=exclude_pattern
        )

        # Process directories with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing directories...", total=None)

            # Configure parallel processing
            if parallel:
                optimizer.parallel_processor.n_jobs = jobs
            else:
                optimizer.parallel_processor.n_jobs = 1

            # Process directory
            results = process_directory(
                path,
                depth=depth,
                include_hidden=include_hidden,
                output_name=output_name,
                dry_run=dry_run,
                human_readable=human_readable,
                git_integration=git_integration,
                git_only=git_only,
            )
            progress.update(task, completed=True)

        # Show summary
        console.print("\n[bold green]✅ Processing complete![/bold green]")
        console.print(f"📊 Processed {len(results)} directories")

        if verbose:
            for dir_path, metadata in results.items():
                console.print(f"\n[bold]Directory: {dir_path}[/bold]")
                stats = [
                    f"Files: {metadata.total_files}",
                    f"Subdirs: {metadata.total_subdirs}",
                    f"Size: {metadata.total_size:,} bytes",
                ]
                if git_integration and metadata.git_info and metadata.git_info.is_git_repo:
                    stats.extend([
                        f"Git tracked: {metadata.git_tracked_files}",
                        f"Git modified: {metadata.git_modified_files}",
                        f"Git untracked: {metadata.git_untracked_files}",
                    ])
                console.print(" | ".join(stats))

        if dry_run:
            console.print("\n[yellow]⚠️  This was a dry run - no files were written[/yellow]")

        # Clean up resources
        optimizer.cleanup()

    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()