from enum import Enum, auto


class ScannerType(Enum):
    """
    Enum representing the different types of scanners supported by Inspector.

    Attributes:
        PYTHON: A scanner implemented as a Python package with pyproject.toml
        EXECUTABLE: A scanner implemented as an executable file
        UNKNOWN: Scanner of unknown type
    """

    UNKNOWN = auto()
    PYTHON = auto()
    EXECUTABLE = auto()

    def __str__(self):
        """String representation of the scanner type."""
        return self.name.lower()

    @classmethod
    def _missing_(cls, value):
        """
        Handle missing enum values - allows direct string conversion.
        This is called when an enum is constructed with a value that isn't a member.
        """
        if isinstance(value, str):
            # Try to match case-insensitive string to enum
            for member in cls:
                if member.name.lower() == value.lower():
                    return member
            return cls.UNKNOWN
        return None
