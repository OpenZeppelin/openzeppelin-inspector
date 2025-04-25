import datetime
import logging
import os
import shutil
import tempfile
from logging import Logger
from pathlib import Path
from typing import Optional, Dict, Any

from .exceptions import (
    InstallationError,
    InvalidScannerDirectoryError,
    ScannerAlreadyInstalledError,
    DownloadError,
    ExtractionError,
    DependencyInstallationError,
)

from .scanners_installable import InstallableScanner
from .scanners_python import PythonInstallableScanner
from .scanners_executable import ExecutableInstallableScanner

from .helpers import (
    _get_scanner_paths,
    _remove_dir_or_link,
    _remove_existing_installation,
    _extract_zip,
    _download_remote_zip,
)

from ...scanners.types import ScannerType
from ... import scanner_registry

logger: Logger = logging.getLogger(__name__)


class ScannerHandlerFactory:
    """Factory for creating scanner handlers based on scanner type."""

    @staticmethod
    def create_handler(scanner_type: ScannerType, installer) -> InstallableScanner:
        """
        Create a scanner handler for the given scanner type.

        Args:
            scanner_type: The type of scanner to create a handler for.
            installer: The ScannerInstaller instance that will use the handler.

        Returns:
            A scanner handler for the given scanner type.

        Raises:
            ValueError: If the scanner type is not supported.
        """
        if scanner_type == ScannerType.PYTHON:
            return PythonInstallableScanner(installer)
        elif scanner_type == ScannerType.EXECUTABLE:
            return ExecutableInstallableScanner(installer)
        else:
            raise ValueError(f"Unsupported scanner type: {scanner_type}")


