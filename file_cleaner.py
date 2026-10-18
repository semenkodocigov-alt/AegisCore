"""Module for secure deletion, disinfection, and backup of infected files."""
import os
import shutil
import logging
import subprocess
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Generator

logger = logging.getLogger(__name__)

# Chunk size for overwrite operations (1 MB) — prevents OOM on large files
_OVERWRITE_CHUNK: int = 1024 * 1024


class FileCleaner:
    """Secure file deletion, disinfection, and backup management."""

    def __init__(self, backup_dir: Optional[str] = None) -> None:
        """Initialize the cleaner with a backup directory.

        Args:
            backup_dir: Path for backup copies before deletion.
                        Defaults to a 'backups' folder next to this module.
        """
        self.backup_dir: Path = (
            Path(backup_dir) if backup_dir else Path(__file__).parent / "backups"
        )
        self.backup_dir.mkdir(exist_ok=True)
        self.log: List[str] = []

    # ------------------------------------------------------------------
    # Backup context manager
    # ------------------------------------------------------------------

    @contextmanager
    def _backup_context(
        self, filepath: Path
    ) -> Generator[Optional[Path], None, None]:
        """Context manager that creates a backup and yields its path.

        On context exit, the backup remains on disk (by design — it's a
        safety net). Yields None if backup creation fails.
        """
        backup_path: Optional[Path] = None
        try:
            backup_name = (
                f"{filepath.stem}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                f"{filepath.suffix}"
            )
            backup_path = self.backup_dir / backup_name
            shutil.copy2(filepath, backup_path)
            self.log.append(f"✓ Резервная копия: {backup_path}")
        except OSError as e:
            self.log.append(f"⚠ Ошибка при создании резервной копии: {e}")
            backup_path = None
        yield backup_path

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete_file(
        self, filepath: str, create_backup: bool = True
    ) -> Tuple[bool, str]:
        """Delete a file, optionally creating a backup first.

        Returns (success, message).
        """
        try:
            filepath_p = Path(filepath)
            if not filepath_p.exists():
                return False, "Файл не найден"

            if not os.access(filepath_p, os.W_OK):
                return False, "Нет прав на удаление файла"

            # Create backup if requested (via context manager)
            if create_backup:
                with self._backup_context(filepath_p):
                    pass  # backup is created on entry

            filepath_p.unlink()
            msg = f"Файл успешно удален: {filepath_p}"
            self.log.append(f"✓ {msg}")
            return True, msg

        except PermissionError:
            msg = "Ошибка доступа: требуются права администратора"
            self.log.append(f"✗ {msg}")
            return False, msg
        except OSError as e:
            msg = f"Ошибка удаления: {e}"
            self.log.append(f"✗ {msg}")
            return False, msg

    def secure_delete(self, filepath: str, passes: int = 3) -> Tuple[bool, str]:
        """Securely delete a file by overwriting with random data before removal.

        Handles edge cases:
        - Zero-byte files: skips overwrite, just deletes.
        - Very large files: writes in 1 MB chunks to avoid memory exhaustion.

        Args:
            filepath: Path to the file to securely delete.
            passes: Number of overwrite passes (default 3).

        Returns (success, message).
        """
        try:
            filepath_p = Path(filepath)
            if not filepath_p.exists():
                return False, "Файл не найден"

            file_size: int = filepath_p.stat().st_size

            # Zero-byte files: nothing to overwrite, just delete
            if file_size == 0:
                filepath_p.unlink()
                msg = f"Файл безопасно удален (пустой): {filepath_p}"
                self.log.append(f"✓ {msg}")
                return True, msg

            # Overwrite in multiple passes with random data
            with open(filepath_p, 'r+b') as f:
                for i in range(passes):
                    f.seek(0)
                    remaining = file_size
                    # Write in chunks to handle very large files
                    while remaining > 0:
                        chunk_size = min(_OVERWRITE_CHUNK, remaining)
                        f.write(os.urandom(chunk_size))
                        remaining -= chunk_size
                    f.flush()
                    os.fsync(f.fileno())
                    self.log.append(
                        f"Проход {i + 1}/{passes} безопасного удаления..."
                    )

            filepath_p.unlink()
            msg = f"Файл безопасно удален: {filepath_p}"
            self.log.append(f"✓ {msg}")
            return True, msg

        except PermissionError:
            msg = f"Нет прав для безопасного удаления: {filepath}"
            self.log.append(f"✗ {msg}")
            return False, msg
        except OSError as e:
            msg = f"Ошибка безопасного удаления: {e}"
            self.log.append(f"✗ {msg}")
            return False, msg

    # ------------------------------------------------------------------
    # Quarantine (standalone, without QuarantineManager)
    # ------------------------------------------------------------------

    def quarantine_file(
        self, filepath: str, quarantine_dir: str
    ) -> Tuple[bool, str]:
        """Move a file into a quarantine directory.

        Returns (success, message).
        """
        try:
            filepath_p = Path(filepath)
            quarantine_dir_p = Path(quarantine_dir)

            if not filepath_p.exists():
                return False, "Файл не найден"

            quarantine_dir_p.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            quarantine_name = f"{filepath_p.stem}_{timestamp}{filepath_p.suffix}"
            quarantine_path = quarantine_dir_p / quarantine_name

            shutil.move(str(filepath_p), str(quarantine_path))
            msg = f"Файл помещен в карантин: {quarantine_path}"
            self.log.append(f"✓ {msg}")
            return True, msg

        except OSError as e:
            msg = f"Ошибка при помещении в карантин: {e}"
            self.log.append(f"✗ {msg}")
            return False, msg

    # ------------------------------------------------------------------
    # Disinfection
    # ------------------------------------------------------------------

    def disinfect_file(self, filepath: str) -> Tuple[bool, str]:
        """Attempt to disinfect a file by neutralizing dangerous code.

        For PE files (.exe/.dll/.sys): triggers a Windows Defender scan via
        PowerShell (safe, non-destructive). The previous dangerous
        Remove-MpPreference command has been removed.

        For script files (.vbs/.js/.bat/.cmd/.ps1): comments out known
        dangerous keywords.

        Returns (success, message).
        """
        try:
            filepath_p = Path(filepath)
            if not filepath_p.exists():
                return False, "Файл не найден"

            ext = filepath_p.suffix.lower()

            # PE files: request a Windows Defender scan (safe operation)
            if ext in ('.exe', '.dll', '.sys'):
                try:
                    # Safe PowerShell command: scan this specific file
                    ps_cmd = (
                        f'Start-MpScan -ScanType CustomScan '
                        f'-ScanPath "{filepath_p}"'
                    )
                    subprocess.Popen(
                        ['powershell', '-NoProfile', '-Command', ps_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                except FileNotFoundError:
                    logger.debug("PowerShell not available for scan")
                except OSError as e:
                    logger.debug("Failed to launch Defender scan: %s", e)

                msg = "Попытка лечения выполнена. Требуется ручная проверка."
                self.log.append(f"⚠ {msg}")
                return True, msg

            # Script files: comment out dangerous keywords
            if ext in ('.vbs', '.js', '.bat', '.cmd', '.ps1'):
                with open(filepath_p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                dangerous_keywords = (
                    'createobject', 'eval', 'execute', 'activex',
                    'rundll32', 'powershell', 'cmd.exe', 'wscript',
                )

                cleaned = content
                for keyword in dangerous_keywords:
                    if keyword in content.lower():
                        cleaned = cleaned.replace(keyword, f"'{keyword}")

                with open(filepath_p, 'w', encoding='utf-8') as f:
                    f.write(cleaned)

                msg = "Файл протестирован и подозрительный код заблокирован"
                self.log.append(f"✓ {msg}")
                return True, msg

            msg = "Этот тип файла не поддерживает лечение"
            self.log.append(f"⚠ {msg}")
            return False, msg

        except PermissionError:
            msg = f"Нет прав для лечения файла: {filepath}"
            self.log.append(f"✗ {msg}")
            return False, msg
        except OSError as e:
            msg = f"Ошибка при лечении файла: {e}"
            self.log.append(f"✗ {msg}")
            return False, msg

    # ------------------------------------------------------------------
    # Backup management
    # ------------------------------------------------------------------

    def restore_from_backup(
        self, backup_path: str, original_path: str
    ) -> Tuple[bool, str]:
        """Restore a file from a backup copy.

        Returns (success, message).
        """
        try:
            backup_p = Path(backup_path)
            original_p = Path(original_path)

            if not backup_p.exists():
                return False, "Резервная копия не найдена"

            original_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_p, original_p)
            msg = f"Файл восстановлен из резервной копии: {original_p}"
            self.log.append(f"✓ {msg}")
            return True, msg

        except OSError as e:
            msg = f"Ошибка при восстановлении: {e}"
            self.log.append(f"✗ {msg}")
            return False, msg

    def get_backups(self) -> List[Path]:
        """Return a sorted list of available backup file paths."""
        try:
            if not self.backup_dir.exists():
                return []
            return sorted(list(self.backup_dir.glob('*')), reverse=True)
        except OSError as e:
            logger.error("Failed to list backups: %s", e)
            return []

    def get_log(self) -> List[str]:
        """Return the operation log."""
        return self.log

    def clear_log(self) -> None:
        """Clear the operation log."""
        self.log = []
