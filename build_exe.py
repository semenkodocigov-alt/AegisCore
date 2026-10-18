"""Build the Aegis Core one-file Windows application and Desktop shortcut."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
ICON_PATH = ROOT / "icon.ico"
ICON_SIZES = [(16, 16), (32, 32), (48, 48), (256, 256)]


def find_app_image() -> Path:
    candidates: list[Path] = []
    user_profile = Path(os.environ.get("USERPROFILE", Path.home()))
    candidates.append(user_profile / "Desktop")
    for one_drive in (os.environ.get("OneDrive"), str(user_profile / "OneDrive")):
        if one_drive:
            candidates.append(Path(one_drive) / "Desktop")
    candidates.append(ROOT)

    seen: set[Path] = set()
    for directory in candidates:
        normalized = directory.resolve()
        if normalized in seen:
            continue
        seen.add(normalized)
        if not normalized.is_dir():
            continue
        for extension in (".png", ".jpg", ".jpeg"):
            image_path = normalized / f"ACP{extension}"
            if image_path.is_file():
                return image_path
            image_path = normalized / f"ACP{extension.upper()}"
            if image_path.is_file():
                return image_path

    locations = "\n".join(f"  - {path}" for path in seen)
    raise FileNotFoundError(
        "Could not find ACP.png, ACP.jpg, or ACP.jpeg on the Desktop or in the "
        f"project root. Searched:\n{locations}"
    )


def generate_icon(source: Path, destination: Path = ICON_PATH) -> None:
    with Image.open(source) as image:
        image = ImageOps.fit(
            image.convert("RGBA"),
            (max(image.width, image.height),) * 2,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        image.save(destination, format="ICO", sizes=ICON_SIZES)


def run_frontend_build() -> None:
    frontend_dir = ROOT / "frontend"
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm is None:
        raise FileNotFoundError("npm was not found; install Node.js to build the frontend.")

    def run_npm(*arguments: str) -> None:
        environment = os.environ.copy()
        environment["PATH"] = (
            str(Path(npm).parent) + os.pathsep + environment.get("PATH", "")
        )
        command = [Path(npm).name, *arguments]
        if os.name == "nt" and Path(npm).suffix.lower() in {".cmd", ".bat"}:
            command = ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(command)]
        subprocess.run(command, cwd=frontend_dir, env=environment, check=True)

    if not (frontend_dir / "node_modules").is_dir():
        run_npm("install")
    run_npm("run", "build")

    if not (frontend_dir / "dist" / "index.html").is_file():
        raise FileNotFoundError("The frontend build did not produce frontend/dist/index.html.")


def build_executable() -> Path:
    executable_path = ROOT / "dist" / "Aegis-Core.exe"
    spec_directory = ROOT / "build"
    spec_directory.mkdir(parents=True, exist_ok=True)
    pyinstaller_command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--specpath",
        str(spec_directory),
        "--onefile",
        "--windowed",
        "--icon",
        str(ICON_PATH),
        "--name",
        "Aegis-Core",
        "--add-data",
        f"{ROOT / 'frontend' / 'dist'}{os.pathsep}frontend/dist",
        "--add-data",
        f"{ROOT / 'native_scanner.cpp'}{os.pathsep}.",
        "--collect-submodules",
        "webview",
        str(ROOT / "main.py"),
    ]
    subprocess.run(pyinstaller_command, cwd=ROOT, check=True)
    if not executable_path.is_file():
        raise FileNotFoundError(f"PyInstaller did not create {executable_path}.")
    return executable_path


def create_desktop_shortcut(executable_path: Path) -> None:
    if os.name != "nt":
        raise OSError("Creating a Windows Desktop shortcut is only supported on Windows.")

    script = (
        "$desktop = [Environment]::GetFolderPath('Desktop'); "
        "$shell = New-Object -ComObject WScript.Shell; "
        "$shortcut = $shell.CreateShortcut((Join-Path $desktop 'Aegis-Core.lnk')); "
        f"$shortcut.TargetPath = '{str(executable_path).replace(chr(39), chr(39) * 2)}'; "
        f"$shortcut.WorkingDirectory = '{str(executable_path.parent).replace(chr(39), chr(39) * 2)}'; "
        f"$shortcut.IconLocation = '{str(executable_path).replace(chr(39), chr(39) * 2)},0'; "
        "$shortcut.Save()"
    )
    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        cwd=ROOT,
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main() -> None:
    source_image = find_app_image()
    print(f"Using app artwork: {source_image}")
    generate_icon(source_image)
    print(f"Generated multi-resolution icon: {ICON_PATH}")
    run_frontend_build()
    executable_path = build_executable()
    create_desktop_shortcut(executable_path)
    print(f"Built executable: {executable_path}")
    print("Created Aegis-Core.lnk on the Windows Desktop.")


if __name__ == "__main__":
    main()
