"""
Scanner Management System for Code Analysis

This module provides a framework for managing and executing various code analysis scanners.
It supports both Python-based and executable scanners, handling their discovery, initialization,
and execution in isolated virtual environments.

Key Components:
- VenvPathManager: Manages Python path manipulation for virtual environments
- AbstractScannerRunner: Base class for scanner execution
- PythonScannerRunner: Handles Python-based scanners
- ExecutableScannerRunner: Handles binary/executable scanners
- ScannerManager: Main singleton class orchestrating scanner operations

Environment Variables:
    INSPECTOR_SCANNERS: Colon-separated paths to additional scanner locations
"""

import json
import os
import logging
import abc
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import importlib
import traceback
from .constants import PATH_USER_INSPECTOR_SCANNERS_VENVS
from .models.minimal.scanner_response import MinimalScannerResponse
from .models._complete.scanner_response import CompleteScannerResponse
from .response_expander import expand_response_minimal_to_full
from .scanners import BaseScanner
from .scanners.types import ScannerType
from . import scanner_registry
from .source_code_manager import SourceCodeManager


class VenvPathManager:
    """
    Manages Python path manipulation for virtual environments.
    Provides context management for temporarily modifying sys.path.
    """

    @staticmethod
    @contextmanager
    def temporary_venv_path(
        venv_dir: Path, scanner_dir: str, scanner_path: Path | None = None
    ):
        """
        Temporarily modifies sys.path to include virtual environment paths.

        Args:
            venv_dir: Base directory containing virtual environments
            scanner_dir: Name of the scanner's directory
            scanner_path: Optional path to the scanner's source code

        Yields:
            None: Provides a context where sys.path is modified
        """
        if sys.platform == "win32":
            venv_python = venv_dir / scanner_dir / "Scripts" / "python.exe"
        else:
            venv_python = venv_dir / scanner_dir / "bin" / "python"
        venv_paths = (
            subprocess.check_output(
                [str(venv_python), "-c", "import sys; print(':'.join(sys.path))"],
                text=True,
            )
            .strip()
            .split(":")
        )

        original_path = sys.path.copy()
        try:
            if scanner_path and scanner_path.is_dir():
                sys.path.insert(0, str(scanner_path))
            sys.path[0:0] = [p for p in venv_paths if p and p not in sys.path]
            yield
        finally:
            sys.path = original_path


class AbstractScannerRunner(abc.ABC):
    """
    Abstract base class defining the interface for scanner runners.
    """

    @abc.abstractmethod
    def get_scanner_name(self) -> str:
        pass

    @abc.abstractmethod
    def get_supported_detector_metadata(self) -> dict[str, dict]:
        pass

    @abc.abstractmethod
    def get_root_test_dirs(self) -> list[Path]:
        pass

    @abc.abstractmethod
    def run(
        self, detector_names: list[str], code_paths: list[Path], project_root: Path
    ) -> MinimalScannerResponse:
        pass


class PythonScannerRunner(AbstractScannerRunner):
    def __init__(self, scanner: BaseScanner, scanner_dir: str):
        self._scanner = scanner
        self._scanner_dir = scanner_dir
        self._venvs_dir = PATH_USER_INSPECTOR_SCANNERS_VENVS

    def get_scanner_name(self) -> str:
        return self._scanner.get_scanner_name()

    def get_supported_detector_metadata(self) -> dict[str, dict]:
        with VenvPathManager.temporary_venv_path(self._venvs_dir, self._scanner_dir):
            return self._scanner.get_supported_detector_metadata()

    def get_root_test_dirs(self) -> list[Path]:
        with VenvPathManager.temporary_venv_path(self._venvs_dir, self._scanner_dir):
            return self._scanner.get_root_test_dirs()

    def run(
        self, detector_names: list[str], code_paths: list[Path], project_root: Path
    ) -> MinimalScannerResponse:
        with VenvPathManager.temporary_venv_path(self._venvs_dir, self._scanner_dir):
            return self._scanner.run(detector_names, code_paths, project_root)


class ExecutableScannerRunner(AbstractScannerRunner):
    def __init__(self, scanner_path: Path, scanner_name: str):
        self._scanner_path = scanner_path
        self._scanner_name = scanner_name
        self._scanner_info = scanner_registry.get_scanner_info(scanner_name)

    def get_scanner_name(self) -> str:
        return self._scanner_name

    def get_supported_detector_metadata(self) -> dict[str, dict]:
        return self._scanner_info.get("detectors", {})

    def get_root_test_dirs(self) -> list[Path]:
        return []

    def run(
        self, detector_names: list[str], code_paths: list[Path], project_root: Path
    ) -> MinimalScannerResponse:
        scanner_executable = self._scanner_path / "scanner"
        cmd = [
            str(scanner_executable),
            "scan",
            *(str(p.resolve()) for p in code_paths),
            "--detectors",
            *detector_names,
            "--project-root",
            str(project_root.resolve()),
        ]

        try:
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            raw_output = json.loads(process.stdout)

            return self._parse_scanner_output(raw_output)

        except subprocess.CalledProcessError:
            raise
        except json.JSONDecodeError:
            raise

    @staticmethod
    def _parse_scanner_output(raw_output: dict) -> MinimalScannerResponse:
        return MinimalScannerResponse.from_dict(raw_output)


