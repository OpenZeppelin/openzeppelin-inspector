from enum import Enum


class DetectorSeverities(Enum):
    """
    Enumeration of detector severity levels.

    Severity levels are ordered from lowest to highest impact:
    - INFO: Informational findings with no security impact
    - NOTE: Minor issues that should be noted but have minimal risk
    - LOW: Issues with low security impact
    - MEDIUM: Issues with moderate security impact
    - HIGH: Issues with significant security impact
    - CRITICAL: Severe issues requiring immediate attention
    """

    INFO = "info"
    NOTE = "note"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self) -> str:
        """Returns the string representation of the severity level."""
        return self.value

    def __repr__(self) -> str:
        """Returns the official enum member representation."""
        return f"{self.__class__.__name__}.{self.name}"

    @classmethod
    def from_string(cls, severity_str: str) -> "DetectorSeverities | None":
        """
        Convert a string to the corresponding severity enum.

        Args:
            severity_str: A lowercase or uppercase string matching a severity.

        Returns:
            A DetectorSeverities enum instance or None if invalid.
        """
        severity_str = severity_str.lower()
        for severity in cls:
            if severity.value == severity_str:
                return severity
        return None

    def to_dict(self) -> dict[str, str]:
        """
        Return a dictionary representation of the enum.

        Returns:
            Dictionary with 'name' and 'value' keys.
        """
        return {"name": self.name, "value": self.value}

    def __lt__(self, other):
        """
        Allow sorting by comparing severity level ranks.

        Args:
            other: Another DetectorSeverities enum member.

        Returns:
            True if this severity is lower than the other.
        """
        severity_order = {
            DetectorSeverities.INFO: 0,
            DetectorSeverities.NOTE: 1,
            DetectorSeverities.LOW: 2,
            DetectorSeverities.MEDIUM: 3,
            DetectorSeverities.HIGH: 4,
            DetectorSeverities.CRITICAL: 5,
        }

        return severity_order[self] < severity_order[other]
