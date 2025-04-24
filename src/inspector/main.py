# set up logging early, so that all dynamic imports are logged
from .setup_logging import initialize_logging

initialize_logging()

import os
import json
from time import time

from termcolor import colored
from argcomplete.shell_integration import shellcode

from . import __version__ as inspector_version
from .cli.argument_handler import interpret_arguments, parse_arguments
from .cli.capabilities import install, uninstall
from .cli.capabilities.exceptions import (
    ScannerAlreadyInstalledError,
    InvalidScannerDirectoryError,
    DownloadError,
    ExtractionError,
    InstallationError,
    DependencyInstallationError,
    ShellConfigurationError,
    AutoCompletionNotFoundError,
)
from .response_finalizer import responses_finalizer


from .composer import FindingComposer
from .helpers import (
    get_version_info,
    get_version_info_string,
    print_if_not_silent,
    SpinnerWrapper,
)
from .detector_tester import run_detector_tests, NoTestFilesDiscoveredError
from .scan_executor import ScanExecutor
from . import scanner_registry


def main():
    """Fetch args and run the scan."""

    # start timing how long the program takes to execute
    time_started = time()

    # handle the command line arguments
    args = parse_arguments()

    # look at the arguments we were passed and adjust other options if necessary
    interpret_arguments(args)

    # Create a single spinner instance to be used throughout the function
    status_spinner = SpinnerWrapper(args=args, color="blue")

    # Process command based on mode
    # if running in version mode, print version and exit
    if args.mode == "version":
        print(inspector_version)
        raise SystemExit()

    elif args.mode == "scanner" or args.mode == "scanners":
        if not hasattr(args, "scanner_action") or args.scanner_action is None:
            print("scanner command requires an action: install, uninstall, or list")
            raise SystemExit(1)

        if args.scanner_action == "list":
            # Display installed scanners
            scanner_list = scanner_registry.get_installed_scanners_with_info()
            if getattr(args, "detailed", False):
                cleaned_list = [
                    {k: v for k, v in scanner.items() if k != "detectors"}
                    for scanner in scanner_list
                ]
                print(json.dumps(cleaned_list, indent=4))
            else:
                # Print a simplified list format
                if not scanner_list:
                    print("No scanners installed.")
                else:
                    print("Installed scanners:")
                    for scanner in scanner_list:
                        print(
                            f"  - {scanner['name']} (version: {scanner.get('version', 'unknown')}) by {scanner.get('org', 'unknown')}"
                        )
            raise SystemExit()

        elif args.scanner_action == "install":
            # Install scanner from specified target
            scanner_install_type, scanner_install_target = args.target
            try:
                status_spinner.start("Installing requested scanner...")
                install(
                    "scanner",
                    scanner_install_type,
                    scanner_install_target,
                    reinstall=getattr(args, "reinstall", False),
                    develop=args.dev,
                )
                status_spinner.succeed(
                    f"Installed scanner successfully: {scanner_install_target}"
                )
                raise SystemExit()
            except (
                ScannerAlreadyInstalledError,
                InvalidScannerDirectoryError,
                DownloadError,
                ExtractionError,
                InstallationError,
                DependencyInstallationError,
            ) as e:
                status_spinner.fail(f"Installation error: {str(e)}")
                raise SystemExit(1)
            except Exception as e:
                status_spinner.fail(
                    f"Unexpected error during scanner installation: {str(e)}"
                )
                raise SystemExit(1)

        elif args.scanner_action == "uninstall":
            # Uninstall specified scanner
            try:
                status_spinner.start("Uninstalling requested scanner...")
                uninstall("scanner", args.target)
                status_spinner.succeed(
                    f"Uninstalled scanner successfully: {args.target}"
                )
                raise SystemExit()
            except (InstallationError, ScannerAlreadyInstalledError) as e:
                status_spinner.fail(f"Uninstall error: {str(e)}")
                raise SystemExit(1)
            except Exception as e:
                status_spinner.fail(
                    f"Unexpected error during scanner uninstallation: {str(e)}"
                )
                raise SystemExit(1)

    elif args.mode == "autocomplete":
        if not hasattr(args, "autocomplete_action") or args.autocomplete_action is None:
            print(
                "autocomplete command requires an action: install, uninstall, or show"
            )
            raise SystemExit(1)

        # Install shell autocompletion
        if args.autocomplete_action == "install":
            try:
                install("autocomplete")
                print("Installed autocomplete successfully")
                raise SystemExit()
            except (ShellConfigurationError, AutoCompletionNotFoundError) as e:
                print(f"Autocomplete installation error: {str(e)}")
                raise SystemExit(1)
            except Exception as e:
                print(f"Unexpected error during autocomplete installation: {str(e)}")
                raise SystemExit(1)

        # Uninstall shell autocompletion
        elif args.autocomplete_action == "uninstall":
            try:
                uninstall("autocomplete")
                print("Uninstalled autocomplete successfully")
                raise SystemExit()
            except (ShellConfigurationError, AutoCompletionNotFoundError) as e:
                print(f"Autocomplete uninstallation error: {str(e)}")
                raise SystemExit(1)
            except Exception as e:
                print(f"Unexpected error during autocomplete uninstallation: {str(e)}")
                raise SystemExit(1)
        # Print out autocompletion code for use with shell eval
        elif args.autocomplete_action == "show":
            raw = shellcode("inspector")
            fixed = raw.replace(
                "#compdef i n s p e c t o r", "compdef _python_argcomplete inspector"
            )
            print(fixed)
            raise SystemExit()

    elif args.mode == "test":
        status_spinner.start("Running tests... this may take a while...")
        try:
            test_results, test_has_failures, test_report = run_detector_tests(
                args.scanners,
                args.detector_names,
                args.leave_test_annotations,
                args.output_format,
                args.test_paths,
            )
            status_spinner.succeed("Testing complete. Results below.")
            if args.output_format == "differences":
                print("Noted deviations from expected test results:")
            print(test_results)
            raise SystemExit(test_has_failures)
        except NoTestFilesDiscoveredError as e:
            status_spinner.fail()
            print("No test files found!")
            print("Searched directories:")
            for d in e.searched_dirs:
                print(f" - {d}")
            raise SystemExit()

    # running with scan mode, perform regular scan
    elif args.mode == "scan":
        try:
            status_spinner.start("Scanning...")
            scan_executor = ScanExecutor(
                detectors_names=args.detectors_to_run,
                source_code=args.scannable_code,
                project_root=args.project_root,
                scanners=args.scanners,
            )
            # execute the scan
            scanner_responses = scan_executor.execute()
            # Complete the responses
            finalized_scanner_responses, finalized_scanned_files = responses_finalizer(
                scanner_responses
            )

            status_spinner.succeed("Scanning complete. Results:")

        except Exception as e:
            status_spinner.fail()
            raise SystemExit(f"Executing scanners failed: {e}")

        try:
            # instantiate Composer class
            report_format = getattr(args, "output_format")

            finding_composer = FindingComposer(
                detector_response=finalized_scanner_responses,
                project_root=getattr(args, "project_root"),
                absolute_paths=getattr(args, "absolute_paths", False),
            )
            # get the composed findings
            (
                composed_scanner_results,
                findings_count,
            ) = finding_composer.render(report_format)

        except Exception as e:
            status_spinner.fail()
            raise SystemExit(f"Composing findings failed: {e}")

        try:
            if args.mode == "scan" and not args.quiet:
                print(composed_scanner_results)

            # write out findings to file, if requested
            if findings_count > 0 and getattr(args, "output_file_used", False):
                report_fname = os.path.join(f"{args.output_file}.{args.output_format}")
                versions_appendix = (
                    f"\n{get_version_info(scanner_responses.keys(), report_format)}\n"
                )

                report_text = (
                    json.dumps(
                        json.loads(
                            composed_scanner_results[:-1]
                            + ',"run-info":'
                            + versions_appendix.strip("\n")
                            + "}"
                        ),
                        indent=2,
                    )
                    if report_format == "json"
                    else composed_scanner_results + versions_appendix
                )

                with open(report_fname, "w", encoding="UTF-8") as f:
                    f.write(report_text)

            time_taken = round(time() - time_started, 2)

            # print a summary of all issues found
            print_if_not_silent(
                "\n------- Scan Summary -------\n"
                f"⚠️  {findings_count} potential issue{'s' if findings_count != 1 else ''} found.\n"
                f"🧪  {len(finalized_scanner_responses)} detector{'s' if len(finalized_scanner_responses) != 1 else ''} run in {time_taken:.2f} second{'s' if time_taken != 1 else ''}.\n"
                f"📂  {len(args.scannable_code)} file{'s' if len(args.scannable_code) != 1 else ''} provided, "
                f"{len(finalized_scanned_files)} file{'s' if len(finalized_scanned_files) != 1 else ''} scanned (based on extension).\n",
                args.minimal_output,
            )

            # Print scanner versions to console
            print_if_not_silent(
                colored(
                    get_version_info_string([scanner for scanner in args.scanners]),
                    "light_grey",
                ),
                args.minimal_output,
            )
        except Exception as e:
            status_spinner.fail()
            raise SystemExit(f"Presenting issues failed: {e}")
    else:
        print("Unknown mode. Exiting.")
        raise SystemExit()


if __name__ == "__main__":
    main()
