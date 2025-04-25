"""
Scanner Registry Management

This module provides in-memory management of scanner metadata, backed by a JSON file.
It allows adding, updating, removing, and querying scanners and their detectors,
as well as filtering based on tags and severities.

The registry is loaded once when the module is imported and can be reloaded on demand.
"""

import json
import logging
from pathlib import Path
from .constants import PATH_USER_INSPECTOR_SCANNERS_REGISTRY

_logger = logging.getLogger(__name__)

# Internal in-memory scanner registry.
_registry: dict[str, dict] = {}

# Path to the persistent registry JSON file.
_registry_path: Path = PATH_USER_INSPECTOR_SCANNERS_REGISTRY


def set_registry_path(path: Path) -> None:
    """
    Override the default registry file path.

    Useful for testing or alternative runtime environments.
    """
    global _registry_path
    _registry_path = path


def _load_registry() -> None:
    """
    Load the scanner registry from disk into memory.

    If the registry file does not exist or is invalid, an empty registry is loaded.
    """
    global _registry
    if not _registry_path.exists():
        _logger.debug(f"Scanner registry not found: {_registry_path}")
        _registry = {}
        return

    try:
        with open(_registry_path, "r") as f:
            _registry = json.load(f)
            _logger.debug(f"Loaded registry with {len(_registry)} scanners")
    except (json.JSONDecodeError, IOError) as e:
        _logger.error(f"Failed to read scanner registry: {e}")
        _registry = {}


def reload() -> None:
    """
    Reload the registry from disk.

    Clears and repopulates the in-memory registry from the latest saved state.
    """
    _logger.debug("Reloading scanner registry from disk")
    _load_registry()


def has_scanner(scanner_name: str) -> bool:
    """
    Check if a scanner with the given name exists in the registry.
    """
    return scanner_name in _registry


def add_or_update_scanner(scanner_name: str, scanner_entry: dict) -> None:
    """
    Add a new scanner or update an existing scanner in the registry.

    Immediately persists the change to disk.
    """
    _logger.debug(f"Adding/updating scanner '{scanner_name}' in registry")
    _registry[scanner_name] = scanner_entry

    try:
        _registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(_registry_path, "w") as f:
            json.dump(_registry, f, indent=2)
        _logger.info(f"Scanner '{scanner_name}' successfully added/updated")
    except IOError as e:
        _logger.error(f"Failed to save updated registry: {e}")
        raise


def remove_scanner(scanner_name: str) -> None:
    """
    Remove a scanner from the registry by name.

    No error is raised if the scanner does not exist.
    Immediately persists the change to disk.
    """
    if scanner_name not in _registry:
        _logger.debug(f"Scanner '{scanner_name}' not found. Nothing to remove.")
        return

    del _registry[scanner_name]
    _logger.debug(f"Removed scanner '{scanner_name}'")

    try:
        with open(_registry_path, "w") as f:
            json.dump(_registry, f, indent=2)
        _logger.debug(f"Saved updated registry to {_registry_path}")
    except IOError as e:
        _logger.error(f"Failed to save updated scanner registry: {e}")


def get_installed_scanner_names() -> list[str]:
    """
    Return a list of all installed scanner names.
    """
    return list(_registry.keys())


def get_scanner_info(scanner_name: str) -> dict | None:
    """
    Get metadata for a specific scanner by name.

    Returns None if the scanner is not found.
    """
    return _registry.get(scanner_name)


def get_installed_scanners_with_info() -> list[dict]:
    """
    Return a list of installed scanners with their full metadata, including their name.
    """
    return [
        {**info, "name": name}
        for name, info in _registry.items()
        if isinstance(info, dict)
    ]


def get_scanner_detector_info(scanner_name: str, detector_name: str) -> dict | None:
    """
    Return metadata for a specific detector under a specific scanner.

    Returns None if either the scanner or detector is not found.
    """
    scanner_info = _registry.get(scanner_name)
    if not scanner_info or "detectors" not in scanner_info:
        return None

    return scanner_info["detectors"].get(detector_name)


def get_all_detector_names() -> list[str]:
    """
    Return a sorted list of all detector names across all scanners.
    """
    detector_names = set()

    for scanner_info in _registry.values():
        if "detectors" in scanner_info and scanner_info["detectors"]:
            detector_names.update(scanner_info["detectors"].keys())

    return sorted(detector_names)


def get_detector_info(detector_name: str) -> dict | None:
    """
    Retrieve metadata for a detector by name, searching across all scanners.

    Returns None if not found.
    """
    for scanner_info in _registry.values():
        if (
            "detectors" in scanner_info
            and scanner_info["detectors"]
            and detector_name in scanner_info["detectors"]
        ):
            return scanner_info["detectors"][detector_name]
    return None


def get_tags_by_criteria(
    scanners: list[str] | None = None,
    severities: list[str] | None = None,
) -> list[dict]:
    """
    Retrieve tags grouped by detectors and scanners, optionally filtered by scanners and severities.

    Returns a sorted list of tag metadata.
    """
    scanner_names = scanners if scanners else get_installed_scanner_names()
    valid_scanner_names = [name for name in scanner_names if name in _registry]

    tag_info = {}

    for scanner_name in valid_scanner_names:
        scanner_info = _registry[scanner_name]
        if "detectors" not in scanner_info or not scanner_info["detectors"]:
            continue

        for detector_name, detector_info in scanner_info["detectors"].items():
            if "report" not in detector_info:
                continue

            if severities and (
                "severity" not in detector_info["report"]
                or detector_info["report"]["severity"] not in severities
            ):
                continue

            for tag in detector_info["report"].get("tags", []):
                if tag not in tag_info:
                    tag_info[tag] = {
                        "name": tag,
                        "detectors": [],
                        "scanners": [],
                        "detector_count": 0,
                        "scanner_count": 0,
                    }

                if detector_name not in tag_info[tag]["detectors"]:
                    tag_info[tag]["detectors"].append(detector_name)
                    tag_info[tag]["detector_count"] += 1

                if scanner_name not in tag_info[tag]["scanners"]:
                    tag_info[tag]["scanners"].append(scanner_name)
                    tag_info[tag]["scanner_count"] += 1

    return sorted(tag_info.values(), key=lambda x: x["name"])


