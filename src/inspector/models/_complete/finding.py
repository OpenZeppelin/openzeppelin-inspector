from dataclasses import dataclass, field

from .instance import CompleteInstance


@dataclass
class CompleteFinding:
    """
    A collection of one or more matched instances.

    Attributes:
        instances: List of Instance objects.
        impacted: Map of filenames to instance counts.
        lines: Matched source code lines.
        fixes: Suggested project-wide fixes.
    """

    instances: list[CompleteInstance] = field(default_factory=list)
    impacted: dict[str, int] = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)

    def add_instance(self, instance: CompleteInstance) -> None:
        """
        Add a new instance to the finding.

        Args:
            instance: The Instance to add.
        """
        self.instances.append(instance)

    def add_filename(self, filename: str) -> None:
        """
        Track the file impacted by an instance.

        Args:
            filename: The impacted file's name.
        """
        self.impacted[filename] = self.impacted.get(filename, 0) + 1

    def __json__(self) -> dict:
        """
        Convert to a JSON-serializable dictionary.

        Returns:
            Dictionary representation of the finding.
        """
        return {
            "impacted": self.impacted,
            "instances": [i.__json__() for i in self.instances],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CompleteFinding":
        return cls(
            instances=[
                CompleteInstance.from_dict(d) for d in data.get("instances", [])
            ],
            lines=data.get("lines", []),
            fixes=data.get("fixes", []),
        )
