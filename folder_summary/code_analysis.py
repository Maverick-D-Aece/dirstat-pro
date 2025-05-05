"""Code analysis utilities for folder-summary."""

import ast
import hashlib
import re
import time
import tokenize
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Language detection patterns
LANGUAGE_PATTERNS = {
    'Python': ['.py', '.pyw', '.pyx'],
    'JavaScript': ['.js', '.jsx', '.ts', '.tsx'],
    'Java': ['.java'],
    'C/C++': ['.c', '.cpp', '.h', '.hpp'],
    'Ruby': ['.rb'],
    'Go': ['.go'],
    'Rust': ['.rs'],
    'PHP': ['.php'],
    'HTML': ['.html', '.htm'],
    'CSS': ['.css', '.scss', '.sass'],
}

# Patterns for potential secrets
SECRET_PATTERNS = [
    (r'(?i)api[_-]key.*[\'"][0-9a-zA-Z]{32,}[\'"]', 'API Key'),
    (r'(?i)aws[_-]key.*[\'"][A-Z0-9]{20}[\'"]', 'AWS Key'),
    (r'(?i)password.*[\'"][^\'"\s]{8,}[\'"]', 'Password'),
    (r'(?i)secret.*[\'"][^\'"\s]{8,}[\'"]', 'Secret'),
    (r'(?i)token.*[\'"][^\'"\s]{8,}[\'"]', 'Token'),
]

class CodeAnalyzer:
    """Analyze code files for various metrics."""

    def __init__(self):
        self.line_counts: Dict[str, int] = {}
        self.secrets: List[Tuple[Path, str, str]] = []
        self.complexity_metrics: Dict[Path, Dict[str, int]] = {}
        self.duplicates: Dict[str, List[Path]] = {}
        self.findings: List[Tuple[Path, str, str]] = []

    def count_lines(self, file_path: Path) -> int:
        """Count lines of code, excluding comments and blank lines."""
        try:
            with tokenize.open(file_path) as f:
                tokens = list(tokenize.generate_tokens(f.readline))
                lines = set(token.start[0] for token in tokens
                          if token.type not in {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE})
                return len(lines)
        except (SyntaxError, tokenize.TokenError, UnicodeDecodeError):
            # Fallback to simple line counting for non-Python files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return sum(1 for line in f if line.strip())
            except UnicodeDecodeError:
                return 0

    def detect_secrets(self, file_path: Path) -> List[Tuple[str, str]]:
        """Detect potential secrets in the file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                findings = []
                for pattern, secret_type in SECRET_PATTERNS:
                    matches = re.finditer(pattern, content)
                    findings.extend((secret_type, match.group(0)) for match in matches)
                return findings
        except UnicodeDecodeError:
            return []

    def calculate_complexity(self, file_path: Path) -> Dict[str, int]:
        """Calculate code complexity metrics."""
        metrics = {
            'cyclomatic_complexity': 0,
            'number_of_functions': 0,
            'max_nesting_depth': 0
        }

        if not file_path.suffix == '.py':
            return metrics

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            class ComplexityVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.complexity = 0
                    self.current_depth = 0
                    self.max_depth = 0
                    self.function_count = 0

                def visit_FunctionDef(self, node):
                    self.function_count += 1
                    self.generic_visit(node)

                def visit_If(self, node):
                    self.complexity += 1
                    self.current_depth += 1
                    self.max_depth = max(self.max_depth, self.current_depth)
                    self.generic_visit(node)
                    self.current_depth -= 1

                def visit_While(self, node):
                    self.complexity += 1
                    self.current_depth += 1
                    self.max_depth = max(self.max_depth, self.current_depth)
                    self.generic_visit(node)
                    self.current_depth -= 1

                def visit_For(self, node):
                    self.complexity += 1
                    self.current_depth += 1
                    self.max_depth = max(self.max_depth, self.current_depth)
                    self.generic_visit(node)
                    self.current_depth -= 1

            visitor = ComplexityVisitor()
            visitor.visit(tree)

            metrics['cyclomatic_complexity'] = visitor.complexity
            metrics['number_of_functions'] = visitor.function_count
            metrics['max_nesting_depth'] = visitor.max_depth

        except (SyntaxError, UnicodeDecodeError):
            pass

        return metrics

    def find_duplicates(self, file_path: Path, min_size: int = 100) -> str:
        """Generate hash for file content to identify duplicates."""
        try:
            if file_path.stat().st_size < min_size:
                return ""

            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except (IOError, PermissionError):
            return ""

    def get_language(self, file_path: Path) -> str:
        """Determine the programming language of a file."""
        suffix = file_path.suffix.lower()
        for language, extensions in LANGUAGE_PATTERNS.items():
            if suffix in extensions:
                return language
        return "Other"

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Perform comprehensive analysis of a single file."""
        language = self.get_language(file_path)
        line_count = self.count_lines(file_path)
        complexity = self.calculate_complexity(file_path) if language == 'Python' else {}
        secrets = self.detect_secrets(file_path)
        file_hash = self.find_duplicates(file_path)

        return {
            'language': language,
            'line_count': line_count,
            'complexity': complexity,
            'secrets': secrets,
            'file_hash': file_hash
        }

def get_file_age_days(file_path: Path) -> float:
    """Get the age of a file in days."""
    try:
        mtime = file_path.stat().st_mtime
        age_seconds = time.time() - mtime
        return age_seconds / (24 * 3600)
    except (OSError, AttributeError):
        return 0.0