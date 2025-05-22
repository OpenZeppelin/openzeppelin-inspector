from pathlib import Path
from string import Template
from typing import Optional, Any, Dict, List, Tuple

from ..models._complete.finding import CompleteFinding

DEFAULT_ISSUE_TITLE = "An issue"
DEFAULT_INSTANCE_TEXT = (
    "* On [line $instance_line]($instance_line_link) of [`$file_name`]($file_path)"
)
DEFAULT_ITEM_INTRO = ""


class ComposedFinding:
    """
    Composes human-readable findings from raw analysis results, codebase context, and templates.
    """

    def __init__(
        self,
        detector_id: str,
        finding: CompleteFinding,
        metadata: dict,
        project_root: str,
        absolute_paths: bool = False,
    ):
        self._id = detector_id
        self._finding = finding
        self._metadata = metadata
        self._project_root = project_root
        self._absolute_paths = absolute_paths

        self._template = metadata["report"].get("template", {})
        self._uid = metadata.get("uid")
        self._issue_categories = metadata["report"]["tags"]
        self._severity = metadata["report"].get("severity")

        self._num_instances = len(finding.instances)
        self._num_files = len(finding.impacted)
        self._num_lines = sum(len(instance.lines) for instance in finding.instances)

        self._files_one_or_many = "single" if self._num_files == 1 else "multiple"
        self._instances_one_or_many = "single" if self._num_files == 1 else "multiple"

        # Composed output fields
        self.title: str = ""
        self.body: str = ""
        self.opening: Optional[str] = None
        self.closing: Optional[str] = None
        self.instances_intro: str = ""
        self.instances: List[str] = []
        self.instances_location: List[Any] = []

        # Caches
        self._full_text: str = ""
        self._brief_text: str = ""
        self._instance_list_text: str = ""

        self._compose_finding()

    @property
    def id(self) -> str:
        return self._id

    @property
    def uid(self) -> Optional[str]:
        return self._uid

    @property
    def num_instances(self) -> int:
        return self._num_instances

    @property
    def num_files(self) -> int:
        return self._num_files

    @property
    def num_lines(self) -> int:
        return self._num_lines

    @property
    def issue_categories(self) -> List[str]:
        return self._issue_categories

    @property
    def template(self) -> dict:
        return self._template

    @property
    def severity(self) -> Optional[str]:
        return self._severity

    def _compose_finding(self) -> None:
        """Main composition function that orchestrates the finding creation."""
        self._enumerate_instances = self._should_enumerate_instances()
        (
            self.instances,
            self.instances_location,
            replacements,
        ) = self._compose_instances()
        self.title = self._compose_title(replacements)
        self.body = self._compose_body(replacements)
        self.opening = self._compose_opening(replacements)
        self.closing = self._template.get("closing")
        self.instances_intro = self._template.get(
            "body-list-item-intro", DEFAULT_ITEM_INTRO
        )

    def _should_enumerate_instances(self) -> bool:
        """Determine if instances should be enumerated in the output."""
        always = self._template.get("body-list-item-always")
        multiple_instances = self._instances_one_or_many != "single"
        guidance_tag = (
                len(self.issue_categories) == 1 and "guidance" in self.issue_categories
        )
        return bool(always or multiple_instances or guidance_tag)

    def _compose_title(self, replacements: Dict[str, Any]) -> str:
        """Select the appropriate title template and apply replacements."""
        generic_title = self._template.get("title")
        title_key = f"title-{self._instances_one_or_many}-instance"
        instance_aware_title = self._template.get(title_key)
        title_template = instance_aware_title or generic_title or DEFAULT_ISSUE_TITLE
        return (
            Template(title_template).safe_substitute(replacements)
            if replacements
            else title_template
        )

    def _compose_instances(self) -> Tuple[List[str], List[Any], Dict[str, Any]]:
        """Compose formatted instance descriptions and collect replacements."""
        instances: List[str] = []
        locations: List[Any] = []
        replacements: Dict[str, Any] = {}

        for instance in self._sorted_instances():
            instance_text, instance_replacements = self._compose_single_instance(
                instance
            )
            if instance_text:
                instances.append(instance_text)
                locations.append(instance)
                replacements = instance_replacements  # Use last for global replacements

        return instances, locations, replacements

    def _sorted_instances(self) -> List[Any]:
        """Sort instances by file path and line number."""
        return sorted(
            self._finding.instances,
            key=lambda inst: (inst.location.path, inst.location.start.line),
        )

    def _resolved_path(self, path: str) -> str:
        """
        Return the resolved file path, either absolute or prefixed with './' for relative paths.
        """
        if self._absolute_paths:
            return str(Path(self._project_root) / path)

        return "." if not path or path == "." else f"./{path}"

    def _compose_single_instance(
        self, instance: Any
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Format a single finding instance."""
        file_name = instance.location.path.name
        file_path = self._resolved_path(instance.location.path)
        line_start = str(instance.location.start.line)
        line_end = str(instance.location.end.line)
        line_link = self._create_line_link(file_path, line_start, line_end)

        replacements = self._build_replacements(
            instance, file_name, file_path, line_start, line_end, line_link
        )
        instance_text = self._apply_instance_template(replacements)
        return instance_text, replacements

    @staticmethod
    def _create_line_link(file_path: str, line_start: str, line_end: str) -> str:
        """Create a link to the relevant line(s) in the file."""
        line_range = (
            f"{line_start}-{line_end}" if line_start != line_end else line_start
        )
        return f"{file_path}:{line_range}"

    def _build_replacements(
        self,
        instance: Any,
        file_name: str,
        file_path: str,
        line_start: str,
        line_end: str,
        line_link: str,
    ) -> Dict[str, Any]:
        """Build the replacements dictionary for templates."""
        replacements = {
            "file_name": file_name,
            "file_path": file_path,
            "instance_line": line_start,
            "instance_line_start": line_start,
            "instance_line_end": line_end,
            "instance_line_link": line_link,
            "instance_line_count": len(instance.lines),
            "codebase_path": self._resolved_path("."),
            "total_instances": self.num_instances,
            "total_files": self.num_files,
            "total_lines": self.num_lines,
        }
        # Add metavariables if present
        if getattr(instance, "extra", None) and getattr(
            instance.extra, "metavars", None
        ):
            replacements.update(instance.extra.metavars)
        return replacements

    def _apply_instance_template(self, replacements: Dict[str, Any]) -> Optional[str]:
        """Apply the appropriate template to a single instance."""
        item_template_key = f"body-list-item-{self._files_one_or_many}-file"
        template_str = (
            self._template.get("body-list-item-always")
            or self._template.get(item_template_key)
            or self._template.get("body-list-item")
            or DEFAULT_INSTANCE_TEXT
        )
        return (
            Template(template_str).safe_substitute(replacements)
            if template_str
            else None
        )

    def _compose_body(self, replacements: Dict[str, Any]) -> str:
        """Compose the main body text for the finding."""
        key = f"body-{self._files_one_or_many}-file-{self._instances_one_or_many}-instance"
        body_template = (
            self._template.get(key)
            or self._template.get("body")
            or self._template.get("body-list-item")
            or ""
        )
        return (
            Template(body_template).safe_substitute(replacements)
            if replacements
            else body_template
        )

    def _compose_opening(self, replacements: Dict[str, Any]) -> Optional[str]:
        """Compose the opening section, if present."""
        opening = self._template.get("opening")
        return Template(opening).safe_substitute(replacements) if opening else None

    def get_full_text(self) -> str:
        """Return the full, formatted finding text including severity and title."""
        if self._full_text:
            return self._full_text

        blocks: list[str] = []

        # Block 0: [severity] ### Title
        if self.title or self.severity:
            parts = []
            if self.severity:
                parts.append(f"[{self.severity}]")
            if self.title:
                parts.append(f"### {self.title}")
            blocks.append("\n".join(parts).strip())

        # Block 1+: rest of the composed sections
        if self.opening:
            blocks.append(self.opening.strip())

        if self.body:
            blocks.append(self.body.strip())

        if self._enumerate_instances and self.instances:
            if self.instances_intro:
                blocks.append(self.instances_intro.strip())
            blocks.append("\n".join(s.rstrip() for s in self.instances))

        if self.closing:
            blocks.append(self.closing.strip())

        self._full_text = "\n\n".join(blocks) + "\n"
        return self._full_text

    def get_text_json(self) -> Dict[str, Any]:
        """Return the finding as a structured dictionary."""
        res: Dict[str, Any] = {}
        if self.title:
            res["title"] = self.title
        if self.opening:
            res["opening"] = self.opening
        if self.body:
            res["body"] = self.body
        if self.instances:
            res["instances"] = [
                {
                    "content": content,
                    "location": instance.location.__json__(),
                }
                for content, instance in zip(self.instances, self.instances_location)
            ]
        if self.closing:
            res["closing"] = self.closing
        return res
