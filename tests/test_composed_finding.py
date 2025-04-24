import unittest
from pathlib import Path
from inspector.response_expander import minimal_finding_to_finding
from inspector.composer.composed_finding import ComposedFinding
from inspector.models import (
    Extra,
    MinimalFinding,
    MinimalInstance,
)
from inspector.models._complete.finding import CompleteFinding
from inspector.models._complete.instance import CompleteInstance
from inspector.models._complete.location import Location, LocationPoint
from inspector.models._complete.extra import Extra as CompleteExtra
from inspector.source_code_manager import SourceCodeManager


class TestComposedFinding(unittest.TestCase):
    def setUp(self):
        # MinimalFinding with one instance
        minimal_finding = MinimalFinding(
            instances=[
                MinimalInstance(
                    path="tests/utils/files/NoIssues.sol",
                    offset_start=0,
                    offset_end=1,
                    extra=Extra(metavars={}),
                )
            ],
        )

        # Create SourceCodeManager and project_root for conversion
        self.scm = SourceCodeManager()
        self.project_root = Path(".")

        # Convert to Finding for ComposedFinding
        self.finding = minimal_finding_to_finding(
            minimal_finding, self.scm, self.project_root
        )

        self.metadata = {
            "report": {
                "tags": ["audit"],
                "template": {
                    "title": "Test Title",
                    "body": "Test body with $file_name",
                    "opening": "Test opening",
                    "closing": "Test closing",
                    "body-list-item-intro": "Test intro",
                },
            },
            "confidence": 3,
            "uid": "test-uid",
        }

    def test_basic_composition(self):
        """Test basic finding composition with minimal data."""
        finding = ComposedFinding(
            detector_id="test-id",
            finding=self.finding,
            metadata=self.metadata,
            project_root="",
        )

        self.assertEqual(finding.id, "test-id")
        self.assertEqual(finding.uid, "test-uid")
        self.assertEqual(finding.num_instances, 1)
        self.assertEqual(finding.num_files, 1)
        self.assertEqual(finding.num_lines, 1)
        self.assertEqual(finding.issue_categories, ["audit"])
        self.assertEqual(finding.severity, None)

    def test_multiple_instances(self):
        """Test finding composition with multiple instances."""
        minimal_finding = MinimalFinding(
            instances=[
                MinimalInstance(
                    path="tests/utils/files/WETH9.sol",
                    offset_start=0,
                    offset_end=2,
                    extra=Extra(metavars={}),
                ),
                MinimalInstance(
                    path="tests/utils/files/WETHUpdate.sol",
                    offset_start=0,
                    offset_end=1,
                    extra=Extra(metavars={}),
                ),
            ],
        )

        # Convert to Finding for ComposedFinding
        finding = minimal_finding_to_finding(
            minimal_finding, self.scm, self.project_root
        )

        composed = ComposedFinding(
            detector_id="test-id",
            finding=finding,
            metadata=self.metadata,
            project_root="",
        )

        self.assertEqual(composed.num_instances, 2)
        self.assertEqual(composed.num_files, 2)
        self.assertEqual(composed.num_lines, 2)

    def test_template_variations(self):
        """Test different template configurations."""
        metadata = self.metadata.copy()
        metadata["report"]["template"].update(
            {
                "title-single-instance": "Single Instance Title",
                "title-multiple-instance": "Multiple Instance Title",
            }
        )

        finding = ComposedFinding(
            detector_id="test-id",
            finding=self.finding,
            metadata=metadata,
            project_root="",
        )
        self.assertEqual(finding.title, "Single Instance Title")

        # MinimalFinding with multiple instances in different files
        # Note: ComposedFinding uses _num_files to determine if it's single or multiple instance
        # so we need to use different files to get "multiple" instance behavior
        minimal_finding = MinimalFinding(
            instances=[
                MinimalInstance(
                    path="tests/utils/files/WETH9.sol",
                    offset_start=0,
                    offset_end=2,
                    extra=Extra(metavars={}),
                ),
                MinimalInstance(
                    path="tests/utils/files/WETHUpdate.sol",
                    offset_start=0,
                    offset_end=1,
                    extra=Extra(metavars={}),
                ),
            ],
        )

        # Convert to Finding for ComposedFinding
        finding = minimal_finding_to_finding(
            minimal_finding, self.scm, self.project_root
        )
        composed = ComposedFinding(
            detector_id="test-id", finding=finding, metadata=metadata, project_root=""
        )
        self.assertEqual(composed.title, "Multiple Instance Title")

    def test_instance_enumeration(self):
        """Test instance enumeration logic. If the report has a guidance tag
        or body-list-item-always, the instances should be enumerated."""
        metadata = self.metadata.copy()
        metadata["report"]["tags"] = ["guidance"]
        finding = ComposedFinding(
            detector_id="test-id",
            finding=self.finding,
            metadata=metadata,
            project_root="",
        )
        self.assertTrue(finding._enumerate_instances)

        # Test with body-list-item-always
        metadata = self.metadata.copy()
        metadata["report"]["template"]["body-list-item-always"] = "Always show"
        finding = ComposedFinding(
            detector_id="test-id",
            finding=self.finding,
            metadata=metadata,
            project_root="",
        )
        self.assertTrue(finding._enumerate_instances)

    def test_text_generation(self):
        """Test text generation methods."""
        finding = ComposedFinding(
            detector_id="test-id",
            finding=self.finding,
            metadata=self.metadata,
            project_root="",
        )

        # Test full text
        full_text = finding.get_full_text()
        self.assertIn("Test opening", full_text)
        self.assertIn("Test body with NoIssues.sol", full_text)
        self.assertIn("Test closing", full_text)

        # Test JSON text
        json_text = finding.get_text_json()
        self.assertEqual(json_text["title"], "Test Title")
        self.assertEqual(json_text["opening"], "Test opening")
        self.assertEqual(json_text["body"], "Test body with NoIssues.sol")
        self.assertEqual(json_text["closing"], "Test closing")
        self.assertEqual(len(json_text["instances"]), 1)

    def test_complete_finding_multiple_instances(self):
        """Test ComposedFinding with a CompleteFinding object with multiple instances."""
        # Create a CompleteFinding with multiple instances
        complete_finding = CompleteFinding(
            instances=[
                CompleteInstance(
                    location=Location(
                        path=Path("tests/utils/files/WETH9.sol"),
                        start=LocationPoint(line=10, col=1, offset=100),
                        end=LocationPoint(line=12, col=10, offset=150),
                    ),
                    lines=["line 10", "line 11", "line 12"],
                    fixes=["Fix suggestion 1"],
                    extra=CompleteExtra(metavars={"var": "value1"}),
                ),
                CompleteInstance(
                    location=Location(
                        path=Path("tests/utils/files/WETHUpdate.sol"),
                        start=LocationPoint(line=20, col=1, offset=200),
                        end=LocationPoint(line=22, col=10, offset=250),
                    ),
                    lines=["line 20", "line 21", "line 22"],
                    fixes=["Fix suggestion 2"],
                    extra=CompleteExtra(metavars={"var": "value2"}),
                ),
            ],
            impacted={
                "tests/utils/files/WETH9.sol": 1,
                "tests/utils/files/WETHUpdate.sol": 1,
            },
            lines=["line 10", "line 11", "line 12", "line 20", "line 21", "line 22"],
            fixes=["Project-wide fix 1", "Project-wide fix 2"],
        )

        composed = ComposedFinding(
            detector_id="test-id",
            finding=complete_finding,
            metadata=self.metadata,
            project_root="",
        )

        self.assertEqual(composed.num_instances, 2)
        self.assertEqual(composed.num_files, 2)
        self.assertEqual(composed.num_lines, 6)  # 3 lines per instance

    def test_complete_finding_with_metavars(self):
        """Test ComposedFinding with a CompleteFinding object that has metavariables."""
        # Create a CompleteFinding with metavariables
        complete_finding = CompleteFinding(
            instances=[
                CompleteInstance(
                    location=Location(
                        path=Path("tests/utils/files/NoIssues.sol"),
                        start=LocationPoint(line=10, col=1, offset=100),
                        end=LocationPoint(line=12, col=10, offset=150),
                    ),
                    lines=["line 10", "line 11", "line 12"],
                    fixes=[],
                    extra=CompleteExtra(
                        metavars={"function_name": "transfer", "amount": "100"}
                    ),
                )
            ],
            impacted={"tests/utils/files/NoIssues.sol": 1},
            lines=["line 10", "line 11", "line 12"],
            fixes=[],
        )

        # Add a template that uses metavariables
        metadata = self.metadata.copy()
        metadata["report"]["template"][
            "body"
        ] = "Test body with $file_name\n\nFunction: $function_name\nAmount: $amount"

        composed = ComposedFinding(
            detector_id="test-id",
            finding=complete_finding,
            metadata=metadata,
            project_root="",
        )

        # Test that metavariables are included in the text
        full_text = composed.get_full_text()
        self.assertIn("Function: transfer", full_text)
        self.assertIn("Amount: 100", full_text)


if __name__ == "__main__":
    unittest.main()
