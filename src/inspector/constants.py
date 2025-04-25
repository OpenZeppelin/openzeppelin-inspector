from pathlib import Path


def find_project_root(start_path: Path) -> Path:
    """Find the project root by looking for pyproject.toml"""
    current = start_path
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return start_path


# Root paths
PATH_INSPECTOR_ROOT: Path = Path(__file__).resolve().parent
PATH_PROJECT_ROOT: Path = find_project_root(PATH_INSPECTOR_ROOT)

# OpenZeppelin directories
PATH_USER_OPENZEPPELIN: Path = Path.home() / ".OpenZeppelin"
PATH_USER_INSPECTOR: Path = PATH_USER_OPENZEPPELIN / "inspector"
PATH_USER_INSPECTOR_SCANNERS: Path = PATH_USER_INSPECTOR / "scanners"
PATH_USER_INSPECTOR_SCANNERS_VENVS: Path = PATH_USER_INSPECTOR_SCANNERS / "venvs"
PATH_USER_INSPECTOR_SCANNERS_REGISTRY: Path = (
    PATH_USER_INSPECTOR_SCANNERS / "scanners.json"
)

# Log levels
LOG_LEVEL_DEFAULT_DEBUG_MODE = "debug"
LOG_LEVEL_DEFAULT = "critical"
