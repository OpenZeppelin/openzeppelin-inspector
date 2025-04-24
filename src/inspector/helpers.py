import json
import logging
import glob
import argparse

from glob import has_magic
from pathlib import Path

from halo import Halo

from . import __version__ as version
from .scanner_manager import ScannerManager
from .scanner_registry import get_scanner_version

logger = logging.getLogger(__name__)


def print_if_not_silent(what_to_print: str, silent: bool = False) -> None:
    if not silent:
        print(what_to_print)
    else:
        pass


def read_file_contents(filename: str) -> list[str]:
    with open(filename, "r", encoding="UTF-8") as f:
        return list(f)


def smart_resolve_path(
    raw_entry: str,
    project_root: Path,
    prefer_project_root: bool = False,
) -> Path | None:
    """
    Resolve a single path entry, checking in this order:
    1. If absolute and exists, return as-is.
    2. If relative and exists relative to preferred root (project or cwd), return that.
    3. Else, return None (invalid).
    """
    raw_path = Path(str(raw_entry).strip())

    # 1. Absolute and valid
    if raw_path.is_absolute() and raw_path.exists():
        return raw_path.resolve()

    # 2. Relative, prefer project root if requested
    rel_roots = (
        [project_root, Path.cwd()]
        if prefer_project_root
        else [Path.cwd(), project_root]
    )

    for base in rel_roots:
        candidate = (base / raw_path).resolve()
        if candidate.exists():
            return candidate

    return None


def normalize_and_expand_paths(
    raw_inputs: list[str],
    project_root: Path,
    label: str,
    prefer_project_root: bool,
) -> tuple[set[Path], set[Path]]:
    """
    Normalize paths from CLI or scope file input.
    """
    valid_paths = set()
    invalid_paths = set()

    for entry in raw_inputs:
        entry = str(entry).strip()
        if not entry or entry.startswith("#"):
            continue
        if "," in entry:
            raise ValueError(
                "Path lists should not contain commas. Use newlines instead."
            )

        # Expand globs first (relative to root or cwd depending on source)
        path_obj = Path(entry.strip())
        rel_roots = (
            [project_root, Path.cwd()]
            if prefer_project_root
            else [Path.cwd(), project_root]
        )
        matched = []

        if has_magic(entry):
            for root in rel_roots:
                globbed = glob.glob(str(root / path_obj), recursive=True)
                matched.extend(globbed)
            if matched:
                valid_paths.update(Path(p).resolve() for p in matched)
            else:
                invalid_paths.add(path_obj)
        else:
            resolved = smart_resolve_path(entry, project_root, prefer_project_root)
            if resolved:
                valid_paths.add(resolved)
            else:
                invalid_paths.add(Path(entry))

    if invalid_paths:
        invalid_str = "\n".join(str(p) for p in sorted(invalid_paths))
        logger.warning(f"The following {label} paths are invalid:\n{invalid_str}")

    return valid_paths, invalid_paths


def get_all_files_in_directory(directory: Path) -> set[Path]:
    """
    Recursively collects all files in the given directory.

    Args:
        directory: Path to the directory to search.

    Returns:
        A set of Path objects representing all files in the directory and its subdirectories.
    """
    return {file for file in directory.rglob("*") if file.is_file()}


def code_location_expander(values: set[Path]) -> set[Path]:
    """
    Expands directories to individual files.

    Args:
        values: Set of Path objects to process.

    Returns:
        A set of Path objects representing all files found.
    """

    def expand_path(path: Path) -> set[Path]:
        abs_path = path.resolve()
        if abs_path.is_dir():
            return set(get_all_files_in_directory(abs_path))
        elif abs_path.is_file():
            return {abs_path}
        return set()

    return {file for path in values if path for file in expand_path(path)}


def get_version_info(scan_results, format: str = "md") -> str:
    """
    Get a string conveying the inspector version as well as the versions of all scanners in use.
    """
    return (
        get_version_info_json_string(scan_results)
        if format == "json"
        else get_version_info_string(scan_results)
    )


