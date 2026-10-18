"""Standalone Tk installer for Aegis Core."""
from __future__ import annotations

import base64
import ctypes
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import winreg
from pathlib import Path
from tkinter import filedialog, messagebox

APP_NAME = "Aegis-Core"
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Aegis-Core"
BACKGROUND = "#09090b"
SURFACE = "#18181b"
SURFACE_HOVER = "#27272a"
TEXT = "#f4f4f5"
MUTED = "#a1a1aa"
ACCENT = "#76c7d4"
ERROR = "#f87171"

TRANSLATIONS = {
    "en": {
        "title": "Aegis Core Setup",
        "welcome_title": "Protection, ready when you are.",
        "welcome_body": "Install Aegis Core on this PC. Your existing files stay untouched; setup only places the app in the selected folder.",
        "location": "INSTALL LOCATION",
        "browse": "Browse",
        "shortcuts": "Create Desktop and Start Menu shortcuts",
        "install": "Install Aegis Core",
        "installing": "Installing Aegis Core…",
        "complete_title": "Aegis Core is ready.",
        "complete_body": "Installation finished successfully. You can launch the app now or open it later from your shortcuts.",
        "launch": "Launch Aegis Core",
        "finish": "Finish",
        "cancel": "Cancel",
        "step_prepare": "Preparing installation…",
        "step_copy": "Copying application files…",
        "step_shortcuts": "Creating shortcuts…",
        "step_registry": "Registering uninstall information…",
        "step_done": "Installation complete.",
        "choose_folder": "Choose installation folder",
        "confirm_replace": "Aegis-Core.exe already exists in this folder. Replace this app file? Other files will be left untouched.",
        "error_title": "Installation failed",
        "error_path": "Choose a valid installation folder.",
        "error_payload": "The installer package is missing Aegis-Core.exe or icon.ico.",
        "error_close": "Wait for installation to finish before closing setup.",
        "failed": "Setup could not complete:\n{}",
        "header": "AEGIS CORE  /  SETUP",
        "language": "RU",
    },
    "ru": {
        "title": "Установка Aegis Core",
        "welcome_title": "Защита готова к работе.",
        "welcome_body": "Установите Aegis Core на этот компьютер. Существующие файлы не затрагиваются — приложение будет помещено в выбранную папку.",
        "location": "ПАПКА УСТАНОВКИ",
        "browse": "Обзор",
        "shortcuts": "Создать ярлыки на рабочем столе и в меню «Пуск»",
        "install": "Установить Aegis Core",
        "installing": "Установка Aegis Core…",
        "complete_title": "Aegis Core готов к работе.",
        "complete_body": "Установка успешно завершена. Запустите приложение сейчас или откройте его позже с помощью ярлыка.",
        "launch": "Запустить Aegis Core",
        "finish": "Готово",
        "cancel": "Отмена",
        "step_prepare": "Подготовка установки…",
        "step_copy": "Копирование файлов приложения…",
        "step_shortcuts": "Создание ярлыков…",
        "step_registry": "Регистрация сведений для удаления…",
        "step_done": "Установка завершена.",
        "choose_folder": "Выберите папку установки",
        "confirm_replace": "В этой папке уже есть Aegis-Core.exe. Заменить файл приложения? Остальные файлы останутся без изменений.",
        "error_title": "Ошибка установки",
        "error_path": "Выберите допустимую папку для установки.",
        "error_payload": "В пакете установки отсутствует Aegis-Core.exe или icon.ico.",
        "error_close": "Дождитесь завершения установки, прежде чем закрывать окно.",
        "failed": "Не удалось завершить установку:\n{}",
        "header": "AEGIS CORE  /  УСТАНОВКА",
        "language": "EN",
    },
}


