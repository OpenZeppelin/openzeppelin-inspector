from dataclasses import dataclass, field

from .instance import MinimalInstance


@dataclass
class MinimalFinding:
    """
    A minimal container for issue instances.

    Attributes:
        instances: List of MinimalInstance objects.
    """

    instances: list[MinimalInstance] = field(default_factory=list)

    def __json__(self) -> dict:
        """
        Convert to a JSON-serializable dictionary.

        Returns:
            Dictionary representing the minimal finding.
        """
        return {
            "instances": [instance.__json__() for instance in self.instances],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MinimalFinding":
        """
        Construct a MinimalFinding from a dictionary.

        Args:
            data: A dictionary with finding data.

        Returns:
            A MinimalFinding object.
        """
        return cls(
            instances=[
                MinimalInstance.from_dict(instance_data)
                for instance_data in data.get("instances", [])
            ]
        )
