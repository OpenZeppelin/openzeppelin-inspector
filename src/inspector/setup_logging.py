import logging
import sys

from .constants import LOG_LEVEL_DEFAULT, LOG_LEVEL_DEFAULT_DEBUG_MODE
from .cli.utils import parse_cli_args


class SmartWidthFormatter(logging.Formatter):
    """
    Custom logging formatter that ensures consistent width for logger names.

    This formatter automatically calculates the maximum width needed for all existing
    logger names to ensure aligned log output. If longer logger names are encountered
    during runtime, the width will expand to accommodate them, but will never shrink.
    This improves readability when multiple loggers with different name lengths are
    used in the application.

    Attributes:
        width (int): The current maximum width for logger names.
    """

    # Class variable to track the maximum width across all instances
    _max_width = 0

    def __init__(self, fmt=None, datefmt=None):
        """
        Initialize the formatter with calculated smart width for logger names.

        Args:
            fmt (str, optional): Custom format string. If None, a default format with
                smart width for logger names will be created.
            datefmt (str, optional): Custom date format string.
        """
        # Get all existing loggers and find the longest name
        root = logging.root
        existing_loggers = [name for name in root.manager.loggerDict]
        existing_loggers.append("root")  # Don't forget the root logger
        current_max_width = max(len(name) for name in existing_loggers)

        # Update class-level max width if current max is larger
        if current_max_width > SmartWidthFormatter._max_width:
            SmartWidthFormatter._max_width = current_max_width

        self.width = SmartWidthFormatter._max_width

        super().__init__(fmt, datefmt)

    def format(self, record):
        """
        Format the specified record as text.

        This overridden method checks if the current logger name is longer than
        the current width and updates the format string if necessary.

        Args:
            record: The log record to format.

        Returns:
            str: The formatted log record.
        """
        # Check if current logger name is longer than the current width
        if len(record.name) > self.width:
            # Update the class-level max width
            SmartWidthFormatter._max_width = len(record.name)
            self.width = SmartWidthFormatter._max_width

            # Update the format string with the new width
            self._style._fmt = (
                f"%(asctime)s - %(levelname)-8s - %(name)-{self.width}s - %(message)s"
            )

        return super().format(record)


def initialize_logging() -> tuple[bool, str]:
    """
    Initialize logging configuration based on early command line argument processing.

    This function serves as the main entry point for setting up logging in the application
    before the main argument parser runs. This enables capturing log output during the
    earliest phases of application startup, including module imports and initialization.

    Returns:
        tuple[bool, str]: A tuple containing:
            - debug_requested (bool): True if debug mode was requested via command line
            - log_level_requested (str): The effective log level being used

    Note:
        If --debug is specified without a log level, LOG_LEVEL_DEFAULT_DEBUG_MODE is used.
        Otherwise, LOG_LEVEL_DEFAULT is used when no log level is specified.

        This early logging setup complements rather than replaces full argument parsing.
        The application should still use argparse for complete command-line argument
        processing after calling this function.
    """
    debug_requested, log_level_requested = configure_early_logging()

    if debug_requested and not log_level_requested:
        log_level_requested = LOG_LEVEL_DEFAULT_DEBUG_MODE
    elif not log_level_requested:
        log_level_requested = LOG_LEVEL_DEFAULT

    setup_root_logger(log_level_requested, debug_requested)
    return debug_requested, log_level_requested


def configure_early_logging() -> tuple[bool, str | None]:
    """
    Configure logging before argparse initialization by examining raw command line arguments.

    This function enables logging configuration to be set up very early in the application
    startup process, before the main argument parser is initialized. This is crucial for
    capturing debug information during module loading and initialization phases, which
    would be missed if logging were configured only after argparse completes.

    The function directly examines sys.argv for logging-related flags (--debug and
    --log-level) without interfering with subsequent argparse processing.

    Returns:
        tuple[bool, str | None]: A tuple containing:
            - debug_enabled (bool): True if --debug flag is present
            - level (str | None): The specified log level if --log-level is provided,
              None otherwise

    Examples:
        --debug                     -> (True, None)
        --debug --log-level debug   -> (True, "debug")
        --debug --log-level info    -> (True, "info")
        --log-level debug           -> (False, "debug")
        --option                    -> (False, None)

    Raises:
        SystemExit: If invalid arguments are provided:
            - --debug with unexpected value
            - --log-level without value
            - --log-level with invalid level

    Note:
        This function is designed to work alongside argparse, not replace it. After this
        function configures early logging, the application should still use argparse for
        complete command-line argument processing.
    """
    VALID_LOG_LEVELS = {"debug", "info", "warn", "error", "critical"}

    # Use the common parsing utility
    arg_map = parse_cli_args()

    # Check for debug flag and validate it has no value
    debug_enabled = "debug" in arg_map
    if debug_enabled and arg_map["debug"]:
        raise SystemExit("Error: --debug flag doesn't accept values")

    # Check for log level and validate its value
    log_level = None
    if "log-level" in arg_map:
        if not arg_map["log-level"]:
            raise SystemExit("Error: --log-level requires a value")

        log_level = arg_map["log-level"][0].lower()

        if log_level not in VALID_LOG_LEVELS:
            raise SystemExit(
                f"Error: Invalid log level '{log_level}'. "
                f"Must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}"
            )

    return debug_enabled, log_level


def setup_root_logger(
    level: str | None = None,
    create_debug_file: bool = False,
    silence_loggers: list[str] | None = None,
) -> None:
    """
    Configure the root logger with appropriate handlers and formatting.

    This function sets up the root logger with console output and optionally a debug
    file. It also allows silencing specific loggers by setting them to CRITICAL level.

    Args:
        level (str | None, optional): The logging level to set. If None, defaults to
            LOG_LEVEL_DEFAULT from constants. Valid values are "DEBUG", "INFO", "WARN",
            "ERROR", or "CRITICAL" (case-insensitive).
        create_debug_file (bool, optional): If True, creates a debug log file named
            "inspector_output_debug.log" that captures all log messages. Defaults to False.
        silence_loggers (list[str] | None, optional): List of logger names to silence
            by setting their level to CRITICAL. Defaults to None.

    Note:
        This function clears any existing handlers on the root logger before
        configuring new ones.
    """
    # Clear any existing handlers first
    logging.root.handlers = []

    # Set up console handler first - this should always exist
    console_handler = logging.StreamHandler()
    formatter = SmartWidthFormatter()
    console_handler.setFormatter(formatter)
    logging.root.addHandler(console_handler)

    # Set the log level (either from debug flag or default)
    log_level = str(level or LOG_LEVEL_DEFAULT).upper()
    logging.root.setLevel(logging.getLevelName(log_level))

    if create_debug_file:
        file_handler = logging.FileHandler("inspector_output_debug.log")
        file_handler.setFormatter(formatter)
        logging.root.addHandler(file_handler)

        header = "#" * 30
        logging.info("%s BEGIN INSPECTOR RUN %s", header, header)

    if silence_loggers:
        for logger_name in silence_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.CRITICAL)
