import logging
from pathlib import Path
from typing import List, Dict, Optional

from .models._complete.scanner_response import CompleteScannerResponse
from .scanner_manager import ScannerManager


class ScanExecutor:
    """
    Handles the execution of scans using multiple scanners and aggregates their results.
    """

    def __init__(
        self,
        detectors_names: List[str],
        source_code: List[str],
        project_root: str,
        scanners: Optional[List[str]] = None,
    ):
        self.detectors_names = detectors_names
        self.source_code = source_code
        self.project_root = project_root
        self.scanners = scanners or []
        self.scanner_manager = ScannerManager()

    async def execute(self) -> dict[str, CompleteScannerResponse]:
        """
        Execute the scanning process using the configured rules and scanners.

        Returns:
            Dictionary mapping scanner names to their ScannerResponse objects
        """
        scanner_manager_scanner_responses: dict[str, CompleteScannerResponse] = {}
        try:
            project_root_path = (
                self.project_root
                if isinstance(self.project_root, Path)
                else Path(self.project_root)
            )
            source_code_paths = [Path(path) for path in self.source_code]
            scanner_manager_scanner_responses = await self.scanner_manager.execute_scan(
                self.detectors_names,
                source_code_paths,
                project_root_path,
                self.scanners,
            )
        except Exception as e:
            logging.getLogger("INSPECTOR").warning(
                f"Failed to run scan via ScannersManager: {e}"
            )

        if not scanner_manager_scanner_responses:
            raise Exception("Notice: No scanners were successfully run.")

        return scanner_manager_scanner_responses
