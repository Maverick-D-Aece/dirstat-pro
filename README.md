# 🚀 DirStat Pro

**DirStat Pro** is a powerful command-line tool for comprehensive directory analysis, storage optimization, and metadata management.

## ✨ Key Features

### 📊 Directory Analysis
- 🔍 Recursive directory traversal and summary
- 📝 Metadata extraction and reporting
- 📈 File statistics with size, type, and distribution insights
- 🎨 Interactive and color-rich CLI interface
- 💾 Export results in JSON, CSV, HTML, and Markdown

### 🔬 Code Intelligence
- 📊 Count lines of code and analyze complexity
- 🔐 Scan for secrets in source files
- 🧠 Detect programming languages and analyze usage
- 🔁 Identify duplicate code segments
- 📈 Evaluate cyclomatic complexity and nesting depth

### 📦 Dependency Insight
- 📊 Analyze project dependencies across environments
- 🔄 Detect outdated packages
- 🛡️ Perform security vulnerability scans
- 🧭 Auto-detect project types and configurations
- 📈 Analyze imports and unused dependencies

### 🔄 Git-Aware Analysis
- 📥 Detect Git repository status
- 👀 List tracked, untracked, and modified files
- 🔄 Filter data by Git status

### 💽 Storage Optimization
- 🔍 Identify duplicate and large files
- 🗑️ Detect temporary and cache files
- 🧼 Find old backups and compressible candidates
- 📊 Estimate space-saving potential

### 🎯 Filtering Capabilities
- 📅 Filter files by modification date or age
- 📏 Restrict analysis by size thresholds
- 🔍 Match patterns using include/exclude filters
- ⚙️ Customize filter logic for precision targeting

### ⚡ Performance & Efficiency
- 🚀 Parallel processing for scalable performance
- 💾 Smart result caching
- 🔄 Real-time directory monitoring
- 📈 Incremental file system updates

## 📦 Installation

### Recommended: Using `uv` and `pip`
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install dirstat-pro
```

### Manual Installation (From Source)
```bash
git clone https://github.com/Maverick-D-Aece/dirstat-pro.git
cd dirstat-pro
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

## 🚀 Getting Started

### Basic Usage
```bash
dirstat /path/to/directory
```

### Common Scenarios
```bash
# Analyze directory with limited depth
dirstat . --depth 2 --output-name "summary.txt"

# Analyze only Git-tracked files
dirstat . --git --git-only

# Find duplicates and large files
dirstat . --find-duplicates --min-size 100MB

# Apply advanced filters
dirstat . --min-age 30 --max-size 1GB --include "*.py" --exclude "test_*"

# Maximize performance
dirstat . --parallel --jobs 4 --cache --monitor
```

## 🧰 Command-Line Options

_(For full help, run `dirstat --help`)_

### General Options
- `--depth`, `--output-name`, `--top-n`, `--include-hidden`, `--human-readable`
- `--dry-run`, `--verbose`

### Git Integration
- `--git`, `--git-only`

### Advanced Filters
- `--min-age`, `--max-age`, `--min-size`, `--max-size`
- `--include`, `--exclude`

### Code Analysis
- `--analyze-code`, `--detect-secrets`, `--complexity-threshold`
- `--max-nesting`, `--detect-duplicates`

### Dependency Analysis
- `--check-dependencies`, `--security-scan`, `--outdated-check`
- `--unused-deps`, `--project-type`

### Performance
- `--parallel`, `--jobs`, `--cache`, `--monitor`

### Miscellaneous
- `--version`, `--help`

## 🛠 Development

```bash
git clone https://github.com/Maverick-D-Aece/dirstat-pro.git
cd dirstat-pro
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements-dev.txt
```

### Run Tests & Checks
```bash
pytest          # Run tests with coverage
ruff check .    # Lint code
mypy folder_summary  # Type checks (optional)
uv pip install -e .  # Dev install
```

## 📤 Output Formats

### CLI Text Summary Example
```
📁 Directory Summary: /project
📅 Date: 2024-02-20 15:30:45

📊 Stats:
  • Files: 42 | Folders: 5 | Size: 128.5 MB

📋 Extensions:
  • .py (15 files, 2.3 MB)
  • .json (4 files, 45.8 KB)

📦 Storage:
  • Duplicates: 3 sets (25.6 MB savings)
  • Large files: 2
  • Temp files: 15 (78.9 MB)
  • Compressible: 8

🔄 Git Status:
  • Tracked: 45 | Modified: 3 | Untracked: 12
```

### Other Formats
- JSON: Structured data export
- CSV: Spreadsheet-ready
- HTML: Interactive report
- Markdown: Shareable summaries

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/xyz`
3. Install dev dependencies: `uv pip install -r requirements-dev.txt`
4. Make changes and commit: `git commit -m 'Add new feature'`
5. Push and open a PR: `git push origin feature/xyz`

## 📝 License

Licensed under the MIT License.
