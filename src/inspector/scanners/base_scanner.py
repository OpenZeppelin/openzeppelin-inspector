import logging
from abc import ABC, abstractmethod
from pathlib import Path

from ..models.minimal.scanner_response import MinimalScannerResponse


class ScannerException(Exception):
    """
    Base exception class for all scanner-related errors.

    This exception serves as the root of the scanner exception hierarchy,
    allowing for unified handling of all scanner-specific error conditions.

    Typical usage:
        try:
            # Scanner code
        except ScannerException as exc:
            # Handle any scanner error

    All custom scanner exceptions should inherit from this class.
    """

    pass


class DependencyException(ScannerException):
    """
    Exception raised when scanner dependencies are missing or incompatible.

    This exception indicates issues with required external dependencies,
    such as missing packages, version conflicts, or failed initialization.

    Examples:
        - Required Python package is not installed.
        - Installed package version is incompatible.
        - Dependency initialization fails at runtime.
    """

    pass


class SetupException(ScannerException):
    """
    Exception raised when scanner initialization or setup fails.

    This exception covers errors related to scanner configuration,
    resource allocation, or environment preparation.

    Examples:
        - Invalid scanner configuration provided.
        - Failure to allocate required resources.
        - Environment variables or setup scripts are missing or incorrect.
    """

    pass


class ScanException(ScannerException):
    """
    Exception raised when a scanner encounters an error during execution.

    This exception covers runtime errors during the scanning process,
    such as file parsing failures, pattern matching errors, or resource
    exhaustion.

    Examples:
        - Syntax error in the code being scanned.
        - Pattern matching engine fails.
        - Out-of-memory or timeout conditions.
    """

    pass


class BaseScanner(ABC):
    """
    Abstract base class defining the interface for single-file code scanners.

    This class establishes the contract for implementing code analysis scanners.
    Each scanner analyzes source code files and reports findings based on
    configured detection rules.

    Design Principles:
        - Single Responsibility: Each scanner targets specific detection patterns.
        - Isolation: Scanners operate independently, with no internal coupling.
        - Extensibility: New scanners can be added by subclassing this interface.
        - Reliability: Robust error handling and logging.

    Design Constraints:
        - Only standard library and pip-installed packages may be used.
        - No internal coupling with other project modules is permitted.
        - Scanner implementations should not exceed 1000 lines of code.
        - Complex scanners should be moved to dedicated repositories.

    Attributes:
        _logger (logging.Logger): Logger instance specific to the scanner.

    Raises:
        DependencyException: If required dependencies are missing or incompatible.
        SetupException: If scanner initialization or setup fails.
        ScanException: If scan execution encounters errors.
    """

    def __init__(self):
        """
        Initialize the scanner with a configured logger.

        The logger is created in the 'scanners' namespace, using the scanner's
        unique identifier as determined by get_scanner_name().

        Example:
            logger = logging.getLogger('scanners.smart-contract-scanner')
        """
        self._logger = logging.getLogger(f"scanners.{self.get_scanner_name()}")

    @abstractmethod
    def _get_scanner_name(self) -> str:
        """
        Retrieve the canonical Python module/package name for this scanner.

        This method must be implemented by all scanner subclasses. It should
        return the scanner's unique identifier using only lowercase letters and
        underscores, following Python module naming conventions.

        Example:
            Returns:
                'smart_contract_scanner'

        Returns:
            str: Canonical Python module/package name for this scanner.
        """
        pass

    def get_scanner_name(self) -> str:
        """
        Retrieve the user-facing, normalized scanner name for registry and CLI use.

        This method returns a unique, normalized name for the scanner, suitable for
        use in registries, CLI arguments, and user interfaces. The name is derived
        from the canonical Python module name returned by `_get_scanner_name()`,
        with underscores replaced by hyphens.

        Example:
            If `_get_scanner_name()` returns 'smart_contract_scanner',
            this method returns 'smart-contract-scanner'.

        Returns:
            str: Normalized scanner name (hyphens instead of underscores).
        """
        return self._get_scanner_name().replace("_", "-")

    @abstractmethod
    def get_supported_detector_metadata(self) -> dict[str, dict]:
        """
        Retrieve the metadata for all detectors supported by this scanner.

        Returns:
            dict[str, dict]: Dictionary mapping detector names to their metadata.
                Each value should be a dictionary describing the detector's
                properties, such as description, severity, and remediation.
        """
        pass

    @abstractmethod
    def get_root_test_dirs(self) -> list[Path]:
        """
        Retrieve the root test directories provided by this scanner.

        These directories will be treated as additional root test directories
        by the Inspector Test Framework, which will handle the actual test file
        discovery and organization according to the standard directory structure:

            root_test_dir/
            ├── detector_name/
            │   ├── test_project_1/
            │   │   └── test_files...
            │   └── test_project_2/
            │       └── test_files...

        Returns:
            list[Path]: List of Path objects pointing to root test directories.
        """
        pass

    @abstractmethod
    def run(
        self,
        detector_names: list[str],
        code_paths: list[Path],
        project_root: Path,
    ) -> MinimalScannerResponse:
        """
        Execute the scan operation on the provided code files using specified detectors.

        This method analyzes the given source files with the enabled detectors and
        returns a MinimalScannerResponse summarizing the results. The response includes
        scanner-level errors, a list of scanned files (relative to the project root),
        and a mapping of detector IDs to their respective MinimalDetectorResponse objects.

        Args:
            detector_names (list[str]):
                List of detector identifiers to enable for this scan. Each identifier
                must correspond to a supported detector.
            code_paths (list[Path]):
                List of Path objects pointing to source code files to analyze.
                Each Path should reference a valid, readable file.
            project_root (Path):
                Path object representing the absolute path to the project's root
                directory. Used for resolving relative file paths in the output.

        Returns:
            MinimalScannerResponse:
                An object containing:
                    - errors: List of scanner-level error messages encountered during the scan.
                    - scanned: List of file paths (as strings, relative to project_root) that were successfully scanned.
                    - responses: Dictionary mapping detector IDs to MinimalDetectorResponse objects,
                      each representing the findings and metadata for that detector.

        Raises:
            ScanException:
                If the scan operation fails due to invalid detector configuration,
                file access or parsing errors, resource constraints, or internal scanner errors.
        """
        pass
