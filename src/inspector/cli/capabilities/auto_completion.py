import logging
import os
import sys
import shutil
import re
from logging import Logger
from pathlib import Path

from .exceptions import (
    AutoCompletionNotFoundError,
    ShellConfigurationError,
)

logger: Logger = logging.getLogger(__name__)

SUPPORTED_SHELLS = {
    "bash": ".bashrc",
    "zsh": ".zshrc",
}

ARGCOMPLETE_CMD = "register-python-argcomplete inspector"


def _is_running_as_executable() -> bool:
    return getattr(sys, "frozen", False)


def _get_shell_config_file() -> tuple[Path, str]:
    shell = os.environ.get("SHELL", "").lower()
    shell_name = next((name for name in SUPPORTED_SHELLS if name in shell), None)

    if not shell_name:
        raise ShellConfigurationError(f"Unsupported shell: {shell}")

    return Path.home() / SUPPORTED_SHELLS[shell_name], shell_name


def _read_shell_config(config_file: Path) -> str:
    try:
        return config_file.read_text(encoding="UTF-8")
    except IOError as e:
        raise ShellConfigurationError(f"Unable to read shell config file: {str(e)}")


def _write_shell_config(config_file: Path, content: str):
    try:
        config_file.write_text(content, encoding="UTF-8", newline="\n")
    except IOError as e:
        raise ShellConfigurationError(f"Failed to write shell config: {str(e)}")


def is_auto_completion_installed() -> bool:
    try:
        config_file, _ = _get_shell_config_file()
        content = _read_shell_config(config_file)
        if _is_running_as_executable():
            check_str = f"{sys.executable} autocomplete show"
        else:
            check_str = ARGCOMPLETE_CMD
        return check_str in content
    except ShellConfigurationError:
        return False


def _install_auto_completion() -> str:
    logger.info("Setting up autocomplete")
    config_file, shell_name = _get_shell_config_file()
    logger.debug(f"Shell config file: {config_file}")

    if _is_running_as_executable():
        eval_str = f'eval "$({sys.executable} autocomplete show)"'
        check_str = f"{sys.executable} autocomplete show"
    else:
        executable_path = shutil.which("register-python-argcomplete")
        if not executable_path:
            raise ShellConfigurationError(
                "Could not find `register-python-argcomplete` in PATH."
            )
        eval_str = f'eval "$({executable_path} inspector)"'
        check_str = ARGCOMPLETE_CMD

    content = _read_shell_config(config_file)

    if check_str in content or eval_str in content:
        logger.info("Autocomplete already installed")
        return f"Auto-completion already set up in `~/{config_file.name}`"

    # If “inspector” isn’t on PATH, add an alias so the eval will find it
    if shutil.which("inspector") is None:
        # sys.argv[0] should be the path they invoked
        inspector_path = Path(sys.argv[0]).resolve()
        alias_line = f"alias inspector='{inspector_path}'"
        if alias_line not in content:
            content += (
                f"\n# make sure OpenZeppelin 'inspector' is callable\n{alias_line}"
            )

    # Now append the eval for argcomplete
    content += f"\n{eval_str}\n\n"
    _write_shell_config(config_file, content)

    success_message = (
        f"Auto-completion for inspector has been set up in `~/{config_file.name}`"
    )

    if shell_name == "zsh" and "compinit" not in content:
        success_message += (
            f"\nYou may need to add the following lines to the top of your `{config_file.name}`:\n\n"
            "autoload -Uz compinit\ncompinit"
        )

    success_message += (
        f"\nYou may need to restart your shell or run `source ~/{config_file.name}`"
    )

    logger.info("Successfully set up autocomplete")
    return success_message


def _uninstall_auto_completion() -> str:
    logger.info("Removing autocomplete configuration")
    config_file, _ = _get_shell_config_file()

    if not config_file.exists():
        raise ShellConfigurationError(
            f"Shell configuration file not found: {config_file}"
        )

    if not is_auto_completion_installed():
        raise AutoCompletionNotFoundError(
            f"No auto-completion configuration was found in `~/{config_file.name}`"
        )

    content = _read_shell_config(config_file)
    lines = content.splitlines()
    new_lines: list[str] = []
    skip_next_blank = False

    # same check_str as before
    if _is_running_as_executable():
        check_str = f"{sys.executable} autocomplete show"
    else:
        check_str = "register-python-argcomplete"

    # pattern to catch the alias you injected in install
    alias_re = re.compile(r"^alias\s+inspector=.*$")
    # optional comment you prepended
    comment_re = re.compile(r"^# make sure ['\"]inspector['\"] is callable$")

    for line in lines:
        # remove the argcomplete eval or register line
        if check_str in line or alias_re.match(line) or comment_re.match(line):
            logger.debug(f"Removing line: {line}")
            skip_next_blank = True
            continue

        # drop the blank line _after_ any removed line
        if skip_next_blank and not line.strip():
            skip_next_blank = False
            continue

        new_lines.append(line)

    _write_shell_config(config_file, "\n".join(new_lines))
    logger.info("Autocomplete config removed")
    return f"Auto-completion for inspector has been removed from `~/{config_file.name}`"
