# Scanner Response Format Specification

**Audience:** Developers building scanners that integrate with the OpenZeppelin Inspector CLI.  
**Purpose:** Define the JSON response format that a scanner **MUST** return after execution in order to be compatible
with the Inspector pipeline.

---

## Overview

Each scanner must return a response that conforms to the `MinimalScannerResponse` schema. This schema organizes:

- Detector-level findings or errors
- High-level scanner errors
- The list of scanned files

The structure ensures consistency, traceability, and compatibility across various scanners.

---

## Top-Level Structure

The scanner **MUST** return a JSON object matching this schema:

```json
{
  "errors": [
    {
      "message": "..."
    }
  ],
  "scanned": [
    "relative/path/to/file.ext"
  ],
  "responses": {
    "<detector_id>": {
      "findings": [
        {
          "instances": [
            {
              "path": "relative/path/to/file.ext",
              "offset_start": 20,
              "offset_end": 30,
              "fixes": ["suggested fix"],
              "extra": {
                "metavars": {},
                "other": {}
              }
            }
          ]
        }
      ],
      "errors": ["Error message"]
    }
  }
}
```

---

## Fields

### `responses` (required)

- **Type:** `object`
- **Description:** A mapping of detector IDs to their corresponding responses.
- Each detector response contains `findings` and `errors` arrays.

#### Structure:

```json
"responses": {
  "detector_xyz": {
    "findings": [
      {
        "instances": [
          {
            "path": "relative/path/to/file.ext",
            "offset_start": 20,
            "offset_end": 30,
            "fixes": ["suggested fix"],
            "extra": {
              "metavars": {},
              "other": {}
            }
          }
        ]
      }
    ],
    "errors": ["Error message"]
  }
}
```

---

### `findings` (inside `responses`)

- **Type:** `array of objects`
- **Description:** An array of findings, each containing instances of code issues found by a detector.
- **Schema:**

```json
"findings": [
  {
    "instances": [
      {
        "path": "src/contracts/file.sol",
        "offset_start": 20,
        "offset_end": 30,
        "fixes": [
          "uint256 x = y.safeAdd(z);"
        ],
        "extra": {
          "metavars": {
            "X": "x",
            "Y": "y"
          },
          "other": {}
        }
      }
    ]
  }
]
```

---

### `errors` (inside `responses`)

- **Type:** `array of strings`
- **Description:** An array of error messages encountered while running this specific detector.

```json
"errors": [
  "Timeout running detector XYZ",
  "Failed to parse input file"
]
```

---

### `errors` (optional at scanner level)

- **Type:** `array of objects`
- **Description:** Scanner-wide errors not tied to a specific detector.

```json
"errors": [
  {
    "message": "Parser failed on input files"
  }
]
```

---

### `scanned` (required)

- **Type:** `array of strings`
- **Description:** List of file paths that the scanner processed.

```json
"scanned": [
  "contracts/Token.sol",
  "contracts/Utils.sol"
]
```

Paths should be **relative to the project root**.

---

## Requirements Summary

| Requirement                                       | Mandatory |
|---------------------------------------------------|-----------|
| Return a JSON object                              | Yes       |
| Include `responses`                               | Yes       |
| Include `findings` and `errors` arrays per detector | Yes     |
| `scanned` field                                   | Yes       |
| Top-level `errors` field                          | Optional  |
| Fields must be JSON-serializable                  | Yes       |
| Paths must be relative to project root            | Yes       |

---

## Example Minimal Response

```json
{
  "errors": [],
  "scanned": [
    "src/Contract.sol"
  ],
  "responses": {
    "unused_variable": {
      "findings": [
        {
          "instances": [
            {
              "path": "src/Contract.sol",
              "offset_start": 125,
              "offset_end": 131,
              "fixes": [
                "literal replacement suggestion for offset range",
                "alternate replacement suggestion for offset range"
              ],
              "extra": {
                "metavars": {
                  "VAR_NAME": "replacement text for template"
                },
                "other": {}
              }
            }
          ]
        }
      ],
      "errors": []
    }
  }
}
```
