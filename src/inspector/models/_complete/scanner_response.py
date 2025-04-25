from dataclasses import dataclass, field

from .detector_response import CompleteDetectorResponse
from .error import Error


@dataclass
class CompleteScannerResponse:
    """
    The main response structure returned by a scanner after a scan operation.

    Attributes:
        errors: A list of errors that occurred during the scan at the scanner level.
                These are not specific to any one detector.
        scanned: A list of file paths"," relative to project root, that the scanner attempted to scan.
        responses: A mapping of detector IDs to their corresponding DetectorResponse.
                            Each detector represents a rule or check applied during the scan.
    """

    errors: list[Error] = field(default_factory=list)
    scanned: list[str] = field(default_factory=list)
    responses: dict[str, CompleteDetectorResponse] = field(default_factory=dict)

    def __json__(self) -> dict:
        """
        Convert the scanner response into a JSON-serializable dictionary.

        Returns:
            A dictionary representing the full scanner response, with detector responses,
            error messages, and scanned files.
        """
        return {
            "errors": [error.__json__() for error in self.errors],
            "scanned": self.scanned,
            "responses": {
                detector_id: response.__json__()
                for detector_id, response in self.responses.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CompleteScannerResponse":
        return cls(
            errors=[
                Error(message=e) if isinstance(e, str) else Error(**e)
                for e in data.get("errors", [])
            ],
            scanned=data.get("scanned", []),
            responses={
                detector_id: CompleteDetectorResponse.from_dict(detector_data)
                for detector_id, detector_data in data.get("responses", {}).items()
            },
        )
