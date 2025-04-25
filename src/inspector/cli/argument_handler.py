import logging
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from pathlib import Path

from argcomplete import autocomplete

from .parsers import Parsers, Subparsers
from ..helpers import (
    normalize_and_expand_paths,
    read_file_contents,
    code_location_expander,
)
from .. import scanner_registry

logger = logging.getLogger(__name__)

DESCRIPTION = """
OpenZeppelin Inspector coordinates multiple code scanners to analyze source code
for a wide range of potential issues, presenting results in a unified format.
"""

EPILOG = """
For help with specific subcommands, use:
    python3 ./inspector_cli.py {scan, test, version, scanner, autocomplete} -h
"""


def parse_arguments() -> Namespace:
    """Parse command-line arguments."""
    root_parser = ArgumentParser(
        description=DESCRIPTION,
        usage="python3 ./inspector_cli.py {scan, test, version, scanner, autocomplete}",
        formatter_class=RawTextHelpFormatter,
        epilog=EPILOG,
    )
    parsers = Parsers()
    Subparsers(root_parser, parsers)
    autocomplete(root_parser, always_complete_options=False)
    return root_parser.parse_args()


def _resolve_code_paths(args: Namespace) -> None:
    """Resolve the set of code locations to be scanned."""
    args.scannable_code = set()
    root_path = Path(args.project_root).resolve()

    # Ensure args.include / exclude are sets of strings
    args.include = set(args.include) if args.include else set()
    args.exclude = set(args.exclude) if args.exclude else set()

    # 1. Scope file paths (relative to project root)
    if args.scope_file:
        try:
            raw_scope = read_file_contents(args.scope_file)
            scope_paths, _ = normalize_and_expand_paths(
                raw_scope,
                project_root=root_path,
                label="scope",
                prefer_project_root=True,
            )

            if not scope_paths:
                logger.critical(
                    "Provided scope file does not contain any valid files or directories."
                )
                raise SystemExit(1)

            args.scannable_code.update(code_location_expander(scope_paths))

        except Exception as e:
            logger.critical(
                f"Unable to parse scope file into a valid scope due to error: {e}"
            )
            raise SystemExit(1)

    # 2. If no scope file, fall back to --include or root path
    if not args.scope_file:
        if args.include:
            include_paths, _ = normalize_and_expand_paths(
                list(args.include),
                project_root=root_path,
                label="include",
                prefer_project_root=False,
            )
            args.scannable_code.update(code_location_expander(include_paths))
        else:
            args.scannable_code.update(code_location_expander({root_path}))

    # 3. Apply extra includes even when scope file is present
    if args.include and args.scope_file:
        include_paths, _ = normalize_and_expand_paths(
            list(args.include),
            project_root=root_path,
            label="include",
            prefer_project_root=False,
        )
        args.scannable_code.update(code_location_expander(include_paths))

    # 4. Apply excludes (CLI-only, relative to CWD)
    if args.exclude:
        exclude_paths, _ = normalize_and_expand_paths(
            list(args.exclude),
            project_root=root_path,
            label="exclude",
            prefer_project_root=False,
        )
        args.scannable_code.difference_update(code_location_expander(exclude_paths))


def _filter_detectors(args: Namespace) -> list[str]:
    """Filter detectors by names and tags."""
    available = scanner_registry.get_detectors_by_criteria(
        scanners=args.scanners,
        severities=args.severities,
        tags=args.tags,
    )

    requested = getattr(args, "detector_names", None)
    selected = (
        [d["name"] for d in available]
        if not requested
        else [name for name in requested if any(d["name"] == name for d in available)]
    )

    filtered = []
    for name in selected:
        metadata = scanner_registry.get_detector_info(name)
        detector_tags = metadata.get("report", {}).get("tags", [])
        if args.tags and not set(args.tags).intersection(detector_tags):
            continue
        filtered.append(name)

    # Filter out excluded detectors
    excluded = getattr(args, "excluded_detector_names", None)
    if excluded:
        logger.info(f"Excluding detectors: {excluded}")
        filtered = [name for name in filtered if name not in excluded]
    logger.info(f"Filtered detectors: {filtered}")
    if not filtered:
        if excluded and requested and set(requested).issubset(set(excluded)):
            raise SystemExit(
                "No detectors available: all requested detectors have been excluded"
            )
        else:
            raise SystemExit(
                "No detectors available with the current configuration. Please review the arguments."
            )

    return filtered


def interpret_arguments(args: Namespace) -> None:
    """Interpret and validate parsed arguments."""
    if args.mode in {"scan", "test"}:
        if not scanner_registry.get_installed_scanner_names():
            raise SystemExit(
                f"No scanners installed. Please install one before running '{args.mode}'."
            )

    if args.mode == "scan":
        _resolve_code_paths(args)
        filtered = _filter_detectors(args)
        args.detectors_to_run = filtered
