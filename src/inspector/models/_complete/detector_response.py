from dataclasses import dataclass, field
from typing import Any

from .error import Error
from .finding import CompleteFinding


@dataclass
class CompleteDetectorResponse:
    """
    Represents the result of running a single detector rule.

    Attributes:
        findings: The security or code issue found by this detector, if any
                  (generally there will be a single finding per detector).
        errors: Error encountered by this detector, if any.
        metadata: Arbitrary metadata associated with the detector execution,
                  such as execution time, rule version, etc.
    """

    findings: list[CompleteFinding] = field(default_factory=list)
    errors: list[Error] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __json__(self) -> dict:
        """
        Convert the detector response to a JSON-serializable dictionary.

        Returns:
            A dictionary containing the finding and error, if present.
        """
        return {
            "errors": [error.__json__() for error in self.errors],
            "findings": [finding.__json__() for finding in self.findings],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CompleteDetectorResponse":
        findings_data = data.get("findings", [])
        findings = (
            [CompleteFinding.from_dict(f) for f in findings_data]
            if findings_data
            else []
        )

        errors_data = data.get("errors", [])
        errors = [
            Error(message=e) if isinstance(e, str) else Error(**e) for e in errors_data
        ]

        metadata = data.get("metadata", {})

        return cls(
            findings=findings,
            errors=errors,
            metadata=metadata,
        )
