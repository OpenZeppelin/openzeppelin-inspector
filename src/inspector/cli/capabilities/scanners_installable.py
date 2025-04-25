from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class InstallableScanner(ABC):
    """
    Abstract base class for scanner type-specific handlers.
    Subclasses should implement methods for handling scanner type-specific operations.
    """

    def __init__(self, installer):
        """
        Initialize the handler with a reference to the ScannerInstaller instance.

        Args:
            installer: The ScannerInstaller instance that is using this handler.
        """
        self.installer = installer

    @abstractmethod
    def fetch_metadata(self, source: Path) -> Dict[str, Any]:
        """
        Fetch metadata from the scanner source.

        Args:
            source: The path to the scanner source.

        Returns:
            A dictionary containing the scanner metadata.

        Raises:
            InvalidScannerDirectoryError: If the scanner source is invalid or metadata cannot be fetched.
        """
        pass

    @abstractmethod
    def place_scanner_files(self, source_to_use: Path, use_develop: bool) -> None:
        """
        Place scanner files from the source to the installation path.

        Args:
            source_to_use: The path to the scanner source.
            use_develop: Whether to use development mode (symlink instead of copy).

        Raises:
            InstallationError: If the scanner files cannot be placed.
        """
        pass

    @abstractmethod
    def post_install_setup(self) -> None:
        """
        Perform post-installation setup for the scanner.

        Raises:
            InstallationError: If the post-installation setup fails.
        """
        pass

    @abstractmethod
    def collect_detector_metadata(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Collect detector metadata from the scanner.

        Returns:
            A dictionary containing detector metadata, or None if collection fails.
        """
        pass

    @abstractmethod
    def is_effective_develop(self) -> bool:
        """
        Determine if the scanner is in effective development mode.

        Returns:
            True if the scanner is in effective development mode, False otherwise.
        """
        pass