class ScannerInstaller:
    """
    Handles the installation of a scanner from various sources based on simplified assumptions.

    Assumptions:
    1. Zip Source (`local_zip`, `remote_zip`): After unzipping, the root must contain *either*:
        a) A Python scanner structure with `pyproject.toml`.
        b) A *single* executable file.
    2. Non-Zip File Source (`local_path` pointing to a file): Assumed to be the executable scanner file.
    3. Directory Source (`local_path` pointing to a directory): Must contain *either*:
        a) A Python scanner structure with `pyproject.toml`.
        b) A *single* executable file at the root.
    4. Scanner Discovery: Only the root of the provided path/extracted zip is checked. No subdirectories are searched.
    5. Develop Mode (`--develop`): Only applicable for `local_path` directory Python scanners.
    """

    def __init__(
        self, source_type: str, path_value: str, reinstall: bool, develop: bool
    ):
        self.source_type = source_type
        self.path_value = path_value
        self.reinstall = reinstall
        self.develop = develop

        self._temp_dir_manager: Optional[tempfile.TemporaryDirectory] = None
        # Resolved path or root extraction dir
        self._prepared_source_path: Optional[Path] = None
        # True if the original local_path pointed to a file
        self._source_is_file: bool = False
        # True if the source was local_zip or remote_zip
        self._source_was_zip: bool = False

        self._scanner_metadata: Optional[Dict[str, Any]] = None
        self._scanner_type: Optional[ScannerType] = None
        self._determined_scanner_name: Optional[str] = None
        self._install_path: Optional[Path] = None
        self._venv_path: Optional[Path] = None
        # Path to executable if type is EXECUTABLE (either original or in temp dir)
        self._executable_path_in_source: Optional[Path] = None

        # Scanner handler will be set after scanner type is determined
        self._scanner_handler: Optional[InstallableScanner] = None

    def install(self) -> str:
        """Orchestrates the scanner installation process."""
        try:
            # 1. Prepare Source
            self._prepare_source()
            if (
                not self._prepared_source_path
                or not self._prepared_source_path.exists()
            ):
                raise InstallationError("Failed to prepare scanner source location.")

            # 2. Fetch Metadata
            self._fetch_metadata()
            if not self._scanner_metadata or self._scanner_type is None:
                raise InvalidScannerDirectoryError(
                    "Could not identify scanner type or retrieve metadata from source (check installation assumptions)."
                )

            # 3. Determine Final Name & Paths
            self._determine_final_name_and_paths()
            if (
                not self._determined_scanner_name
                or not self._install_path
                or not self._venv_path
            ):
                raise InstallationError(
                    "Failed to determine scanner name or installation paths."
                )

            # 4. Prepare Target
            self._prepare_target()

            # 5. Place Scanner Files
            self._place_scanner_files()

            # 6. Post-Install Setup
            self._post_install_setup()

            # 7. Register
            self._register()

            # 8. Success Message
            is_effective_develop = self._scanner_handler.is_effective_develop()
            mode = " in development mode" if is_effective_develop else ""
            type_desc = self._scanner_type.name.lower()
            success_message = f"Successfully installed scanner '{self._determined_scanner_name}' ({type_desc}){mode}"
            logger.info(success_message)
            return success_message

        except (
            InstallationError,
            InvalidScannerDirectoryError,
            ScannerAlreadyInstalledError,
            DownloadError,
            ExtractionError,
            DependencyInstallationError,
            ValueError,
        ) as e:
            logger.error(f"Installation failed: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during installation: {e}", exc_info=True)
            raise InstallationError(
                f"An unexpected error occurred during installation: {str(e)}"
            ) from e
        finally:
            # 9. Cleanup
            self._cleanup()

    def _prepare_source(self) -> None:
        """Resolves or downloads/extracts the source, setting flags."""
        logger.debug(
            f"Preparing source: type='{self.source_type}', value='{self.path_value}'"
        )
        self._source_was_zip = False

        if self.source_type == "local_path":
            resolved_path = Path(self.path_value).expanduser().resolve()
            if not resolved_path.exists():
                raise InvalidScannerDirectoryError(
                    f"Local path does not exist: {resolved_path}"
                )
            self._prepared_source_path = resolved_path
            self._source_is_file = resolved_path.is_file()
            logger.debug(
                f"Using resolved local path: {self._prepared_source_path} (is_file: {self._source_is_file})"
            )
        elif self.source_type in ["local_zip", "remote_zip"]:
            self._temp_dir_manager = tempfile.TemporaryDirectory(
                suffix="-scanner-install"
            )
            temp_dir = Path(self._temp_dir_manager.name)
            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir()
            self._source_was_zip = True
            if self.source_type == "local_zip":
                zip_path = Path(self.path_value).expanduser().resolve()
                if not zip_path.is_file():
                    raise InvalidScannerDirectoryError(
                        f"Local zip path is not a file: {zip_path}"
                    )
                _extract_zip(zip_path, extract_dir)
            else:  # remote_zip
                zip_file_path = temp_dir / f"{Path(self.path_value).stem}.zip"
                _download_remote_zip(self.path_value, zip_file_path)
                _extract_zip(zip_file_path, extract_dir)
            self._prepared_source_path = extract_dir
            self._source_is_file = False
            logger.debug(
                f"Source prepared in temp directory: {self._prepared_source_path} (from zip)"
            )
        else:
            raise ValueError(f"Unknown source type: {self.source_type}")

    def _fetch_metadata(self) -> None:
        """Fetches metadata based on assumptions about the prepared source path."""
        if not self._prepared_source_path:
            raise InstallationError(
                "Source path not prepared before fetching metadata."
            )

        source = self._prepared_source_path
        source_kind = (
            "zip archive content"
            if self._source_was_zip
            else "directory"
            if source.is_dir()
            else "file"
        )
        logger.info(
            f"Fetching metadata from prepared source: {source} (type: {source_kind})"
        )

        if self._source_is_file:
            # Assumption: A direct file path IS the executable
            if not os.access(source, os.X_OK):
                # Attempt to make it executable if it wasn't already
                try:
                    os.chmod(source, os.stat(source).st_mode | 0o111)
                    if not os.access(source, os.X_OK):  # Check again
                        raise InvalidScannerDirectoryError(
                            f"Provided file source could not be made executable: {source}"
                        )
                    logger.warning(f"Made provided file source executable: {source}")
                except OSError as e:
                    raise InvalidScannerDirectoryError(
                        f"Could not set execute permission on file source {source}: {e}"
                    )

            self._scanner_type = ScannerType.EXECUTABLE
            self._executable_path_in_source = source
            # Create the scanner handler
            self._scanner_handler = ScannerHandlerFactory.create_handler(
                self._scanner_type, self
            )
            # Use the handler to fetch metadata
            self._scanner_metadata = self._scanner_handler.fetch_metadata(source)

        elif source.is_dir():
            # Check for Python scanner first (pyproject.toml)
            toml_path = source / "pyproject.toml"
            if toml_path.exists() and toml_path.is_file():
                self._scanner_type = ScannerType.PYTHON
                # Create the scanner handler
                self._scanner_handler = ScannerHandlerFactory.create_handler(
                    self._scanner_type, self
                )
                # Use the handler to fetch metadata
                self._scanner_metadata = self._scanner_handler.fetch_metadata(source)
            else:
                # If not Python, check for a single executable at the root
                executable_path = self._find_executable_at_root(source)
                if executable_path:
                    self._scanner_type = ScannerType.EXECUTABLE
                    self._executable_path_in_source = executable_path
                    # Ensure the found executable (potentially from zip) has execute permissions
                    # before attempting to run it for metadata.
                    if not os.access(executable_path, os.X_OK):
                        try:
                            logger.debug(
                                f"Setting execute permission on found executable: {executable_path}"
                            )
                            os.chmod(
                                executable_path,
                                os.stat(executable_path).st_mode | 0o111,
                            )
                            # Verify it worked
                            if not os.access(executable_path, os.X_OK):
                                raise InvalidScannerDirectoryError(
                                    f"Could not make found executable runnable: {executable_path}"
                                )
                        except OSError as e:
                            raise InvalidScannerDirectoryError(
                                f"Failed to set execute permission on {executable_path}: {e}"
                            )
                    # Create the scanner handler
                    self._scanner_handler = ScannerHandlerFactory.create_handler(
                        self._scanner_type, self
                    )
                    # Use the handler to fetch metadata
                    self._scanner_metadata = self._scanner_handler.fetch_metadata(
                        executable_path
                    )
                else:
                    # Neither Python nor single executable found at root
                    origin_desc = f"The provided {source_kind} '{source.name if source_kind != 'zip archive content' else self.path_value}'"
                    raise InvalidScannerDirectoryError(
                        f"{origin_desc} is not a valid scanner: "
                        f"No 'pyproject.toml' found for a Python scanner, and no single executable file found at the root for an Executable scanner."
                    )
        else:
            # Should not happen if _prepare_source is correct
            raise InvalidScannerDirectoryError(
                f"Prepared source is neither a file nor a directory: {source}"
            )

        # Basic validation (remains the same)
        if not self._scanner_metadata or not isinstance(self._scanner_metadata, dict):
            raise InvalidScannerDirectoryError(
                "Failed to retrieve valid metadata structure."
            )
        if not self._scanner_metadata.get("name"):
            raise InvalidScannerDirectoryError(
                "Scanner metadata is missing the required 'name' field."
            )

        logger.info(
            f"Successfully fetched metadata for '{self._scanner_metadata.get('name')}' (type: {self._scanner_type.name})"
        )

    def _find_executable_at_root(self, directory: Path) -> Optional[Path]:
        """Finds a single executable file directly within a directory (non-recursive)."""
        executables = []
        logger.debug(f"Searching for single executable directly in: {directory}")
        try:
            for item in directory.iterdir():
                # Check if it's a file first. Then check permissions OR just look for files.
                # Let's rely on setting permissions later if needed, to handle cases where zip extraction didn't preserve them.
                if item.is_file():
                    # Basic check to exclude common non-scanner files
                    if not item.name.startswith(".") and item.name not in [
                        "__main__.py",
                        "activate",
                        "run",
                        "setup.py",
                        "pyproject.toml",  # Added this
                        "README",  # Added common text files
                        "README.md",
                        "LICENSE",
                        "requirements.txt",
                        "requirements-dev.txt",
                    ]:
                        # We can't reliably check os.access() here if permissions were lost in zip
                        logger.debug(
                            f"Found potential executable candidate (will check/set permissions later): {item.name}"
                        )
                        executables.append(item)
        except OSError as e:
            logger.warning(f"Could not list directory contents for {directory}: {e}")
            return None
        if len(executables) == 1:
            logger.debug(f"Found single executable candidate: {executables[0]}")
            return executables[0]
        elif len(executables) > 1:
            logger.warning(
                f"Multiple potential executables found directly in {directory}: {[e.name for e in executables]}. Ambiguous."
            )
        else:
            logger.debug(f"No executable file found directly in {directory}")
        return None

    # Methods _fetch_python_metadata_from_toml and _fetch_executable_metadata_from_cli
    # have been refactored into the PythonScannerHandler and ExecutableScannerHandler classes

    def _determine_final_name_and_paths(self) -> None:
        """Sets the final scanner name from metadata and derives install/venv paths."""
        raw_name = self._scanner_metadata.get("name")
        self._determined_scanner_name = raw_name.replace("_", "-") if raw_name else None
        if not self._determined_scanner_name:
            raise InstallationError(
                "Internal Error: Scanner name missing after metadata fetch."
            )
        self._install_path, self._venv_path = _get_scanner_paths(
            self._determined_scanner_name
        )
        logger.debug(
            f"Determined scanner name: '{self._determined_scanner_name}', Install: {self._install_path}, Venv: {self._venv_path}"
        )

    def _prepare_target(self) -> None:
        """Checks registry and filesystem for existing installs, cleans if reinstall=True."""
        if (
            not self._determined_scanner_name
            or not self._install_path
            or not self._venv_path
        ):
            raise InstallationError(
                "Internal Error: Cannot prepare target before determining name/paths."
            )
        logger.info(
            f"Preparing installation target for '{self._determined_scanner_name}'"
        )
        is_registered = scanner_registry.has_scanner(self._determined_scanner_name)
        files_exist = (
            self._install_path.exists()
            or self._install_path.is_symlink()
            or self._venv_path.exists()
        )
        if is_registered or files_exist:
            if not self.reinstall:
                reason = (
                    ("already registered" if is_registered else "")
                    + (" and " if is_registered and files_exist else "")
                    + ("installation files exist" if files_exist else "")
                )
                raise ScannerAlreadyInstalledError(
                    f"Scanner '{self._determined_scanner_name}' {reason}. Use --reinstall."
                )
            else:
                logger.info(
                    f"Reinstall requested. Removing existing installation for '{self._determined_scanner_name}'."
                )
                if is_registered:
                    try:
                        scanner_registry.remove_scanner(self._determined_scanner_name)
                    except Exception as e:
                        logger.error(
                            f"Failed removing '{self._determined_scanner_name}' from registry: {e}"
                        )  # Proceed
                if not _remove_existing_installation(self._determined_scanner_name):
                    raise InstallationError(
                        f"Failed removing existing files for '{self._determined_scanner_name}'. Cannot proceed."
                    )
        else:
            # Ensure parent directories exist before trying to place files/symlinks
            self._install_path.parent.mkdir(parents=True, exist_ok=True)
            if (
                self._venv_path
            ):  # venv_path might be None initially? Make sure parent exists if needed.
                self._venv_path.parent.mkdir(parents=True, exist_ok=True)

    def _place_scanner_files(self) -> None:
        """Copies or symlinks scanner files from prepared source to final install path."""
        if (
            not self._install_path
            or not self._prepared_source_path
            or not self._scanner_handler
        ):
            raise InstallationError(
                "Internal Error: Paths or scanner handler not set for placing files."
            )
        logger.info(
            f"Placing scanner files for '{self._determined_scanner_name}' into {self._install_path}"
        )
        # Allow dev mode for both Python (dir) and Executable (file) local_path sources
        can_develop = self.source_type == "local_path" and (
            (self._scanner_type == ScannerType.PYTHON and not self._source_is_file)
            or (self._scanner_type == ScannerType.EXECUTABLE and self._source_is_file)
        )
        use_develop = self.develop and can_develop
        if self.develop and not can_develop:
            logger.warning(
                f"Develop mode ignored: not applicable for source type '{self.source_type}'/{self._scanner_type.name}."
            )
        source_to_use = (
            Path(self.path_value).expanduser().resolve()
            if use_develop
            else self._prepared_source_path
        )
        install_verb = "symlinking" if use_develop else "copying"
        try:
            # Use the scanner handler to place scanner files
            self._scanner_handler.place_scanner_files(source_to_use, use_develop)
            logger.info(
                f"Scanner files {install_verb.replace('ing','ed')} successfully."
            )
        except FileExistsError as e:
            # This might happen if prepare_target didn't fully clean up, or race condition.
            logger.error(
                f"File/directory conflict during file placement: {e}. Path: {self._install_path}"
            )
            raise InstallationError(f"Target path conflict during file placement: {e}")
        except Exception as e:
            logger.error(f"Failed {install_verb} scanner files: {e}", exc_info=True)
            _remove_dir_or_link(self._install_path)  # Attempt cleanup
            raise InstallationError(
                f"Failed {install_verb} scanner files: {str(e)}"
            ) from e

    def _post_install_setup(self) -> None:
        """Handles post-installation tasks like venv creation for Python scanners."""
        if not self._scanner_handler:
            raise InstallationError(
                "Internal Error: Scanner handler not set for post-install setup."
            )

        if not self._determined_scanner_name:
            raise InstallationError(
                "Internal Error: Cannot run post-install without name."
            )

        try:
            # Use the scanner handler to perform post-installation setup
            self._scanner_handler.post_install_setup()
        except (DependencyInstallationError, InstallationError) as e:
            logger.error(
                f"Post-install setup failed for '{self._determined_scanner_name}'. Cleaning up."
            )
            _remove_existing_installation(self._determined_scanner_name)
            raise e
        except Exception as e:
            logger.error(
                f"Unexpected post-install setup error for '{self._determined_scanner_name}'. Cleaning up.",
                exc_info=True,
            )
            _remove_existing_installation(self._determined_scanner_name)
            raise InstallationError(
                f"Post-install setup failed unexpectedly: {str(e)}"
            ) from e

    # Method _setup_python_scanner_venv has been refactored into the PythonScannerHandler class

    def _register(self) -> None:
        """Updates the scanner registry with the final structured metadata."""
        if (
            not self._determined_scanner_name
            or not self._scanner_type
            or not self._scanner_metadata
            or not self._install_path
            or not self._scanner_handler
        ):
            raise InstallationError(
                "Internal Error: Cannot register scanner, essential data missing."
            )

        logger.info(
            f"Structuring and registering scanner '{self._determined_scanner_name}'"
        )

        # Extract core info needed for the top level of the registry entry
        scanner_version = self._scanner_metadata.get("version", "unknown")
        scanner_org = self._scanner_metadata.get("org", "unknown")
        scanner_description = self._scanner_metadata.get("description", "")
        extensions = self._scanner_metadata.get("extensions", [])

        # --- Handle Detectors ---
        logger.info(
            f"Collecting detector metadata for '{self._determined_scanner_name}'..."
        )

        # Use the scanner handler to collect detector metadata
        detector_data = self._scanner_handler.collect_detector_metadata()

        if detector_data is not None:
            logger.info(f"Successfully collected {len(detector_data)} detectors.")
            final_detectors_dict = detector_data
        else:
            logger.warning(
                f"Failed to collect detector metadata for '{self._determined_scanner_name}'. Registering with empty detectors."
            )
            final_detectors_dict = {}  # Fallback to empty if collection failed

        is_effective_develop = self._scanner_handler.is_effective_develop()

        # Construct the final dictionary VALUE to be stored under the scanner_name key
        registry_entry_value = {
            "path": str(self._install_path),
            "installed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "version": scanner_version,
            "type": str(self._scanner_type),
            "org": scanner_org,
            "description": scanner_description,
            "develop_mode": is_effective_develop,
            "extensions": extensions,
            "detectors": final_detectors_dict,
        }

        try:
            # Add/update the entry: scanner_name is the KEY, registry_entry_value is the VALUE
            scanner_registry.add_or_update_scanner(
                self._determined_scanner_name, registry_entry_value
            )
            logger.info(
                f"Scanner '{self._determined_scanner_name}' registered successfully with {len(final_detectors_dict)} detectors."
            )
        except Exception as e:
            logger.error(
                f"Failed to write structured data to scanner registry for '{self._determined_scanner_name}': {e}",
                exc_info=True,
            )
            # Cleanup on registration failure? Yes, likely installation is incomplete.
            _remove_existing_installation(self._determined_scanner_name)
            raise InstallationError(
                f"Failed to register scanner '{self._determined_scanner_name}': {str(e)}"
            )

    # Method _collect_python_detector_metadata has been refactored into the PythonScannerHandler class

    def _cleanup(self) -> None:
        """Removes the temporary directory if it was created."""
        if self._temp_dir_manager:
            try:
                logger.debug(f"Cleaning up temp dir: {self._temp_dir_manager.name}")
                # Use shutil.rmtree for robustness, TemporaryDirectory.cleanup can fail on Windows
                shutil.rmtree(self._temp_dir_manager.name, ignore_errors=True)
                # self._temp_dir_manager.cleanup() # Original method
                self._temp_dir_manager = None
            except Exception as e:
                # Log error but don't raise, cleanup failure is not critical path
                logger.error(
                    f"Failed cleanup temp dir {self._temp_dir_manager.name}: {e}",
                    exc_info=True,
                )


