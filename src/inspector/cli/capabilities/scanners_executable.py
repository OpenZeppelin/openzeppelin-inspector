import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from logging import Logger

from .exceptions import (
    InvalidScannerDirectoryError,
    InstallationError,
)
from .helpers import _remove_dir_or_link
from .scanners_installable import InstallableScanner

METADATA_FETCH_TIMEOUT = 15  # seconds for executable metadata

logger: Logger = logging.getLogger(__name__)


class ExecutableInstallableScanner(InstallableScanner):
    """Handler for executable scanners."""

    def is_effective_develop(self) -> bool:
        """
        Determine if the executable scanner is in effective development mode.

        Returns:
            True if the scanner is in effective development mode, False otherwise.
        """
        return (
            self.installer.develop
            and self.installer.source_type == "local_path"
            and self.installer._source_is_file
        )

    def fetch_metadata(self, source: Path) -> Dict[str, Any]:
        """Fetch metadata from an executable scanner source."""
        logger.debug(f"Querying executable scanner metadata: {source} metadata")
        if not source.is_file():
            raise InvalidScannerDirectoryError(
                f"Executable path is not a file: {source}"
            )
        # Permission check is now done *before* calling this method in _fetch_metadata
        try:
            process = subprocess.run(
                [str(source), "metadata"],
                capture_output=True,
                text=True,
                check=True,
                timeout=METADATA_FETCH_TIMEOUT,
                encoding="utf-8",
                errors="replace",
            )
            scanner_metadata = json.loads(process.stdout)

            if "extensions" not in scanner_metadata:
                scanner_metadata["extensions"] = []
            if "detectors" not in scanner_metadata:
                scanner_metadata["detectors"] = []

            return scanner_metadata

        except FileNotFoundError:
            # Should ideally not happen if called correctly, but good to keep
            raise InvalidScannerDirectoryError(
                f"Scanner executable not found at expected path: {source}"
            )
        except PermissionError as e:  # Catch explicit PermissionError
            logger.error(f"Permission denied running metadata command: {source}")
            raise InvalidScannerDirectoryError(
                f"Permission denied executing scanner for metadata: {source}"
            ) from e
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else "(no stderr)"
            stdout = e.stdout.strip() if e.stdout else "(no stdout)"
            # Check for permission error messages in output as a fallback
            if (
                "permission denied" in stderr.lower()
                or "permission denied" in stdout.lower()
            ):
                logger.error(
                    f"Executable metadata command failed likely due to permissions (ret={e.returncode}): {source}.\nstderr: {stderr}\nstdout: {stdout}"
                )
                raise InvalidScannerDirectoryError(
                    f"Failed getting metadata from executable: Permission denied running {source}."
                )
            else:
                logger.error(
                    f"Executable metadata command failed (ret={e.returncode}): {source}.\nstderr: {stderr}\nstdout: {stdout}"
                )
                raise InvalidScannerDirectoryError(
                    "Failed to get metadata from executable: Command failed."
                )
        except subprocess.TimeoutExpired:
            raise InstallationError(
                "Timeout fetching metadata from executable scanner."
            )
        except json.JSONDecodeError as e:
            raise InvalidScannerDirectoryError(
                f"Failed to parse metadata JSON from executable: {e}"
            )
        except Exception as e:
            # Catch other potential OS errors related to execution
            logger.error(
                f"Unexpected error running metadata command for {source}: {e}",
                exc_info=True,
            )
            raise InstallationError(f"Failed to get metadata from executable: {str(e)}")

    def place_scanner_files(self, source_to_use: Path, use_develop: bool) -> None:
        """Place executable scanner files from source to installation path."""
        if use_develop:
            # New logic for executable scanner (file)
            self.installer._install_path.mkdir(parents=True, exist_ok=True)
            symlink_path = self.installer._install_path / "scanner"
            if symlink_path.exists() or symlink_path.is_symlink():
                _remove_dir_or_link(symlink_path)
            os.symlink(source_to_use, symlink_path)
        else:
            if (
                not self.installer._executable_path_in_source
                or not self.installer._executable_path_in_source.is_file()
            ):
                raise InstallationError(
                    "Internal Error: Executable source path invalid or not a file."
                )
            # The install path is the *directory* where the executable will live
            self.installer._install_path.mkdir(parents=True, exist_ok=True)
            # The destination is the executable file *inside* the install path directory
            destination = self.installer._install_path / "scanner"
            logger.debug(
                f"Copying executable from {self.installer._executable_path_in_source} to {destination}"
            )
            shutil.copy2(self.installer._executable_path_in_source, destination)
            logger.debug(
                f"Setting execute permission on final executable: {destination}"
            )
            try:
                os.chmod(destination, os.stat(destination).st_mode | 0o111)
            except OSError as e:
                _remove_dir_or_link(self.installer._install_path)  # Cleanup attempt
                raise InstallationError(
                    f"Failed to set execute permission on final executable {destination}: {e}"
                ) from e

    def post_install_setup(self) -> None:
        """No post-installation setup needed for executable scanners."""
        logger.debug(
            f"No post-install setup needed for executable scanner '{self.installer._determined_scanner_name}'."
        )

    def collect_detector_metadata(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Collect detector metadata from an executable scanner."""
        # For EXECUTABLE scanners, metadata comes from metadata JSON
        raw_detectors_data = self.installer._scanner_metadata.get(
            "detectors"
        )  # Should be a list
        final_detectors_dict = {}

        if isinstance(raw_detectors_data, list):
            logger.debug(
                "Converting executable detector list to dictionary format for registry."
            )
            skipped_count = 0
            for detector_info in raw_detectors_data:
                detector_id = None
                if isinstance(detector_info, dict):
                    # Prefer 'id', fallback to 'name'
                    detector_id = detector_info.get("id") or detector_info.get("name")

                if detector_id:
                    # Use the id/name as the key, store the whole dict as the value
                    detector_value = detector_info.copy()
                    final_detectors_dict[
                        str(detector_id)
                    ] = detector_value  # Ensure key is string
                else:
                    skipped_count += 1
                    logger.warning(
                        f"Skipping invalid detector entry during list conversion (missing 'id' or 'name'): {detector_info}"
                    )
            if skipped_count > 0:
                logger.warning(
                    f"Skipped {skipped_count} invalid entries during executable detector list conversion."
                )
        elif raw_detectors_data is not None:  # Log if it exists but isn't a list
            logger.warning(
                f"Executable detectors data is not a list (type: {type(raw_detectors_data)}). Registering with empty detectors."
            )
        else:  # Log if 'detectors' key was missing entirely
            logger.debug(
                "No 'detectors' key found in executable metadata. Registering with empty detectors."
            )

        return final_detectors_dict
