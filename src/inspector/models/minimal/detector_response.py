from dataclasses import dataclass, field

from .finding import MinimalFinding
from .error import Error


@dataclass
class MinimalDetectorResponse:
    """
    The minimal result of a single detector rule execution.

    Attributes:
        findings: List of MinimalFinding objects.
        errors: List of error messages encountered during execution.
    """

    findings: list[MinimalFinding] = field(default_factory=list)
    errors: list[Error] = field(default_factory=list)

    def __json__(self) -> dict:
        """
        Convert to a JSON-serializable dictionary.

        Returns:
            Dictionary representing the detector response.
        """
        return {
            "findings": [finding.__json__() for finding in self.findings],
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MinimalDetectorResponse":
        """
        Construct a MinimalDetectorResponse from a dictionary.

        Args:
            data: A dictionary with detector response data.

        Returns:
            A MinimalDetectorResponse object.
        """
        return cls(
            findings=[
                MinimalFinding.from_dict(finding_data)
                for finding_data in data.get("findings", [])
            ],
            errors=data.get("errors", []),
        )