def _install_scanner(
    source_type: str, path_value: str, reinstall: bool = False, develop: bool = False
) -> str:
    """Installs a scanner using the ScannerInstaller class."""
    installer = ScannerInstaller(source_type, path_value, reinstall, develop)
    return installer.install()


def _uninstall_scanner(scanner_name: str, force: bool = False) -> str:
    """Uninstalls a scanner from the system."""
    logger.info(f"Attempting uninstall: '{scanner_name}' (force={force})")
    is_registered = scanner_registry.has_scanner(scanner_name)
    install_dir, venv_dir = _get_scanner_paths(scanner_name)
    # Check existence more robustly
    install_exists = install_dir.exists() or install_dir.is_symlink()
    venv_exists = venv_dir.exists()
    files_exist = install_exists or venv_exists

    if not is_registered and not files_exist:
        if not force:
            raise ValueError(
                f"Scanner '{scanner_name}' not found (not registered and no files exist)."
            )
        else:
            return f"Scanner '{scanner_name}' not found, nothing to uninstall."

    if not is_registered and files_exist and not force:
        existing_paths = []
        if install_exists:
            existing_paths.append(str(install_dir))
        if venv_exists:
            existing_paths.append(str(venv_dir))
        raise ValueError(
            f"Scanner '{scanner_name}' has files ({', '.join(existing_paths)}) but isn't registered. Use --force to remove files."
        )

    try:
        # Remove registry entry first
        if is_registered:
            try:
                logger.debug(f"Removing '{scanner_name}' from registry.")
                scanner_registry.remove_scanner(scanner_name)
            except Exception as e:
                # Log error but continue to file removal if force=True or if files exist
                logger.error(
                    f"Failed removing '{scanner_name}' from registry: {e}. Continuing file removal."
                )
        else:
            logger.debug(f"Scanner '{scanner_name}' not found in registry.")

        # Remove files if they exist
        if files_exist:
            logger.debug(f"Removing installation files for '{scanner_name}'...")
            if not _remove_existing_installation(scanner_name):
                # This helper already logs errors, raise an error here if it failed
                raise InstallationError(
                    f"Failed removing one or more installation files/directories for '{scanner_name}'."
                )
            else:
                logger.debug("Installation files removed.")
        else:
            logger.debug(f"No installation files found for '{scanner_name}'.")

        return f"Successfully uninstalled scanner '{scanner_name}'"

    except InstallationError as e:
        # Re-raise installation errors directly
        raise InstallationError(f"Uninstall failed for '{scanner_name}': {str(e)}")
    except Exception as e:
        # Catch unexpected errors during the process
        logger.error(
            f"Unexpected uninstall error for '{scanner_name}': {e}", exc_info=True
        )
        raise InstallationError(
            f"Unexpected uninstall error for '{scanner_name}': {str(e)}"
        )
