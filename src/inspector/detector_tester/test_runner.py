"""
Test runner module for detectors and comparing expected vs actual results.
Provides functionality to validate scanner outputs against predefined test cases.
"""

import json
import logging
import shutil
import tempfile
import time
import datetime
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from tabulate import tabulate
from termcolor import colored

from ..scanner_manager import ScannerManager
from ..scanner_registry import get_scanner_detector_names
from .test_file_manager import DetectorTestManager

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Test markers used in test files.
TEST_MARKERS = {
    "positive": {
        ":true-positive-below:",
        ":true-positive-above:",
        ":true-positive-here:",
    },
    "negative": {
        ":true-negative-below:",
        ":true-negative-above:",
        ":true-negative-here:",
    },
}


@dataclass
class TestResult:
    """Container for expected test result data."""

    true_positives: list[int]
    true_negatives: list[int]


@dataclass
class Accuracy:
    """Container for accuracy metrics."""

    expected_positives: int
    actual_positives: int
    total_findings: int
    false_positives: int = 0
    false_negatives: int = 0


@dataclass
class ScannerResults:
    """Container for scanner-specific results."""

    findings: dict[str, dict[Path, set[int]]] = field(default_factory=dict)
    differences: dict[str, dict[Path, dict[str, list[int]]]] = field(
        default_factory=dict
    )
    accuracy: dict[str, Accuracy] = field(default_factory=dict)


def _get_target_line(line_num: int, marker: str) -> int:
    """Determine the target line number based on the marker type."""
    if "below" in marker:
        return line_num + 1
    if "above" in marker:
        return line_num - 1
    return line_num


def _process_test_file(filepath: Path, detector_name: str) -> TestResult | None:
    """
    Process a test file to extract expected true positive and true negative line numbers.
    """
    positives, negatives = [], []
    try:
        with filepath.open("r", encoding="UTF-8") as f:
            for idx, line in enumerate(f, 1):
                is_disabled = ":disable-detector-test:" in line
                if is_disabled:
                    logger.info(
                        f"Testing {detector_name} and encountered disabled test annotation in {filepath.parts[-1]}:{idx}"
                    )
                    logger.info(f"Line contents: {line.strip()}")
                for marker_type, markers in TEST_MARKERS.items():
                    for marker in markers:
                        if marker not in line:
                            continue
                        if detector_name not in line:
                            logger.warning(
                                f"Testing {detector_name} and encountered unexpected detector name in test file {filepath.parts[-1]}:{idx}"
                            )
                            logger.warning(f"Line contents: {line.strip()}")
                            continue
                        target = _get_target_line(idx, marker)
                        if is_disabled:
                            # Skip this marker if disabled
                            continue
                        if marker_type == "positive":
                            positives.append(target)
                        else:
                            negatives.append(target)
        return TestResult(true_positives=positives, true_negatives=negatives)
    except UnicodeDecodeError:
        logger.warning("Skipping %s due to Unicode decode error", filepath)
        return None


def parse_expected_results(
    detector_name: str, test_project_name: str, test_files: list[Path]
) -> dict[Path, TestResult]:
    """
    Parse test files for a specific detector and test_project to extract expected results.
    Returns a dict mapping file paths to their expected TestResult.
    """
    results = {}
    for filepath in test_files:
        test_result = _process_test_file(filepath, detector_name)
        if test_result is not None:
            results[filepath] = test_result
    return results


def _extract_detector_findings(
    response, valid_files: set[Path], test_dir: Path
) -> dict[Path, set[int]]:
    detector_findings = {}
    relative_path_mapping = {f.relative_to(test_dir): f for f in valid_files}

    for finding in response.findings:
        for instance in finding.instances:
            instance_path = Path(instance.location.path)
            matching_file = None

            if instance_path in valid_files:
                matching_file = instance_path
            else:
                try:
                    if instance_path.is_absolute():
                        try:
                            rel_instance_path = instance_path.relative_to(test_dir)
                            if rel_instance_path in relative_path_mapping:
                                matching_file = relative_path_mapping[rel_instance_path]
                        except ValueError:
                            pass
                    elif instance_path in relative_path_mapping:
                        matching_file = relative_path_mapping[instance_path]
                except Exception as e:
                    logger.warning(f"Error matching path {instance_path}: {e}")

            if matching_file:
                detector_findings.setdefault(matching_file, set()).add(
                    instance.location.position.start.line
                )
            else:
                logger.warning(f"Could not match finding path: {instance_path}")

    return detector_findings


