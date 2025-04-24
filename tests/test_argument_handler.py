import unittest
import os
import subprocess
import shutil
import logging
from logging import Logger

logger: Logger = logging.getLogger(__name__)

DEFAULT_CODEBASE_TEST_FOLDER = "./tests/utils/files"
MOCK_SCANNER_PATH = "./tests/utils/mock_scanner"
SCOPE_FILE = "test.scope"


class TestArgumentHandler(unittest.TestCase):
    folder_path = DEFAULT_CODEBASE_TEST_FOLDER
    test_dir = "/tmp/inspector_cli_tests_dir"
    scope_file = os.path.join(test_dir, SCOPE_FILE)

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""

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
        assert result.returncode == 0
        assert "Installed scanner successfully:" in result.stdout

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        logger.debug("Cleaning up test environment...")
        if os.path.exists(cls.test_dir):
            for root, dirs, files in os.walk(cls.test_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(cls.test_dir)

        # Uninstall mock-scanner
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

    def test_error_empty_scope_file(self):
        """Test handling of empty scope file"""
        with open(self.scope_file, "w") as f:
            f.write("")

        result = subprocess.run(
            [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scan",
                self.test_dir,
                "--scope",
                self.scope_file,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Provided scope file does not contain any valid files", result.stderr
        )

    def test_include_exclude_flags(self):
        """Test handling of include and exclude flags"""
        # Test file paths
        include1 = os.path.join(self.test_dir, "WETH9.sol")
        exclude1 = os.path.join(self.test_dir, "WETHUpdate.sol")

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
                "--include",
                include1,
                exclude1,
                "--exclude",
                exclude1,
                "--log-level",
                "warn",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("potential issue", result.stdout)
        self.assertNotIn("WETHUpdate.sol", result.stdout)

    def test_tag_filtering(self):
        """Test tag filtering logic"""
        # Create a test contract
        test_file = os.path.join(self.test_dir, "test.sol")
        with open(test_file, "w") as f:
            f.write("// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;")

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
                "--tags",
                "reportable",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("potential issue", result.stdout)

    def test_invalid_scope_files(self):
        """Test handling of invalid scope files"""
        # Create a scope file with invalid paths
        with open(self.scope_file, "w") as f:
            f.write("nonexistent/path.sol\n")

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
                "--scope",
                self.scope_file,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Provided scope file does not contain any valid files", result.stderr
        )

    def test_mixed_scope_and_include(self):
        """Test mixing scope file with include flags"""
        # Create a valid scope file
        with open(self.scope_file, "w") as f:
            f.write("WETH9.sol\n")

        include1 = os.path.join(self.test_dir, "WETHUpdate.sol")
        include2 = os.path.join(self.test_dir, "NoIssues.sol")

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
                "--scope",
                self.scope_file,
                "--include",
                include1,
                include2,
                "--debug",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        # 1 file from the scope and two files provided through include flags
        self.assertIn("3 files provided", result.stdout)

    def test_mixed_scope_and_exclude(self):
        """Test mixing scope file with exclude flags"""
        # Create a temp file
        file = "tempfile.txt"

        # Create a valid scope file
        with open(self.scope_file, "w") as f:
            f.write("WETH9.sol\nWETHUpdate.sol\n" + file)

        with open(os.path.join(self.test_dir, file), "w") as f:
            f.write("This is a test file")

        exclude1 = os.path.join(self.test_dir, file)

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
                "--scope",
                self.scope_file,
                "--exclude",
                exclude1,
                "--debug",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        # 3 files provided with scope and 1 file excluded
        self.assertIn("2 files provided", result.stdout)

    def test_glob_patterns_in_scope(self):
        """Test handling of glob patterns in scope file"""
        # Create a nested directory structure
        nested_dir = os.path.join(self.test_dir, "nested")
        os.makedirs(nested_dir)

        # Create some test files
        with open(os.path.join(nested_dir, "test1.sol"), "w") as f:
            f.write("// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;")
        with open(os.path.join(nested_dir, "test2.sol"), "w") as f:
            f.write("// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;")
        with open(os.path.join(nested_dir, "test3.txt"), "w") as f:
            f.write("// This file won't be added to the scan")

        # Create scope file with glob pattern
        with open(self.scope_file, "w") as f:
            f.write("nested/*.sol\n")

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
                "--scope",
                self.scope_file,
                "--debug",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        # 2 files provided with scope, 2 solidity files.
        self.assertIn("2 files provided", result.stdout)

    def test_relative_paths_in_scope(self):
        """Test handling of relative paths in scope file"""
        # Create a scope file with relative paths
        with open(self.scope_file, "w") as f:
            f.write("./WETH9.sol\nWETHUpdate.sol\n")

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
                "--scope",
                self.scope_file,
                "--debug",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("2 files provided", result.stdout)

    def test_invalid_paths_in_scope(self):
        """Test handling of invalid paths in scope file"""
        # Create a scope file with invalid paths
        with open(self.scope_file, "w") as f:
            f.write("nonexistent.sol\ninvalid/path.sol\n")

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
                "--scope",
                self.scope_file,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Provided scope file does not contain any valid files", result.stderr
        )

    def test_fallback_to_include(self):
        """Test fallback to include when no scope file is provided"""
        include1 = os.path.join(self.test_dir, "WETH9.sol")
        include2 = os.path.join(self.test_dir, "WETHUpdate.sol")

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
                "--include",
                include1,
                include2,
                "--debug",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("2 files provided", result.stdout)

    def test_global_include_exclude(self):
        """Test include and exclude using glob pattern"""
        exclude1 = "*.scope"
        include1 = "*.sol"
        # Test folder contains 4 files: 3 sol and a .scope file

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
                "--exclude",
                exclude1,
                "--include",
                include1,
                "--debug",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("3 files provided", result.stdout)

    def test_scope_containing_incorrect_path(self):
        """Test scope file containing one path that doesn't exist"""
        with open(self.scope_file, "w") as f:
            f.write("nonexistent.sol\nWETH9.sol\n")

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
                "--scope",
                self.scope_file,
                "--debug",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("1 file provided", result.stdout)


if __name__ == "__main__":
    unittest.main()
