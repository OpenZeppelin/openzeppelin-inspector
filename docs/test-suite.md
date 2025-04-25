# Inspector Test Suite Documentation

## Overview

This document describes the test suite framework for the OpenZeppelin Inspector tool, which allows for automated testing of security scanners and detectors against predefined test cases. The test suite validates that scanners correctly identify issues in code files based on specially marked annotations.

## Test File Format

Test files use special comment annotations to mark lines that should trigger detections (true positives) or should not trigger detections (true negatives).

### Annotation Markers

The following markers can be used in test files:

- **True Positive Markers**:
  - ```:true-positive-below: [detector_name]``` - Indicates the line below should trigger a detection
  - ```:true-positive-above: [detector_name]``` - Indicates the line above should trigger a detection
  - ```:true-positive-here: [detector_name]``` - Indicates the current line should trigger a detection

- **True Negative Markers**:
  - ```:true-negative-below: [detector_name]``` - Indicates the line below should not trigger a detection
  - ```:true-negative-above: [detector_name]``` - Indicates the line above should not trigger a detection
  - ```:true-negative-here: [detector_name]``` - Indicates the current line should not trigger a detection

- **Disable Test Marker**:
  - ```:disable-detector-test: [detector_name]``` - Deactivates a marker for the specified detector when placed on the same line as another marker

### Example Test File

```solidity
// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

// :true-negative-below: function-visibility-too-broad
function fooz1() {}

contract FunctionVisibilityTooBroad {

    // :true-positive-below: function-visibility-too-broad
    function foo1() public { bar1(); }
    function bar1() public {}
    
    function foo2() external { bar2(); } // :true-negative-here: function-visibility-too-broad
    function bar2() public {}
}

contract ExternalFunctionExample {
    uint public data;
    
    function updateData(uint _data) public {
        // :true-positive-above: function-visibility-too-broad
        data = _data;
    }
}
```

**Note**: During test project creation, everything in a comment line from the annotation marker to the end of the line is removed. Any content before the annotation in the same comment line is preserved. This ensures that the annotation itself doesn't influence the detector's behavior while maintaining the structure of the file.

## Folder Structure

Test files must be organized in a specific directory structure:

```
inspector_tests/
├── [detector_name]/
│   ├── [test_project_name]/
│   │   ├── file1.sol
│   │   ├── file2.sol
│   │   └── ...
│   └── [another_test_project]/
│       └── ...
└── [another_detector]/
    └── ...
```

Where:
- ```[detector_name]``` is the name of the detector being tested
- ```[test_project_name]``` is a descriptive name for a group of related test files

Tests can be provided in two locations:
1. User-defined tests in ```PATH_USER_INSPECTOR_TESTS```
2. Scanner-provided tests from each scanner's ```get_root_test_dirs()``` method

## How the Test Suite Works

1. The test suite discovers all test files organized by detector and test project
2. For each detector and test project:
   - The test files are copied to a temporary in-memory location
   - Test annotations are stripped from the files
   - The scanner is run against the clean files
   - The scanner's findings are compared against the expected results from the annotations
   - Accuracy metrics are calculated

## Scanner Integration Requirements

Scanners that wish to integrate with the test suite should:

1. Implement the ```get_root_test_dirs()``` method to provide paths to their test directories
2. Ensure their detector implementations properly identify issues in the test files
3. Return findings in the expected format:
   - Each finding should include a file path and line number
   - Line numbers should match the lines marked in the test files

## Test Results and Metrics

The test suite calculates and reports the following metrics:

- **Expected**: Number of true positives that should be found
- **Found**: Total number of findings reported by the scanner
- **Extra**: False positives (findings that shouldn't have been reported)
- **Missing**: False negatives (issues that weren't detected)
- **Accuracy**: Percentage of correctly identified issues

## Running Tests

Tests can be run using the CLI with the ```test``` command:

```bash
python3 src/inspector_cli.py test --rules [OPTIONAL_LIST_RULE_IDS] --scanners [OPTIONAL_LIST_SCANNER_IDS] [--table]
```

Key options:
- ```--rules```: Specify which detectors to test (defaults to all available detectors)
- ```--scanners```: Specify which scanners to test (defaults to all available scanners)
- ```--table```: Print results in a table format (otherwise outputs JSON)

Programmatically, tests can be run using the ```run_detector_tests()``` function with the following parameters:
- ```scanners```: List of scanner identifiers to test
- ```detectors```: List of detector names to test
- ```print_table```: If True, returns a formatted table; otherwise, returns JSON

## Debugging

When debugging test failures, you can examine:
1. The differences between expected and actual results
2. The specific files and line numbers where detections were missed or incorrectly reported
3. The accuracy metrics for each detector

The test suite can also preserve temporary test files for debugging by setting the ```debug``` parameter to ```True``` in the ```create_annotation_free_test_project``` function.