def _compute_detector_accuracy(
    expected_results: dict[Path, TestResult], actual_findings: dict[Path, set[int]]
) -> tuple[Accuracy, dict[Path, dict[str, list[int]]]]:
    """
    For a single detector, compare expected results with actual findings,
    returning both accuracy metrics and detailed differences.
    """
    total_expected = 0
    total_actual = 0
    differences = {}

    for path, exp_result in expected_results.items():
        exp_positives = set(exp_result.true_positives)
        total_expected += len(exp_positives)
        actual = actual_findings.get(path, set())
        false_positives = actual - exp_positives
        false_negatives = exp_positives - actual
        if false_positives or false_negatives:
            differences[path] = {
                "false_positives": sorted(false_positives),
                "false_negatives": sorted(false_negatives),
            }
        total_actual += len(exp_positives & actual)

    accuracy = Accuracy(
        expected_positives=total_expected,
        actual_positives=total_actual,
        total_findings=sum(len(f) for f in actual_findings.values()),
        false_positives=sum(
            len(diff["false_positives"]) for diff in differences.values()
        ),
        false_negatives=sum(
            len(diff["false_negatives"]) for diff in differences.values()
        ),
    )
    return accuracy, differences


def analyze_results(
    expected: dict[str, dict[str, dict[Path, TestResult]]],
    actual: dict[str, dict[str, dict[str, dict[Path, set[int]]]]],
) -> dict[str, ScannerResults]:
    """
    Compare expected and actual scanner results, updating each scanner's results with
    coverage metrics and any differences found.

    Args:
        expected: A dict mapping detector names to test_project names to file paths to expected results
        actual: A dict mapping scanner IDs to detector names to test_project names to file paths to findings

    Returns:
        A dict mapping scanner IDs to ScannerResults
    """
    results = {}

    for scanner_id, scanner_findings in actual.items():
        scanner_results = ScannerResults()

        for detector_name, detector_test_projects in scanner_findings.items():
            # Merge all test_project findings for this detector
            merged_detector_findings = {}
            for test_project_findings in detector_test_projects.values():
                for file_path, line_numbers in test_project_findings.items():
                    merged_detector_findings.setdefault(file_path, set()).update(
                        line_numbers
                    )

            scanner_results.findings[detector_name] = merged_detector_findings

            # Get expected results for this detector (merged across all test_projects)
            if detector_name in expected:
                merged_expected_results = {}
                for test_project_results in expected[detector_name].values():
                    merged_expected_results.update(test_project_results)

                # Compute accuracy
                coverage, diffs = _compute_detector_accuracy(
                    merged_expected_results, merged_detector_findings
                )
                scanner_results.accuracy[detector_name] = coverage
                if diffs:
                    scanner_results.differences[detector_name] = diffs

        results[scanner_id] = scanner_results

    return results


def color_scanner_prefix(scanner_id):
    return colored(f"{scanner_id}#", "light_grey", attrs=["bold"])


def color_detector_id(detector_id):
    return colored(f"{detector_id}", None, attrs=["bold"])


