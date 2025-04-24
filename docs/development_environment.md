# Setting Up a Development Environment for OpenZeppelin Inspector

This guide provides instructions for setting up a development environment for OpenZeppelin Inspector, including how to install the repository in editable mode, work with scanners during development, and run tests.

## Prerequisites

Before setting up your development environment, ensure you have the following installed:

- Python 3.12
- pip (Python package installer)
- Git (for cloning the repository)

## Cloning the Repository

First, clone the OpenZeppelin Inspector repository:

```bash
git clone https://github.com/OpenZeppelin/openzeppelin-inspector.git
cd openzeppelin-inspector
```

## Setting Up a Virtual Environment

It's recommended to use a virtual environment for development to isolate dependencies:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/macOS
source venv/bin/activate
# On Windows
# venv\Scripts\activate
```

## Installing in Editable Mode

Install the project in editable mode, which allows you to make changes to the code without reinstalling:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install the project in editable mode
pip install -e .
```

Installing in editable mode creates a special link in your Python environment to the project directory, so any changes you make to the code are immediately reflected when you run the `inspector` command.

## Running the Inspector CLI

After installing in editable mode, you can run the Inspector CLI directly:

```bash
# Run the Inspector CLI
inspector --help

# Or run it directly from the source code
python3 src/inspector_cli.py --help
```

## Working with Scanners in Development

OpenZeppelin Inspector supports a plugin system for scanners. When developing scanners, you can install them in development mode to make changes without reinstalling.

### Installing a Scanner in Development Mode

To install a scanner in development mode:

```bash
inspector scanner install /path/to/scanner --dev
```

This creates a symlink to the scanner directory instead of copying the files, allowing you to make changes to the scanner code that are immediately reflected (or, in the case of binary scanners, reflected on re-compile) when running the Inspector.

### Python Scanner Development

For Python scanners, the development mode:

1. Creates a symlink to the scanner directory
2. Sets up a virtual environment for the scanner
3. Installs the scanner package in editable mode using `pip install -e`
4. Attempts to use `requirements-dev.txt` if available, falling back to `requirements.txt`

This allows you to modify the scanner code and have changes reflected immediately without reinstalling.

### Executable Scanner Development

For executable scanners, the development mode:

1. Creates a symlink to the executable file
2. Ensures the executable has the proper permissions

This allows you to re-compile the executable and have changes reflected immediately.

## Running Tests

The project uses pytest for testing. To run the tests:

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/test_cli.py

# Run tests with coverage
coverage run -m pytest
coverage report
```

## Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality. To set up pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Install the pre-commit hooks
pre-commit install
```

## Updating Requirements Files

The project uses pip-tools to manage dependencies. To update the requirements files:

```bash
# Update requirements.txt from pyproject.toml
pip-compile --output-file=requirements.txt --strip-extras pyproject.toml

# Update requirements-dev.txt (if needed)
# Note: requirements-dev.txt is manually maintained
```

## Building Executables

To build executable artifacts for distribution:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller inspector.spec
```

The built executable will be in the `dist` directory.

## Troubleshooting

### Scanner Installation Issues

If you encounter issues with scanner installation in development mode, be sure to use the `--debug` flag when running Inspector:

1. Check that the scanner directory has the correct structure:
   - Python scanners should have a `pyproject.toml` file
   - Executable scanners should have a single executable file at the root

2. Ensure the scanner has the required metadata:
   - Python scanners should have a `[tool.openzeppelin.inspector]` section in `pyproject.toml`
   - Executable scanners should support a `metadata` mode

### Testing Issues

If tests are failing:

1. Ensure you have installed all development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Check that you have installed the project in editable mode:
   ```bash
   pip install -e .
   ```

3. Some tests may require specific scanners to be installed. Install them as needed:
   ```bash
   inspector scanner install tests/utils/mock_scanner --develop
   ```