from typing import Any
from dataclasses import dataclass, field


@dataclass
class Extra:
    """
    Additional metadata associated with an instance, including known metavariables
    and any other arbitrary key-value pairs.

    Attributes:
        metavars: Dictionary of known metavariable names and values.
        other: Dictionary of all other metadata fields.
    """

    metavars: dict[str, str] = field(default_factory=dict)
    other: dict[str, Any] = field(default_factory=dict)

    def __json__(self) -> dict:
        """
        Convert to a JSON-serializable dictionary.

        Returns:
            A dictionary with 'metavars' and, if present, 'other'.
        """
        result = {"metavars": self.metavars}
        if self.other:
            result["other"] = self.other
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Extra":
        """
        Construct an Extra object from a dictionary.

        Args:
            data: A dictionary containing 'metavars' and/or arbitrary other keys.

        Returns:
            An Extra instance.
        """
        known = dict(data)  # make a copy
        metavars = known.pop("metavars", {})
        # Everything else goes into 'other'
        return cls(metavars=metavars, other=known)
