from dataclasses import dataclass, field


@dataclass
class IssueTemplate:
    """Template for generating finding reports with various formatting options."""

    title: str = ""
    opening: str = ""
    body: str = ""
    body_single_file_single_instance: str = ""
    body_single_file_multiple_instance: str = ""
    body_multiple_file_multiple_instance: str = ""
    body_list_item_intro: str = ""
    body_list_item: str = ""
    body_list_item_single_file: str = ""
    body_list_item_multiple_file: str = ""
    closing: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "IssueTemplate":
        """Create template from a dictionary with hyphenated keys."""
        return cls(
            title=data.get("title", ""),
            opening=data.get("opening", ""),
            body=data.get("body", ""),
            body_single_file_single_instance=data.get(
                "body-single-file-single-instance", ""
            ),
            body_single_file_multiple_instance=data.get(
                "body-single-file-multiple-instance", ""
            ),
            body_multiple_file_multiple_instance=data.get(
                "body-multiple-file-multiple-instance", ""
            ),
            body_list_item_intro=data.get("body-list-item-intro", ""),
            body_list_item=data.get("body-list-item", ""),
            body_list_item_single_file=data.get("body-list-item-single-file", ""),
            body_list_item_multiple_file=data.get("body-list-item-multiple-file", ""),
            closing=data.get("closing", ""),
        )


@dataclass
class IssueReport:
    """Container for rule report data including severity, tags, and template."""

    severity: int = 0
    tags: list[str] = field(default_factory=list)
    template: IssueTemplate = field(default_factory=IssueTemplate)

    @classmethod
    def from_dict(cls, data: dict) -> "IssueReport":
        """Create IssueReport from a dictionary."""
        return cls(
            severity=data.get("severity", 0),
            tags=data.get("tags", []),
            template=IssueTemplate.from_dict(data.get("template", {})),
        )
