from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LocationPoint:
    """
    Represents a specific point in a file (e.g., the start or end of a match).

    Attributes:
        col: Column number in the line (1-indexed).
        line: Line number in the file (1-indexed).
        offset: Character offset from the beginning of the file.
    """

    col: int = -1
    line: int = -1
    offset: int = -1

    @classmethod
    def from_dict(cls, data: dict) -> "LocationPoint":
        return cls(
            col=data.get("col", -1),
            line=data.get("line", -1),
            offset=data.get("offset", -1),
        )


@dataclass
class Position:
    """
    Represents a range within a file between two points.

    Attributes:
        start: Starting point.
        end: Ending point.
    """

    start: LocationPoint
    end: LocationPoint


@dataclass
class Location:
    """
    Describes where a code issue is located within a file.

    Attributes:
        path: Path to the file (relative or absolute).
        start: Start point of the issue.
        end: End point of the issue.
    """

    path: Path = field(default_factory=Path)
    start: LocationPoint = field(default_factory=lambda: LocationPoint(0, 0, 0))
    end: LocationPoint = field(default_factory=lambda: LocationPoint(0, 0, 0))

    @property
    def position(self) -> Position:
        """
        Return a Position from the start and end points.

        Returns:
            A Position instance.
        """
        return Position(self.start, self.end)

    def set_start_location(self, col: int, line: int, offset: int) -> None:
        """
        Set the start location.

        Args:
            col: Column number (1-indexed).
            line: Line number (1-indexed).
            offset: Character offset.
        """
        self.start = LocationPoint(col, line, offset)

    def set_end_location(self, col: int, line: int, offset: int) -> None:
        """
        Set the end location.

        Args:
            col: Column number (1-indexed).
            line: Line number (1-indexed).
            offset: Character offset.
        """
        self.end = LocationPoint(col, line, offset)

    def __json__(self) -> dict:
        """
        Convert to a JSON-serializable dictionary.

        Returns:
            A dictionary with path and position data.
        """
        return {
            "path": str(self.path),
            "position": {
                "start": {
                    "col": self.start.col,
                    "line": self.start.line,
                    "offset": self.start.offset,
                },
                "end": {
                    "col": self.end.col,
                    "line": self.end.line,
                    "offset": self.end.offset,
                },
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        return cls(
            path=Path(data["path"]),
            start=LocationPoint.from_dict(data["start"]),
            end=LocationPoint.from_dict(data["end"]),
        )