class ScannerManager:
    """
    Singleton manager class for scanner discovery, initialization, and execution.

    Handles:
    - Scanner discovery across multiple filesystem locations
    - Virtual environment setup for Python-based scanners
    - Scanner execution and result aggregation
    - Error handling and logging
    """

    _instance: "ScannerManager | None" = None
    _initialized: bool = False
    _scanners: dict[str, AbstractScannerRunner] = {}
    _all_detector_names: tuple[str, ...] = ()
    _all_detector_metadata: dict[str, dict] = {}
    _all_scanners: tuple[AbstractScannerRunner, ...] = ()
    _logger: logging.Logger = logging.getLogger(__name__)

    def __new__(cls) -> "ScannerManager":
        """Ensure singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the scanner manager if not already initialized."""
        if not self._initialized:
            self._initialize_scanners()
            self.__class__._initialized = True

    def _initialize_scanners(self) -> None:
        """Initialize scanners and detectors if not already loaded."""
        if not self._scanners:
            self._load_scanners()
        if not self._all_detector_metadata:
            self._load_all_detectors()

    @classmethod
    def reload(cls) -> None:
        """
        Force a full reload of scanner registry and scanner state.
        """
        cls._logger.debug("Reloading scanner registry and scanner state...")

        # Reset internal state
        cls._scanners = {}
        cls._all_detector_metadata = {}
        cls._all_detector_names = ()
        cls._all_scanners = ()
        cls._initialized = False

        # Reload registry
        scanner_registry.reload()

        # Reinitialize
        cls()._initialize_scanners()
        cls._initialized = True

    def execute_scan(
        self,
        detector_names: list[str],
        code: list[Path],
        project_root: Path,
        scanners: list[str] | None = None,
    ) -> dict[str, CompleteScannerResponse]:
        """
        Execute specified detectors using specified scanners (or else all scanners).

        Args:
            detector_names: List of rule identifiers to execute
            code: List of source code file paths to analyze
            project_root: Root directory of the project being analyzed
            scanners: Optional list of specific scanner names to use

        Returns:
            Dictionary mapping scanner names to their CompleteScannerResponse objects

        Note:
            Scanner failures are logged but don't stop execution of other scanners
        """
        source_code_manager = SourceCodeManager()
        results: dict[str, CompleteScannerResponse] = {}
        scanners = scanners or scanner_registry.get_scanners_by_criteria(
            detectors=detector_names
        )

        for scanner_name, runner in self._scanners.items():
            if scanner_name not in scanners:
                continue
            try:
                scanner_minimal_response = runner.run(
                    detector_names, code, project_root
                )
                scanner_full_response = expand_response_minimal_to_full(
                    scanner_minimal_response, source_code_manager, project_root
                )
                results[scanner_name] = scanner_full_response
            except Exception as e:
                self._logger.exception("Scanner %s failed: %s", scanner_name, e)

        return results

    @classmethod
    def get_all_available_detector_names(cls) -> tuple[str, ...]:
        """
        Get list of all available detector names.

        Returns:
            Tuple of detector names
        """
        if not cls._initialized:
            cls()
        return cls._all_detector_names

    @classmethod
    def get_all_available_detector_metadata(cls) -> dict[str, dict]:
        """
        Get all available detector metadata.
        """
        if not cls._initialized:
            cls()
        return cls._all_detector_metadata

    @classmethod
    def get_detector_metadata_by_name(
        cls, detector_name: str
    ) -> dict[str, dict] | None:
        """
        Get all available detector metadata.
        """
        if not cls._initialized:
            cls()
        return cls._all_detector_metadata.get(detector_name, None)

    @classmethod
    def get_all_available_scanner_names(cls) -> tuple[str, ...]:
        """
        Get tuple of all available scanner names.

        Returns:
            Tuple of scanner names (matching their directory names)
        """
        if not cls._initialized:
            cls()
        return tuple(cls._scanners.keys())

    @classmethod
    def get_scanner_by_name(cls, scanner_name: str) -> AbstractScannerRunner:
        """
        Get a specific scanner by name.

        Args:
            scanner_name: Name of the scanner to retrieve

        Returns:
            The requested scanner runner instance

        Raises:
            KeyError: If the requested scanner is not found
        """
        if not cls._initialized:
            cls()

        if scanner_name not in cls._scanners:
            raise KeyError(
                f"Scanner '{scanner_name}' not found. Available scanners: {', '.join(cls._scanners.keys())}"
            )

        return cls._scanners[scanner_name]

    @classmethod
    def get_all_available_scanners(cls) -> tuple[AbstractScannerRunner, ...]:
        """
        Get tuple of all available scanners.

        Returns:
            Tuple of scanners
        """
        if not cls._initialized:
            cls()
        return cls._all_scanners

    def _load_all_detectors(self) -> None:
        """Load and cache all available detector metadata from registered scanners."""
        all_detectors = {}
        for scanner in self._scanners.values():
            try:
                self._logger.debug(
                    "Begin loading detectors for scanner %s",
                    scanner.get_scanner_name(),
                )
                scanner_detectors = scanner.get_supported_detector_metadata()
                for detector_name, detector_metadata in scanner_detectors.items():
                    all_detectors[detector_name] = detector_metadata
                self._logger.debug(
                    "Finish loading detectors for scanner %s",
                    scanner.get_scanner_name(),
                )
            except Exception as e:
                self._logger.warning(
                    "Failed to load detectors from scanner: %s", str(e)
                )
                traceback.print_exc()

        sorted_detectors = sorted(all_detectors.values(), key=lambda x: x["id"])
        self.__class__._all_detector_metadata = {}
        for detector in sorted_detectors:
            detector_id = detector["id"]
            self.__class__._all_detector_metadata[detector_id] = detector

        # Set _all_detector_names based on the keys in _all_detector_metadata
        self.__class__._all_detector_names = tuple(
            sorted(self.__class__._all_detector_metadata.keys())
        )

    @classmethod
    def _load_scanners(cls) -> None:
        """
        Load all registered scanners from the scanner registry using ScannerRegistry.

        Gets scanner information directly using get_installed_scanners_with_info() and loads
        each scanner based on its recorded type. Handles scanner loading failures gracefully.
        """
        cls._logger.debug("Loading scanners from registry...")

        # Use the registry reader to get all scanner info at once
        scanners_info = scanner_registry.get_installed_scanners_with_info()

        if not scanners_info:
            cls._logger.debug("No scanners found in registry")
            return

        # Load each scanner
        for scanner_info in scanners_info:
            scanner_name = scanner_info["name"]
            scanner_path = Path(scanner_info.get("path", ""))

            try:
                # Convert string type to enum
                scanner_type_str = scanner_info.get("type", "unknown")
                scanner_type = ScannerType(scanner_type_str)

                try:
                    # Load scanner based on its type
                    if scanner_type == ScannerType.PYTHON:
                        cls._logger.debug(f"Loading Python scanner: {scanner_name}")
                        cls._load_python_scanner(scanner_name, scanner_path)
                    elif scanner_type == ScannerType.EXECUTABLE:
                        executable_path = scanner_path
                        if executable_path.exists() and os.access(
                            executable_path, os.X_OK
                        ):
                            cls._logger.debug(
                                f"Loading executable scanner: {scanner_name}"
                            )
                            cls._scanners[scanner_name] = ExecutableScannerRunner(
                                executable_path, scanner_name
                            )
                        else:
                            cls._logger.warning(
                                f"Scanner executable not found or not executable: {executable_path}"
                            )
                    else:
                        cls._logger.warning(
                            f"Unknown scanner type '{scanner_type}' for scanner '{scanner_name}'"
                        )
                except Exception as e:
                    cls._logger.warning(f"Failed to load scanner {scanner_name}: {e}")
            except ValueError as e:
                cls._logger.warning(f"Invalid scanner type for {scanner_name}: {e}")

        cls._all_scanners = tuple(scanner for scanner in cls._scanners.values())

    @classmethod
    def _load_python_scanner(cls, scanner_dir: str, scanner_path: Path) -> None:
        """
        Load a Python-based scanner implementation.

        Args:
            scanner_dir: Directory name of the scanner
            scanner_path: Path to scanner source code

        Raises:
            Various exceptions during import or instantiation
        """
        try:
            with VenvPathManager.temporary_venv_path(
                PATH_USER_INSPECTOR_SCANNERS_VENVS, scanner_dir, scanner_path
            ):
                scanner_module = importlib.import_module(scanner_dir.replace("-", "_"))
                class_name = "".join(
                    word.capitalize()
                    for word in scanner_dir.replace("-", "_").split("_")
                )

                if hasattr(scanner_module, class_name):
                    scanner_class = getattr(scanner_module, class_name)
                    cls._scanners[scanner_dir] = PythonScannerRunner(
                        scanner_class(), scanner_dir
                    )
                else:
                    raise AttributeError(
                        f"Class {class_name} not found in module {scanner_dir}"
                    )
        except Exception as e:
            cls._logger.error("Failed to load Python scanner %s: %s", scanner_dir, e)
            raise
