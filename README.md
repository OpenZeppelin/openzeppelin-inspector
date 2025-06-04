# OpenZeppelin Inspector

OpenZeppelin Inspector is a powerful tool for scanning web3 projects and smart contracts for security issues and vulnerabilities. It provides a flexible framework for managing and executing various code analysis scanners.

## Purpose

The Inspector tool helps developers and auditors identify potential security issues in smart contract code by:

- Running multiple specialized scanners against your codebase
- Supporting a plugin system for custom scanners
- Providing detailed reports of findings with severity levels
- Enabling targeted analysis with customizable detector selection

## Installation

OpenZeppelin Inspector can be installed in two ways:

- **From pre-built executables**: Download and use the executable artifacts published on GitHub Releases
- **From Python source code**: Run directly from the source code

For detailed installation instructions, see [installation.md](docs/installation.md).

> **Note:** The rest of the documentation in this repository assumes that OpenZeppelin Inspector has been installed and is callable with the `inspector` command. If you're running from source code directly without installing the source code directly with pip, then replace `inspector` with `python3 src/inspector_cli.py` in all examples.

## CLI Usage Guide

The Inspector CLI provides several modes of operation, each with its own set of options. Below is a comprehensive guide to all available commands and options.

### Global Options

These options are available across multiple commands:

- `--dev`: Enable development mode
- `--debug`: Enable debug logging
- `--log-level {debug,info,warn,error,critical}`: Set log level (defaults to `warn`; `debug` in debug mode)

### Scan Mode

The scan mode is used to analyze web3 projects for security issues.

```
inspector scan <project_root> [options]
```

#### Required Arguments:
- `project_root`: Directory containing the web3 project source code to scan

#### Scope Options:
- `--scope-file, --scope`: Path to file listing source code files explicitly in scope (used as the base scope, --include paths are added to this scope)
- `--include`: Paths to include in scan (if used with --scope-file, these paths are added to the scope)
- `--exclude`: Paths to exclude from scan (always applied, even when --scope-file is used)

#### Detector Options:
- `--severities, --severity`: Filter detectors by severity level
- `--tags, --tag`: Filter detectors by tag
- `--detectors, --detector`: Specify detectors to use
- `--detectors-exclude, --detector-exclude`: Exclude specific detectors

#### Scanner Options:
- `--scanners, --scanner`: List of scanners to run

#### Output Format Options:
- `--output-format {md,json}`: Format of results output (default: md)
- `--output-file`: Optional output path (defaults to inspector_output_<DATE>)
- `--minimal-output`: Reduce verbosity of output
- `--quiet, --silence, -q`: Suppress output to console

### Test Mode

The test mode is used to run detector tests and verify outputs.

```
inspector test [options]
```

#### Detector Options:
- `--severities, --severity`: Filter detectors by severity level
- `--tags, --tag`: Filter detectors by tag
- `--detectors, --detector`: Specify detectors to use
- `--detectors-exclude, --detector-exclude`: Exclude specific detectors

#### Scanner Options:
- `--scanners, --scanner`: List of scanners to run

#### Test-specific Options:
- `--ci`: CI mode disables spinner
- `--leave-test-annotations`: Do not remove test annotations from test projects
- `--output-format {table,json,differences}`: Format of test output (default: differences)

### Scanner Mode

The scanner mode is used to manage scanner plugins.

```
inspector scanner <command> [options]
```

#### Available Commands:

##### Install
Install a scanner from local path or URL.

```
inspector scanner install <target> [options]
```

- `target`: Directory, .zip file, or remote .zip URL
- `--reinstall`: Reinstall if already installed

##### Uninstall
Uninstall a scanner.

```
inspector scanner uninstall <target>
```

- `target`: Scanner to uninstall

##### List
List installed scanners.

```
inspector scanner list [options]
```

- `--detailed`: Show detailed info

### Autocomplete Mode

The autocomplete mode is used to manage shell autocompletion.

```
inspector autocomplete <command>
```

#### Available Commands:

##### Install
Install autocompletion.

```
inspector autocomplete install
```

##### Uninstall
Uninstall autocompletion.

```
inspector autocomplete uninstall
```

##### Show
Display the shell autocompletion code.

```
inspector autocomplete show
```

### Version Mode

The version mode is used to show the Inspector version.

```
inspector version
```

## Examples

### Basic Scan
```
inspector scan /path/to/project --include /path/to/project/contracts
```

### Scan with Specific Detectors
```
inspector scan /path/to/project --detectors detector_name_1 detector_name_2
```

### Run Tests for Specific Detectors
```
inspector test --detectors detector_name_1 detector_name_2
```

### Install a Scanner
```
inspector scanner install /path/to/scanner
```

### List Installed Scanners
```
inspector scanner list --detailed
```

## Scanner Development

OpenZeppelin Inspector supports a plugin system for custom scanners. Scanners are implemented as standalone executables.

For information on creating and integrating your own scanners, refer to the [Scanner Integration Guide](docs/scanner_integration/overview.md).

To see a list of currently available scanners and their features, check out the [Available Scanners](docs/scanners_available.md) documentation.

## Contributing

We welcome contributions from the community! Here's how you can get involved:

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

If you are looking for a good place to start, find a good first issue [here](https://github.com/openzeppelin/openzeppelin-inspector/issues?q=is%3Aissue%20is%3Aopen%20label%3A"good%20first%20issue").

You can open an issue for a [bug report](https://github.com/openzeppelin/openzeppelin-inspector/issues/new?assignees=&labels=T-bug%2CS-needs-triage&projects=&template=bug.yml), [feature request](https://github.com/openzeppelin/openzeppelin-inspector/issues/new?assignees=&labels=T-feature%2CS-needs-triage&projects=&template=feature.yml), or [documentation request](https://github.com/openzeppelin/openzeppelin-inspector/issues/new?assignees=&labels=T-documentation%2CS-needs-triage&projects=&template=docs.yml).

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) and check the [Security Policy](SECURITY.md) for reporting vulnerabilities.

## License

This project is licensed under the GNU Affero General Public License v3.0 — see the [LICENSE](./LICENSE) file for details.

## Security

For security concerns, please refer to our [Security Policy](SECURITY.md).