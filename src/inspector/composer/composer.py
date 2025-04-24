import json

from .composed_finding import ComposedFinding
from ..models._complete.detector_response import CompleteDetectorResponse


class FindingComposer:
    """
    Composes human-readable findings from detector responses.
    """

    def __init__(
        self,
        detector_response: dict[str, CompleteDetectorResponse],
        project_root: str = "",
        absolute_paths: bool = False,
    ):
        self._detector_response = detector_response
        self._project_root = project_root
        self._composed_findings: list[ComposedFinding] = []
        self._failed_detectors: list[str] = []
        self._absolute_paths: bool = absolute_paths

    def compose(self) -> None:
        """
        Compose all findings from detector responses.
        Populates internal composed findings and failed detectors.
        """
        self._composed_findings.clear()
        self._failed_detectors.clear()
        for detector_id, response in self._detector_response.items():
            if getattr(response, "findings", None):
                self._composed_findings.extend(
                    ComposedFinding(
                        detector_id=detector_id,
                        finding=finding,
                        metadata=response.metadata,
                        project_root=self._project_root,
                        absolute_paths=self._absolute_paths,
                    )
                    for finding in response.findings
                )
            elif getattr(response, "errors", None):
                self._failed_detectors.append(detector_id)

    def get_findings(self) -> list[ComposedFinding]:
        """
        Return the list of composed findings.
        """
        return self._composed_findings

    def render(self, out_format: str = "md") -> tuple[str | list[dict], int]:
        """
        Render composed findings into the specified format.

        Args:
            out_format (str): The output format, "md" or "json".

        Returns:
            Tuple of the rendered content and number of findings.
        """
        # Ensure findings are composed before rendering
        if not self._composed_findings and not self._failed_detectors:
            self.compose()

        findings = self.get_findings()
        if out_format == "json":
            return self._render_as_json(findings)
        return self._render_as_markdown(findings)

    def _render_as_markdown(self, findings: list[ComposedFinding]) -> tuple[str, int]:
        if not findings:
            return "\n🥳 No issues to report.", 0

        lines = []
        for finding in findings:
            lines.append("\n\n")
            lines.append(finding.get_full_text())

        if self._failed_detectors:
            lines.append("\n# Rule Execution Failures 😞\n")
            lines.extend(f"- The `{rule}` rule.\n" for rule in self._failed_detectors)
            lines.append("\nPlease check these manually.\n")

        return "".join(lines), len(findings)

    def _render_as_json(self, findings: list[ComposedFinding]) -> tuple[str, int]:
        results = [
            {
                "detector-id": finding.id,
                "detector-uid": finding.uid,
                "severity": finding.severity,
                "tags": finding.issue_categories,
                "text": finding.get_text_json(),
            }
            for finding in findings
        ]

        payload = {
            "findings": results,
            "failures": self._failed_detectors,
        }

        return json.dumps(payload, indent=2), len(results)