def resource_path(name: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    root = Path(bundle_root) if bundle_root else Path(__file__).resolve().parent
    payload_path = root / "payload" / name
    if payload_path.is_file():
        return payload_path
    return root / name


def ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def powershell(script: str) -> None:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def create_shortcuts(install_dir: Path) -> None:
    executable = install_dir / f"{APP_NAME}.exe"
    script = f"""
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$programs = Join-Path $env:APPDATA 'Microsoft\\Windows\\Start Menu\\Programs'
New-Item -ItemType Directory -Force -Path $programs | Out-Null
$targets = @(
    (Join-Path $desktop 'Aegis-Core.lnk'),
    (Join-Path $programs 'Aegis-Core.lnk')
)
foreach ($target in $targets) {{
    $link = $shell.CreateShortcut($target)
    $link.TargetPath = {ps_literal(str(executable))}
    $link.WorkingDirectory = {ps_literal(str(install_dir))}
    $link.IconLocation = {ps_literal(str(install_dir / "icon.ico"))}
    $link.Save()
}}
"""
    powershell(script)


def create_uninstaller(install_dir: Path) -> Path:
    uninstaller = install_dir / "uninstaller.bat"
    script = (
        "@echo off\r\n"
        "setlocal\r\n"
        'set "AEGIS_INSTALL_DIR=%~dp0"\r\n'
        'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Aegis-Core" /f >nul 2>&1\r\n'
        'start "" /b powershell.exe -NoProfile -WindowStyle Hidden -Command '
        '"Start-Sleep -Seconds 2; '
        "$desktop = [Environment]::GetFolderPath('Desktop'); "
        "$programs = Join-Path $env:APPDATA 'Microsoft\\Windows\\Start Menu\\Programs'; "
        "Remove-Item -LiteralPath (Join-Path $desktop 'Aegis-Core.lnk') -Force -ErrorAction SilentlyContinue; "
        "Remove-Item -LiteralPath (Join-Path $programs 'Aegis-Core.lnk') -Force -ErrorAction SilentlyContinue; "
        "Remove-Item -LiteralPath $env:AEGIS_INSTALL_DIR -Recurse -Force -ErrorAction SilentlyContinue\"\r\n"
        "endlocal\r\n"
    )
    uninstaller.write_text(script, encoding="utf-8")
    return uninstaller


def register_uninstall(install_dir: Path, uninstaller: Path) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Aegis Core")
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "2.5.0")
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Aegis Core")
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(install_dir / "icon.ico"))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller}"')


class InstallerWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.language = "en"
        self.messages = TRANSLATIONS[self.language]
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.installing = False
        self.target_progress = 0.0
        self.display_progress = 0.0
        self.root.overrideredirect(True)
        self.root.configure(bg=BACKGROUND)
        self.root.geometry(self.center_geometry(700, 540))
        self.root.minsize(640, 500)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _event: self.close())
        self.build_ui()
        self.root.after(60, self.process_events)
        self.root.after(16, self.animate_progress)

    def center_geometry(self, width: int, height: int) -> str:
        self.root.update_idletasks()
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def t(self, key: str) -> str:
        return self.messages[key]

    def drag(self, event: tk.Event) -> None:
        if event.widget is self.language_button or event.widget is self.close_button:
            return
        if os.name != "nt":
            return
        user32 = ctypes.windll.user32
        user32.ReleaseCapture.argtypes = []
        user32.ReleaseCapture.restype = ctypes.c_int
        user32.SendMessageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        ]
        user32.SendMessageW.restype = ctypes.c_ssize_t
        user32.ReleaseCapture()
        user32.SendMessageW(self.root.winfo_id(), 0x00A1, 2, 0)

    def build_ui(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

        self.root.title(self.t("title"))
        icon_path = resource_path("icon.ico")
        if icon_path.is_file():
            try:
                self.root.iconbitmap(str(icon_path))
            except tk.TclError:
                pass

        header = tk.Frame(self.root, bg=SURFACE, height=48, highlightthickness=1,
                          highlightbackground="#27272a")
        header.pack(fill="x")
        header.pack_propagate(False)
        header.bind("<Button-1>", self.drag)

        brand = tk.Label(header, text=self.t("header"), bg=SURFACE, fg=MUTED,
                         font=("Segoe UI", 9, "bold"), padx=20)
        brand.pack(side="left", fill="y")
        brand.bind("<Button-1>", self.drag)

        controls = tk.Frame(header, bg=SURFACE)
        controls.pack(side="right", padx=8, fill="y")
        self.language_button = self.make_button(
            controls, self.t("language"), self.toggle_language, compact=True
        )
        self.language_button.pack(side="left", padx=4, pady=7)
        self.close_button = self.make_button(controls, "×", self.close, compact=True)
        self.close_button.pack(side="left", padx=(4, 8), pady=7)

        self.content = tk.Frame(self.root, bg=BACKGROUND, padx=44, pady=36)
        self.content.pack(fill="both", expand=True)
        self.render_welcome()

    def make_button(
        self,
        parent: tk.Widget,
        text: str,
        command: object,
        *,
        primary: bool = False,
        compact: bool = False,
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=ACCENT if primary else SURFACE_HOVER,
            fg=BACKGROUND if primary else TEXT,
            activebackground="#91d7e1" if primary else "#3f3f46",
            activeforeground=BACKGROUND if primary else TEXT,
            disabledforeground="#71717a",
            relief="flat",
            borderwidth=0,
            padx=12 if compact else 18,
            pady=7 if compact else 11,
            cursor="hand2",
            font=("Segoe UI", 9 if compact else 10, "bold"),
        )
        return button

    def clear_content(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()

    def render_welcome(self) -> None:
        self.phase = "welcome"
        self.clear_content()
        tk.Label(self.content, text="A", bg=BACKGROUND, fg=ACCENT,
                 font=("Segoe UI", 31, "bold")).pack(anchor="w", pady=(0, 10))
        tk.Label(
            self.content,
            text=self.t("welcome_title"),
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI", 23, "bold"),
            wraplength=590,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            self.content,
            text=self.t("welcome_body"),
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 10),
            wraplength=580,
            justify="left",
        ).pack(anchor="w", pady=(0, 25))

        tk.Label(self.content, text=self.t("location"), bg=BACKGROUND, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 8))
        path_row = tk.Frame(self.content, bg=BACKGROUND)
        path_row.pack(fill="x")
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        self.path_value = tk.StringVar(value=str(local_app_data / "Programs" / APP_NAME))
        self.path_entry = tk.Entry(
            path_row,
            textvariable=self.path_value,
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#3f3f46",
            highlightcolor=ACCENT,
            font=("Segoe UI", 10),
        )
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 8))
        self.browse_button = self.make_button(path_row, self.t("browse"), self.browse)
        self.browse_button.pack(side="right")

        self.shortcuts_value = tk.BooleanVar(value=True)
        self.shortcuts_check = tk.Checkbutton(
            self.content,
            text=self.t("shortcuts"),
            variable=self.shortcuts_value,
            bg=BACKGROUND,
            fg=TEXT,
            activebackground=BACKGROUND,
            activeforeground=TEXT,
            selectcolor=SURFACE,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self.shortcuts_check.pack(anchor="w", pady=(17, 24))
        self.install_button = self.make_button(
            self.content, self.t("install"), self.begin_install, primary=True
        )
        self.install_button.pack(anchor="e")

    def render_installing(self) -> None:
        self.phase = "installing"
        self.clear_content()
        self.progress_title = tk.Label(
            self.content,
            text=self.t("installing"),
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI", 20, "bold"),
        )
        self.progress_title.pack(anchor="w", pady=(34, 20))
        self.step_label = tk.Label(
            self.content,
            text=self.t("step_prepare"),
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        self.step_label.pack(anchor="w", pady=(0, 12))
        self.progress_canvas = tk.Canvas(
            self.content, height=8, bg=SURFACE, highlightthickness=0, bd=0
        )
        self.progress_canvas.pack(fill="x")
        self.progress_rect = self.progress_canvas.create_rectangle(
            0, 0, 0, 8, fill=ACCENT, outline=""
        )
        self.percent_label = tk.Label(
            self.content, text="0%", bg=BACKGROUND, fg=MUTED,
            font=("Segoe UI", 9, "bold")
        )
        self.percent_label.pack(anchor="e", pady=(8, 0))
        self.installing = True
        self.close_button.configure(state="disabled")
        self.language_button.configure(state="disabled")

    def render_complete(self) -> None:
        self.phase = "complete"
        self.installing = False
        self.clear_content()
        tk.Label(self.content, text="✓", bg=BACKGROUND, fg=ACCENT,
                 font=("Segoe UI", 34, "bold")).pack(anchor="w", pady=(26, 12))
        tk.Label(
            self.content,
            text=self.t("complete_title"),
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI", 22, "bold"),
            wraplength=590,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            self.content,
            text=self.t("complete_body"),
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 10),
            wraplength=580,
            justify="left",
        ).pack(anchor="w", pady=(0, 30))
        buttons = tk.Frame(self.content, bg=BACKGROUND)
        buttons.pack(fill="x", side="bottom")
        self.make_button(buttons, self.t("finish"), self.root.destroy).pack(side="right")
        self.make_button(
            buttons, self.t("launch"), self.launch_app, primary=True
        ).pack(side="right", padx=(0, 8))
        self.close_button.configure(state="normal")
        self.language_button.configure(state="normal")

    def browse(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.root,
            title=self.t("choose_folder"),
            initialdir=self.path_value.get() or str(Path.home()),
            mustexist=False,
        )
        if selected:
            self.path_value.set(selected)

    def toggle_language(self) -> None:
        phase = self.phase
        self.language = "ru" if self.language == "en" else "en"
        self.messages = TRANSLATIONS[self.language]
        self.build_ui()
        if phase == "installing":
            self.render_installing()
        elif phase == "complete":
            self.render_complete()

    def begin_install(self) -> None:
        if self.installing:
            return
        raw_path = self.path_value.get().strip()
        try:
            target = Path(raw_path).expanduser()
            if not raw_path or target.exists() and not target.is_dir():
                raise ValueError
            target = target.resolve()
        except (OSError, RuntimeError, ValueError):
            messagebox.showerror(self.t("error_title"), self.t("error_path"), parent=self.root)
            return

        source_executable = resource_path(f"{APP_NAME}.exe")
        source_icon = resource_path("icon.ico")
        if not source_executable.is_file() or not source_icon.is_file():
            messagebox.showerror(
                self.t("error_title"), self.t("error_payload"), parent=self.root
            )
            return

        existing = target / f"{APP_NAME}.exe"
        if existing.exists() and not messagebox.askyesno(
            self.t("title"), self.t("confirm_replace"), parent=self.root
        ):
            return

        self.install_target = target
        self.create_shortcuts_value = self.shortcuts_value.get()
        self.render_installing()
        threading.Thread(target=self.install_worker, daemon=True).start()

    def install_worker(self) -> None:
        try:
            target = self.install_target
            self.events.put(("step", ("step_copy", 5)))
            target.mkdir(parents=True, exist_ok=True)
            executable_source = resource_path(f"{APP_NAME}.exe")
            executable_target = target / f"{APP_NAME}.exe"
            temporary_executable = target / f".{APP_NAME}.exe.installing"
            total_size = max(1, executable_source.stat().st_size)
            copied = 0
            try:
                with executable_source.open("rb") as source, temporary_executable.open("wb") as output:
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                        copied += len(chunk)
                        percent = 5 + int(75 * copied / total_size)
                        self.events.put(("progress", percent))
                os.replace(temporary_executable, executable_target)
            finally:
                temporary_executable.unlink(missing_ok=True)

            shutil.copy2(resource_path("icon.ico"), target / "icon.ico")
            self.events.put(("step", ("step_shortcuts", 84)))
            if self.create_shortcuts_value:
                create_shortcuts(target)

            self.events.put(("step", ("step_registry", 92)))
            uninstaller = create_uninstaller(target)
            register_uninstall(target, uninstaller)
            self.events.put(("complete", target))
        except Exception as error:
            self.events.put(("error", str(error)))

    def process_events(self) -> None:
        try:
            while True:
                event_type, payload = self.events.get_nowait()
                if event_type == "step":
                    key, progress = payload
                    self.step_label.configure(text=self.t(key))
                    self.target_progress = max(self.target_progress, float(progress))
                elif event_type == "progress":
                    self.target_progress = max(self.target_progress, float(payload))
                elif event_type == "complete":
                    self.target_progress = 100
                    self.step_label.configure(text=self.t("step_done"))
                    self.root.after(260, self.render_complete)
                elif event_type == "error":
                    self.installing = False
                    self.close_button.configure(state="normal")
                    self.language_button.configure(state="normal")
                    self.render_welcome()
                    messagebox.showerror(
                        self.t("error_title"),
                        self.t("failed").format(payload),
                        parent=self.root,
                    )
        except queue.Empty:
            pass
        self.root.after(60, self.process_events)

    def animate_progress(self) -> None:
        if hasattr(self, "progress_rect") and self.progress_canvas.winfo_exists():
            self.display_progress += (self.target_progress - self.display_progress) * 0.22
            if abs(self.target_progress - self.display_progress) < 0.3:
                self.display_progress = self.target_progress
            width = self.progress_canvas.winfo_width()
            self.progress_canvas.coords(
                self.progress_rect, 0, 0, width * self.display_progress / 100, 8
            )
            self.percent_label.configure(text=f"{int(self.display_progress)}%")
        self.root.after(16, self.animate_progress)

    def launch_app(self) -> None:
        executable = self.install_target / f"{APP_NAME}.exe"
        try:
            os.startfile(executable)
            self.root.destroy()
        except OSError as error:
            messagebox.showerror(
                self.t("error_title"), self.t("failed").format(error), parent=self.root
            )

    def close(self) -> None:
        if self.installing:
            messagebox.showinfo(self.t("title"), self.t("error_close"), parent=self.root)
            return
        self.root.destroy()


def main() -> None:
    if os.name != "nt":
        raise OSError("Aegis Core Setup is a Windows installer.")
    root = tk.Tk()
    InstallerWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
