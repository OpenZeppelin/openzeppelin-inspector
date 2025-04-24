from collections import Counter
from pathlib import Path

from .models._complete.scanner_response import CompleteScannerResponse
from .models._complete.finding import CompleteFinding
from .models._complete.instance import CompleteInstance
from .models._complete.location import LocationPoint, Location
from .models._complete.detector_response import CompleteDetectorResponse
from inspector.models._complete.error import Error
from .source_code_manager import SourceCodeManager
from .models.minimal.finding import MinimalFinding
from .models.minimal.detector_response import MinimalDetectorResponse
from .models.minimal.scanner_response import MinimalScannerResponse
from .models.minimal.instance import MinimalInstance


def minimal_instance_to_instance(
    minimal_instance: MinimalInstance,
    scm: SourceCodeManager,
    project_root: Path,
) -> CompleteInstance:
    """
    Convert a MinimalInstance to a CompleteInstance.

    Args:
        minimal_instance: The minimal instance to convert.
        scm: SourceCodeManager instance.
        project_root: Project root path to resolve relative file paths.

    Returns:
        A CompleteInstance.
    """
    relative_path = Path(minimal_instance.path)
    full_path = project_root / relative_path

    scm.load_file(full_path)

    start_line, start_col = scm.offset_to_line_col(
        full_path, minimal_instance.offset_start
    )
    end_line, end_col = scm.offset_to_line_col(full_path, minimal_instance.offset_end)

    location = Location(
        path=relative_path,
        start=LocationPoint(
            col=start_col,
            line=start_line,
            offset=minimal_instance.offset_start,
        ),
        end=LocationPoint(
            col=end_col, line=end_line, offset=minimal_instance.offset_end
        ),
    )

    lines = scm.get_text_range(
        full_path,
        minimal_instance.offset_start,
        minimal_instance.offset_end,
    )

    return CompleteInstance(
        location=location,
        lines=lines,
        fixes=minimal_instance.fixes,
        extra=minimal_instance.extra,
    )


def minimal_finding_to_finding(
    minimal_finding: MinimalFinding,
    scm: SourceCodeManager,
    project_root: Path,
) -> CompleteFinding:
    """
    Convert a MinimalFinding to a CompleteFinding.

    Args:
        minimal_finding: The minimal finding to convert.
        scm: SourceCodeManager instance.
        project_root: Project root path to resolve relative file paths.

    Returns:
        A CompleteFinding.
    """
    full_instances = [
        minimal_instance_to_instance(minimal_instance, scm, project_root)
        for minimal_instance in minimal_finding.instances
    ]

    return CompleteFinding(
        instances=full_instances,
        impacted=Counter(instance.location.path.name for instance in full_instances),
        lines=[],
        fixes=[],
    )


def minimal_detector_response_to_detector_response(
    minimal_detector_response: MinimalDetectorResponse,
    scm: SourceCodeManager,
    project_root: Path,
) -> CompleteDetectorResponse:
    """
    Convert a MinimalDetectorResponse to a CompleteDetectorResponse.

    Args:
        minimal_detector_response: The minimal detector response to convert.
        scm: SourceCodeManager instance.
        project_root: Project root path to resolve relative file paths.

    Returns:
        A CompleteDetectorResponse.
    """
    full_findings = [
        minimal_finding_to_finding(minimal_finding, scm, project_root)
        for minimal_finding in minimal_detector_response.findings
    ]

    return CompleteDetectorResponse(
        findings=full_findings,
        errors=[Error(message=e) for e in minimal_detector_response.errors],
        metadata={},
    )


def expand_response_minimal_to_full(
    minimal_response: MinimalScannerResponse,
    scm: SourceCodeManager,
    project_root: Path,
) -> CompleteScannerResponse:
    """
    Expand a MinimalScannerResponse into a CompleteScannerResponse.

    Args:
        minimal_response: The minimal scanner response to expand.
        scm: SourceCodeManager instance.
        project_root: Project root path to resolve relative file paths.

    Returns:
        A CompleteScannerResponse.
    """
    full_detector_responses = {
        detector_id: minimal_detector_response_to_detector_response(
            minimal_detector_response, scm, project_root
        )
        for detector_id, minimal_detector_response in minimal_response.responses.items()
    }

    return CompleteScannerResponse(
        errors=[Error(message=e) for e in minimal_response.errors],
        scanned=minimal_response.scanned,
        responses=full_detector_responses,
    )
