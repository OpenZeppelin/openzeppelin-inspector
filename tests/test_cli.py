import os
import shutil
import unittest
import argparse
import subprocess
from inspector import __version__
from inspector.cli.capabilities.auto_completion import is_auto_completion_installed
from inspector.constants import PATH_PROJECT_ROOT
import json
import logging
from logging import Logger

logger: Logger = logging.getLogger(__name__)


DEFAULT_CODEBASE_TEST_FOLDER = PATH_PROJECT_ROOT / "tests/utils/files"
MOCK_SCANNER_PATH = PATH_PROJECT_ROOT / "tests/utils/mock_scanner"
MOCK_SCANNER_ZIP_PATH = PATH_PROJECT_ROOT / "tests/utils/mock_scanner.zip"
MOCK_EXECUTABLE_SCANNER_PATH = (
    PATH_PROJECT_ROOT / "tests/utils/mock_executable_scanner/mock_scanner.py"
)


class TestCLI(unittest.TestCase):
    folder_path = DEFAULT_CODEBASE_TEST_FOLDER
    test_dir = "/tmp/cli_tests_dir"
    is_autocompletion_installed = False

    @classmethod
    def setUpClass(cls):
        """Ensure the provided folder exists and contains Solidity files."""
        os.environ["COVERAGE_PROCESS_START"] = ".coveragerc"
        os.environ["COVERAGE_FILE"] = ".coverage"

        if not cls.folder_path:
            raise ValueError("Folder path must be provided via arguments.")
        if not os.path.exists(cls.folder_path):
            raise FileNotFoundError(
                f"Provided folder path does not exist: {cls.folder_path}"
            )

        shutil.copytree(cls.folder_path, cls.test_dir)

        # Install mock_scanner
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "install",
            MOCK_SCANNER_PATH,
            "--reinstall",
            "--dev",
        ]
        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )

        # Autocomplete setup, save if it is installed
        cls.is_autocompletion_installed = is_auto_completion_installed()
        if cls.is_autocompletion_installed:
            logger.debug("Autocomplete is already installed")

        assert result.returncode == 0
        assert "Installed scanner successfully:" in result.stdout
        logger.debug(f"Setup completed. Using Solidity codebase from: {cls.test_dir}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test directories and files."""
        for root, dirs, files in os.walk(cls.test_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(cls.test_dir)

        # Uninstall mock_scanner
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "uninstall",
            "mock-scanner",
        ]
        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Uninstalled scanner successfully:" in result.stdout

    def install_autocomplete(self):
        result = subprocess.run(
            ["coverage", "run", "-m", "src.inspector_cli", "autocomplete", "install"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Installed autocomplete successfully" in result.stdout
        logger.info("Installed autocomplete successfully")
        return

    @unittest.skipIf(
        os.environ.get("GITHUB_ACTIONS") == "true",
        "Skipping autocomplete test when testing via GitHub",
    )
    def test_install_uninstall_autocomplete(self):
        """Test the 'install autocomplete' command."""
        # Store initial state
        initial_state = is_auto_completion_installed()

        try:
            result = subprocess.run(
                [
                    "coverage",
                    "run",
                    "-m",
                    "src.inspector_cli",
                    "autocomplete",
                    "install",
                ],
                capture_output=True,
                text=True,
            )
            installed = is_auto_completion_installed()
            self.assertTrue(installed)
            self.assertEqual(result.returncode, 0)
            self.assertIn(
                "Installed autocomplete successfully",
                result.stdout,
            )
            logger.info("Installed autocomplete successfully")

            uninstall_result = subprocess.run(
                [
                    "coverage",
                    "run",
                    "-m",
                    "src.inspector_cli",
                    "autocomplete",
                    "uninstall",
                ],
                capture_output=True,
                text=True,
            )
            installed = is_auto_completion_installed()
            self.assertFalse(installed)
            self.assertEqual(uninstall_result.returncode, 0)
            self.assertIn(
                "Uninstalled autocomplete successfully",
                uninstall_result.stdout,
            )
        finally:
            # Restore initial state
            if initial_state and not is_auto_completion_installed():
                self.install_autocomplete()
            elif not initial_state and is_auto_completion_installed():
                subprocess.run(
                    [
                        "coverage",
                        "run",
                        "-m",
                        "src.inspector_cli",
                        "autocomplete",
                        "uninstall",
                    ],
                    capture_output=True,
                    text=True,
                )

    @unittest.skipIf(
        os.environ.get("GITHUB_ACTIONS") == "true",
        "Skipping autocomplete test when testing via GitHub",
    )
    def test_uninstall_autocomplete_error(self):
        """Test the 'uninstall autocomplete' command when it is not installed."""
        try:
            if is_auto_completion_installed():
                # Uninstall autocomplete if it is installed
                result = subprocess.run(
                    [
                        "coverage",
                        "run",
                        "-m",
                        "src.inspector_cli",
                        "autocomplete",
                        "uninstall",
                    ],
                    capture_output=True,
                    text=True,
                )

            # The uninstall command should fail if it is not installed
            result = subprocess.run(
                [
                    "coverage",
                    "run",
                    "-m",
                    "src.inspector_cli",
                    "autocomplete",
                    "uninstall",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertFalse(is_auto_completion_installed())
            self.assertIn(
                "No auto-completion configuration was found in `~/",
                result.stdout,
            )
        finally:
            # Restore initial state
            if self.is_autocompletion_installed:
                self.install_autocomplete()

    def test_scan_with_valid_input(self):
        """Test the 'scan' command with a valid project directory."""
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "potential issue",
            result.stdout,
        )

    def test_scan_exclude_detectors(self):
        """Test the 'scan' command with a valid project directory."""
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--scanner",
                "mock-scanner",
                "--detectors-exclude",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        # return code is 1 because there are no more detectors
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "No detectors",
            result.stderr,
        )
        self.assertNotIn(
            "potential issue",
            result.stdout,
        )

    def test_scan_with_valid_input_json_output(self):
        """Test the 'scan' command with a valid project directory."""
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
                "--output-format",
                "json",
                "--minimal-output",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        json_response = json.loads(result.stdout)
        self.assertEqual(len(json_response.get("findings", [])), 1)

    def test_scan_with_valid_input_syntax_errors(self):
        """Test the 'scan' command with a valid project directory."""
        # Creating a sample Solidity file in the test directory for testing syntax errors
        with open(
            os.path.join(self.test_dir, "TestContractWithSyntaxErrors.sol"), "w"
        ) as f:
            f.write(
                """
                // SPDX-License-Identifier: MIT
                pragma solidity ^0.8.0

                contract TestContract 
                    function test() public pure returns (string memory) {
                        return "Hello, World!";
                    }
                }
            """
            )

        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "potential issue",
            result.stdout,
        )

    def test_scan_with_empty_directory(self):
        """Test the 'scan' command with an empty project directory."""
        empty_dir = "/tmp/empty_inspector_codebase_1"
        os.makedirs(empty_dir, exist_ok=True)

        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                empty_dir,
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("", result.stdout)
        self.assertIn(f"Directory '{empty_dir}' is empty.", result.stderr)
        os.rmdir(empty_dir)

    def test_scan_exclude(self):
        """Test the 'scan' command with excluded paths."""
        file_path = f"{self.test_dir}/WETHUpdate.sol"

        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--exclude",
                file_path,
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("WETHUpdate", result.stdout)

    def test_scan_exclude_non_existing(self):
        """Test the 'scan' command with non-existent excluded paths."""
        file_path = f"{self.test_dir}/TestContract.sol"
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--exclude",
                file_path,
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(f"Path '{file_path}' does not exist", result.stderr)

    def test_version_command(self):
        """Test the 'version' command to check if the version is returned correctly."""

        result = subprocess.run(
            ["coverage", "run", "-m", "src.inspector_cli", "version"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn(__version__, result.stdout)

    def test_scanner_list_command(self):
        """Test the 'scanner list' command with a valid option."""

        scanner_name = "mock-scanner"
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "list",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(scanner_name, result.stdout)

    def test_inspector_test_command(self):
        """Test the 'test' command with a valid option."""
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "test",
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Testing complete. Results below.", result.stdout)

    def test_inspector_table_command(self):
        """Test the 'test' command with --table option."""
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "test",
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
                "--output-format",
                "table",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Testing complete. Results below.", result.stdout)

    def test_scanner_command_no_action(self):
        """Test scanner command without action."""
        result = subprocess.run(
            ["coverage", "run", "-m", "src.inspector_cli", "scanner"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("scanner command requires an action", result.stdout)

    def test_autocomplete_command_no_action(self):
        """Test autocomplete command without action."""
        result = subprocess.run(
            ["coverage", "run", "-m", "src.inspector_cli", "autocomplete"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("autocomplete command requires an action", result.stdout)

    def test_scan_with_output_file(self):
        """Test scan command with output file."""
        output_file = "test_output"
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--output-file",
                output_file,
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.exists(f"{output_file}.md"))
        os.remove(f"{output_file}.md")

    def test_scan_with_json_output(self):
        """Test scan command with JSON output format."""
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--output-format",
                "json",
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        # Verify output is valid JSON
        try:
            # Find the start and end of the JSON object
            json_start = result.stdout.find("{")
            json_end = result.stdout.rfind("}\n")
            if json_start == -1 or json_end == -1:
                self.fail("No valid JSON object found in output")

            json_output = result.stdout[json_start : json_end + 1]
            parsed_json = json.loads(json_output)

            # Verify the expected structure
            self.assertIn("findings", parsed_json)
            self.assertIsInstance(parsed_json["findings"], list)
        except json.JSONDecodeError as e:
            self.fail(f"Output is not valid JSON: {e} || {json_output}")

    def test_scan_with_quiet_mode(self):
        """Test scan command with quiet mode."""
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--quiet",
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("### Mock test", result.stdout)

    def test_scan_with_minimal_output(self):
        """Test scan command with minimal output."""
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--minimal",
                "--scanner",
                "mock-scanner",
                "--detector",
                "mock-test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("### Mock test", result.stdout)
        self.assertNotIn("Scanned", result.stdout)

    def test_scan_with_file_write_error(self):
        """Test scan command with file write error."""
        # Create a directory that we can't write to
        read_only_dir = "/tmp/read_only_dir"
        os.makedirs(read_only_dir, exist_ok=True)
        os.chmod(read_only_dir, 0o444)  # Read-only permissions

        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--output-file",
                f"{read_only_dir}/test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Presenting issues failed", result.stderr)

        # Clean up
        os.chmod(read_only_dir, 0o755)  # Restore permissions
        os.rmdir(read_only_dir)

    def test_test_with_leave_annotations(self):
        """Test test command with leave test annotations option."""
        # Create a test file with annotations
        test_file = os.path.join(self.test_dir, "TestContract.sol")
        with open(test_file, "w") as f:
            f.write(
                """
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.0;
            
            contract Test {
                // :true-positive-here: test_detector
                function test() public {
                    // :true-negative-here: test_detector
                }
            }
            """
            )

        # Test with leave annotations
        result_with = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "test",
                "--scanner",
                "mock-scanner",
                "--leave-test-annotations",
                "--ci",
            ],
            capture_output=True,
            text=True,
        )

        # Test without leave annotations
        result_without = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "test",
                "--scanner",
                "mock-scanner",
                "--ci",
            ],
            capture_output=True,
            text=True,
        )

        # Verify we have the same output when flag is set
        self.assertEqual(result_with.returncode, 0)
        self.assertEqual(result_without.returncode, 0)
        self.assertEqual(result_with.stdout, result_without.stdout)


class TestMockScannerInstallationCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment for install related commands."""
        logger.debug("Setting up test environment...")

        # Ensure test directories exist
        os.makedirs(os.path.dirname(MOCK_SCANNER_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(MOCK_SCANNER_ZIP_PATH), exist_ok=True)

        # Verify test files exist
        if not os.path.exists(MOCK_SCANNER_PATH):
            raise FileNotFoundError(f"Mock scanner path not found: {MOCK_SCANNER_PATH}")
        if not os.path.exists(MOCK_SCANNER_ZIP_PATH):
            raise FileNotFoundError(
                f"Mock scanner zip not found: {MOCK_SCANNER_ZIP_PATH}"
            )

        logger.debug("Checking if mock-scanner is installed...")
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "list",
        ]

        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )
        if "mock-scanner" in result.stdout:
            logger.debug("mock-scanner is installed, uninstalling...")
            coverage_command = [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "uninstall",
                "mock-scanner",
            ]

            result = subprocess.run(
                coverage_command,
                capture_output=True,
                text=True,
            )
        logger.debug("Setup Class completed.")
        assert result.returncode == 0
        assert "mock-scanner" not in result.stdout

    @classmethod
    def tearDownClass(cls):
        """Clean up test directories and files."""
        logger.debug("Tearing down test environment...")
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "list",
        ]

        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )
        if "mock-scanner" in result.stdout:
            logger.debug("mock-scanner is installed, uninstalling...")
            coverage_command = [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "uninstall",
                "mock-scanner",
            ]

            result = subprocess.run(
                coverage_command,
                capture_output=True,
                text=True,
            )
        pass

    def test_scanner_install_command(self):
        """Test the 'scanner install' command with a valid option."""
        logger.debug(f"Mock scanner path: {MOCK_SCANNER_PATH}")
        logger.debug(f"Mock scanner path exists: {os.path.exists(MOCK_SCANNER_PATH)}")
        logger.debug(f"Project root: {PATH_PROJECT_ROOT}")

        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "install",
            MOCK_SCANNER_PATH,
            "--dev",
        ]
        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"Command failed with return code {result.returncode}")
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")

        self.assertEqual(result.returncode, 0)
        self.assertIn("Installed scanner successfully:", result.stdout)

    def test_scanner_uninstall_command(self):
        """Test the 'scanner uninstall' command with a valid option."""
        # Install mock-scanner if it is not installed
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "list",
        ]

        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )
        if "mock-scanner" not in result.stdout:
            self.test_scanner_install_command()
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "uninstall",
            "mock-scanner",
        ]
        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Uninstalled scanner successfully:", result.stdout)

    def test_scanner_install_zip_command(self):
        """Test the 'scanner install' command with a zip file."""
        # Uninstall mock-scanner if it is installed
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "list",
        ]

        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )
        if "mock-scanner" in result.stdout:
            self.test_scanner_uninstall_command()
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "install",
            MOCK_SCANNER_ZIP_PATH,
            "--reinstall",
            "--log-level",
            "warn",
        ]
        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Installed scanner successfully:", result.stdout)

    def test_scanner_install_failure_with_non_existent_scanner(self):
        """Test scanner installation failure. when a non-existent scanner is provided"""
        # Mock a non-existent scanner path to trigger installation failure
        non_existent_scanner_path = "/tmp/non_existent_inspector_scanner"
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "install",
                non_existent_scanner_path,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            f"Invalid scanner source: '{non_existent_scanner_path}'", result.stderr
        )

    def test_scanner_uninstall_failure(self):
        """Test scanner uninstallation failure."""
        scanner_name = "non_existent_scanner"
        # Try to uninstall a non-existent scanner
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "uninstall",
                scanner_name,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(f"invalid choice: '{scanner_name}'", result.stderr)

    def test_scanner_install_with_corrupted_registry(self):
        """Test scanner installation when registry file is corrupted."""
        # Create a corrupted registry file
        registry_path = os.path.expanduser("~/.inspector/scanners/registry.json")
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)

        with open(registry_path, "w") as f:
            f.write("{invalid json}")

        # Try to install scanner
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "install",
                MOCK_SCANNER_PATH,
                "--reinstall",
            ],
            capture_output=True,
            text=True,
        )

        # Clean up corrupted registry
        if os.path.exists(registry_path):
            os.remove(registry_path)

        # Should still install successfully
        self.assertEqual(result.returncode, 0)
        self.assertIn("Installed scanner successfully:", result.stdout)

    def test_scanner_install_from_invalid_remote_zip(self):
        """Test scanner installation from an invalid remote zip URL."""
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "install",
                "https://fake-url.local/fake_scanner.zip",
                "--reinstall",
                "--log-level",
                "warn",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Failed to download scanner", result.stderr)
        self.assertIn("Installation error", result.stdout)

    def test_scanner_install_from_corrupted_zip(self):
        """Test scanner installation from a corrupted zip file."""
        # Create a corrupted zip file
        corrupted_zip = "corrupted_scanner.zip"
        with open(corrupted_zip, "w") as f:
            f.write("This is not a valid zip file")

        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "install",
                corrupted_zip,
                "--reinstall",
                "--log-level",
                "warn",
            ],
            capture_output=True,
            text=True,
        )
        # Clean up
        if os.path.exists(corrupted_zip):
            os.remove(corrupted_zip)

        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid zip file", result.stderr)
        self.assertIn("Installation error", result.stdout)

    def test_scanner_install_with_post_install_failure(self):
        """Test scanner installation when post-installation setup fails."""
        # Create a temporary scanner with invalid requirements.txt
        temp_dir = "/tmp/temp_failing_scanner"
        os.makedirs(temp_dir, exist_ok=True)

        # Create a pyproject.toml with invalid package name
        with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
            f.write(
                """
                [project]
                name = "failing_scanner"
                version = "1.0.0"

                [tool.openzeppelin.inspector]
                scanner_name = "failing_scanner"
                scanner_org = "test"
                """
            )

        # Create an invalid requirements.txt
        with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
            f.write("nonexistent-package==1.0.0")

        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "install",
                temp_dir,
                "--reinstall",
                "--log-level",
                "warn",
            ],
            capture_output=True,
            text=True,
        )

        # Clean up
        shutil.rmtree(temp_dir)

        # Should fail during post-installation
        self.assertEqual(result.returncode, 1)
        self.assertIn("Python setup failed for", result.stderr)


class TestExecutableScanner(unittest.TestCase):
    test_dir = "./tests/utils/files/"
    temp_dirs = [
        "/tmp/temp_invalid_metadata_scanner",
        "/tmp/temp_no_permission_scanner",
        "/tmp/temp_failing_scanner",
    ]

    @classmethod
    def setUpClass(cls):
        """Set up test environment for install related commands."""
        logger.debug("Setting up test environment...")

        # Ensure test directories exist
        os.makedirs(os.path.dirname(MOCK_EXECUTABLE_SCANNER_PATH), exist_ok=True)
        # Verify test files exist
        if not os.path.exists(MOCK_EXECUTABLE_SCANNER_PATH):
            raise FileNotFoundError(
                f"Mock scanner path not found: {MOCK_EXECUTABLE_SCANNER_PATH}"
            )

        logger.debug("Checking if mock-executable-scanner is installed...")
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "list",
        ]

        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )
        if "mock-executable-scanner" in result.stdout:
            logger.debug("mock-executable-scanner is installed, uninstalling...")
            coverage_command = [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "uninstall",
                "mock-executable-scanner",
            ]

            uninstall_result = subprocess.run(
                coverage_command,
                capture_output=True,
                text=True,
            )
            assert uninstall_result.returncode == 0

        logger.debug("Setup Class completed.")
        assert result.returncode == 0
        assert "mock-executable-scanner" not in result.stdout

    @classmethod
    def tearDownClass(cls):
        """Clean up test directories and files."""
        logger.debug("Tearing down test environment...")
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "list",
        ]

        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )
        if "mock-executable-scanner" in result.stdout:
            logger.debug("mock-executable-scanner is installed, uninstalling...")
            coverage_command = [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "uninstall",
                "mock-executable-scanner",
            ]

            result = subprocess.run(
                coverage_command,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "Uninstalled scanner successfully:" in result.stdout

        for temp_dir in cls.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temp directory: {temp_dir}")

    def test_executable_scanner_install(self):
        """Test scanner installation when the scanner is an executable."""
        logger.debug(f"Mock scanner path: {MOCK_EXECUTABLE_SCANNER_PATH}")
        logger.debug(
            f"Mock scanner path exists: {os.path.exists(MOCK_EXECUTABLE_SCANNER_PATH)}"
        )
        logger.debug(f"Project root: {PATH_PROJECT_ROOT}")

        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "install",
            MOCK_EXECUTABLE_SCANNER_PATH,
            "--dev",
            "--reinstall",
        ]
        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"Command failed with return code {result.returncode}")
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")

        self.assertEqual(result.returncode, 0)
        self.assertIn("Installed scanner successfully:", result.stdout)

    def test_executable_scanner_detector_metadata(self):
        """Test detector metadata collection from executable scanner."""
        # First install the scanner
        self.test_executable_scanner_install()

        # Run a scan to verify detector metadata is collected correctly
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--scanner",
                "mock-executable-scanner",
                "--output-format",
                "json",
                "--minimal-output",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        json_output = json.loads(result.stdout)
        self.assertIn("findings", json_output)
        self.assertIsInstance(json_output["findings"], list)

        # Clean up
        subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "uninstall",
                "mock-executable-scanner",
            ],
            capture_output=True,
            text=True,
        )

    def test_executable_scanner_invalid_metadata(self):
        """Test handling of invalid metadata from executable scanner."""
        # Create a temporary scanner with invalid metadata output
        temp_dir = "/tmp/temp_invalid_metadata_scanner"
        os.makedirs(temp_dir, exist_ok=True)

        # Create a Python script that outputs invalid JSON
        scanner_script = os.path.join(temp_dir, "invalid_scanner.py")
        with open(scanner_script, "w") as f:
            f.write(
                """
            #!/usr/bin/env python3
            import sys
            import json

            if sys.argv[1] == "metadata":
                print("invalid json")
                sys.exit(0)
            """
            )
        os.chmod(scanner_script, 0o755)

        # Try to install the invalid scanner
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "install",
                scanner_script,
                "--reinstall",
                "--log-level",
                "warn",
            ],
            capture_output=True,
            text=True,
        )

        # Clean up
        shutil.rmtree(temp_dir)

        # Should fail due to invalid metadata
        self.assertEqual(result.returncode, 1)
        self.assertIn("Failed to get metadata from executable", result.stderr)

    def test_executable_scanner_permission_error(self):
        """Test handling of permission errors when running executable scanner."""
        # Create a temporary scanner without execute permissions
        temp_dir = "/tmp/temp_no_permission_scanner"
        os.makedirs(temp_dir, exist_ok=True)

        # Create a Python script without execute permissions
        scanner_script = os.path.join(temp_dir, "no_permission_scanner.py")
        with open(scanner_script, "w") as f:
            f.write(
                """
            #!/usr/bin/env python3
            import sys
            import json

            if sys.argv[1] == "metadata":
                print(json.dumps({"name": "no-permission-scanner"}))
                sys.exit(0)
            """
            )
        os.chmod(scanner_script, 0o644)  # Read-only permissions

        # Try to install the scanner
        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "install",
                scanner_script,
                "--reinstall",
                "--log-level",
                "warn",
            ],
            capture_output=True,
            text=True,
        )

        # Clean up
        shutil.rmtree(temp_dir)

        # Should fail due to permission error
        self.assertEqual(result.returncode, 2)
        self.assertIn("not executable", result.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Run tests for the Solidity processing tool."
    )
    parser.add_argument(
        "--codebase",
        required=False,
        help="Path to the Solidity codebase folder to test.",
        default=DEFAULT_CODEBASE_TEST_FOLDER,
    )

    args = parser.parse_args()

    # Dynamically set test parameters
    TestCLI.folder_path = args.codebase

    # Run the test suite
    test_loader = unittest.TestLoader()
    test_suite = test_loader.loadTestsFromTestCase(TestCLI)
    unittest.TextTestRunner(verbosity=2).run(test_suite)


if __name__ == "__main__":
    main()
