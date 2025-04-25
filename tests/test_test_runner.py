import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

from inspector.detector_tester.test_runner import (
    _process_test_file,
    _extract_detector_findings,
    _compute_detector_accuracy,
    _remove_test_annotations,
    run_detector_tests,
    TestResult,
    Accuracy,
    analyze_results,
    format_coverage_table,
    format_differences_json,
    create_detector_test_report,
)


class TestTestRunner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.sol"
        self.test_file.write_text(
            """
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.0;

            contract Test {
                // :true-positive-here: test_detector
                function test() public {
                    // :true-negative-here: test_detector
                    // :disable-detector-test: test_detector
                    // :true-positive-here: test_detector
                }
            }
            """
        )

    def tearDown(self):
        import shutil
        from inspector.scanner_manager import ScannerManager

        shutil.rmtree(self.temp_dir)
        # Reset ScannerManager state
        ScannerManager._instance = None
        ScannerManager._initialized = False
        ScannerManager._scanners = {}
        ScannerManager._all_detector_names = ()
        ScannerManager._all_detector_metadata = {}
        ScannerManager._all_scanners = ()

    def test_process_test_file_with_unicode_error(self):
        """Test handling of Unicode decode errors in test file processing."""
        # Create a file with invalid UTF-8
        invalid_file = Path(self.temp_dir) / "invalid.sol"
        invalid_file.write_bytes(b"\x80invalid utf-8")

        result = _process_test_file(invalid_file, "test_detector")
        self.assertIsNone(result)

    def test_process_test_file_with_invalid_detector(self):
        """Test processing file with invalid detector name in annotations."""
        test_content = """
        // :true-positive-here: wrong_detector
        // :true-negative-here: wrong_detector
        """
        test_file = Path(self.temp_dir) / "wrong_detector.sol"
        test_file.write_text(test_content)

        result = _process_test_file(test_file, "test_detector")
        self.assertIsNotNone(result)
        self.assertEqual(len(result.true_positives), 0)
        self.assertEqual(len(result.true_negatives), 0)

    def test_extract_detector_findings_with_absolute_paths(self):
        """Test finding extraction with absolute paths."""
        mock_response = MagicMock()
        mock_finding = MagicMock()
        mock_instance = MagicMock(
            location=MagicMock(
                path=str(self.test_file.absolute()),
                position=MagicMock(start=MagicMock(line=5)),
            )
        )
        mock_finding.instances = [mock_instance]
        mock_response.findings = [mock_finding]

        findings = _extract_detector_findings(
            mock_response, {self.test_file}, Path(self.temp_dir)
        )
        self.assertEqual(findings[self.test_file], {5})

    def test_extract_detector_findings_with_relative_paths(self):
        """Test finding extraction with relative paths."""
        mock_response = MagicMock()
        mock_finding = MagicMock()
        mock_instance = MagicMock(
            location=MagicMock(
                path="test.sol", position=MagicMock(start=MagicMock(line=5))
            )
        )
        mock_finding.instances = [mock_instance]
        mock_response.findings = [mock_finding]

        findings = _extract_detector_findings(
            mock_response, {self.test_file}, Path(self.temp_dir)
        )
        self.assertEqual(findings[self.test_file], {5})

    def test_extract_detector_findings_with_invalid_path(self):
        """Test finding extraction with invalid file path."""
        mock_response = MagicMock()
        mock_response.finding.instances = [
            MagicMock(
                location=MagicMock(
                    path="nonexistent.sol", position=MagicMock(start=MagicMock(line=5))
                )
            )
        ]

        findings = _extract_detector_findings(
            mock_response, {self.test_file}, Path(self.temp_dir)
        )
        self.assertEqual(findings, {})

    def test_compute_detector_accuracy_edge_cases(self):
        """Test accuracy computation with edge cases."""
        # Test with no findings
        accuracy, diffs = _compute_detector_accuracy(
            {self.test_file: TestResult(true_positives=[5], true_negatives=[7])}, {}
        )
        self.assertEqual(accuracy.expected_positives, 1)
        self.assertEqual(accuracy.actual_positives, 0)
        self.assertEqual(accuracy.total_findings, 0)
        self.assertEqual(accuracy.false_positives, 0)
        self.assertEqual(accuracy.false_negatives, 1)

        # Test with extra findings
        accuracy, diffs = _compute_detector_accuracy(
            {self.test_file: TestResult(true_positives=[5], true_negatives=[7])},
            {self.test_file: {5, 8}},
        )
        self.assertEqual(accuracy.expected_positives, 1)
        self.assertEqual(accuracy.actual_positives, 1)
        self.assertEqual(accuracy.total_findings, 2)
        self.assertEqual(accuracy.false_positives, 1)
        self.assertEqual(accuracy.false_negatives, 0)

    def test_analyze_results(self):
        """Test analysis of scanner results."""
        expected = {
            "test_detector": {
                "test_project": {
                    self.test_file: TestResult(true_positives=[5], true_negatives=[7])
                }
            }
        }

        actual = {
            "scanner1": {"test_detector": {"test_project": {self.test_file: {5, 8}}}}
        }

        results = analyze_results(expected, actual)
        self.assertIn("scanner1", results)
        self.assertIn("test_detector", results["scanner1"].accuracy)
        self.assertEqual(
            results["scanner1"].accuracy["test_detector"].expected_positives, 1
        )
        self.assertEqual(
            results["scanner1"].accuracy["test_detector"].actual_positives, 1
        )
        self.assertEqual(
            results["scanner1"].accuracy["test_detector"].total_findings, 2
        )
        self.assertEqual(
            results["scanner1"].accuracy["test_detector"].false_positives, 1
        )
        self.assertEqual(
            results["scanner1"].accuracy["test_detector"].false_negatives, 0
        )

    def test_format_coverage_table(self):
        """Test coverage table formatting."""
        # Mock the ScannerManager.get_all_available_scanners method
        mock_scanner = MagicMock()
        mock_scanner.get_scanner_name.return_value = "scanner1"

        with patch(
            "inspector.detector_tester.test_runner.ScannerManager.get_all_available_scanners",
            return_value=[mock_scanner],
        ), patch(
            "inspector.detector_tester.test_runner.get_scanner_detector_names",
            return_value={"test_detector"},
        ):
            results = {
                "scanner1": MagicMock(
                    accuracy={
                        "test_detector": Accuracy(
                            expected_positives=2,
                            actual_positives=1,
                            total_findings=3,
                            false_positives=2,
                            false_negatives=1,
                        )
                    }
                )
            }

            table = format_coverage_table(results)
            self.assertIn("scanner1", table)
            self.assertIn("test_detector", table)
            self.assertIn("2", table)  # Expected & Extra Fields
            self.assertIn("3", table)  # Total findings
            self.assertIn("1", table)  # Missing
            self.assertIn("0.00%", table)  # Accuracy

    def test_format_differences_json(self):
        """Test differences JSON formatting."""
        results = {
            "scanner1": MagicMock(
                differences={
                    "test_detector": {
                        self.test_file: {"false_positives": [8], "false_negatives": [5]}
                    }
                }
            )
        }

        json_str = format_differences_json(results)
        self.assertIn("scanner1", json_str)
        self.assertIn("test_detector", json_str)
        self.assertIn("false_positives", json_str)
        self.assertIn("false_negatives", json_str)

    def test_remove_test_annotations_edge_cases(self):
        """Test annotation removal with edge cases."""
        test_content = """
        // :true-positive-here: test_detector // :true-negative-here: test_detector
        // :true-positive-here: test_detector :temporarily-invert-detector-test:
        """
        cleaned = _remove_test_annotations(test_content)
        self.assertNotIn(":true-positive-here:", cleaned)
        self.assertNotIn(":true-negative-here:", cleaned)
        self.assertNotIn(":temporarily-invert-detector-test:", cleaned)

    def test_run_detector_tests_with_no_detectors(self):
        """Test running tests with no available detectors."""
        with patch(
            "inspector.detector_tester.test_runner.ScannerManager"
        ) as mock_scanner, patch(
            "inspector.detector_tester.test_runner.DetectorTestManager"
        ) as mock_test_manager:
            # Mock ScannerManager to return no detectors
            mock_scanner.get_all_available_detector_names.return_value = []

            # Mock DetectorTestManager to return an empty test files dictionary
            mock_test_manager_instance = MagicMock()
            mock_test_manager_instance.get_test_projects.return_value = []
            mock_test_manager.return_value = mock_test_manager_instance

            output, has_failures, report = run_detector_tests(
                scanners=["test_scanner"], detectors=["test_detector"]
            )
            self.assertEqual(output, "No detectors available to test")
            self.assertTrue(has_failures)

    def test_create_detector_test_report(self):
        """Test creation of detector test report."""
        with patch("inspector.scanner_manager.ScannerManager") as mock_scanner_manager:
            results = {
                "scanner1": MagicMock(
                    accuracy={
                        "test_detector": Accuracy(
                            expected_positives=2,
                            actual_positives=1,
                            total_findings=3,
                            false_positives=2,
                            false_negatives=1,
                        )
                    },
                    differences={
                        "test_detector": {
                            self.test_file: {
                                "false_positives": [8],
                                "false_negatives": [5],
                            }
                        }
                    },
                )
            }

            report = create_detector_test_report(results, 1.5)
            self.assertIn("metadata", report)
            self.assertIn("scanners", report)
            self.assertIn("scanner1", report["scanners"])
            self.assertIn("accuracy_metrics", report["scanners"]["scanner1"])
            self.assertIn("differences", report["scanners"]["scanner1"])


if __name__ == "__main__":
    unittest.main()
