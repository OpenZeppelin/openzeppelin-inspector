"""
Inspector CLI Argument Parser Module

This module defines the CLI interface for the Inspector tool.
Arguments are organized by concern (scope, detectors, scanners, etc.),
with validation and autocompletion support.
"""

import os
import re
from pathlib import Path
from functools import wraps
from argparse import (
    ArgumentParser,
    Action,
    RawTextHelpFormatter,
)
from datetime import datetime

from .utils import parse_cli_args
from ..setup_logging import configure_early_logging
from ..models._complete.severities import DetectorSeverities
from .. import scanner_registry
from ..constants import LOG_LEVEL_DEFAULT, LOG_LEVEL_DEFAULT_DEBUG_MODE

INSTALLED_SCANNERS = scanner_registry.get_installed_scanner_names()
NO_SCANNERS_INSTALLED = ["... NO SCANNERS INSTALLED"]
ALL_AVAILABLE_DETECTOR_NAMES = scanner_registry.get_all_detector_names()
ALL_AVAILABLE_DETECTOR_TAGS = [
    tag["name"] for tag in scanner_registry.get_tags_by_criteria()
]


def detector_choices(command_line: str | None = None) -> list[str]:
    """
    Return a list of detector names filtered by any --scanner / --severity / --tag
    flags found in `command_line` (or in sys.argv if command_line is None).

    This is safe to call at parser-build time to produce a static choices list.
    """
    args_map = parse_cli_args(command_line)
    scanners = args_map.get("scanner")
    severities = args_map.get("severity")
    tags = args_map.get("tag")

    detectors = scanner_registry.get_detectors_by_criteria(
        scanners=scanners,
        severities=severities,
        tags=tags,
    )
    return [d["name"] for d in detectors]


def get_cli_args_for_completion():
    """
    Parse COMP_LINE into a dict of arg names to values.
    To work around nargs="*" and argcomplete difficulties.
    """
    return parse_cli_args(os.environ.get("COMP_LINE", ""))


def get_arg_value(parsed_args, name, cli_args):
    return (
        getattr(parsed_args, name, None)
        or cli_args.get(name)
        or cli_args.get(f"{name}s")
        or (cli_args.get(f"{name[:-1]}ies") if name.endswith("y") else None)
    )


def with_merged_args(*arg_names):
    """Decorator that injects merged arg context into completer functions."""

    def decorator(func):
        @wraps(func)
        def wrapper(prefix, parsed_args, **kwargs):
            cli_args = get_cli_args_for_completion()
            merged_args = {
                name: get_arg_value(parsed_args, name, cli_args) for name in arg_names
            }
            return func(prefix, merged_args, **kwargs)

        return wrapper

    return decorator


@with_merged_args("tag", "severity", "detector")
def scanner_completer(prefix, merged_args, **kwargs):
    tags = merged_args.get("tag")
    severities = merged_args.get("severity")
    detectors = merged_args.get("detector")

    matching = scanner_registry.get_scanners_by_criteria(
        tags=tags,
        severities=severities,
        detectors=detectors,
    )

    return {
        scanner["name"]: scanner.get("description", "")
        for scanner in matching
        if scanner["name"].startswith(prefix)
    }


@with_merged_args("scanner", "tag")
def severity_completer(prefix, merged_args, **kwargs):
    scanners = merged_args.get("scanner")
    tags = merged_args.get("tag")
    severity_results = scanner_registry.get_severities_by_criteria(
        scanners=scanners, tags=tags
    )
    return {
        s.value: f"Used by {len(severity_results.get(s.value, []))} detectors"
        for s in DetectorSeverities
        if s.value.startswith(prefix)
    }


@with_merged_args("scanner", "severity")
def tag_completer(prefix, merged_args, **kwargs):
    scanners = merged_args.get("scanner")
    severities = merged_args.get("severity")
    tag_results = scanner_registry.get_tags_by_criteria(
        scanners=scanners, severities=severities
    )
    return {
        tag[
            "name"
        ]: f"Used by {tag['detector_count']} detectors in {tag['scanner_count']} scanners"
        for tag in tag_results
        if tag["name"].startswith(prefix)
    }


@with_merged_args("scanner", "severity", "tag")
def detector_completer(prefix, merged_args, **kwargs):
    res = scanner_registry.get_detectors_by_criteria(
        scanners=merged_args.get("scanner"),
        severities=merged_args.get("severity"),
        tags=merged_args.get("tag"),
    )
    return {d["name"]: d["description"] for d in res if d["name"].startswith(prefix)}