def format_coverage_table(results: dict[str, ScannerResults]) -> str:
    """
    Build a formatted table summarizing accuracy metrics per detector and per scanner.
    """
    headers = [
        colored(h, "blue", attrs=["bold"])
        for h in ["Detector", "Expected", "Found", "Extra", "Missing", "Accuracy"]
    ]
    table_data = []

    # Get all available detector names for each scanner
    scanner_detector_map = {}
    for scanner in ScannerManager.get_all_available_scanners():
        scanner_name = scanner.get_scanner_name()
        scanner_detector_map[scanner_name] = set(
            get_scanner_detector_names(scanner_name)
        )

    for scanner_id, scanner_results in results.items():
        # Get the set of detectors supported by this scanner
        supported_detectors = scanner_detector_map.get(scanner_id, set())

        for detector_name, accuracy in scanner_results.accuracy.items():
            # Only include detectors with at least one expected positive test
            if accuracy.expected_positives == 0:
                continue

            # Skip if this detector is not supported by this scanner
            if detector_name not in supported_detectors:
                continue

            extra = accuracy.total_findings - accuracy.actual_positives
            missing = accuracy.expected_positives - accuracy.actual_positives

            final_accuracy = 100.0
            if accuracy.expected_positives > 0:
                total_errors = extra + missing
                final_accuracy = max(
                    0,
                    (
                        (accuracy.expected_positives - total_errors)
                        / accuracy.expected_positives
                    )
                    * 100,
                )
            elif extra > 0:
                final_accuracy = 0.0

            accuracy_color = (
                "light_green"
                if final_accuracy == 100
                else "light_yellow"
                if final_accuracy >= 80
                else "light_red"
            )

            table_data.append(
                [
                    f"  {color_scanner_prefix(scanner_id)}{color_detector_id(detector_name)}",
                    accuracy.expected_positives,
                    accuracy.total_findings,
                    colored(str(extra), "red") if extra > 0 else "0",
                    colored(str(missing), "red") if missing > 0 else "0",
                    colored(f"{final_accuracy:.2f}%", accuracy_color),
                ]
            )
    return tabulate(table_data, headers=headers, tablefmt="fancy_grid") + "\n"


def format_differences_json(results: dict[str, ScannerResults]) -> str:
    """
    Build a JSON string reporting the differences between expected and actual results.
    """
    # Convert the nested dictionary structure, ensuring Path objects are converted to strings
    differences = {}
    for scanner_id, scanner_results in results.items():
        scanner_diff = {}
        for detector_name, detector_differences in scanner_results.differences.items():
            detector_diff = {}
            for path, diff_data in detector_differences.items():
                # Convert Path to string
                detector_diff[str(path)] = diff_data
            scanner_diff[detector_name] = detector_diff
        differences[scanner_id] = scanner_diff

    return json.dumps(differences, indent=2)


