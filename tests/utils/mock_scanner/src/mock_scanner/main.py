from pathlib import Path
from typing_extensions import override

from inspector.scanners import BaseScanner
from inspector.models import (
    MinimalFinding,
    MinimalDetectorResponse,
    MinimalInstance,
    Error,
    Extra,
)
from inspector.models._complete.detector_response import CompleteDetectorResponse
from inspector.models._complete.scanner_response import CompleteScannerResponse


from .constants import DETECTOR_TEST_PATH


class MockScanner(BaseScanner):
    """A simplified mock scanner for demonstration purposes."""

    def __init__(self) -> None:
        super().__init__()
        # Predefined mock data
        self._detector_names = ["mock-test"]
        self._detector_metadata = {
            "mock-test": {
                "id": "mock-test",
                "uid": "059413",
                "description": "Mock test",
                "report": {
                    "severity": "low",
                    "tags": ["audit", "reportable"],
                    "template": {
                        "title": "Mock test",
                        "opening": "Mock test for Mock Scanner",
                        "body-single-file-single-instance": "In `$file_name`, [`$_CONTRACT_NAME`]($instance_line_link) is a mock contract.",
                        "body-single-file-multiple-instance": "Throughout the codebase, there are multiple contracts that are mock contracts.",
                        "body-multiple-file-multiple-instance": "Throughout the codebase, there are multiple contracts that are mock contracts.",
                        "body-list-item-intro": "For instance:",
                        "body-list-item-single-file": "- The [`$_CONTRACT_NAME`]($instance_line_link) contract.",
                        "body-list-item-multiple-file": "- The [`$_CONTRACT_NAME`]($instance_line_link) contract.",
                        "closing": "Mock test for Mock Scanner",
                    },
                },
            }
        }

    @override
    def _get_scanner_name(self) -> str:
        return "mock-scanner"

    @override
    def get_supported_detector_metadata(self) -> dict[str, dict]:
        return self._detector_metadata

    @override
    def get_root_test_dirs(self) -> list[Path]:
        return self._get_root_test_dirs()

    @classmethod
    def _get_root_test_dirs(cls) -> list[Path]:
        """
        Get a list of root test directories provided by this scanner.

        These directories will be treated as additional root test directories
        by the Inspector Test Framework, which will handle the actual test file
        discovery and organization.

        Returns:
            A list of Path objects pointing to root test directories.
        """
        if not hasattr(cls, "_cached_root_test_dirs"):
            # Cache the result to avoid repeated filesystem operations
            if DETECTOR_TEST_PATH.exists() and DETECTOR_TEST_PATH.is_dir():
                cls._cached_root_test_dirs = [DETECTOR_TEST_PATH]
            else:
                cls._cached_root_test_dirs = []

        return cls._cached_root_test_dirs

    def run(
        self,
        detector_names: list[str],
        code_paths: list[Path],
        project_root: Path,
    ) -> CompleteScannerResponse:
        """Return mock findings without actually running any detectors."""

        detector_responses = {}

        for detector_name in detector_names:
            if detector_name in self._detector_names:
                finding = MinimalFinding()

                instance = MinimalInstance(
                    path=str(code_paths[0]),
                    offset_start=0,
                    offset_end=0,
                    extra=Extra(metavars={"_CONTRACT_NAME": "MockContract"}),
                    fixes=[],
                )

                finding.instances.append(instance)

                detector_responses[detector_name] = MinimalDetectorResponse(
                    findings=[finding], errors=[]
                )
            else:
                detector_responses[detector_name] = CompleteDetectorResponse(
                    errors=[Error("Detector not supported")]
                )

        return CompleteScannerResponse(
            errors=[],
            scanned=[str(code_paths[0])],
            responses=detector_responses,
        )
