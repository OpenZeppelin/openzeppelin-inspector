#!/usr/bin/env python3

import json
import sys
import argparse
from typing import Dict, List, Any
from pathlib import Path

def get_metadata() -> Dict[str, Any]:
    """Return metadata about the scanner and its detectors."""
    return {
        "name": "mock_executable_scanner",
        "version": "1.0.0",
        "description": "A mock scanner for testing OpenZeppelin Inspector",
        "org": "OpenZeppelin",
        "extensions": [".sol"],
        "detectors": [
            {
                "id": "mock-detector",
                "uid": "MOCK001",
                "description": "A mock detector that always finds issues",
                "severity": "HIGH",
                "tags": ["mock", "test"],
                "template": {
                    "title": "Mock Finding",
                    "opening": "This is a mock finding for testing purposes.",
                    "body-list-item-intro": "The following instances were found:",
                    "body-list-item-always": "- On line $instance_line of [`$file_name`]($instance_line_link)",
                    "closing": "This is a mock finding and should be ignored."
                }
            }
        ]
    }

def scan_files(files: List[str], project_root: str, detectors: List[str]) -> Dict[str, Any]:
    """Mock scanner that returns a simple analysis result following the required format."""
    # Convert project_root to Path for easier path manipulation
    project_root_path = Path(project_root)
    
    # Generate mock findings for each file
    findings = []
    for file_path in files:
        # Convert to relative path
        relative_path = str(Path(file_path).relative_to(project_root_path))
        
        findings.append({
            "instances": [
                {
                    "path": relative_path,
                    "offset_start": 0,
                    "offset_end": 10,
                    "fixes": ["// Mock fix suggestion"],
                    "extra": {
                        "metavars": {
                            "CONTRACT_NAME": "MockContract"
                        }
                    }
                }
            ]
        })
    
    return {
        "errors": [],
        "scanned": [str(Path(f).relative_to(project_root_path)) for f in files],
        "responses": {
            "mock-detector": {
                "findings": findings,
                "errors": []
            }
        }
    }

def main():
    parser = argparse.ArgumentParser(description="Mock scanner for OpenZeppelin Inspector")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Metadata command
    subparsers.add_parser("metadata")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("files", nargs="+", help="Files to scan")
    scan_parser.add_argument("--project-root", required=True, help="Project root directory")
    scan_parser.add_argument("--detectors", nargs="+", help="Detectors to run")
    
    args = parser.parse_args()
    
    if args.command == "metadata":
        print(json.dumps(get_metadata(), indent=2))
    elif args.command == "scan":
        result = scan_files(args.files, args.project_root, args.detectors or ["mock-detector"])
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 