class FileExistsAction(Action):
    def __call__(self, parser, namespace, value, option_string=None):
        path = Path(value)
        if not path.is_file():
            parser.error(f"File '{value}' does not exist.")
        setattr(namespace, self.dest, path)


class PathsAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        values = [values] if not isinstance(values, list) else values
        paths = set()

        # Characters that indicate a glob pattern
        glob_chars = {"*", "?", "[", "]", "{", "}"}

        for val in values:
            # Check if this looks like a glob pattern
            is_glob = any(char in val for char in glob_chars)

            path = Path(val)

            # If it's not a glob pattern, verify it exists
            if not is_glob and not path.exists():
                parser.error(f"Path '{val}' does not exist.")

            paths.add(path)

        setattr(namespace, self.dest, paths)


class DetectorAction(Action):
    def __call__(self, parser, namespace, requested_detectors, option_string=None):
        for detector_name in requested_detectors:
            if detector_name not in ALL_AVAILABLE_DETECTOR_NAMES:
                parser.error(f"Invalid detector: '{detector_name}'")
        setattr(namespace, self.dest, requested_detectors)


class CodeLocationAction(Action):
    def __call__(self, parser, namespace, value, option_string=None):
        path = Path(value).expanduser().resolve()
        if path.is_file():
            parser.error(f"'{value}' is a file; must be a directory.")
        if not path.exists():
            parser.error(f"Directory '{value}' does not exist.")
        if not any(path.iterdir()):
            parser.error(f"Directory '{value}' is empty.")
        setattr(namespace, self.dest, path.resolve())


class OutputFileAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(
            namespace,
            self.dest,
            values or Path(f"inspector_output_{datetime.now().strftime('%Y%m%d')}"),
        )
        setattr(namespace, "output_file_used", True)


class ValidateScannerTarget(Action):
    def __call__(self, parser, namespace, value, option_string=None):
        path = Path(value).expanduser().resolve()

        if path.is_file():
            if path.suffix == ".zip":
                return setattr(namespace, self.dest, ("local_zip", path))
            elif os.access(path, os.X_OK):
                return setattr(namespace, self.dest, ("local_path", path))
            else:
                parser.error(
                    f"Non-archive file exists but is not executable: '{value}'"
                )

        elif path.is_dir():
            return setattr(namespace, self.dest, ("local_path", path))

        elif re.match(r"^https?://.*\.zip$", value, re.IGNORECASE):
            return setattr(namespace, self.dest, ("remote_zip", value))

        parser.error(f"Invalid scanner source: '{value}'")


class CheckPathsAction(Action):
    def __init__(self, option_strings, dest, **kwargs):
        self.must_exist = kwargs.pop("must_exist", True)
        self.must_be_dir = kwargs.pop("must_be_dir", False)
        self.allow_files = kwargs.pop("allow_files", True)
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        values = [values] if not isinstance(values, list) else values
        validated_paths = []

        for value in values:
            path = Path(value).expanduser().resolve()

            if self.must_exist and not path.exists():
                parser.error(f"Path '{value}' does not exist.")

            if self.must_be_dir and not path.is_dir():
                parser.error(f"Path '{value}' is not a directory.")

            if not self.allow_files and path.is_file():
                parser.error(f"File path '{value}' is not allowed.")

            validated_paths.append(path)

        setattr(namespace, self.dest, validated_paths)


