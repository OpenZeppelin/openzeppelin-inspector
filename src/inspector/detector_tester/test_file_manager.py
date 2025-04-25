"""
Test file management module for detector-based testing framework.

This module provides functionality for discovering and managing test files across
both internal and user-defined test directories.

The module assumes a specific directory structure where test files are organized
in subdirectories named after their corresponding detectors, with test_project subfolders
within each detector directory.
"""

import logging
from pathlib import Path

from ..scanner_manager import ScannerManager


class NoTestFilesDiscoveredError(Exception):
    def __init__(self, searched_dirs):
        self.searched_dirs = searched_dirs
        dirs_str = ", ".join(str(d) for d in searched_dirs)
        super().__init__(
            f"No test files were discovered in the following directories: {dirs_str}"
        )


class DetectorTestManager:
    """
    A class that manages test file discovery and caching.

    This class handles the discovery and caching of test files from both internal
    and user-defined test directories. It maintains a mapping of detector names to
    test_project names to their associated test files and provides a clean interface
    for accessing these files.

    Attributes:
        _test_files (dict[str, dict[str, list[Path]]]): Cached mapping of detector names
                                                       to test_project names to their test file paths.
    """

    def __init__(
        self,
        requested_scanners: tuple[str, ...] = None,
        requested_detectors: tuple[str, ...] = None,
        root_test_dirs: tuple[Path, ...] = (),
    ) -> None:
        """
        Initializes the TestManager instance.

        Args:
            requested_scanners: Optional tuple of scanner names to filter by
            requested_detectors: Optional tuple of detector names to filter by
            root_test_dirs: Optional tuple of root test directories to use exclusively
        """
        # initialize logger
        self._logger = logging.getLogger(__name__)

        # Save the scanners manager for later use
        self.scanners_manager = ScannerManager
        self._test_files: dict[str, dict[str, list[Path]]] = {}
        self._test_project_dirs: dict[str, dict[str, Path]] = {}
        self._requested_scanners = requested_scanners or ()
        self._requested_detectors = requested_detectors or ()
        self._root_test_dirs = root_test_dirs
        self._discover_test_files()

    def _discover_test_files(self) -> None:
        """
        Discovers and caches test files from configured directories.

        If self._root_test_dirs is provided and non-empty, only those directories are used.
        Otherwise, falls back to scanner-provided test directories.
        """
        all_detector_names = self.scanners_manager.get_all_available_detector_names()

        # If specific detectors were requested, only look for those
        detector_names_to_process = set(all_detector_names)
        if self._requested_detectors:
            detector_names_to_process = (
                set(self._requested_detectors) & detector_names_to_process
            )

        # Decide which root test dirs to use
        if self._root_test_dirs:
            root_test_dirs = list(self._root_test_dirs)
            self._logger.info(
                f"Using only provided root test directories: {root_test_dirs}"
            )
        else:
            # Fallback: use scanner-provided test dirs
            root_test_dirs = []
            available_scanners = ScannerManager.get_all_available_scanners()
            scanners_to_use = available_scanners
            if self._requested_scanners:
                scanners_to_use = [
                    scanner
                    for scanner in available_scanners
                    if scanner.get_scanner_name() in self._requested_scanners
                ]
            for scanner in sorted(scanners_to_use, key=lambda s: s.get_scanner_name()):
                scanner_name = scanner.get_scanner_name()
                self._logger.debug(
                    f"Getting root test directories from scanner: {scanner_name}"
                )
                scanner_test_dirs = scanner.get_root_test_dirs()
                if scanner_test_dirs:
                    sorted_test_dirs = sorted(scanner_test_dirs, key=str)
                    self._logger.debug(
                        f"Scanner {scanner_name} provided {len(sorted_test_dirs)} root test directories"
                    )
                    root_test_dirs.extend(sorted_test_dirs)
                else:
                    self._logger.debug(
                        f"Scanner {scanner_name} provided no root test directories"
                    )

        # Process all root test directories - sort for determinism
        for base_dir in sorted(root_test_dirs, key=str):
            if not base_dir.exists():
                self._logger.debug(
                    "Base test directory does not exist and will be skipped: %s",
                    base_dir,
                )
                continue
            else:
                self._logger.debug(
                    "Base test directory exists and will be inspected for tests: %s",
                    base_dir,
                )

            # Process each detector directory - sort for determinism
            for detector_dir in sorted(base_dir.iterdir(), key=lambda p: p.name):
                if detector_dir.is_dir():
                    detector_name = detector_dir.name

                    if detector_name in detector_names_to_process:
                        self._logger.debug(
                            "Inspector test file path for detector %s: %s",
                            detector_name,
                            detector_dir,
                        )

                        # Initialize detector in test_files if not present
                        self._test_files.setdefault(detector_name, {})

                        # Look for test_project subdirectories - sort for determinism
                        test_project_dirs = sorted(
                            [d for d in detector_dir.iterdir() if d.is_dir()],
                            key=lambda p: p.name,
                        )

                        # Check for loose files at the detector level (excluding documentation files)
                        all_files = sorted(
                            list(detector_dir.glob("*")), key=lambda p: p.name
                        )
                        files = [f for f in all_files if f.is_file()]

                        non_doc_loose_files = []
                        for f in sorted(files, key=lambda p: p.name):
                            name_parts = f.stem.split("-")
                            if not (len(name_parts) > 1 and name_parts[-1] == "doc"):
                                non_doc_loose_files.append(f)

                        if non_doc_loose_files:
                            self._logger.warning(
                                "Found loose files at detector level for %s in test directory. "
                                "Files should be organized within test_project subdirectories. "
                                "These files will be ignored: %s",
                                detector_name,
                                [
                                    f.name
                                    for f in sorted(
                                        non_doc_loose_files, key=lambda p: p.name
                                    )
                                ],
                            )

                        # Process each test_project directory - sort for determinism
                        if test_project_dirs:
                            for test_project_dir in sorted(
                                test_project_dirs, key=lambda p: p.name
                            ):
                                test_project_name = test_project_dir.name

                                # No prefixing for source, since only explicit dirs are used
                                unique_test_project_name = test_project_name

                                # Store the test project directory
                                self._test_project_dirs.setdefault(detector_name, {})[
                                    unique_test_project_name
                                ] = test_project_dir

                                # Sort files immediately after collection for determinism
                                all_paths = sorted(test_project_dir.rglob("*"))
                                project_files = sorted(
                                    [p for p in all_paths if p.is_file()], key=str
                                )

                                if project_files:
                                    self._test_files[detector_name][
                                        unique_test_project_name
                                    ] = project_files
                                    self._logger.debug(
                                        "Found test_project '%s' for detector '%s' with %d files in test directory %s",
                                        unique_test_project_name,
                                        detector_name,
                                        len(project_files),
                                        base_dir,
                                    )
                                else:
                                    self._logger.debug(
                                        "Test_project '%s' for detector '%s' in test directory %s contains no files and will be skipped",
                                        unique_test_project_name,
                                        detector_name,
                                        base_dir,
                                    )

        # Sort file lists for deterministic ordering and log summary
        for detector_name in sorted(self._test_files.keys()):
            for test_project_name in sorted(self._test_files[detector_name].keys()):
                self._test_files[detector_name][test_project_name] = sorted(
                    self._test_files[detector_name][test_project_name], key=str
                )
                self._logger.debug(
                    "Final test file count for detector %s, test_project %s: %d files",
                    detector_name,
                    test_project_name,
                    len(self._test_files[detector_name][test_project_name]),
                )

            if not self._test_files[detector_name]:
                self._logger.warning(
                    "No test files found for detector: %s", detector_name
                )

        # Raise error if no test files were found at all
        if not any(self._test_files.values()):
            raise NoTestFilesDiscoveredError(root_test_dirs)

    def get_test_files(
        self, detector_name: str, test_project_name: str = None
    ) -> list[Path]:
        """
        Retrieves the list of test files associated with a specific detector and optionally a test_project.

        Args:
            detector_name (str): The name of the detector to get test files for.
            test_project_name (str, optional): The name of the test_project to get test files for.
                                         If None, returns all files for all test_projects.

        Returns:
            list[Path]: A sorted list of Path objects associated with the detector and test_project.
                       Returns an empty list if no files are found.
        """
        if detector_name not in self._test_files:
            return []

        if test_project_name is not None:
            # Return files for a specific test_project
            return sorted(
                self._test_files[detector_name].get(test_project_name, []), key=str
            )
        else:
            # Return all files for all test_projects
            all_files = []
            for test_project in sorted(self._test_files[detector_name].keys()):
                all_files.extend(self._test_files[detector_name][test_project])
            return sorted(all_files, key=str)

    def get_test_projects(self, detector_name: str) -> list[str]:
        """
        Retrieves the list of test_project names for a specific detector.

        Args:
            detector_name (str): The name of the detector to get test_projects for.

        Returns:
            list[str]: A sorted list of test_project names associated with the detector.
                      Returns an empty list if no test_projects are found.
        """
        if detector_name not in self._test_files:
            return []

        return sorted(self._test_files[detector_name].keys())

    def get_all_detector_test_projects(self) -> dict[str, list[str]]:
        """
        Retrieves all detectors and their associated test_projects.

        Returns:
            dict[str, list[str]]: A dictionary mapping detector names to lists of test_project names.
        """
        return {
            detector: sorted(test_projects.keys())
            for detector, test_projects in self._test_files.items()
        }

    def get_test_project_dir(self, detector_name: str, test_project_name: str) -> Path:
        """
        Returns the directory for a specific detector's test project.

        Args:
            detector_name: The name of the detector
            test_project_name: The name of the test project

        Returns:
            Path object for the test project directory or None if not found
        """
        return self._test_project_dirs.get(detector_name, {}).get(test_project_name)
