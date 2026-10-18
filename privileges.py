"""Windows privilege checks and UAC elevation support."""
from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def hide_console_window() -> None:
    """Hide the current process console without affecting GUI subsystem builds."""
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        kernel32.GetConsoleWindow.restype = ctypes.c_void_p
        window_handle = kernel32.GetConsoleWindow()
        if window_handle:
            user32.ShowWindow(window_handle, 0)
    except (AttributeError, OSError):
        logger.exception("Could not hide the attached console window")


def is_admin() -> bool:
    """Return whether this process has an elevated administrator token."""
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        logger.exception("Could not determine the current Windows privilege level")
        return False


def get_gui_executable() -> str | None:
    """Return the executable to use for a windowed Python launch."""
    if getattr(sys, "frozen", False):
        return sys.executable
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        return str(executable)
    pythonw = executable.with_name("pythonw.exe")
    return str(pythonw) if pythonw.is_file() else None


def request_admin_elevation(arguments: list[str]) -> bool:
    """Request UAC elevation for the current app; return whether relaunch started."""
    if os.name != "nt":
        return False

    executable = get_gui_executable()
    if executable is None:
        logger.error("Cannot request silent UAC elevation: pythonw.exe was not found")
        return False
    parameters = list(arguments)
    if not getattr(sys, "frozen", False):
        parameters.insert(0, os.path.abspath(sys.argv[0]))

    try:
        shell32 = ctypes.windll.shell32
        shell32.ShellExecuteW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_int,
        ]
        shell32.ShellExecuteW.restype = ctypes.c_void_p
        result = shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            subprocess.list2cmdline(parameters),
            os.path.dirname(os.path.abspath(sys.argv[0])),
            1,
        )
    except (AttributeError, OSError) as error:
        logger.warning("Windows UAC elevation request failed: %s", error)
        return False
    if not result or result <= 32:
        logger.warning("Windows declined or could not start the elevated Aegis Core process")
        return False
    return True
