from dataclasses import dataclass, field

from .location import Location
from .extra import Extra


@dataclass
class CompleteInstance:
    """
    Represents a single instance of a code issue.

    Attributes:
        location: Location in the code.
        lines: Source code lines matched.
        fixes: Suggested fixes (if any).
        extra: Additional context or metadata.
    """

    location: Location | None = None
    lines: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
    extra: Extra = field(default_factory=Extra)

    def __json__(self) -> dict:
        """
        Convert to a JSON-serializable dictionary.

        Returns:
            Dictionary representation of the instance.
        """
        return {
            "location": self.location.__json__() if self.location else None,
            "lines": self.lines,
            "fixes": self.fixes,
            "extra": self.extra.__json__(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CompleteInstance":
        return cls(
            location=Location.from_dict(
                {
                    "path": data["file_path"],
                    "start": {"col": -1, "line": -1, "offset": data["offset_start"]},
                    "end": {"col": -1, "line": -1, "offset": data["offset_end"]},
                }
            ),
            lines=[],
            fixes=[],
            extra=Extra.from_dict(data.get("extras", {})),
        )
