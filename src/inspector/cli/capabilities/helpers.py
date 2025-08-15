import os
import subprocess
import enum
import logging
import shutil
import urllib.request, urllib.error
import zipfile
from logging import Logger
from pathlib import Path
from typing import Optional, Tuple

from ...constants import (
    PATH_USER_INSPECTOR_SCANNERS,
    PATH_USER_INSPECTOR_SCANNERS_VENVS,
)
from .exceptions import DependencyInstallationError, ExtractionError, DownloadError


logger: Logger = logging.getLogger(__name__)


def _get_scanner_paths(scanner_name: str) -> Tuple[Path, Path]:
    """Returns the installation and venv paths for a scanner."""
    scanner_install_dir = PATH_USER_INSPECTOR_SCANNERS / scanner_name
    scanner_venv_dir = PATH_USER_INSPECTOR_SCANNERS_VENVS / scanner_name
    return scanner_install_dir, scanner_venv_dir


def _remove_dir_or_link(path: Path) -> bool:
    """Removes a directory tree or a symlink. Returns True on success or if path doesn't exist."""
    if not path.exists():
        return True
    try:
        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except Exception as e:
        logger.error(f"Failed to remove path {path}: {e}")
        return False
    return True


def _get_pip_path(venv_path: Path) -> Path:
    # Construct the path to the pip executable within the venv
    if os.name == "nt":  # Windows
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:  # Linux, macOS, etc.
        pip_path = venv_path / "bin" / "pip"

    if not pip_path or not pip_path.exists():
        logger.error(f"Could not find pip executable at expected location: {pip_path}")
        raise DependencyInstallationError(
            f"Could not find pip executable in created venv: {venv_path}"
        )
    return pip_path


def _restore_pyproject_dependencies(
    req_path: Path, logger: Logger, pip_path: Optional[Path] = None
) -> None:
    """A wrapper that can restore unmanaged (pip) and managed (rye / uv) Python projects"""
    PIP_INSTALL_TIMEOUT = 600  # seconds (10 minutes)
    if pip_path:
        cmd = [
            str(pip_path),
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",  # Avoid potential caching issues
            "-r",
            str(req_path),
        ]
    else:
        cmd = ["rye", "sync", "-f"]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=PIP_INSTALL_TIMEOUT,
            encoding="utf-8",
            errors="replace",
            cwd=req_path,
        )
        logger.debug(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=PIP_INSTALL_TIMEOUT,
            encoding="utf-8",
            errors="replace",
        )
        logger.debug(f"pip install requirements output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"pip install requirements stderr:\n{result.stderr}")
        elif result.returncode == 0:
            logger.info(f"pip install requirements succeeded")
        else:
            logger.error(
                f"pip install requirements failed with code {result.returncode}"
            )
    except subprocess.CalledProcessError as e:
        raise DependencyInstallationError(
            f"Failed installing deps from {req_path.name}: {e.stderr or e.stdout}"
        )
    except subprocess.TimeoutExpired:
        raise DependencyInstallationError(
            f"Timeout installing deps from {req_path.name}"
        )
    except Exception as e:
        logger.error(f"Unexpected error installing requirements: {e}", exc_info=True)
        raise DependencyInstallationError(
            f"Unexpected error installing requirements from {req_path.name}: {str(e)}"
        ) from e


def _remove_existing_installation(scanner_name: str) -> bool:
    """Removes the scanner directory and venv directory if they exist. Returns True if all removals succeeded."""
    scanner_install_dir, scanner_venv_dir = _get_scanner_paths(scanner_name)
    logger.info(f"Removing existing installation files for scanner '{scanner_name}'")
    install_removed = _remove_dir_or_link(scanner_install_dir)
    venv_removed = _remove_dir_or_link(scanner_venv_dir)
    if not install_removed or not venv_removed:
        logger.error(
            f"Failed to completely remove existing installation files for '{scanner_name}'. Manual cleanup might be required."
        )
        return False
    return True


def _extract_zip(zip_path: Path, extract_to_dir: Path) -> None:
    """Extracts a zip file strictly to the target directory."""
    logger.debug(f"Extracting zip file {zip_path} to {extract_to_dir}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to_dir)
        logger.info(f"Successfully extracted {zip_path} to {extract_to_dir}")
    except zipfile.BadZipFile:
        raise ExtractionError(f"Invalid zip file: {zip_path}")
    except Exception as e:
        raise ExtractionError(f"Failed to extract zip file: {str(e)}")


def _download_remote_zip(url: str, target_zip_path: Path) -> None:
    """Downloads a zip file from a URL, showing progress."""
    logger.debug(f"Downloading scanner from {url} to {target_zip_path}")
    try:
        with urllib.request.urlopen(url) as response:
            file_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            print(
                f"Downloading scanner from {url}"
                + (f" ({file_size / 1024 / 1024:.1f} MB)" if file_size else "")
            )
            with open(target_zip_path, "wb") as out_file:
                block_size = 8192
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    if file_size:
                        print(
                            f"\rDownloaded {downloaded / 1024 / 1024:.1f} MB",
                            end="",
                            flush=True,
                        )
                if file_size:
                    print()
            logger.debug(f"Download completed: {downloaded} bytes")
    except urllib.error.URLError as e:
        raise DownloadError(f"Failed to download scanner: {str(e)}")
    except Exception as e:
        raise DownloadError(f"Unexpected error during download: {str(e)}")