class Parsers:
    def __init__(self):
        self.scope_parser = self._build_scope_parser()
        self.detector_parser = self._build_detector_parser()
        self.scanner_parser = self._build_scanner_parser()
        debug_enabled, log_level = configure_early_logging()
        self.dev_parser = self._build_dev_parser(debug_enabled, log_level)
        self.code_parser = self._build_code_parser()
        self.output_parser = self._build_output_parser()

    def _build_scope_parser(self):
        parser = ArgumentParser(add_help=False)
        group = parser.add_argument_group(
            "Scope Options",
            "Specify which source code files are explicitly in scope to inspect.",
        )

        group.add_argument(
            "--scope-file",
            "--scope",
            action=FileExistsAction,
            help="Path to file listing source code files explicitly in scope. Overrides --include/--exclude.",
        )

        group.add_argument(
            "--include",
            nargs="*",
            action=PathsAction,
            help="Paths to include in scan.",
        )

        group.add_argument(
            "--exclude",
            nargs="*",
            action=PathsAction,
            help="Paths to exclude from scan.",
        )

        return parser

    def _build_code_parser(self):
        parser = ArgumentParser(add_help=False)
        group = parser.add_argument_group(
            "Code Options", "Specify root directory of code to scan."
        )
        group.add_argument(
            "project_root",
            action=CodeLocationAction,
            help="Directory containing the source code to scan.",
        )
        return parser

    def _build_dev_parser(self, debug_enabled, log_level):
        parser = ArgumentParser(add_help=False)
        group = parser.add_argument_group(
            "Development Options", "Dev and debugging flags."
        )

        group.add_argument("--dev", action="store_true", help="Enable dev mode.")
        group.add_argument(
            "--debug",
            action="store_true",
            default=debug_enabled,
            help="Enable debug logging.",
        )
        group.add_argument(
            "--log-level",
            type=str,
            default=log_level
            or (LOG_LEVEL_DEFAULT_DEBUG_MODE if debug_enabled else LOG_LEVEL_DEFAULT),
            choices=["debug", "info", "warn", "error", "critical"],
            help="Set log level. Defaults to 'warn' generally or 'debug' in debug mode.",
        )
        return parser

    def _build_output_parser(self):
        parser = ArgumentParser(add_help=False)
        group = parser.add_argument_group(
            "Output Format Options", "Control output format and destination."
        )

        group.add_argument(
            "--output-format",
            type=str,
            choices=["md", "json"],
            default="md",
            help="Format of results output.",
        )
        group.add_argument(
            "--output-file",
            nargs="?",
            action=OutputFileAction,
            default=None,
            help="Optional output path. Defaults to inspector_output_<DATE>.",
        )
        group.add_argument(
            "--minimal-output", action="store_true", help="Reduce verbosity of output."
        )
        return parser

    def _build_scanner_parser(self):
        parser = ArgumentParser(add_help=False)
        group = parser.add_argument_group(
            "Scanner Options", "Specify which scanners to use."
        )

        scanner_arg = group.add_argument(
            "--scanners",
            "--scanner",
            nargs="+",
            choices=INSTALLED_SCANNERS or NO_SCANNERS_INSTALLED,
            default=INSTALLED_SCANNERS,
            help="List of scanners to run. Must specify at least one. Default is all installed scanners.",
        )
        scanner_arg.completer = scanner_completer
        return parser

    def _build_detector_parser(self):
        parser = ArgumentParser(add_help=False)
        group = parser.add_argument_group(
            "Detector Options", "Filter detectors by tag, severity, or name."
        )

        severities_arg = group.add_argument(
            "--severities",
            "--severity",
            choices=[s.value for s in DetectorSeverities],
            nargs="*",
            action="extend",
            help="Filter detectors by severity level.",
        )
        severities_arg.completer = severity_completer

        tags_arg = group.add_argument(
            "--tags",
            "--tag",
            choices=ALL_AVAILABLE_DETECTOR_TAGS,
            nargs="*",
            action="extend",
            help="Filter detectors by tag.",
        )
        tags_arg.completer = tag_completer

        detectors_arg = group.add_argument(
            "--detectors",
            "--detector",
            choices=detector_choices(),
            action=DetectorAction,
            nargs="*",
            dest="detector_names",
            help="Specify detectors to use.",
        )
        detectors_arg.completer = detector_completer

        excluded_arg = group.add_argument(
            "--detectors-exclude",
            "--detector-exclude",
            choices=detector_choices(),
            action=DetectorAction,
            nargs="*",
            dest="excluded_detector_names",
            help="Exclude specific detectors.",
        )
        excluded_arg.completer = detector_completer

        return parser