def get_severities_by_criteria(
    scanners: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, list[str]]:
    """
    Retrieve severities mapped to detector names, optionally filtered by scanners and tags.
    """
    scanner_names = scanners if scanners else get_installed_scanner_names()
    valid_scanner_names = [name for name in scanner_names if name in _registry]

    severity_map = {}

    for scanner_name in valid_scanner_names:
        scanner_info = _registry[scanner_name]
        if "detectors" not in scanner_info or not scanner_info["detectors"]:
            continue

        for detector_name, detector_info in scanner_info["detectors"].items():
            if "report" not in detector_info:
                continue

            detector_tags = set(detector_info["report"].get("tags", []))
            if tags and not all(tag in detector_tags for tag in tags):
                continue

            severity = detector_info["report"].get("severity", "unknown")
            severity_map.setdefault(severity, []).append(detector_name)

    for severity in severity_map:
        severity_map[severity].sort()

    return severity_map


def get_detectors_by_criteria(
    scanners: list[str] | None = None,
    severities: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """
    Retrieve detectors matching the given scanners, severities, and/or tags.

    Returns a sorted list of detector metadata.
    """
    scanner_names = scanners if scanners else get_installed_scanner_names()
    valid_scanner_names = [name for name in scanner_names if name in _registry]

    matching_detectors = {}

    for scanner_name in valid_scanner_names:
        scanner_info = _registry[scanner_name]
        if "detectors" not in scanner_info or not scanner_info["detectors"]:
            continue

        for detector_name, detector_info in scanner_info["detectors"].items():
            if detector_name in matching_detectors:
                continue

            matches = True

            if severities and (
                "report" not in detector_info
                or "severity" not in detector_info["report"]
                or detector_info["report"]["severity"] not in severities
            ):
                matches = False
                continue

            if tags and (
                "report" not in detector_info
                or "tags" not in detector_info["report"]
                or not all(tag in detector_info["report"]["tags"] for tag in tags)
            ):
                matches = False
                continue

            if matches:
                matching_detectors[detector_name] = {
                    "name": detector_name,
                    "description": detector_info.get(
                        "description", "No description available"
                    ),
                    "severity": detector_info.get("report", {}).get(
                        "severity", "unknown"
                    ),
                    "tags": detector_info.get("report", {}).get("tags", []),
                    "scanner": scanner_name,
                }

    return sorted(matching_detectors.values(), key=lambda x: x["name"])


def get_scanners_by_criteria(
    detectors: list[str] | None = None,
    tags: list[str] | None = None,
    severities: list[str] | None = None,
) -> list[dict]:
    """
    Retrieve scanners matching the specified detectors, tags, or severities.

    Returns a sorted list of matching scanner metadata.
    """
    matching_scanners = []

    for scanner_name, scanner_info in _registry.items():
        if "detectors" not in scanner_info or not scanner_info["detectors"]:
            continue

        for detector_name, detector_info in scanner_info["detectors"].items():
            report = detector_info.get("report", {})

            if detectors and detector_name not in detectors:
                continue

            if tags:
                detector_tags = set(report.get("tags", []))
                if not all(tag in detector_tags for tag in tags):
                    continue

            if severities:
                if report.get("severity") not in severities:
                    continue

            matching_scanners.append({**scanner_info, "name": scanner_name})
            break

    return sorted(matching_scanners, key=lambda x: x["name"])


def get_scanner_full_detector_metadata(scanner_name: str) -> dict:
    """
    Return the full detectors dictionary for a given scanner.

    If the scanner or its detectors are not found, returns an empty dictionary.
    """
    scanner_info = _registry.get(scanner_name)
    if not scanner_info or "detectors" not in scanner_info:
        return {}
    return scanner_info["detectors"]


def get_scanner_version(scanner_name: str) -> str | None:
    """
    Get the version of a specific scanner by name.

    Returns None if the scanner is not found or version is not available.
    """
    scanner_info = _registry.get(scanner_name)
    if not scanner_info:
        return None
    return scanner_info.get("version")


def get_scanner_org(scanner_name: str) -> str | None:
    """
    Get the organization of a specific scanner by name.

    Returns None if the scanner is not found or organization is not available.
    """
    scanner_info = _registry.get(scanner_name)
    if not scanner_info:
        return None
    return scanner_info.get("org")


def get_scanner_description(scanner_name: str) -> str | None:
    """
    Get the description of a specific scanner by name.

    Returns None if the scanner is not found or description is not available.
    """
    scanner_info = _registry.get(scanner_name)
    if not scanner_info:
        return None
    return scanner_info.get("description")


def get_scanner_detector_names(scanner_name: str) -> list[str]:
    """
    Get a list of detector names for a specific scanner.

    Returns an empty list if the scanner is not found or has no detectors.
    """
    scanner_info = _registry.get(scanner_name)
    if not scanner_info or "detectors" not in scanner_info:
        return []
    return sorted(scanner_info["detectors"].keys())


# Load registry immediately on module import.
_load_registry()
