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


if __name__ == "__main__":
    unittest.main()
