# 🚀 DirStat Pro

A powerful command-line tool for comprehensive directory analysis, storage optimization, and metadata management.

## ✨ Features

### 📊 Core Features
- 🔍 Recursive directory traversal and analysis
- 📝 Detailed metadata summaries
- 📈 File statistics and distribution analysis
- 🎨 Beautiful, interactive CLI interface
- 💾 Multiple export formats (JSON, CSV, HTML, Markdown)

### 🔬 Code Analysis
- 📊 Line counting and complexity metrics
- 🔐 Secret detection in source code
- 🎯 Language detection and statistics
- 🔄 Duplicate code identification
- 📈 Cyclomatic complexity analysis
- 🔍 Nesting depth analysis

### 📦 Dependency Analysis
- 📊 Project dependency scanning
- 🔄 Outdated package detection
- 🛡️ Security vulnerability checking
- 🎯 Project type detection
- 📈 Import analysis and validation
- 🔍 Unused dependency detection

### 🔄 Git Integration
- 📥 Track Git repository status
- 👀 Monitor tracked/untracked files
- 🔄 Detect modified files
- ⚡ Git-aware filtering

### 💽 Storage Optimization
- 🔍 Find duplicate files
- 📦 Identify large files
- 🗑️ Detect temporary and cache files
- 🔄 Find compressible files
- 💾 Identify old backups
- 📊 Estimate potential space savings

### 🎯 Advanced Filtering
- 📅 Filter by file age/modification date
- 📏 Filter by file size ranges
- 🎯 Complex pattern matching
- 🔍 Multiple include/exclude patterns
- 🎨 Customizable filter combinations

### ⚡ Performance Features
- 🚀 Parallel processing for large directories
- 💾 Result caching
- 🔄 Real-time monitoring
- 📈 Incremental updates

## 📦 Installation

### Using pip with uv (Recommended)
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dirstat-pro
uv pip install dirstat-pro
```

### From Source
```bash
# Clone the repository
git clone https://github.com/Maverick-D-Aece/dirstat-pro.git
cd dirstat-pro

# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with uv
uv pip install -r requirements.txt
```

## 🚀 Usage

Basic usage:
```bash
dirstat /path/to/directory
```

### Common Options

```bash
# Basic directory analysis
dirstat . --depth 2 --output-name "summary.txt"

# Enable Git integration
dirstat . --git --git-only

# Storage optimization
dirstat . --find-duplicates --min-size 100MB

# Advanced filtering
dirstat . \
  --min-age 30 \
  --max-size 1GB \
  --include "*.{py,js}" \
  --exclude "test_*"

# Performance optimization
dirstat . --parallel --jobs 4 --cache --monitor
```

### All Available Options

```bash
Options:
  Directory Processing:
    PATH                          Root directory to process [default: .]
    -d, --depth INTEGER          Maximum directory depth [default: None]
    -o, --output-name TEXT       Output filename [default: .folder_summary.txt]
    -n, --top-n INTEGER         Number of largest files to show [default: 5]
    -i, --include-hidden        Include hidden files/directories
    -h, --human-readable        Show human-readable sizes [default: True]
    --dry-run                   Preview without writing files
    -v, --verbose              Enable verbose output

  Git Integration:
    -g, --git                  Enable Git integration
    --git-only                 Only process Git-tracked files

  Advanced Filtering:
    --min-age INTEGER          Only include files older than N days
    --max-age INTEGER          Only include files newer than N days
    --min-size TEXT            Minimum file size (e.g., '1MB', '500KB')
    --max-size TEXT            Maximum file size (e.g., '1GB', '10MB')
    --include TEXT             Include files matching pattern (multiple allowed)
    --exclude TEXT             Exclude files matching pattern (multiple allowed)

  Code Analysis:
    --analyze-code            Enable code analysis features
    --detect-secrets         Scan for potential secrets in code
    --complexity-threshold   Maximum cyclomatic complexity threshold
    --max-nesting           Maximum allowed nesting depth
    --detect-duplicates     Find duplicate code segments

  Dependency Analysis:
    --check-dependencies    Scan and analyze project dependencies
    --security-scan        Check for security vulnerabilities
    --outdated-check      Check for outdated packages
    --unused-deps         Detect unused dependencies
    --project-type        Auto-detect and analyze project type

  Performance:
    --parallel/--no-parallel   Enable/disable parallel processing [default: True]
    -j, --jobs INTEGER         Number of parallel jobs (-1 for auto)
    --cache/--no-cache        Enable/disable result caching [default: True]
    -m, --monitor             Enable real-time monitoring for changes

  Other:
    --version                  Show version information
    --help                    Show this help message and exit
```

## 🛠 Development

1. Clone the repository:
```bash
git clone https://github.com/Maverick-D-Aece/dirstat-pro.git
cd dirstat-pro
```

2. Create a virtual environment and install development dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies with uv
uv pip install -r requirements-dev.txt
```

3. Run tests and checks:
```bash
# Run tests (includes coverage report)
pytest

# Run linting
ruff check .

# Run type checking (optional)
mypy folder_summary
```

4. Install in development mode:
```bash
uv pip install -e .
```

## 🔄 Output Formats

### Text Summary
```
📁 Directory Summary for: /path/to/dir
📅 Generated on: 2024-02-20 15:30:45
==================================================
📊 Statistics:
  • Total Files: 42
  • Total Subdirectories: 5
  • Total Size: 128.5 MB

📋 Files by Extension:
  • .py: 15 files (2.3 MB)
  • .txt: 8 files (156.2 KB)
  • .json: 4 files (45.8 KB)

📦 Storage Analysis:
  • Duplicate Files: 3 sets found (potential savings: 25.6 MB)
  • Large Files (>100MB): 2 files
  • Temporary Files: 15 files (78.9 MB)
  • Compression Candidates: 8 files

🔄 Git Status:
  • Tracked (unchanged): 45 files
  • Modified/Staged: 3 files
  • Untracked: 12 files
```

### Other Formats
- Export to JSON for programmatic analysis
- Generate CSV for spreadsheet processing
- Create interactive HTML reports with visualizations
- Produce Markdown for documentation

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Install development dependencies (`uv pip install -r requirements-dev.txt`)
4. Make your changes
5. Run tests and linting (`pytest tests/ && ruff check .`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📝 License

MIT License

Code and dependency analysis:
```bash
# Analyze code complexity and detect secrets
dirstat . --analyze-code --detect-secrets

# Scan for outdated dependencies and security issues
dirstat . --check-dependencies --security-scan

# Combined analysis with Git integration
dirstat . \
  --analyze-code \
  --check-dependencies \
  --git \
  --include "*.py" \
  --exclude "test_*" \
  --parallel
```