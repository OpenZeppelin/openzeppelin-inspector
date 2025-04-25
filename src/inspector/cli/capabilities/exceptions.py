class InstallerError(Exception):
    """Base exception for all installer-related errors."""

    pass


class InvalidInstallationTypeError(InstallerError):
    """Raised when an invalid installation type is specified."""

    pass


class ScannerAlreadyInstalledError(InstallerError):
    """Raised when attempting to install a scanner that is already installed."""

    pass


class InvalidScannerDirectoryError(InstallerError):
    """Raised when a directory does not contain a valid scanner."""

    pass


class DownloadError(InstallerError):
    """Raised when there's an error downloading a remote scanner."""

    pass


class ExtractionError(InstallerError):
    """Raised when there's an error extracting a zip file."""

    pass


class InstallationError(InstallerError):
    """Raised when there's a general error during installation."""

    pass


class DependencyInstallationError(InstallerError):
    """Raised when there's an error installing dependencies."""

    pass


class ShellConfigurationError(InstallerError):
    """Raised when there's an error configuring shell autocompletion."""

    pass


class AutoCompletionNotFoundError(InstallerError):
    """Raised when no autocompletion configuration is found."""

    pass
