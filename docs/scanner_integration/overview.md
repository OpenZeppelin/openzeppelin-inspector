# Scanner Integration Guide

This guide explains how to create and integrate scanners with OpenZeppelin Inspector. Scanners are plugins that analyze code for security issues and report findings back to Inspector.

## Scanner Types

Inspector supports executable scanners, which are standalone executables that follow a specific command-line interface.

## Requirements for Scanner Compatibility

For a scanner to be compatible with Inspector, it must:

1. Be an executable
2. Implement the required command-line arguments
3. Return findings in the expected format
4. Be installable via the Inspector scanner installation mechanism

## Implementing a Scanner

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
  "errors": [],
  "scanned": [
    "/relative/path/to/scanned_file.sol"
  ],
  "detector_responses": {
    "detector-id": {
      "findings": [
        {
          "instances": [
            {
              "path": "/relative/path/to/scanned_file.sol",
              "offset_start": 357,
              "offset_end": 364,
              "fixes": [],
              "extra": {
                "metavars": {
                  "CONTRACT_NAME": "Contract"
                }
              }
            }
          ]
        }
      ],
      "errors": [],
      "metadata": {}
    }
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
  "org": "My organization",
  "extensions": [
    ".sol",
    ".js"
  ],
  "detectors": [
    {
      "id": "detector-one",
      "uid": "XYZ123",
      "description": "Detects issue type 1",
      "severity": "HIGH",
      "tags": [
        "security",
        "tag1"
      ],
      "template": {
        "title": "Some Interesting Issue",
        "opening": "This issue is dangerous, because of XYZ.",
        "body-list-item-intro": "The following instances of this issue were found in the code:",
        "body-list-item-always": "- On line $instance_line of [`$file_name`]($instance_line_link)",
        "closing": "Consider fixing this issue by checking for XYZ before execution."
      }
    }
  ]
}
```

## Installing Your Scanner

Once you've implemented your scanner, you can install it using the Inspector scanner installation mechanism:

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
