import logging
from enum import Enum, auto

from .exceptions import InvalidInstallationTypeError
from .auto_completion import _install_auto_completion, _uninstall_auto_completion
from .scanners import _uninstall_scanner, _install_scanner

# Set up logger
logger = logging.getLogger(__name__)


class InstallationType(Enum):
    """
    Supported installation types for the Inspector tool.

    Each enum value represents a different component that can be installed:
    - AUTOCOMPLETE: Command-line autocompletion for bash and zsh shells
    - SCANNER: External scanner modules that extend Inspector functionality
    """

    UNKNOWN = auto()
    AUTOCOMPLETE = auto()
    SCANNER = auto()

    @classmethod
    def from_str(cls, value: str) -> "InstallationType":
        """
        Convert a string to an InstallationType enum value (case-insensitive).

        Args:
            value: String representation of the installation type

        Returns:
            Matching InstallationType enum value, or None if no match found

        Example:
            >>> InstallationType.from_str("autocomplete")
            <InstallationType.AUTOCOMPLETE: 1>
        """
        try:
            return cls[value.upper()]
        except KeyError:
            return cls.UNKNOWN


def uninstall(what_to_uninstall: str, scanner_name: str = None):
    """
    Uninstall specified components for the Inspector tool.

    Args:
        what_to_uninstall: Component to uninstall ("autocomplete" or "scanner")
        scanner_name: For scanners, the name of the scanner to uninstall

    Raises:
        InvalidInstallationTypeError: If the uninstallation type is not supported
        ValueError: If required parameters are missing
        Various other exceptions for specific uninstallation failures
    """
    logger.info(f"Starting installation of {what_to_uninstall}")

    install_type = InstallationType.from_str(what_to_uninstall)
    if install_type == InstallationType.UNKNOWN:
        raise InvalidInstallationTypeError(
            f"Invalid installation request: {what_to_uninstall}"
        )

    if install_type == InstallationType.AUTOCOMPLETE:
        logger.info("Installing autocomplete")
        result = _uninstall_auto_completion()
        print(f"* {what_to_uninstall}: {result}")

    elif install_type == InstallationType.SCANNER:
        if not scanner_name:
            raise ValueError("Scanner name must be provided")

        logger.info(f"Uninstalling scanner: {scanner_name}")
        _uninstall_scanner(scanner_name)

    logger.info("Uninstall process completed")


def install(
    what_to_install: str,
    scanner_source_type: str = None,
    scanner_path: str = None,
    reinstall: bool = False,
    develop: bool = False,
):
    """
    Install specified components for the Inspector tool.

    Args:
        what_to_install: Component to install ("autocomplete" or "scanner")
        scanner_source_type: For scanners, the type of source ("local_path", "local_zip", "remote_zip")
        scanner_path: For scanners, the path or URL to the scanner source
        reinstall: Whether to force reinstallation if already installed
        develop: Whether to install in development mode

    Raises:
        InvalidInstallationTypeError: If the installation type is not supported
        ValueError: If required parameters are missing
        Various other exceptions for specific installation failures
    """
    logger.info(f"Starting installation of {what_to_install}")

    install_type = InstallationType.from_str(what_to_install)
    if install_type == InstallationType.UNKNOWN:
        raise InvalidInstallationTypeError(
            f"Invalid installation request: {what_to_install}"
        )

    if install_type == InstallationType.AUTOCOMPLETE:
        logger.info("Installing autocomplete")
        result = _install_auto_completion()
        print(f"* {what_to_install}: {result}")

    elif install_type == InstallationType.SCANNER:
        if not scanner_source_type or not scanner_path:
            raise ValueError("Scanner source type and path must be provided")

        logger.info(
            f"Installing scanner from {scanner_source_type}: {scanner_path} (reinstall={reinstall})"
        )
        _install_scanner(scanner_source_type, scanner_path, reinstall, develop)

    logger.info("Installation process completed")