def scan_with_single_detector_test_project(
    detector_name: str,
    test_project_name: str,
    test_files: list[Path],
    scanners: list[str],
    test_manager: DetectorTestManager,
    leave_test_annotations: bool = False,
) -> dict[str, dict[Path, set[int]]]:
    """
    Execute a scan for a single detector and test_project using only its test files.

    Args:
        detector_name: Name of the detector to test
        test_project_name: Name of the test project
        test_files: List of test files to scan
        scanners: List of scanner IDs to use
        test_manager: Test manager instance
        leave_test_annotations: If False, creates annotation-free copies of test projects before scanning

    Returns:
        Dict mapping scanner IDs to dicts mapping file paths to sets of line numbers
    """
    if not test_files:
        logger.warning(
            "No test files found for detector %s, test_project %s",
            detector_name,
            test_project_name,
        )
        return {}

    test_dir = test_manager.get_test_project_dir(detector_name, test_project_name)
    if not test_dir:
        logger.warning(
            f"Test directory not found for detector {detector_name}, test_project {test_project_name}"
        )
        return {}

    logger.debug(
        f"Testing detector {detector_name}, test_project {test_project_name} with files: {test_files}"
    )
    logger.info(f"Using test directory: {test_dir}")

    findings = {}

    if not leave_test_annotations:
        # Create a temporary copy of the project with annotation-free test files
        with create_annotation_free_test_project(test_dir, test_files) as (
            temp_project_dir,
            file_mapping,
        ):
            # Get the clean files
            clean_files = list(file_mapping.values())

            logger.info(f"Created temporary project at: {temp_project_dir}")
            logger.info(f"Stripped test annotation from {len(clean_files)} test files")

            # Run the scan on the clean files using the temporary project directory
            response = ScannerManager().execute_scan(
                [detector_name], clean_files, temp_project_dir, scanners
            )

            for scanner_id, detector_responses in response.items():
                if detector_name not in detector_responses.responses:
                    logger.warning(
                        f"Detector {detector_name} not found in responses for scanner {scanner_id}"
                    )
                    continue

                detector_response = detector_responses.responses[detector_name]
                if not detector_response.findings:
                    logger.info(
                        f"No findings for detector {detector_name}, test_project {test_project_name} with scanner {scanner_id}"
                    )
                    continue

                # Extract findings from clean files, passing the temp project directory
                clean_findings = _extract_detector_findings(
                    detector_response, set(clean_files), temp_project_dir
                )

                # Map findings back to original files
                original_findings = {}
                reverse_mapping = {v: k for k, v in file_mapping.items()}

                for clean_file, line_numbers in clean_findings.items():
                    original_file = reverse_mapping.get(clean_file)
                    if original_file:
                        original_findings[original_file] = line_numbers

                if original_findings:
                    findings[scanner_id] = original_findings
    else:
        # Run the scan directly on the original test files
        logger.info(f"Testing with original test files (clean_projects=False)")

        response = ScannerManager().execute_scan(
            [detector_name], test_files, test_dir, scanners
        )

        for scanner_id, detector_responses in response.items():
            if detector_name not in detector_responses.responses:
                logger.warning(
                    f"Detector {detector_name} not found in responses for scanner {scanner_id}"
                )
                continue

            detector_response = detector_responses.responses[detector_name]
            if not detector_response.findings:
                logger.info(
                    f"No findings for detector {detector_name}, test_project {test_project_name} with scanner {scanner_id}"
                )
                continue

            # Extract findings directly from test files, passing the test directory
            test_findings = _extract_detector_findings(
                detector_response, set(test_files), test_dir
            )

            if test_findings:
                findings[scanner_id] = test_findings

    return findings


def create_detector_test_report(
    results: dict[str, ScannerResults], execution_time: float
) -> dict:
    """
    Create a comprehensive JSON-serializable report with all test results.

    Args:
        results: The processed ScannerResults with pre-computed accuracy metrics
        execution_time: Total execution time of the test run in seconds

    Returns:
        A dictionary with complete test results data
    """
    # Get all available detector names for each scanner
    scanner_detector_map = {}
    for scanner in ScannerManager.get_all_available_scanners():
        scanner_name = scanner.get_scanner_name()
        scanner_detector_map[scanner_name] = set(
            get_scanner_detector_names(scanner_name)
        )

    report = {
        "metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "execution_time": round(execution_time, 2),
            "scanners": list(results.keys()),
            "detectors": sorted(
                set(
                    detector
                    for scanner_results in results.values()
                    for detector in scanner_results.accuracy.keys()
                )
            ),
        },
        "scanners": {},
    }

    # Process each scanner's results
    for scanner_id, scanner_results in results.items():
        scanner_data = {"accuracy_metrics": {}, "differences": {}}

        # Get the set of detectors supported by this scanner
        supported_detectors = scanner_detector_map.get(scanner_id, set())

        # Add pre-computed accuracy metrics for each detector
        for detector_name, accuracy in scanner_results.accuracy.items():
            # Skip if this detector is not supported by this scanner
            if detector_name not in supported_detectors:
                continue

            # Calculate derived metrics
            extra = accuracy.total_findings - accuracy.actual_positives
            missing = accuracy.expected_positives - accuracy.actual_positives

            final_accuracy = 100.0
            if accuracy.expected_positives > 0:
                total_errors = extra + missing
                final_accuracy = max(
                    0,
                    (
                        (accuracy.expected_positives - total_errors)
                        / accuracy.expected_positives
                    )
                    * 100,
                )
            elif extra > 0:
                final_accuracy = 0.0

            # Store complete metrics
            scanner_data["accuracy_metrics"][detector_name] = {
                "expected_positives": accuracy.expected_positives,
                "actual_positives": accuracy.actual_positives,
                "total_findings": accuracy.total_findings,
                "false_positives": extra,
                "false_negatives": missing,
                "accuracy_percentage": round(final_accuracy, 2),
            }

            # Add detailed differences for each detector
            if detector_name in scanner_results.differences:
                detector_differences = {}
                for path, diff in scanner_results.differences[detector_name].items():
                    detector_differences[str(path)] = {
                        "false_positives": diff.get("false_positives", []),
                        "false_negatives": diff.get("false_negatives", []),
                    }
                scanner_data["differences"][detector_name] = detector_differences

        report["scanners"][scanner_id] = scanner_data

    return report


