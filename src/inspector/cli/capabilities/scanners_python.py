import importlib
import inspect
import os
import shutil
import subprocess
import tomllib
import venv
from pathlib import Path
from shutil import ignore_patterns
from typing import Dict, Any, Optional
import logging
from logging import Logger

from inspector.cli.capabilities.exceptions import (
    InvalidScannerDirectoryError,
    InstallationError,
    DependencyInstallationError,
)
from inspector.cli.capabilities.helpers import (
    _remove_dir_or_link,
    _remove_existing_installation,
)
from .scanners_installable import InstallableScanner
from ...scanner_manager import VenvPathManager

logger: Logger = logging.getLogger(__name__)

PIP_INSTALL_TIMEOUT = 600  # seconds (10 minutes)
PIP_EDITABLE_INSTALL_TIMEOUT = 300  # seconds (5 minutes)
# files that should never be copied from scanner source into the installation location
SENSITIVE_PATTERNS = {
    ".env",
    ".secrets",
    ".env.local",
    "venv",
    ".git",
    ".idea",
    ".github",
    ".pytest_cache",
    ".gitignore",
}


class PythonInstallableScanner(InstallableScanner):
    """Handler for Python scanners."""

    def is_effective_develop(self) -> bool:
        """
        Determine if the Python scanner is in effective development mode.

        Returns:
            True if the scanner is in effective development mode, False otherwise.
        """
        return (
            self.installer.develop
            and self.installer.source_type == "local_path"
            and not self.installer._source_is_file
        )

    def fetch_metadata(self, source: Path) -> Dict[str, Any]:
        """Fetch metadata from a Python scanner source."""
        toml_path = source / "pyproject.toml"
        if not toml_path.exists():
            raise InvalidScannerDirectoryError(f"No pyproject.toml found in {source}")

        logger.debug(f"Reading metadata from pyproject.toml at {toml_path}")
        try:
            with open(toml_path, "rb") as f:
                pyproject = tomllib.load(f)

            oz_section = (
                pyproject.get("tool", {}).get("openzeppelin", {}).get("inspector", {})
            )
            if not oz_section:
                raise InvalidScannerDirectoryError(
                    f"No [tool.openzeppelin.inspector] section found in {toml_path}"
                )

            scanner_metadata = {
                "name": oz_section.get("scanner_name"),
                "org": oz_section.get("scanner_org", "unknown"),
                "description": oz_section.get("scanner_description", ""),
                "version": pyproject.get("project", {}).get("version", "unknown"),
                "extensions": oz_section.get("scanner_extensions", []),
                "detectors": {},  # filled later or left empty
            }

            if not scanner_metadata["name"]:
                raise InvalidScannerDirectoryError(
                    "scanner_name is required in pyproject.toml"
                )

            logger.debug(f"Extracted scanner metadata from toml: {scanner_metadata}")
            return scanner_metadata

        except Exception as e:
            raise InvalidScannerDirectoryError(
                f"Failed to parse scanner metadata from {toml_path}: {e}"
            )

    def place_scanner_files(self, source_to_use: Path, use_develop: bool) -> None:
        """Place Python scanner files from source to installation path."""
        if use_develop:
            # Existing logic for Python scanner (dir)
            if self.installer._install_path.exists():
                _remove_dir_or_link(self.installer._install_path)
            os.symlink(
                source_to_use, self.installer._install_path, target_is_directory=True
            )
        else:
            # source_to_use should be the directory containing pyproject.toml etc.
            shutil.copytree(
                source_to_use,
                self.installer._install_path,
                symlinks=True,
                dirs_exist_ok=True,
                ignore=ignore_patterns(*SENSITIVE_PATTERNS),
            )

    def post_install_setup(self) -> None:
        """Set up virtual environment for Python scanner."""
        if not self.installer._determined_scanner_name:
            raise InstallationError(
                "Internal Error: Cannot run post-install without name."
            )
        logger.info(
            f"Running Python post-install setup for '{self.installer._determined_scanner_name}'"
        )
        try:
            self._setup_python_scanner_venv()
        except (DependencyInstallationError, InstallationError) as e:
            logger.error(
                f"Python setup failed for '{self.installer._determined_scanner_name}'. Cleaning up."
            )
            _remove_existing_installation(self.installer._determined_scanner_name)
            raise e
        except Exception as e:
            logger.error(
                f"Unexpected Python setup error for '{self.installer._determined_scanner_name}'. Cleaning up.",
                exc_info=True,
            )
            _remove_existing_installation(self.installer._determined_scanner_name)
            raise InstallationError(
                f"Python post-install setup failed unexpectedly: {str(e)}"
            ) from e

    def _setup_python_scanner_venv(self) -> None:
        """Creates venv and installs dependencies for a Python scanner."""
        if (
            not self.installer._install_path
            or not self.installer._install_path.is_dir()  # Should be dir for Python scanner
            or not self.installer._venv_path
        ):
            raise InstallationError("Internal Error: Invalid paths for venv setup.")
        if not self.installer._determined_scanner_name:
            raise InstallationError(
                "Internal Error: Scanner name needed for venv setup."
            )
        logger.info(
            f"Setting up venv for '{self.installer._determined_scanner_name}' at {self.installer._venv_path}"
        )

        # 1. Create venv
        try:
            logger.debug(f"Creating venv: {self.installer._venv_path}")
            # Ensure parent exists first
            self.installer._venv_path.parent.mkdir(parents=True, exist_ok=True)
            venv.create(
                self.installer._venv_path, with_pip=True, symlinks=True
            )  # Use symlinks=True for potentially smaller venvs
        except Exception as e:
            raise DependencyInstallationError(f"Failed creating venv: {str(e)}")

        # Construct the path to the pip executable within the venv
        if os.name == "nt":  # Windows
            pip_path = self.installer._venv_path / "Scripts" / "pip.exe"
        else:  # Linux, macOS, etc.
            pip_path = self.installer._venv_path / "bin" / "pip"

        if not pip_path or not pip_path.exists():
            logger.error(
                f"Could not find pip executable at expected location: {pip_path}"
            )
            raise DependencyInstallationError(
                f"Could not find pip executable in created venv: {self.installer._venv_path}"
            )

        is_effective_develop = self.is_effective_develop()
        req_file_name = (
            "requirements-dev.txt" if is_effective_develop else "requirements.txt"
        )
        # install_path should point to the copied/symlinked code
        req_path = self.installer._install_path / req_file_name
        if is_effective_develop and not req_path.exists():
            req_path_fallback = (
                self.installer._install_path / "requirements.txt"
            )  # Fallback
            if req_path_fallback.exists():
                logger.debug(
                    f"Using fallback requirements.txt for develop mode as {req_file_name} not found."
                )
                req_path = req_path_fallback
            else:
                logger.debug(
                    f"Neither {req_file_name} nor requirements.txt found at {self.installer._install_path}."
                )
                req_path = None  # Explicitly set to None if no req file found
        elif not req_path.exists():
            logger.debug(
                f"Requirements file {req_file_name} not found at {self.installer._install_path}."
            )
            req_path = None

        if req_path and req_path.is_file():
            logger.info(f"Installing dependencies from {req_path.name}")
            cmd = [
                str(pip_path),
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",  # Avoid potential caching issues
                "-r",
                str(req_path),
            ]
            try:
                logger.debug(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=PIP_INSTALL_TIMEOUT,
                    encoding="utf-8",
                    errors="replace",
                )
                logger.debug(f"pip install requirements output:\n{result.stdout}")
                if result.stderr:
                    logger.warning(f"pip install requirements stderr:\n{result.stderr}")
            except subprocess.CalledProcessError as e:
                raise DependencyInstallationError(
                    f"Failed installing deps from {req_path.name}: {e.stderr or e.stdout}"
                )
            except subprocess.TimeoutExpired:
                raise DependencyInstallationError(
                    f"Timeout installing deps from {req_path.name}"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error installing requirements: {e}", exc_info=True
                )
                raise DependencyInstallationError(
                    f"Unexpected error installing requirements from {req_path.name}: {str(e)}"
                ) from e
        else:
            logger.debug(
                f"No suitable requirements file found, skipping pip install -r."
            )

        # Always try to install the package itself using -e for Python scanners
        # This ensures the scanner code is runnable from the venv
        pyproject_path = self.installer._install_path / "pyproject.toml"
        setup_py_path = (
            self.installer._install_path / "setup.py"
        )  # Also check for setup.py

        if pyproject_path.exists() or setup_py_path.exists():
            install_target = str(self.installer._install_path)
            logger.info(
                f"Installing scanner package '{self.installer._determined_scanner_name}' from {install_target} in editable mode"
            )
            cmd = [
                str(pip_path),
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "-e",
                install_target,  # Install the directory containing setup.py/pyproject.toml
            ]
            try:
                logger.debug(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=PIP_EDITABLE_INSTALL_TIMEOUT,
                    encoding="utf-8",
                    errors="replace",
                )
                logger.debug(f"pip install -e output:\n{result.stdout}")
                if result.stderr:
                    logger.warning(f"pip install -e stderr:\n{result.stderr}")
            except subprocess.CalledProcessError as e:
                # Provide more context on editable install failure
                logger.error(f"Editable install failed. Command: {' '.join(cmd)}")
                logger.error(f"Stderr:\n{e.stderr}")
                logger.error(f"Stdout:\n{e.stdout}")
                raise DependencyInstallationError(
                    f"Failed installing scanner package '{self.installer._determined_scanner_name}' in editable mode: {e.stderr or e.stdout}"
                )
            except subprocess.TimeoutExpired:
                raise DependencyInstallationError(
                    f"Timeout installing scanner package '{self.installer._determined_scanner_name}' in editable mode"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error during editable install: {e}", exc_info=True
                )
                raise DependencyInstallationError(
                    f"Unexpected error installing scanner package '{self.installer._determined_scanner_name}' in editable mode: {str(e)}"
                ) from e
        else:
            logger.warning(
                f"No pyproject.toml or setup.py found in '{self.installer._install_path}', skipping editable install for Python scanner '{self.installer._determined_scanner_name}'. The scanner might not be importable."
            )

    def collect_detector_metadata(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Collect detector metadata from a Python scanner."""
        if (
            not self.installer._venv_path
            or not self.installer._venv_path.exists()
            or not self.installer._install_path
            or not self.installer._install_path.exists()
            or not self.installer._determined_scanner_name
        ):
            logger.error(
                f"Cannot collect Python metadata for '{self.installer._determined_scanner_name or 'Unknown'}': Missing required paths or name."
            )
            return None
        logger.debug(
            f"Collecting Python detector metadata for '{self.installer._determined_scanner_name}' using venv: {self.installer._venv_path}"
        )
        # Use the actual installed scanner name for module import if different from package name
        # For simplicity, assuming package name matches scanner name (underscores vs hyphens handled)
        # The editable install should make the package directly importable by its name from pyproject.toml/setup.py
        scanner_module_name_from_meta = self.installer._scanner_metadata.get("name")
        if not scanner_module_name_from_meta:
            logger.error(
                "Cannot determine module name for dynamic detector loading: scanner name missing from metadata."
            )
            return None

        scanner_module_name = scanner_module_name_from_meta.replace("-", "_")

        try:
            # Use context manager to temporarily activate venv for import resolution
            with VenvPathManager.temporary_venv_path(
                self.installer._venv_path.parent,  # Base dir for venvs
                self.installer._determined_scanner_name,  # Specific venv name/folder
                self.installer._install_path,  # Add install path too, just in case
            ):
                import sys

                logger.debug(f"Attempting to import module: {scanner_module_name}")

                # Ensure importlib reloads the module in case it was imported before in a different context
                if scanner_module_name in sys.modules:
                    scanner_module = importlib.reload(sys.modules[scanner_module_name])
                else:
                    scanner_module = importlib.import_module(scanner_module_name)

                # Attempt to find the BaseScanner subclass dynamically
                scanner_class = None
                try:
                    # Dynamically import BaseScanner to avoid circular dependency issues at module level
                    base_scanner_module = importlib.import_module("inspector.scanners")
                    base_scanner_cls = getattr(base_scanner_module, "BaseScanner")
                except (ImportError, AttributeError) as e:
                    logger.error(
                        f"Could not import BaseScanner for dynamic lookup: {e}"
                    )
                    return None  # Cannot proceed without BaseScanner

                logger.debug(
                    f"Scanning module '{scanner_module_name}' for BaseScanner subclasses..."
                )
                found_classes = []
                for name, obj in inspect.getmembers(scanner_module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, base_scanner_cls)
                        and obj is not base_scanner_cls
                        and obj.__module__.startswith(
                            scanner_module_name
                        )  # Ensure it's defined within the scanner's package
                    ):
                        logger.debug(
                            f"Found BaseScanner subclass: {name} ({obj.__module__})"
                        )
                        found_classes.append(obj)

                if len(found_classes) == 1:
                    scanner_class = found_classes[0]
                    logger.debug(
                        f"Using dynamically found scanner class: {scanner_class.__name__}"
                    )
                elif len(found_classes) > 1:
                    logger.warning(
                        f"Multiple BaseScanner subclasses found in '{scanner_module_name}': {[c.__name__ for c in found_classes]}. Attempting heuristic based on name..."
                    )
                    # Heuristic: Find class name matching title-cased module name
                    class_name_convention = "".join(
                        word.capitalize() for word in scanner_module_name.split("_")
                    )
                    matching_classes = [
                        c for c in found_classes if c.__name__ == class_name_convention
                    ]
                    if len(matching_classes) == 1:
                        scanner_class = matching_classes[0]
                        logger.debug(
                            f"Selected class based on naming convention: {scanner_class.__name__}"
                        )
                    else:
                        logger.warning(
                            f"Could not uniquely identify scanner class by convention. Using first found: {found_classes[0].__name__}"
                        )
                        scanner_class = found_classes[0]  # Fallback to first found
                else:
                    # Fallback to naming convention if dynamic lookup finds nothing *defined in the module*
                    class_name_convention = "".join(
                        word.capitalize() for word in scanner_module_name.split("_")
                    )
                    logger.debug(
                        f"No specific BaseScanner subclass found directly. Falling back to convention name: {class_name_convention}"
                    )
                    scanner_class = getattr(scanner_module, class_name_convention, None)
                    if scanner_class and not (
                        inspect.isclass(scanner_class)
                        and issubclass(scanner_class, base_scanner_cls)
                    ):
                        logger.warning(
                            f"Class found by convention '{class_name_convention}' is not a valid BaseScanner subclass."
                        )
                        scanner_class = None  # Invalidate if wrong type

                if not scanner_class:
                    logger.error(
                        f"Could not find a valid BaseScanner subclass in module '{scanner_module_name}'. Cannot collect dynamic detectors."
                    )
                    return None  # Return None on failure

                try:
                    # Instantiate the found scanner class
                    logger.debug(
                        f"Instantiating scanner class: {scanner_class.__name__}"
                    )
                    scanner_instance = scanner_class()
                except Exception as e:
                    logger.error(
                        f"Failed instantiating scanner class '{scanner_class.__name__}': {e}",
                        exc_info=True,
                    )
                    return None  # Return None on failure

                # Call the method to get detector metadata
                metadata_method_name = "get_supported_detector_metadata"
                if not hasattr(scanner_instance, metadata_method_name):
                    logger.error(
                        f"Scanner class '{scanner_class.__name__}' does not have method '{metadata_method_name}'. Cannot collect detectors."
                    )
                    return None

                logger.debug(
                    f"Calling {scanner_class.__name__}.{metadata_method_name}()"
                )
                detector_metadata_dict = getattr(
                    scanner_instance, metadata_method_name
                )()

                if isinstance(detector_metadata_dict, dict):
                    logger.debug(
                        f"Collected {len(detector_metadata_dict)} Python detectors."
                    )
                    return detector_metadata_dict  # Return the dictionary
                else:
                    logger.warning(
                        f"{metadata_method_name}() did not return a dictionary (type: {type(detector_metadata_dict)}). Returning empty."
                    )
                    return {}  # Return empty dict if wrong type

        except ImportError as e:
            logger.error(
                f"Import failed for '{scanner_module_name}': {e}. Ensure the package was installed correctly (-e .) in the venv '{self.installer._venv_path}'. Check sys.path if necessary.",
                exc_info=False,  # Often too verbose for simple import error
            )
            # Log sys.path within the venv context for debugging
            import sys

            logger.debug(f"sys.path during import attempt: {sys.path}")
            return None  # Return None on failure
        except Exception as e:
            logger.error(
                f"Error collecting dynamic Python detectors for '{self.installer._determined_scanner_name}': {e}",
                exc_info=True,
            )
            return None  # Return None on failure
