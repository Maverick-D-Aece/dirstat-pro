"""Dependency analysis utilities for folder-summary."""

import ast
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Set

import pkg_resources
import requests
import toml


class DependencyAnalyzer:
    """Analyze project dependencies and security vulnerabilities."""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.dependencies: Dict[str, str] = {}
        self.unused_deps: Set[str] = set()
        self.outdated_deps: Dict[str, Dict[str, str]] = {}
        self.vulnerabilities: List[Dict[str, str]] = []
        self.dependency_files: List[Path] = []
        self.imports: Set[str] = set()
        self.requirements: Set[str] = set()
        self.unused_dependencies: Set[str] = set()
        self.missing_dependencies: Set[str] = set()

    def _find_dependency_files(self) -> List[Path]:
        """Find dependency files in the project."""
        dependency_files = []
        patterns = [
            "requirements.txt",
            "pyproject.toml",
            "setup.py",
            "Pipfile",
            "package.json",
            "composer.json",
            "gemfile",
            "cargo.toml"
        ]

        for pattern in patterns:
            dependency_files.extend(self.root_path.rglob(pattern))

        return dependency_files

    def _parse_requirements_txt(self, file_path: Path) -> Dict[str, str]:
        """Parse requirements.txt file."""
        deps = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Handle different requirement formats
                        if '==' in line:
                            name, version = line.split('==')
                            deps[name] = version
                        elif '>=' in line:
                            name, version = line.split('>=')
                            deps[name] = f">={version}"
                        else:
                            deps[line] = "latest"
        except Exception:
            pass
        return deps

    def _parse_pyproject_toml(self, file_path: Path) -> Dict[str, str]:
        """Parse pyproject.toml file."""
        try:
            data = toml.load(file_path)
            if 'project' in data and 'dependencies' in data['project']:
                return {dep.split('>=')[0]: dep.split('>=')[1] if '>=' in dep else 'latest'
                       for dep in data['project']['dependencies']}
        except Exception:
            pass
        return {}

    def _parse_package_json(self, file_path: Path) -> Dict[str, str]:
        """Parse package.json file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                deps = {}
                deps.update(data.get('dependencies', {}))
                deps.update(data.get('devDependencies', {}))
                return deps
        except Exception:
            pass
        return {}

    def analyze_dependencies(self) -> Dict[str, Dict[str, str]]:
        """Analyze project dependencies."""
        results = {}

        for file_path in self._find_dependency_files():
            if file_path.name == 'requirements.txt':
                deps = self._parse_requirements_txt(file_path)
            elif file_path.name == 'pyproject.toml':
                deps = self._parse_pyproject_toml(file_path)
            elif file_path.name == 'package.json':
                deps = self._parse_package_json(file_path)
            else:
                continue

            if deps:
                results[str(file_path.relative_to(self.root_path))] = deps
                self.dependencies.update(deps)

        # Load requirements and analyze imports
        self._load_requirements()
        self.unused_dependencies = self.requirements - self.imports
        self.missing_dependencies = self.imports - self.requirements - {'__future__', 'typing'}

        return results

    def check_outdated_packages(self) -> Dict[str, Dict[str, str]]:
        """Check for outdated packages."""
        for name, current_version in self.dependencies.items():
            try:
                latest_version = pkg_resources.working_set.by_key[name].version
                if latest_version != current_version and current_version != "latest":
                    self.outdated_deps[name] = {
                        'current': current_version,
                        'latest': latest_version
                    }
            except Exception:
                continue

        return self.outdated_deps

    def find_unused_dependencies(self) -> Set[str]:
        """Find potentially unused dependencies."""
        # This is a basic implementation that could be improved
        used_imports: Set[str] = set()

        # Scan Python files for imports
        for py_file in self.root_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for import statements
                    imports = re.findall(r'(?:import|from)\s+([a-zA-Z0-9_]+)', content)
                    used_imports.update(imports)
            except Exception:
                continue

        # Compare with declared dependencies
        self.unused_deps = set(self.dependencies.keys()) - used_imports
        return self.unused_deps

    def check_security_vulnerabilities(self) -> List[Dict[str, str]]:
        """Check for known security vulnerabilities using safety-db."""
        try:
            # Use safety-db API (example - you would need to implement proper API usage)
            for name, version in self.dependencies.items():
                response = requests.get(
                    f"https://pypi.org/pypi/{name}/json",
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    if 'vulnerabilities' in data:
                        for vuln in data['vulnerabilities']:
                            self.vulnerabilities.append({
                                'package': name,
                                'version': version,
                                'vulnerability': vuln['description'],
                                'severity': vuln.get('severity', 'unknown')
                            })
        except Exception:
            pass

        return self.vulnerabilities

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive dependency analysis report."""
        return {
            'dependencies': self.analyze_dependencies(),
            'outdated_packages': self.check_outdated_packages(),
            'security_vulnerabilities': self.check_security_vulnerabilities(),
            'scanned_files': len(self.dependency_files),
            'total_imports': len(self.imports),
            'total_requirements': len(self.requirements),
            'missing_dependencies': sorted(self.missing_dependencies),
            'vulnerabilities': self.vulnerabilities,
            'all_imports': sorted(self.imports),
            'all_requirements': sorted(self.requirements),
            'unused_imports': sorted(self.unused_dependencies)
        }

    def scan_project(self) -> None:
        """Scan the project for Python files and dependency files."""
        for root, _, files in os.walk(self.root_path):
            for file in files:
                if file.endswith('.py'):
                    self._analyze_imports(Path(root) / file)
                elif file in ('requirements.txt', 'pyproject.toml', 'setup.py'):
                    self.dependency_files.append(Path(root) / file)

    def _analyze_imports(self, file_path: Path) -> None:
        """Analyze imports in a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    self.imports.add(name.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports.add(node.module.split('.')[0])

    def _load_requirements(self) -> None:
        """Load project dependencies from various configuration files."""
        for file_path in self.dependency_files:
            if file_path.name == 'requirements.txt':
                self._parse_requirements_txt(file_path)
            elif file_path.name == 'pyproject.toml':
                self._parse_pyproject_toml(file_path)
            elif file_path.name == 'setup.py':
                self._parse_setup_py(file_path)

    def _parse_requirements_txt(self, file_path: Path) -> None:
        """Parse requirements from requirements.txt file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name from requirement spec
                        package = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                        self.requirements.add(package)
        except (IOError, UnicodeDecodeError):
            pass

    def _parse_pyproject_toml(self, file_path: Path) -> None:
        """Parse dependencies from pyproject.toml file."""
        try:
            data = toml.load(file_path)
            # Check poetry dependencies
            if 'tool' in data and 'poetry' in data['tool']:
                poetry_deps = data['tool']['poetry'].get('dependencies', {})
                self.requirements.update(d for d in poetry_deps if isinstance(d, str))

            # Check project dependencies
            if 'project' in data:
                if 'dependencies' in data['project']:
                    self.requirements.update(
                        d.split('[')[0].split('>=')[0].split('==')[0]
                        for d in data['project']['dependencies']
                        if isinstance(d, str)
                    )
        except (toml.TomlDecodeError, IOError):
            pass

    def _parse_setup_py(self, file_path: Path) -> None:
        """Parse dependencies from setup.py file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == 'setup':
                        for kw in node.keywords:
                            if kw.arg in ('install_requires', 'requires'):
                                if isinstance(kw.value, ast.List):
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Str):
                                            package = elt.s.split('==')[0].split('>=')[0].strip()
                                            self.requirements.add(package)
        except (SyntaxError, IOError):
            pass

    def check_vulnerabilities(self) -> None:
        """Check for known vulnerabilities in project dependencies."""
        try:
            for pkg in self.requirements:
                try:
                    version = pkg_resources.get_distribution(pkg).version
                    response = requests.get(
                        f'https://pypi.org/pypi/{pkg}/json',
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        releases = data.get('releases', {})
                        latest_version = max(releases.keys())
                        if version != latest_version:
                            self.vulnerabilities.append({
                                'package': pkg,
                                'current_version': version,
                                'latest_version': latest_version,
                                'type': 'outdated'
                            })
                except (pkg_resources.DistributionNotFound, requests.RequestException):
                    continue
        except Exception:
            pass


class ProjectType:
    """Detect and analyze project type."""

    MARKERS = {
        'Python': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'Node.js': ['package.json', 'node_modules'],
        'Ruby': ['Gemfile', 'config.ru'],
        'Java': ['pom.xml', 'build.gradle'],
        'PHP': ['composer.json', 'artisan'],
        'Go': ['go.mod', 'main.go'],
        'Rust': ['Cargo.toml', 'src/main.rs'],
    }

    def __init__(self, root_path: Path):
        self.root_path = root_path

    def detect_type(self) -> str:
        """Detect the project type based on file markers."""
        for project_type, markers in self.MARKERS.items():
            for marker in markers:
                if list(self.root_path.rglob(marker)):
                    return project_type
        return "Unknown"

    def get_relevant_metrics(self) -> Dict[str, any]:
        """Get relevant metrics based on project type."""
        project_type = self.detect_type()
        metrics = {
            'type': project_type,
            'metrics': {}
        }

        if project_type == "Python":
            metrics['metrics'].update(self._get_python_metrics())
        elif project_type == "Node.js":
            metrics['metrics'].update(self._get_nodejs_metrics())
        # Add more project types as needed

        return metrics

    def _get_python_metrics(self) -> Dict[str, any]:
        """Get Python-specific metrics."""
        metrics = {}

        # Check test coverage
        try:
            result = subprocess.run(
                ['coverage', 'report'],
                cwd=self.root_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+%)', result.stdout)
                if coverage_match:
                    metrics['test_coverage'] = coverage_match.group(1)
        except Exception:
            pass

        # Count number of tests
        test_files = list(self.root_path.rglob("test_*.py"))
        metrics['test_count'] = len(test_files)

        return metrics

    def _get_nodejs_metrics(self) -> Dict[str, any]:
        """Get Node.js-specific metrics."""
        metrics = {}

        # Parse package.json for scripts
        try:
            with open(self.root_path / 'package.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                metrics['scripts'] = list(data.get('scripts', {}).keys())
        except Exception:
            pass

        return metrics