def run_detector_tests(
    scanners: list[str],
    detectors: list[str],
    leave_test_annotations: bool = False,
    output_format: str = "differences",
    root_test_paths: list[Path] = None,
) -> tuple[str, bool, dict]:
    """
    Execute the test suite for the specified scanners and detectors.

    Args:
        scanners: List of scanner IDs to test
        detectors: List of detector names to test
        leave_test_annotations: Whether to leave test annotations in test files
        output_format: Format for output ("table", "json", "differences")
        root_test_paths: Optional list of extra test root directories to search (as Path objects)

    Returns:
        Tuple containing:
        - Formatted output string based on requested format
        - Whether there were failures
        - Complete test report data with all metrics and findings
    """
    # Start timing the test run
    start_time = time.time()

    # Prepare provided test dirs
    root_test_dirs = tuple(root_test_paths) if root_test_paths else ()

    # Create a test manager with the requested scanners, detectors, and extra test dirs
    test_manager = DetectorTestManager(
        requested_scanners=tuple(scanners) if scanners else None,
        requested_detectors=tuple(detectors) if detectors else None,
        root_test_dirs=root_test_dirs,
    )

    available_detectors = set(ScannerManager.get_all_available_detector_names())
    requested_detectors = set(detectors) if detectors else available_detectors

    # Detectors that are both requested and available
    available_requested_detectors = sorted(available_detectors & requested_detectors)

    # Available detectors that weren't requested
    not_requested_detectors = sorted(available_detectors - requested_detectors)

    # Requested detectors that aren't available
    unavailable_requested_detectors = sorted(requested_detectors - available_detectors)

    for detector in available_requested_detectors:
        logger.debug("Requested detector is available: %s", detector)

    for detector in not_requested_detectors:
        logger.debug("Detector not requested: %s", detector)

    for detector in unavailable_requested_detectors:
        logger.debug("Requested detector is unavailable: %s", detector)

    if not available_requested_detectors:
        logger.info("No detectors available to test")
        return "No detectors available to test", True, {}

    # Structure to hold expected results: detector -> test_project -> file -> TestResult
    expected_results = {detector: {} for detector in available_requested_detectors}

    # Structure to hold actual findings: scanner -> detector -> test_project -> file -> line numbers
    actual_findings = {
        scanner: {detector: {} for detector in available_requested_detectors}
        for scanner in scanners
    }

    # Process each detector and its test_projects
    for detector_name in available_requested_detectors:
        test_projects = test_manager.get_test_projects(detector_name)

        if not test_projects:
            logger.warning(f"No test projects found for detector: {detector_name}")
            continue

        for test_project_name in test_projects:
            # Get test files for this detector and test_project
            test_files = test_manager.get_test_files(detector_name, test_project_name)

            # Parse expected results for this detector and test_project
            expected_results[detector_name][test_project_name] = parse_expected_results(
                detector_name, test_project_name, test_files
            )

            # Scan with this detector and test_project
            per_test_project_findings = scan_with_single_detector_test_project(
                detector_name,
                test_project_name,
                test_files,
                scanners,
                test_manager,
                leave_test_annotations,
            )

            # Store findings for each scanner
            for scanner_id, findings in per_test_project_findings.items():
                actual_findings[scanner_id][detector_name][test_project_name] = findings

    # Analyze all accumulated results at once
    results = analyze_results(expected_results, actual_findings)

    # Calculate total execution time
    execution_time = time.time() - start_time

    # Create comprehensive report with pre-computed metrics and timing
    report = create_detector_test_report(results, execution_time)

    # Determine if there were failures
    has_failures = any(
        bool(scanner_results.differences) for scanner_results in results.values()
    )

    # Generate output based on requested format
    if output_format == "table":
        output = format_coverage_table(results)
    elif output_format == "json":
        output = json.dumps(report, indent=2)
    elif output_format == "differences":
        output = format_differences_json(results)
    else:
        # Default fallback
        output = format_differences_json(results)

    return output, has_failures, report


