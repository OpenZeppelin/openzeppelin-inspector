from dataclasses import dataclass, field

from .detector_response import MinimalDetectorResponse
from .error import Error


@dataclass
class MinimalScannerResponse:
    """
    Minimal scanner output after analyzing a set of files.

    Attributes:
        errors: Scanner-level error messages.
        scanned: List of scanned file paths (relative to project root).
        responses: Mapping from detector IDs to their results.
    """

    errors: list[Error] = field(default_factory=list)
    scanned: list[str] = field(default_factory=list)
    responses: dict[str, MinimalDetectorResponse] = field(default_factory=dict)

    def __json__(self) -> dict:
        """
        Convert to a JSON-serializable dictionary.

        Returns:
            Dictionary representing the scanner response.
        """
        return {
            "errors": self.errors,
            "scanned": self.scanned,
            "responses": {
                detector_id: response.__json__()
                for detector_id, response in self.responses.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MinimalScannerResponse":
        """
        Construct a MinimalScannerResponse from a dictionary.

        Args:
            data: A dictionary with scanner response data.

        Returns:
            A MinimalScannerResponse object.
        """
        return cls(
            errors=data.get("errors", []),
            scanned=data.get("scanned", []),
            responses={
                detector_id: MinimalDetectorResponse.from_dict(detector_data)
                for detector_id, detector_data in data.get(
                    "detector_responses", {}
                ).items()
            },
        )
