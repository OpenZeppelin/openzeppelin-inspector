from dataclasses import dataclass, field

from .extra import Extra


@dataclass
class MinimalInstance:
    """
    A minimal representation of a single code issue instance.

    Attributes:
        path: Path to the affected file (relative to project root).
        offset_start: Starting character offset of the issue.
        offset_end: Ending character offset of the issue.
        fixes: Optional list of suggested fixes.
        extra: Metadata including `metavars` and `other` (arbitrary fields).
    """

    path: str
    offset_start: int
    offset_end: int
    fixes: list[str] = field(default_factory=list)
    extra: Extra = field(default_factory=Extra)

    def __json__(self) -> dict:
        return {
            "path": self.path,
            "offset_start": self.offset_start,
            "offset_end": self.offset_end,
            "fixes": self.fixes,
            "extra": self.extra.__json__(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MinimalInstance":
        return cls(
            path=data["path"],
            offset_start=data["offset_start"],
            offset_end=data["offset_end"],
            fixes=data.get("fixes", []),
            extra=Extra.from_dict(data.get("extra", {})),
        )
