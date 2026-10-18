"""Build the separate Aegis Core Windows setup executable."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_EXECUTABLE = ROOT / "dist" / "Aegis-Core.exe"
SETUP_EXECUTABLE = ROOT / "dist" / "Aegis-Core-Setup.exe"
ICON_PATH = ROOT / "icon.ico"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not APP_EXECUTABLE.is_file():
        raise FileNotFoundError(
            f"Existing application executable was not found: {APP_EXECUTABLE}"
        )
    if not ICON_PATH.is_file():
        raise FileNotFoundError(f"Application icon was not found: {ICON_PATH}")

    app_hash_before = sha256(APP_EXECUTABLE)
    work_root = ROOT / "build" / "installer"
    spec_root = work_root / "spec"
    work_path = work_root / "work"
    pyinstaller_command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--icon",
        str(ICON_PATH),
        "--name",
        "Aegis-Core-Setup",
        "--distpath",
        str(APP_EXECUTABLE.parent),
        "--workpath",
        str(work_path),
        "--specpath",
        str(spec_root),
        "--add-data",
        f"{APP_EXECUTABLE}{os.pathsep}payload",
        "--add-data",
        f"{ICON_PATH}{os.pathsep}payload",
        str(ROOT / "installer_setup.py"),
    ]
    subprocess.run(pyinstaller_command, cwd=ROOT, check=True)

    if not SETUP_EXECUTABLE.is_file():
        raise FileNotFoundError(f"PyInstaller did not create {SETUP_EXECUTABLE}")
    app_hash_after = sha256(APP_EXECUTABLE)
    if app_hash_before != app_hash_after:
        raise RuntimeError("The existing application executable changed during setup build.")

    print(f"Built installer: {SETUP_EXECUTABLE}")
    print(f"Preserved application: {APP_EXECUTABLE}")
    print(f"Application SHA-256: {app_hash_after}")


if __name__ == "__main__":
    main()
