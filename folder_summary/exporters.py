"""Export utilities for folder-summary."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from jinja2 import Template


class BaseExporter:
    """Base class for exporters."""

    def __init__(self, metadata: Dict[Path, Any]):
        self.metadata = metadata
        self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def export(self, output_path: Path) -> None:
        """Export the data to the specified format."""
        raise NotImplementedError


class JSONExporter(BaseExporter):
    """Export metadata to JSON format."""

    def export(self, output_path: Path) -> None:
        """Export metadata to JSON file."""
        data = {
            'timestamp': self.timestamp,
            'directories': {
                str(path): {
                    'total_files': meta.total_files,
                    'total_subdirs': meta.total_subdirs,
                    'total_size': meta.total_size,
                    'extensions': {
                        ext: {'count': stats.count, 'size': stats.total_size}
                        for ext, stats in meta.extension_stats.items()
                    },
                    'largest_files': [
                        {'name': str(path.name), 'size': size}
                        for path, size in meta.largest_files
                    ],
                    'git_info': {
                        'tracked_files': meta.git_tracked_files,
                        'modified_files': meta.git_modified_files,
                        'untracked_files': meta.git_untracked_files
                    } if meta.git_info and meta.git_info.is_git_repo else None
                }
                for path, meta in self.metadata.items()
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)


class CSVExporter(BaseExporter):
    """Export metadata to CSV format."""

    def export(self, output_path: Path) -> None:
        """Export metadata to CSV file."""
        headers = ['Directory', 'Total Files', 'Total Subdirs', 'Total Size',
                  'Extensions', 'Largest Files', 'Git Status']

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for path, meta in self.metadata.items():
                extensions = '; '.join(f"{ext}: {stats.count} files ({stats.total_size} bytes)"
                                    for ext, stats in meta.extension_stats.items())
                largest = '; '.join(f"{p.name}: {size} bytes"
                                  for p, size in meta.largest_files)
                git_status = (
                    f"Tracked: {meta.git_tracked_files}, "
                    f"Modified: {meta.git_modified_files}, "
                    f"Untracked: {meta.git_untracked_files}"
                ) if meta.git_info and meta.git_info.is_git_repo else "N/A"

                writer.writerow([
                    str(path),
                    meta.total_files,
                    meta.total_subdirs,
                    meta.total_size,
                    extensions,
                    largest,
                    git_status
                ])


class HTMLExporter(BaseExporter):
    """Export metadata to HTML format with interactive visualizations."""

    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Directory Summary Report</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .chart { margin: 20px 0; padding: 20px; border: 1px solid #ddd; }
            .directory { margin: 20px 0; padding: 20px; border: 1px solid #ddd; }
            h1, h2 { color: #333; }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 10px;
            }
            .stat-box { background: #f5f5f5; padding: 10px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Directory Summary Report</h1>
            <p>Generated on: {{ timestamp }}</p>

            <div class="chart">
                <h2>File Distribution by Extension</h2>
                <div id="extensionChart"></div>
            </div>

            <div class="chart">
                <h2>Directory Sizes</h2>
                <div id="sizeChart"></div>
            </div>

            {% for path, meta in directories.items() %}
            <div class="directory">
                <h2>{{ path }}</h2>
                <div class="stats">
                    <div class="stat-box">
                        <strong>Total Files:</strong> {{ meta.total_files }}
                    </div>
                    <div class="stat-box">
                        <strong>Total Subdirs:</strong> {{ meta.total_subdirs }}
                    </div>
                    <div class="stat-box">
                        <strong>Total Size:</strong> {{ meta.total_size }} bytes
                    </div>
                    {% if meta.git_info %}
                    <div class="stat-box">
                        <strong>Git Status:</strong><br>
                        Tracked: {{ meta.git_info.tracked_files }}<br>
                        Modified: {{ meta.git_info.modified_files }}<br>
                        Untracked: {{ meta.git_info.untracked_files }}
                    </div>
                    {% endif %}
                </div>

                <h3>Largest Files:</h3>
                <ul>
                {% for file in meta.largest_files %}
                    <li>{{ file.name }}: {{ file.size }} bytes</li>
                {% endfor %}
                </ul>
            </div>
            {% endfor %}
        </div>

        <script>
            // Extension distribution chart
            const extensionData = {{ extension_data | tojson }};
            Plotly.newPlot('extensionChart', [{
                values: extensionData.sizes,
                labels: extensionData.extensions,
                type: 'pie'
            }]);

            // Directory size chart
            const sizeData = {{ size_data | tojson }};
            Plotly.newPlot('sizeChart', [{
                x: sizeData.directories,
                y: sizeData.sizes,
                type: 'bar'
            }]);
        </script>
    </body>
    </html>
    """

    def _prepare_chart_data(self):
        """Prepare data for charts."""
        extension_totals = {}
        for meta in self.metadata.values():
            for ext, stats in meta.extension_stats.items():
                if ext not in extension_totals:
                    extension_totals[ext] = 0
                extension_totals[ext] += stats.total_size

        extension_data = {
            'extensions': list(extension_totals.keys()),
            'sizes': list(extension_totals.values())
        }

        size_data = {
            'directories': [str(path) for path in self.metadata.keys()],
            'sizes': [meta.total_size for meta in self.metadata.values()]
        }

        return extension_data, size_data

    def export(self, output_path: Path) -> None:
        """Export metadata to HTML file with interactive visualizations."""
        extension_data, size_data = self._prepare_chart_data()

        template = Template(self.HTML_TEMPLATE)
        html_content = template.render(
            timestamp=self.timestamp,
            directories={str(k): v.__dict__ for k, v in self.metadata.items()},
            extension_data=extension_data,
            size_data=size_data
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


class MarkdownExporter(BaseExporter):
    """Export metadata to Markdown format."""

    def export(self, output_path: Path) -> None:
        """Export metadata to Markdown file."""
        lines = [
            "# Directory Summary Report",
            f"Generated on: {self.timestamp}\n",
        ]

        for path, meta in self.metadata.items():
            lines.extend([
                f"## {path}",
                "### Statistics",
                f"- Total Files: {meta.total_files}",
                f"- Total Subdirectories: {meta.total_subdirs}",
                f"- Total Size: {meta.total_size:,} bytes\n",
            ])

            if meta.git_info and meta.git_info.is_git_repo:
                lines.extend([
                    "### Git Status",
                    f"- Tracked Files: {meta.git_tracked_files}",
                    f"- Modified Files: {meta.git_modified_files}",
                    f"- Untracked Files: {meta.git_untracked_files}\n",
                ])

            lines.extend([
                "### Files by Extension"
            ])
            for ext, stats in sorted(meta.extension_stats.items()):
                lines.append(f"- {ext}: {stats.count} files ({stats.total_size:,} bytes)")

            lines.extend([
                "\n### Largest Files"
            ])
            for file_path, size in meta.largest_files:
                lines.append(f"- {file_path.name}: {size:,} bytes")

            lines.append("\n---\n")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


def create_exporter(format_type: str, metadata: Dict[Path, Any]) -> BaseExporter:
    """Factory function to create the appropriate exporter."""
    exporters = {
        'json': JSONExporter,
        'csv': CSVExporter,
        'html': HTMLExporter,
        'markdown': MarkdownExporter
    }

    exporter_class = exporters.get(format_type.lower())
    if not exporter_class:
        raise ValueError(f"Unsupported format: {format_type}")

    return exporter_class(metadata)