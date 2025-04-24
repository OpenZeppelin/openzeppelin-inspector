# Installing OpenZeppelin Inspector

OpenZeppelin Inspector can be installed and used in two ways:

## Method 1: Using Pre-built Executables

The simplest way to install OpenZeppelin Inspector is to download the pre-built executable artifacts published on the [GitHub Releases](https://github.com/OpenZeppelin/contract-inspector/releases) page.

### Steps:

1. Visit the [Releases page](https://github.com/OpenZeppelin/contract-inspector/releases) on GitHub
2. Download the appropriate executable for your operating system:
   - `inspector-linux` for Linux
   - `inspector-macos` for macOS
   - `inspector-windows.exe` for Windows
3. Make the file executable (Linux/macOS only):
   ```bash
   chmod +x inspector-linux
   # or
   chmod +x inspector-macos
   ```
4. Move the executable to a directory in your PATH (optional, for easier access):
   ```bash
   # Linux/macOS
   sudo mv inspector-linux /usr/local/bin/inspector
   # or
   sudo mv inspector-macos /usr/local/bin/inspector
   ```

After installation, you can run the tool using:
```bash
inspector scan /path/to/project
```

### Quick Setup with Autocomplete

You can quickly make the inspector executable accessible (with or without adding it to your PATH first) by using the autocomplete feature:

1. Move the downloaded executable to its final location (can be anywhere on your system):
   ```bash
   # Example for Linux
   mkdir -p ~/.local/bin
   mv inspector-linux ~/.local/bin/inspector
   chmod +x ~/.local/bin/inspector
   ```

2. Run the autocomplete installation command:
   ```bash
   ~/.local/bin/inspector autocomplete install
   ```

This will create an alias entry in your `bash` or `zsh` shell, making the `inspector` command available from anywhere, even if the executable is not in your PATH.

## Method 2: Running from Python Source Code

If you prefer to run OpenZeppelin Inspector directly from the source code, follow these steps:

### Prerequisites:
- Python 3.12
- pip (Python package installer)
- Git (for cloning the repository)

### Steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/OpenZeppelin/contract-inspector.git
   cd contract-inspector
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the tool using Python:
   ```bash
   python3 src/inspector_cli.py scan /path/to/project
   ```

4. (Optional) Create a virtual environment for isolated installation:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Verifying Installation

To verify that OpenZeppelin Inspector is installed correctly, run:

```bash
# If using the executable
inspector version

# If running from source
python3 src/inspector_cli.py version
```

This should display the current version of OpenZeppelin Inspector.

## Installing Scanners

OpenZeppelin Inspector uses a plugin system for scanners. To install additional scanners:

```bash
# If using the executable
inspector scanner install /path/to/scanner

# If running from source
python3 src/inspector_cli.py scanner install /path/to/scanner
```

For more information on using OpenZeppelin Inspector, refer to the [README](../README.md).
