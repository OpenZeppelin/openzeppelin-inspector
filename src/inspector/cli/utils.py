import logging
import shlex
import sys


def parse_cli_args(command_line: str | None = None) -> dict[str, list[str]]:
    """
    Parse command line arguments into a structured dictionary.

    This function converts command line arguments in the format ```--arg value1 value2```
    into a dictionary mapping argument names to their values. It handles both regular
    command-line parsing (using sys.argv) and tab completion contexts (using COMP_LINE).

    Args:
        command_line: Command line string to parse.
            - If None, uses sys.argv (normal execution context)
            - If provided, parses this string instead (typically for tab completion)

    Returns:
        Dictionary mapping argument names to lists of values.
        Example: {"debug": [], "log-level": ["info"], "include": ["dir1", "dir2"]}

    Note:
        - Arguments without values will have an empty list as their value
        - If parsing fails due to malformed input (e.g., unbalanced quotes),
          returns an empty dictionary
        - Does not handle single-dash arguments like ```-h```

    Examples:
        >>> parse_cli_args('program --debug --log-level info --include dir1 dir2')
        {'debug': [], 'log-level': ['info'], 'include': ['dir1', 'dir2']}

        >>> parse_cli_args()  # Parses sys.argv in actual execution
        {'output-format': ['json'], 'minimal-output': []}
    """
    logger = logging.getLogger(__name__)
    is_completion_context = command_line is not None

    # Determine what we're parsing
    try:
        if is_completion_context:
            # Tab completion context - parse the provided command line
            tokens = shlex.split(command_line)
        else:
            # Normal execution context - parse sys.argv
            tokens = sys.argv[1:]  # Skip program name
    except ValueError as e:
        # Handle parsing errors (typically unbalanced quotes)
        if not is_completion_context:
            # Only log during normal execution, not during tab completion
            logger.warning("Failed to parse command line arguments: %s", str(e))
        return {}

    # Build argument dictionary
    arg_map: dict[str, list[str]] = {}
    current_key = None

    for token in tokens:
        if token.startswith("--"):
            # This token is an argument name
            current_key = token.lstrip("-")
            # Initialize with empty list if not already present
            arg_map.setdefault(current_key, [])
        elif current_key is not None:
            # This token is a value for the current argument
            arg_map[current_key].append(token)

    return arg_map