@contextmanager
def create_annotation_free_test_project(
    test_project_dir: Path, test_files: list[Path], debug: bool = False
) -> tuple[Path, dict[Path, Path]]:
    """
    Creates a RAM-based copy of the test project with annotations removed from test files.
    Preserves comments but removes annotation markers within them.

    Args:
        test_project_dir: The root directory of the test project
        test_files: List of test files to clean
        debug: If True, prints before/after content for each file

    Yields:
        Tuple containing:
        - Path to the in-memory project directory
        - Dict mapping original file paths to clean file paths
    """
    if not test_project_dir or not test_project_dir.exists():
        raise ValueError(f"Invalid test project directory: {test_project_dir}")

    # Create temporary test project directory using tmpfs
    temp_project_dir = Path(tempfile.mkdtemp(prefix="inspector_test_"))
    file_mapping = {}

    logger.info(f"Created temporary test project directory at: {temp_project_dir}")

    try:
        # Copy the contents of the project directory to the temp directory
        shutil.copytree(test_project_dir, temp_project_dir, dirs_exist_ok=True)

        # Process only the specified test files
        for original_file in test_files:
            try:
                # Calculate the relative path from the project directory
                rel_path = original_file.relative_to(test_project_dir)
                clean_file = temp_project_dir / rel_path

                # Clean the file content
                with clean_file.open("r", encoding="UTF-8") as f:
                    content = f.read()

                # Process the content to remove annotations
                cleaned_content = _remove_test_annotations(content)

                # Write the clean content back to the file
                with clean_file.open("w", encoding="UTF-8") as f:
                    f.write(cleaned_content)

                # Add to mapping
                file_mapping[original_file] = clean_file

            except ValueError:
                logger.warning(
                    f"File {original_file} is not within the project directory {test_project_dir}"
                )

        yield temp_project_dir, file_mapping
    finally:
        if debug:
            logger.info(
                f"Preserved temporary test project directory for debugging: {temp_project_dir}"
            )
        else:
            # Only clean up RAM disk files when not debugging
            shutil.rmtree(temp_project_dir)
            logger.info(f"Removed temporary test project directory: {temp_project_dir}")


def _remove_test_annotations(content: str) -> str:
    """Remove test annotations from file content while preserving comments structure."""
    lines = content.splitlines(True)  # Keep line endings
    cleaned_lines = []

    for line in lines:
        cleaned_line = line

        # Check for test markers and disable-detector-test annotation
        markers_to_check = [
            marker for marker_list in TEST_MARKERS.values() for marker in marker_list
        ]
        markers_to_check.append(":disable-detector-test:")

        for marker in markers_to_check:
            if marker in cleaned_line:
                marker_pos = cleaned_line.find(marker)
                comment_start = cleaned_line.rfind("//", 0, marker_pos)

                if comment_start != -1:
                    # Adjust comment_start to include any preceding slashes
                    while comment_start > 0 and cleaned_line[comment_start - 1] == "/":
                        comment_start -= 1

                    # Find next comment if any
                    next_comment = cleaned_line.find("//", marker_pos + len(marker))

                    if next_comment != -1:
                        # Replace just this comment
                        cleaned_line = (
                            cleaned_line[:comment_start] + cleaned_line[next_comment:]
                        )
                    else:
                        # Remove to end of line, preserving newline
                        cleaned_line = cleaned_line[:comment_start]
                        if line.endswith("\n"):
                            cleaned_line += "\n"

        cleaned_lines.append(cleaned_line)

    return "".join(cleaned_lines)
