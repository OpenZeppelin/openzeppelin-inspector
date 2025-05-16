import unittest
import subprocess
import logging

from logging import Logger
from pathlib import Path

from inspector.scanner_manager import ScannerManager, PythonScannerRunner
from inspector.scanners import BaseScanner


logger: Logger = logging.getLogger(__name__)


class TestScannerManager(unittest.TestCase):
    MOCK_SCANNER_PATH = "tests/utils/mock_scanner"

    @classmethod
    def setUpClass(cls):
        """Install mock scanner before running tests."""
        # Install mock_scanner
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "install",
            cls.MOCK_SCANNER_PATH,
            "--dev",
            "--reinstall",
            "--log-level",
            "debug",
        ]
        result = subprocess.run(
            coverage_command,
            capture_output=True,
            text=True,
        )
        logger.debug(f"Setup completed, successfully installed mock scanner.")
        assert result.returncode == 0
        assert "Installed scanner successfully:" in result.stdout

        # force scanner manager to reload scanner information
        # now that a new scanner is installed
        ScannerManager.reload()

    @classmethod
    def tearDownClass(cls):
        """Uninstall mock scanner after tests."""
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

    def test_scanner_discovery(self):
        """Test that mock scanner is discovered and loaded."""
        manager = ScannerManager()
        self.assertIn("mock-scanner", manager.get_all_available_scanner_names())

    def test_detector_metadata(self):
        """Test that mock scanner's detectors are loaded."""
        manager = ScannerManager()
        metadata = manager.get_all_available_detector_metadata()
        self.assertTrue(
            any(detector["id"].startswith("mock") for detector in metadata.values())
        )

    def test_scanner_execution(self):
        """Test executing mock scanner on a test file."""
        manager = ScannerManager()
        test_file = Path("tests/utils/files/TestContract.sol")
        results = manager.execute_scan(
            ["mock-test-detector"], [test_file], test_file.parent, ["mock-scanner"]
        )
        self.assertIn("mock-scanner", results)

    def test_get_scanner_by_name(self):
        """Test retrieving mock scanner by name."""
        scanner = ScannerManager.get_scanner_by_name("mock-scanner")
        self.assertIsInstance(scanner, PythonScannerRunner)

        with self.assertRaises(KeyError):
            ScannerManager.get_scanner_by_name("nonexistent_scanner")

    def test_detector_metadata_by_name(self):
        """Test getting detector metadata by name."""
        manager = ScannerManager()
        metadata = manager.get_detector_metadata_by_name("mock-test")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["id"], "mock-test")

    def test_scanner_registry_handling(self):
        """Test scanner registry loading."""
        manager = ScannerManager()
        # Verify mock scanner is in registry
        self.assertIn("mock-scanner", manager.get_all_available_scanner_names())

    def test_get_all_available_scanners(self):
        """Test getting all available scanners."""
        scanners = ScannerManager.get_all_available_scanners()
        self.assertIsInstance(scanners, tuple)
        self.assertGreater(len(scanners), 0)
        self.assertIn("mock-scanner", ScannerManager.get_all_available_scanner_names())


    def test_load_all_detectors_with_failing_scanner(self):
        """Test loading detectors when a scanner fails to load."""
        # Create a temporary scanner that will fail to load
        failing_scanner_path = Path("/tmp/temp_failing_scanner")
        failing_scanner_path.mkdir(exist_ok=True)
        (failing_scanner_path / "__init__.py").touch()
        
        # Create a scanner that will raise an exception during detector loading
        with open(failing_scanner_path / "failing_scanner.py", "w") as f:
            f.write("""
            class FailingScanner:
                def get_supported_detector_metadata(self):
                    raise Exception("Test failure")
                def get_scanner_name(self):
                    return "failing-scanner"
                def get_root_test_dirs(self):
                    return []
                def run(self, detector_names, code_paths, project_root):
                    return {}
            """)
        
        # Install the failing scanner
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "install",
            str(failing_scanner_path),
            "--dev",
            "--reinstall",
        ]
        subprocess.run(coverage_command, capture_output=True, text=True)
        
        try:
            # Force reload to include the failing scanner
            ScannerManager.reload()
            
            # Verify that other scanners still work
            manager = ScannerManager()
            self.assertIn("mock-scanner", manager.get_all_available_scanner_names())
            self.assertGreater(len(manager.get_all_available_detector_metadata()), 0)
        finally:
            # Cleanup
            uninstall_command = [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "uninstall",
                "failing_scanner",
            ]
            subprocess.run(uninstall_command, capture_output=True, text=True)
            ScannerManager.reload()

    def test_python_scanner_import_error(self):
        """Test error handling when importing a Python scanner fails."""
        # Create a scanner with invalid Python code
        invalid_scanner_path = Path("/tmp/temp_invalid_python_scanner")
        invalid_scanner_path.mkdir(exist_ok=True)
        with open(invalid_scanner_path / "__init__.py", "w") as f:
            f.write("invalid python code")
        
        # Install the invalid scanner
        coverage_command = [
            "coverage",
            "run",
            "-m",
            "src.inspector_cli",
            "scanner",
            "install",
            str(invalid_scanner_path),
            "--dev",
            "--reinstall",
        ]
        subprocess.run(coverage_command, capture_output=True, text=True)
        
        try:
            # Force reload to include the invalid scanner
            ScannerManager.reload()
            
            # Verify that other scanners still work
            manager = ScannerManager()
            self.assertIn("mock-scanner", manager.get_all_available_scanner_names())
        finally:
            # Cleanup
            uninstall_command = [
                "coverage",
                "run",
                "-m",
                "src.inspector_cli",
                "scanner",
                "uninstall",
                "invalid_scanner",
            ]
            subprocess.run(uninstall_command, capture_output=True, text=True)
            ScannerManager.reload()


if __name__ == "__main__":
    unittest.main()