class Subparsers:
    def __init__(self, root_parser: ArgumentParser, parsers: Parsers):
        self.root_parser = root_parser
        self.parsers = parsers
        self.subparser_object = self.root_parser.add_subparsers(dest="mode")

        self.scan = self._add_scan()
        self.test = self._add_test()
        self.version = self._add_version()
        self.scanner = self._add_scanner()
        self.autocomplete = self._add_autocomplete()

    def _add_scan(self):
        parser = self.subparser_object.add_parser(
            name="scan",
            help="Scan a codebase for issues.",
            description="Scan Solidity contracts for issues using selected detectors.",
            usage="python3 inspect_cli.py scan <project_root> --include path/to/code",
            formatter_class=RawTextHelpFormatter,
            parents=[
                self.parsers.code_parser,
                self.parsers.detector_parser,
                self.parsers.scanner_parser,
                self.parsers.scope_parser,
                self.parsers.dev_parser,
                self.parsers.output_parser,
            ],
        )

        parser.add_argument(
            "--quiet",
            "--silence",
            "-q",
            action="store_true",
            help="Suppress output to console.",
        )

        parser.add_argument(
            "--absolute-paths",
            action="store_true",
            help="Output full absolute file paths instead of relative paths.",
        )

        return parser

    def _add_test(self):
        test = self.subparser_object.add_parser(
            name="test",
            help="Run detector tests and verify outputs.",
            description="Run Inspector's tests on detectors to check correctness.",
            usage="python3 src/inspector_cli.py test --detectors detector_name_1 detector_name_2",
            formatter_class=RawTextHelpFormatter,
            parents=[
                self.parsers.detector_parser,
                self.parsers.scanner_parser,
                self.parsers.dev_parser,
            ],
        )
        test.add_argument("--ci", action="store_true", help="CI mode disables spinner.")
        test.add_argument(
            "--leave-test-annotations",
            action="store_true",
            help="Do not remove test annotations from test projects.",
        )
        test.add_argument(
            "--output-format",
            choices=["table", "json", "differences"],
            default="table",
            help="Format of test output.",
        )
        test.add_argument(
            "--test-paths",
            nargs="+",
            metavar="PATH",
            action=CheckPathsAction,
            must_be_dir=True,
            help="Root test folders organized by detector ID.",
        )
        return test

    def _add_version(self):
        return self.subparser_object.add_parser(
            name="version",
            help="Show version and exit.",
            description="Print the Inspector version.",
            usage="python3 src/inspector_cli.py version",
            formatter_class=RawTextHelpFormatter,
        )

    def _add_scanner(self):
        scanner = self.subparser_object.add_parser(
            name="scanner",
            help="Manage scanner plugins.",
            description="Install, uninstall, or list scanner plugins.",
            usage="python3 src/inspector_cli.py scanner <command>",
            formatter_class=RawTextHelpFormatter,
            parents=[self.parsers.dev_parser],
        )

        actions = scanner.add_subparsers(dest="scanner_action")

        self._scanner_install(actions)
        self._scanner_uninstall(actions)
        self._scanner_list(actions)
        return scanner

    def _scanner_install(self, parent):
        install = parent.add_parser(
            "install",
            help="Install a scanner from local path or URL.",
            description="Install scanner plugin from directory, zip, or URL.",
            parents=[self.parsers.dev_parser],
        )
        install.add_argument(
            "target",
            type=str,
            action=ValidateScannerTarget,
            help="Directory, .zip file, or remote .zip URL",
        )
        install.add_argument(
            "--reinstall", action="store_true", help="Reinstall if already installed."
        )

    def _scanner_uninstall(self, parent):
        scanners = INSTALLED_SCANNERS
        uninstall = parent.add_parser(
            "uninstall",
            help="Uninstall a scanner.",
            description="Remove installed scanner plugin.",
            parents=[self.parsers.dev_parser],
        )
        uninstall.add_argument(
            "target",
            choices=INSTALLED_SCANNERS or NO_SCANNERS_INSTALLED,
            help="Scanner to uninstall."
            + (f" Choices: {', '.join(scanners)}" if scanners else ""),
        )

    def _scanner_list(self, parent):
        listing = parent.add_parser(
            "list",
            help="List installed scanners.",
            description="Show installed scanner plugins.",
            parents=[self.parsers.dev_parser],
        )
        listing.add_argument(
            "--detailed", action="store_true", help="Show detailed info."
        )

    def _add_autocomplete(self):
        autocomplete = self.subparser_object.add_parser(
            name="autocomplete",
            help="Manage shell autocompletion.",
            description="Install or uninstall shell autocompletion.",
            usage="python3 src/inspector_cli.py autocomplete <command>",
            formatter_class=RawTextHelpFormatter,
            parents=[self.parsers.dev_parser],
        )
        actions = autocomplete.add_subparsers(dest="autocomplete_action")
        actions.add_parser(
            "install", help="Install autocompletion.", parents=[self.parsers.dev_parser]
        )
        actions.add_parser(
            "uninstall",
            help="Uninstall autocompletion.",
            parents=[self.parsers.dev_parser],
        )
        actions.add_parser(
            "show",
            help="Print shell completion script for use with eval.",
            parents=[self.parsers.dev_parser],
        )
        return autocomplete
