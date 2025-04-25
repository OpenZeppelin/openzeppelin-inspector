from dataclasses import dataclass, field

from inspector.models.issue_template import IssueReport


@dataclass
class DetectorMetadata:
    """Container for individual detector information."""

    id: str = ""
    uid: str = ""
    description: str = ""
    description_full: str = ""
    scanners: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    report: IssueReport = field(default_factory=IssueReport)

    @classmethod
    def from_dict(cls, data: dict) -> "DetectorMetadata":
        """Create DetectorMetadata from a dictionary."""
        return cls(
            id=data.get("id"),
            uid=data.get("uid"),
            description=data.get("description"),
            description_full=data.get("description-full"),  # handles hyphenated key
            scanners=data.get("scanners"),
            references=data.get("references"),
            report=IssueReport.from_dict(data.get("report", {})),
        )
