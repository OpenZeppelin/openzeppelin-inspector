# Scanner Integration Guide

This guide explains how to create and integrate scanners with OpenZeppelin Inspector. Scanners are plugins that analyze code for security issues and report findings back to Inspector.

## Scanner Types

Inspector supports two types of scanners:

1. **Python Scanners**: Implemented as Python packages that extend the [`BaseScanner` class](../../src/inspector/scanners/base_scanner.py)
2. **Executable Scanners**: Standalone executables that follow a specific command-line interface

## Requirements for Scanner Compatibility

For a scanner to be compatible with Inspector, it must:

1. Be either a Python package or an executable
2. Implement the required interface (Python) or command-line arguments (executable)
3. Return findings in the expected format
4. Be installable via the Inspector scanner installation mechanism

## Implementing a Python Scanner

### 1. Create a Python Package

Create a Python package with the following structure:

```
my_scanner/
├── __init__.py
├── scanner.py
└── pyproject.toml
```

### 2. Implement the BaseScanner Class

In `scanner.py`, implement the `BaseScanner` abstract base class:

```python
from pathlib import Path
from inspector.scanners.base_scanner import BaseScanner
from inspector.models.finding_models import Finding

class MyScanner(BaseScanner):
    def __init__(self):
        super().__init__()
        # Initialize your scanner here

    def _get_scanner_name(self) -> str:
        """Return a unique identifier for this scanner."""
        return "my_scanner"

    def get_scanner_version(self) -> str:
        """Return the version of this scanner."""
        return "1.0.0"

    def get_scanner_description(self) -> str:
        """Return a human-readable description of this scanner."""
        return "My scanner that detects security issues in code."

    def get_supported_detector_metadata(self) -> dict[str, dict]:
        """Return metadata for detectors supported by this scanner."""
        return {
            "detector1": {
                "name": "Detector 1",
                "description": "Detects issue type 1",
                "severity": "HIGH",
                "tags": ["security", "tag1"]
            },
            "detector2": {
                "name": "Detector 2",
                "description": "Detects issue type 2",
                "severity": "MEDIUM",
                "tags": ["security", "tag2"]
            }
        }

    def get_supported_detector_names(self) -> tuple:
        """Return names of detectors supported by this scanner."""
        return ("detector1", "detector2")

    def get_supported_file_extensions(self) -> tuple:
        """Return file extensions this scanner can analyze."""
        return (".sol", ".js")

    def get_root_test_dirs(self) -> list[Path]:
        """Return test directories provided by this scanner."""
        return [Path(__file__).parent / "tests"]

    def run(self, detector_names: list[str], code_paths: list[Path], project_root: Path) -> dict[str, Finding]:
        """Execute the scan operation on provided code files using specified detectors."""
        findings = {}

        # Implement your scanning logic here
        # For each finding, create a Finding object and add it to the findings dictionary

        return findings
```

### 3. Create a pyproject.toml File

In `pyproject.toml`, define your package and its dependencies:

```toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my_scanner"
version = "1.0.0"
description = "My scanner for OpenZeppelin Inspector"
requires-python = ">=3.12"
dependencies = [
    # List your dependencies here
]

[tool.openzeppelin.inspector]
scanner_name = "my_scanner"
scanner_org = "OpenZeppelin"
scanner_description = "Static analyzer for Solidity projects and source code"
scanner_extensions = [".sol"]
```

The `tool.openzeppelin.inspector` section is crucial as it tells Inspector about your scanners capabilities and identifier. Inspector looks for this specific key in the pyproject.toml file to detect Python scanners.

## Implementing an Executable Scanner

### 1. Create an Executable

Create an executable (script, binary, etc.) that can be run from the command line.

### 2. Implement the Required Command-Line Interface

Your executable must accept the following command-line arguments for the `scan` command.

- `--detectors`: A separated list of detectors to execute
- `--project-root`: The root directory of the project

Example:

```bash
my_scanner scan /path/to/file1.sol /path/to/file2.sol --detectors detector1 detector2 --project-root /path/to/project
```

### 3. Output Format

Your executable must output JSON to stdout in the following format for `scan`:

```json
{
  "detector1": {
    "findings": [
      {
        "file": "/path/to/file1.sol",
        "line": 42,
        "description": "Security issue found",
        "severity": "HIGH",
        "confidence": "HIGH",
        "recommendation": "Fix the issue by doing X"
      }
    ]
  },
  "detector2": {
    "findings": []
  }
}
```

### 4. Metadata Command

Your executable must also support a `--metadata` command that outputs JSON metadata about the scanner and its detectors:

```bash
my_scanner metadata
```

Output:

```json
{
  "name": "my_scanner",
  "version": "1.0.0",
  "description": "My scanner that detects security issues in code",
  "detectors": {
    "detector1": {
      "name": "Detector 1",
      "description": "Detects issue type 1",
      "severity": "HIGH",
      "tags": ["security", "tag1"]
    },
    "detector2": {
      "name": "Detector 2",
      "description": "Detects issue type 2",
      "severity": "MEDIUM",
      "tags": ["security", "tag2"]
    }
  },
  "supported_extensions": [".sol", ".js"]
}
```

## Installing Your Scanner

Once you've implemented your scanner, you can install it using the Inspector scanner installation mechanism:

### Python Scanner

```bash
# Install from a local directory
inspector scanner install /path/to/my_scanner

# Install in development mode (for testing)
inspector scanner install /path/to/my_scanner --dev
```

### Executable Scanner

```bash
# Install from a local directory
inspector scanner install /path/to/my_scanner_executable

# Install from a remote URL
inspector scanner install https://example.com/my_scanner_executable.zip
```

## Testing Your Scanner

You can test your scanner by running:

```bash
inspector scan /path/to/project --scanner my_scanner
```

## Best Practices

1. **Single Responsibility**: Each scanner should focus on specific detection patterns
2. **Isolation**: Scanners should operate independently with no internal coupling
3. **Extensibility**: Design your scanner to be easily extensible
4. **Reliability**: Implement robust error handling and logging
5. **Dependencies**: Limit dependencies to standard library and pip-installed packages
6. **Distinct Repositories**: Each scanner should have its own dedicated repository
