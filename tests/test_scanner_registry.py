import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from inspector import scanner_registry


class TestScannerRegistry(TestCase):
    def setUp(self):
        """Set up test environment with a temporary registry file."""
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = Path(self.temp_dir) / "registry.json"
        scanner_registry.set_registry_path(self.registry_path)

        # Sample registry data
        self.sample_registry = {
            "scanner1": {
                "path": "/home/test/.OpenZeppelin/inspector/scanners/scanner1",
                "installed_at": "2025-04-01T00:00:00.000000",
                "version": "0.1",
                "type": "python",
                "org": "none",
                "detectors": {
                    "detector1": {
                        "description": "Test detector 1",
                        "report": {
                            "severity": "high",
                            "tags": ["security", "critical", "reportable"],
                        },
                    },
                    "detector2": {
                        "description": "Test detector 2",
                        "report": {
                            "severity": "medium",
                            "tags": ["gas", "optimization"],
                        },
                    },
                },
            },
            "scanner2": {
                "path": "/home/test/.OpenZeppelin/inspector/scanners/scanner2",
                "installed_at": "2025-04-01T00:00:00.000000",
                "version": "0.1",
                "type": "python",
                "org": "none",
                "detectors": {
                    "detector3": {
                        "description": "Test detector 3",
                        "report": {
                            "severity": "low",
                            "tags": ["security", "best-practices"],
                        },
                    }
                },
            },
        }

        # Create registry file with sample data
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump(self.sample_registry, f)

    def tearDown(self):
        """Clean up temporary files."""
        if self.registry_path.exists():
            os.remove(self.registry_path)
        os.rmdir(self.temp_dir)

    def test_load_registry(self):
        """Test loading registry from file."""
        scanner_registry._load_registry()
        self.assertEqual(scanner_registry._registry, self.sample_registry)

    def test_load_registry_corrupted(self):
        """Test loading corrupted registry file."""
        with open(self.registry_path, "w") as f:
            f.write("{invalid json}")
        with patch("logging.Logger.error") as mock_error:
            scanner_registry._load_registry()
            self.assertEqual(scanner_registry._registry, {})
            mock_error.assert_called_once()
            self.assertIn(
                "Failed to read scanner registry:", mock_error.call_args[0][0]
            )

    def test_has_scanner(self):
        """Test checking if scanner exists."""
        scanner_registry._load_registry()
        self.assertTrue(scanner_registry.has_scanner("scanner1"))
        self.assertFalse(scanner_registry.has_scanner("nonexistent"))

    def test_add_or_update_scanner(self):
        """Test adding and updating scanner."""
        new_scanner = {
            "detectors": {
                "detector4": {
                    "description": "New detector",
                    "report": {"severity": "high", "tags": ["security"]},
                }
            }
        }
        with patch("logging.Logger.debug") as mock_debug:
            scanner_registry.add_or_update_scanner("scanner3", new_scanner)
            mock_debug.assert_called_once_with(
                "Adding/updating scanner 'scanner3' in registry"
            )

        self.assertTrue(scanner_registry.has_scanner("scanner3"))
        self.assertEqual(scanner_registry.get_scanner_info("scanner3"), new_scanner)

    def test_remove_scanner(self):
        """Test removing scanner."""
        scanner_registry._load_registry()
        scanner_registry.remove_scanner("scanner1")
        self.assertFalse(scanner_registry.has_scanner("scanner1"))

    def test_get_installed_scanner_names(self):
        """Test getting list of installed scanner names."""
        scanner_registry._load_registry()
        names = scanner_registry.get_installed_scanner_names()
        self.assertEqual(set(names), {"scanner1", "scanner2"})

    def test_get_scanner_info(self):
        """Test getting scanner information."""
        scanner_registry._load_registry()
        info = scanner_registry.get_scanner_info("scanner1")
        self.assertEqual(info, self.sample_registry["scanner1"])

    def test_get_installed_scanners_with_info(self):
        """Test getting all scanners with their information."""
        scanner_registry._load_registry()
        scanners = scanner_registry.get_installed_scanners_with_info()
        self.assertEqual(len(scanners), 2)
        self.assertEqual(scanners[0]["name"], "scanner1")
        self.assertEqual(scanners[1]["name"], "scanner2")

    def test_get_all_detector_names(self):
        """Test getting all detector names."""
        scanner_registry._load_registry()
        detectors = scanner_registry.get_all_detector_names()
        self.assertEqual(set(detectors), {"detector1", "detector2", "detector3"})

    def test_get_detector_info(self):
        """Test getting detector information."""
        scanner_registry._load_registry()
        info = scanner_registry.get_detector_info("detector1")
        self.assertEqual(
            info, self.sample_registry["scanner1"]["detectors"]["detector1"]
        )

    def test_get_tags_by_criteria(self):
        """Test getting tags with various criteria."""
        scanner_registry._load_registry()

        # Test without filters
        tags = scanner_registry.get_tags_by_criteria()
        self.assertEqual(
            len(tags), 6
        )  # security, critical, gas, optimization, best-practices, reportable

        # Test with scanner filter
        tags = scanner_registry.get_tags_by_criteria(scanners=["scanner1"])
        self.assertEqual(
            len(tags), 5
        )  # security, critical, gas, optimization, reportable

        # Test with severity filter
        tags = scanner_registry.get_tags_by_criteria(severities=["high"])
        self.assertEqual(len(tags), 3)  # security, critical, reportable

    def test_get_severities_by_criteria(self):
        """Test getting severities with various criteria."""
        scanner_registry._load_registry()

        # Test without filters
        severities = scanner_registry.get_severities_by_criteria()
        self.assertEqual(set(severities.keys()), {"high", "medium", "low"})

        # Test with scanner filter
        severities = scanner_registry.get_severities_by_criteria(scanners=["scanner1"])
        self.assertEqual(set(severities.keys()), {"high", "medium"})

        # Test with tag filter
        severities = scanner_registry.get_severities_by_criteria(tags=["security"])
        self.assertEqual(set(severities.keys()), {"high", "low"})

    def test_get_detectors_by_criteria(self):
        """Test getting detectors with various criteria."""
        scanner_registry._load_registry()

        # Test without filters
        detectors = scanner_registry.get_detectors_by_criteria()
        self.assertEqual(len(detectors), 3)

        # Test with scanner filter
        detectors = scanner_registry.get_detectors_by_criteria(scanners=["scanner1"])
        self.assertEqual(len(detectors), 2)

        # Test with severity filter
        detectors = scanner_registry.get_detectors_by_criteria(severities=["high"])
        self.assertEqual(len(detectors), 1)

        # Test with tag filter
        detectors = scanner_registry.get_detectors_by_criteria(tags=["security"])
        self.assertEqual(len(detectors), 2)

    def test_get_scanners_by_criteria(self):
        """Test getting scanners with various criteria."""
        scanner_registry._load_registry()

        # Test without filters
        scanners = scanner_registry.get_scanners_by_criteria()
        self.assertEqual(len(scanners), 2)

        # Test with detector filter
        scanners = scanner_registry.get_scanners_by_criteria(detectors=["detector1"])
        self.assertEqual(len(scanners), 1)

        # Test with tag filter
        scanners = scanner_registry.get_scanners_by_criteria(tags=["security"])
        self.assertEqual(len(scanners), 2)

        # Test with severity filter
        scanners = scanner_registry.get_scanners_by_criteria(severities=["high"])
        self.assertEqual(len(scanners), 1)

    def test_reload_registry(self):
        """Test reloading the registry."""
        scanner_registry._load_registry()
        initial_registry = scanner_registry._registry.copy()

        # Modify registry in memory
        scanner_registry._registry["test_scanner"] = {"test": "data"}

        # Reload should restore original state
        scanner_registry.reload()
        self.assertEqual(scanner_registry._registry, initial_registry)

    def test_add_or_update_scanner_io_error(self):
        """Test handling IOError when adding/updating scanner."""
        scanner_registry._load_registry()

        # Make registry path read-only to force IOError
        os.chmod(self.registry_path, 0o444)

        with patch("logging.Logger.error") as mock_error:
            with self.assertRaises(IOError):
                scanner_registry.add_or_update_scanner("test_scanner", {"test": "data"})
            mock_error.assert_called_once()
            self.assertIn("Failed to save updated registry", mock_error.call_args[0][0])

        # Restore permissions
        os.chmod(self.registry_path, 0o666)

    def test_get_scanner_detector_info(self):
        """Test getting detector info for a specific scanner."""
        scanner_registry._load_registry()

        # Test existing detector
        info = scanner_registry.get_scanner_detector_info("scanner1", "detector1")
        self.assertEqual(
            info, self.sample_registry["scanner1"]["detectors"]["detector1"]
        )

        # Test non-existent scanner
        info = scanner_registry.get_scanner_detector_info("nonexistent", "detector1")
        self.assertIsNone(info)

        # Test non-existent detector
        info = scanner_registry.get_scanner_detector_info("scanner1", "nonexistent")
        self.assertIsNone(info)

    def test_get_scanner_full_detector_metadata(self):
        """Test getting full detector metadata for a scanner."""
        scanner_registry._load_registry()

        # Test existing scanner
        metadata = scanner_registry.get_scanner_full_detector_metadata("scanner1")
        self.assertEqual(metadata, self.sample_registry["scanner1"]["detectors"])

        # Test non-existent scanner
        metadata = scanner_registry.get_scanner_full_detector_metadata("nonexistent")
        self.assertEqual(metadata, {})

    def test_get_scanner_version(self):
        """Test getting scanner version."""
        scanner_registry._load_registry()

        # Test existing scanner
        version = scanner_registry.get_scanner_version("scanner1")
        self.assertEqual(version, "0.1")

        # Test non-existent scanner
        version = scanner_registry.get_scanner_version("nonexistent")
        self.assertIsNone(version)

    def test_get_scanner_org(self):
        """Test getting scanner organization."""
        scanner_registry._load_registry()

        # Test existing scanner
        org = scanner_registry.get_scanner_org("scanner1")
        self.assertEqual(org, "none")

        # Test non-existent scanner
        org = scanner_registry.get_scanner_org("nonexistent")
        self.assertIsNone(org)

    def test_get_scanner_description(self):
        """Test getting scanner description."""
        scanner_registry._load_registry()

        # Test existing scanner without description
        desc = scanner_registry.get_scanner_description("scanner1")
        self.assertIsNone(desc)

        # Test non-existent scanner
        desc = scanner_registry.get_scanner_description("nonexistent")
        self.assertIsNone(desc)

    def test_get_scanner_detector_names(self):
        """Test getting detector names for a scanner."""
        scanner_registry._load_registry()

        # Test existing scanner
        names = scanner_registry.get_scanner_detector_names("scanner1")
        self.assertEqual(set(names), {"detector1", "detector2"})

        # Test non-existent scanner
        names = scanner_registry.get_scanner_detector_names("nonexistent")
        self.assertEqual(names, [])

    def test_get_detector_info_not_found(self):
        """Test getting detector info when not found."""
        scanner_registry._load_registry()

        # Test non-existent detector
        info = scanner_registry.get_detector_info("nonexistent")
        self.assertIsNone(info)

    ## Edge cases
    def test_get_tags_by_criteria_edge_cases(self):
        """Test edge cases for get_tags_by_criteria."""
        scanner_registry._load_registry()

        # Test with invalid scanner
        tags = scanner_registry.get_tags_by_criteria(scanners=["nonexistent"])
        self.assertEqual(len(tags), 0)

        # Test with invalid severity
        tags = scanner_registry.get_tags_by_criteria(severities=["nonexistent"])
        self.assertEqual(len(tags), 0)

    def test_get_severities_by_criteria_edge_cases(self):
        """Test edge cases for get_severities_by_criteria."""
        scanner_registry._load_registry()

        # Test with invalid scanner
        severities = scanner_registry.get_severities_by_criteria(
            scanners=["nonexistent"]
        )
        self.assertEqual(severities, {})

        # Test with invalid tag
        severities = scanner_registry.get_severities_by_criteria(tags=["nonexistent"])
        self.assertEqual(severities, {})

    def test_get_detectors_by_criteria_edge_cases(self):
        """Test edge cases for get_detectors_by_criteria."""
        scanner_registry._load_registry()

        # Test with invalid scanner
        detectors = scanner_registry.get_detectors_by_criteria(scanners=["nonexistent"])
        self.assertEqual(detectors, [])

        # Test with invalid severity
        detectors = scanner_registry.get_detectors_by_criteria(
            severities=["nonexistent"]
        )
        self.assertEqual(detectors, [])

        # Test with invalid tag
        detectors = scanner_registry.get_detectors_by_criteria(tags=["nonexistent"])
        self.assertEqual(detectors, [])

    def test_get_scanners_by_criteria_edge_cases(self):
        """Test edge cases for get_scanners_by_criteria."""
        scanner_registry._load_registry()

        # Test with invalid detector
        scanners = scanner_registry.get_scanners_by_criteria(detectors=["nonexistent"])
        self.assertEqual(scanners, [])

        # Test with invalid tag
        scanners = scanner_registry.get_scanners_by_criteria(tags=["nonexistent"])
        self.assertEqual(scanners, [])

        # Test with invalid severity
        scanners = scanner_registry.get_scanners_by_criteria(severities=["nonexistent"])
        self.assertEqual(scanners, [])
