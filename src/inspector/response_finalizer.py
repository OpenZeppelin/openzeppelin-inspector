import logging
from pathlib import Path

from . import scanner_registry
from .models._complete.scanner_response import CompleteScannerResponse
from .models._complete.detector_response import CompleteDetectorResponse

logger = logging.getLogger(__name__)


def responses_finalizer(
    scanner_responses: dict[str, CompleteScannerResponse],
) -> tuple[dict[str, CompleteDetectorResponse], set[Path]]:
    """
    Complete and flatten all ScannerResponses into a single flat detector response mapping.

    Args:
        scanner_responses: Dict of scanner name -> ScannerResponse

    Returns:
        Tuple:
            - Dict of `scanner_name#detector_id` -> completed DetectorResponse
            - Count of total unique files scanned across all scanners
    """
    complete_detector_responses: dict[str, CompleteDetectorResponse] = {}
    unique_files: set[Path] = set()

    for scanner_name, scanner_response in scanner_responses.items():
        # Add scanned files from top-level scanner metadata
        unique_files.update(Path(p) for p in scanner_response.scanned)

        for detector_id, detector_response in scanner_response.responses.items():
            # Add scanned files from findings' instance locations
            for finding in detector_response.findings:
                for instance in finding.instances:
                    unique_files.add(instance.location.path)

            # Attach metadata if available
            metadata = scanner_registry.get_scanner_detector_info(
                scanner_name, detector_id
            )
            if metadata is not None:
                detector_response.metadata = metadata
            else:
                logger.warning(
                    f"⚠️ No metadata found for detector `{detector_id}` from scanner `{scanner_name}`."
                )

            # Build unique key
            full_key = f"{scanner_name}#{detector_id}"
            if full_key in complete_detector_responses:
                logger.warning(
                    f"⚠️ Duplicate scanner_id#detector_id `{full_key}` detected while finalizing responses. Overwriting previous entry."
                )
            complete_detector_responses[full_key] = detector_response

    return complete_detector_responses, unique_files
