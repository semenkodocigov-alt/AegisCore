"""
Aegis Core - Запуск приложения
"""
import logging
import subprocess
import sys
import os
import tempfile
from pathlib import Path

from privileges import (
    get_gui_executable,
    hide_console_window,
    is_admin,
    request_admin_elevation,
)

hide_console_window()

logging.basicConfig(
    filename=Path(tempfile.gettempdir()) / "AegisCore-startup.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("aegis.startup")

# Добавляем текущую папку в путь
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def register_shell_context_menu():
    if os.name != 'nt':
        logger.info("Shell context menu registration is only available on Windows")
        return

    try:
        import winreg
        key_path = r"*\shell\AegisCoreScan"
        executable = get_gui_executable()
        if executable is None:
            logger.error("Cannot register shell scan: pythonw.exe was not found")
            return
        command_parts = [executable]
        if not getattr(sys, "frozen", False):
            command_parts.append(os.path.abspath(__file__))
        command = subprocess.list2cmdline([*command_parts, "%1"])

        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
            winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'Проверить с Aegis Core')
            winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, executable)

        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command") as cmd_key:
            winreg.SetValueEx(cmd_key, '', 0, winreg.REG_SZ, command)

        logger.info("Registered the Aegis Core shell context menu")
    except Exception as e:
        logger.exception("Could not register the Aegis Core shell context menu: %s", e)


def unregister_shell_context_menu():
    if os.name != 'nt':
        logger.info("Shell context menu registration is only available on Windows")
        return

    try:
        import winreg
        key_path = r"*\shell\AegisCoreScan\command"
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\AegisCoreScan")
        logger.info("Removed the Aegis Core shell context menu")
    except Exception as e:
        logger.exception("Could not remove the Aegis Core shell context menu: %s", e)


if __name__ == "__main__":
    try:
        if os.name == "nt" and not is_admin():
            if request_admin_elevation(sys.argv[1:]):
                raise SystemExit(0)
            logger.info("Continuing Aegis Core without administrator elevation")

        scan_target = None
        if len(sys.argv) > 1:
            first_arg = sys.argv[1]
            if first_arg == '--register-shell':
                register_shell_context_menu()
                sys.exit(0)
            elif first_arg == '--unregister-shell':
                unregister_shell_context_menu()
                sys.exit(0)
            elif os.path.exists(first_arg):
                scan_target = first_arg

        from desktop_app import AegisDesktopApp

        app = AegisDesktopApp(scan_target)
        app.run()
    except SystemExit:
        raise
    except Exception as e:
        logger.exception("Aegis Core failed to start")
        message = f"Aegis Core could not start. Details: {e}"
        if os.name == "nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, "Aegis Core", 0x10)
        else:
            logger.error("%s", message)