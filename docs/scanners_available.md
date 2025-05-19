# Available Scanners

This document lists and describes the currently available scanners for OpenZeppelin Inspector.

## Table of Scanners

| Scanner | Description | Link |
|---------|-------------|------|
| Compact Scanner | Analyzes `Compact` language for security vulnerabilities within the Midnight platform | [View Details](#compact-scanner) |


## Compact Scanner

The Compact Scanner analyzes `Compact` language for security vulnerabilities within the Midnight platform.

### Features

- AST (Abstract Syntax Tree) building and analysis
- Custom security detector development
- Built-in security detectors for common vulnerability patterns
- CLI tool for scanning `.compact` files

### Installation

To install the Compact Scanner:

1. Download the latest executable release for your OS
2. Extract the zip file
3. Install the executable detector with the following command

```bash
inspector scanner install /path/to/compact-scanner
```


### Usage

After installation, you can use the scanner through the OpenZeppelin Inspector CLI:

```bash
inspector scan <path-to-files> --scanner compact-scanner 
```

### Documentation

For more detailed information about the Compact Scanner, visit:
- [GitHub Repository](https://github.com/OpenZeppelin/compact-security-detectors-sdk)

### Contributing

Contributions for the Compact Scanner are welcome. Please refer to the [contributing guidelines](https://github.com/OpenZeppelin/compact-security-detectors-sdk/blob/main/contributing.md) for more information.

## Adding New Scanners

If you're interested in developing a new scanner for OpenZeppelin Inspector, please refer to the [Scanner Integration Guide](./scanner_integration/overview.md) for detailed instructions on how to create and integrate new scanners. 