def get_version_info_string(scan_results) -> str:
    """
    Get a human-readable string conveying the Inspector version
    and the versions of all scanners in use.
    """
    lines = [
        "------- Version Info -------",
        f"OpenZeppelin Inspector version {version}",
        "Scanners used:",
    ]

    for scanner in scan_results:
        scanner_version = get_scanner_version(scanner)
        lines.append(f"  - {scanner} version {scanner_version}")

    return "\n".join(lines)


def get_version_info_json_string(scan_results) -> str:
    """
    Returns a json string containing scanners versions
    """

    version_info = {"contract-inspector-version": version}

    for scanner in scan_results:
        version_info[scanner] = get_scanner_version(scanner)
    return json.dumps(version_info)


def is_valid_scanner_directory(directory_path, required_files=None):
    """
    Validates if a directory is a valid scanner directory.

    A directory is considered a valid scanner directory if it either:
    1. Contains a single executable file, OR
    2. Contains at least one of the files specified in required_files list

    Args:
        directory_path (str or Path): Path to the directory to validate.
        required_files (list): List of filenames to check for (default: ["pyproject.toml"])

    Returns:
        bool: True if the directory is a valid scanner directory, False otherwise
    """

    # Convert to Path object if it's not already
    directory = Path(directory_path)

    if not directory.is_dir():
        return False

    # Default to looking for pyproject.toml if no files specified
    if required_files is None:
        required_files = ["pyproject.toml"]

    # Check if there's a single executable file
    for file_path in directory.iterdir():
        if (
            file_path.is_file() and file_path.stat().st_mode & 0o111
        ):  # Check executable bit
            return True

    # Check if any of the required files exist
    for req_file in required_files:
        if (directory / req_file).is_file():
            return True

    return False


class SpinnerWrapper:
    """
    A wrapper for a Halo spinner that suppresses all output when disabled.

    Halo will emit control sequences and other artifacts to stdout even if you pass
    `enabled=False`, which can pollute CLI output in non-interactive or scripted runs.
    By centralizing spinner creation in one place and only instantiating Halo when
    truly enabled, we guarantee no stray spinner output when we have a single shared
    spinner instance across the entire CLI main flow.
    """

    def __init__(self, args=None, **kwargs):
        """
        Initialize the SpinnerWrapper.

        Parameters
        ----------
        args : argparse.Namespace, optional
            The parsed CLI arguments. We inspect flags like
            `minimal_output`, `debug`, `ci`, and also detect the
            `autocomplete` subcommand (via `args.command` or
            `args.autocomplete_action`) to decide spinner behavior.
        **kwargs
            Passed directly to the Halo constructor when enabled.

        Notes
        -----
        - We only call `Halo(enabled=True, **kwargs)` when we truly want a spinner.
          Otherwise `self.spinner` stays `None`, so Halo never even sees the call.
        - This ensures zero spinner artifacts leak into stdout when disabled.
        """
        self.args = args or argparse.Namespace()
        # detect if we're running "inspector autocomplete …"
        is_autocomplete = (
            getattr(self.args, "command", None) == "autocomplete"
            or getattr(self.args, "autocomplete_action", None) is not None
        )

        # disable spinner on minimal_output, debug, ci, or any autocomplete command
        self.enabled = (
            not any(
                getattr(self.args, flag, False)
                for flag in ("minimal_output", "debug", "ci")
            )
            and not is_autocomplete
        )

        # only create the Halo spinner if enabled, avoiding any stray stdout
        self.spinner = Halo(enabled=self.enabled, **kwargs) if self.enabled else None

    def __getattr__(self, name):
        """
        Proxy method calls to the underlying Halo instance when enabled.

        Parameters
        ----------
        name : str
            The name of the Halo method being called (e.g., `start`, `succeed`, `fail`).

        Returns
        -------
        callable
            - If the spinner is enabled, returns the corresponding method on `self.spinner`.
            - Otherwise returns a no-op that returns `self`, letting you chain calls safely.
        """
        if self.spinner:
            return getattr(self.spinner, name)

        def no_op(*args, **kwargs):
            # Spinner is disabled: swallow calls, return self for chaining
            return self

        return no_op
