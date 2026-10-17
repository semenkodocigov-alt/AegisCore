"""Quarantine manager with thread-safe metadata and atomic file operations."""
import os
import shutil
import time
import json
import stat
import logging
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from config import get_config

logger = logging.getLogger(__name__)


class QuarantineManager:
    """Manages quarantined files with thread-safe metadata persistence.

    Metadata is protected by a threading.Lock to prevent corruption
    during concurrent access. File writes use atomic temp-file + rename.
    """

    def __init__(self) -> None:
        """Initialize quarantine directory and load metadata."""
        cfg = get_config()
        quarantine_dir: str = cfg.get("quarantine_dir", "./quarantine")
        if not os.path.isabs(quarantine_dir):
            quarantine_dir = str(
                Path(__file__).parent.joinpath(quarantine_dir).resolve()
            )
        self.quarantine_dir: str = quarantine_dir
        os.makedirs(self.quarantine_dir, exist_ok=True)
        self.meta_file: str = os.path.join(self.quarantine_dir, "metadata.json")
        self.files: List[str] = []

        # Lock guards all reads/writes to self.metadata and self._cached_count
        self._lock = threading.Lock()
        self.metadata: Dict[str, Any] = {}
        self._cached_count: Optional[int] = None

        self._load_meta()

    def _load_meta(self) -> None:
        """Load quarantine metadata from JSON file (thread-safe)."""
        with self._lock:
            try:
                if os.path.exists(self.meta_file):
                    with open(self.meta_file, 'r', encoding='utf-8') as f:
                        self.metadata = json.load(f)
                else:
                    self.metadata = {}
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load quarantine metadata: %s", e)
                self.metadata = {}
            # Invalidate count cache after reload
            self._cached_count = None

    def _save_meta(self) -> None:
        """Save quarantine metadata atomically (write to temp, then rename).

        Must be called while holding self._lock.
        """
        try:
            # Write to a temp file in the same directory, then atomically rename.
            # os.replace is atomic on the same filesystem on most OSes.
            fd, tmp_path = tempfile.mkstemp(
                dir=self.quarantine_dir, suffix='.tmp', prefix='meta_'
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, self.meta_file)
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except OSError as e:
            logger.error("Failed to save quarantine metadata: %s", e)

    def add(
        self,
        filepath: Optional[str],
        threat_name: str = "",
        remove_original: bool = True,
    ) -> bool:
        """Add a file to quarantine and optionally remove the original.

        Args:
            filepath: Path to the file to quarantine.
            threat_name: Name of the detected threat.
            remove_original: Whether to delete the original file.

        Returns True on success, False on failure.
        """
        # Input validation
        if not filepath or not filepath.strip():
            logger.warning("add() called with empty filepath")
            return False

        try:
            filepath = os.path.abspath(filepath)
            if not os.path.exists(filepath):
                return False

            timestamp = int(time.time())
            name = os.path.basename(filepath)
            quarantine_name = f"q_{timestamp}_{name}"
            quarantine_path = os.path.join(self.quarantine_dir, quarantine_name)

            shutil.copy2(filepath, quarantine_path)

            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

            with self._lock:
                self.metadata[quarantine_name] = {
                    "original_path": filepath,
                    "original_name": name,
                    "timestamp": timestamp,
                    "threat_name": threat_name,
                    "size": file_size,
                }
                self._save_meta()
                self._cached_count = None  # Invalidate cache

            if remove_original:
                try:
                    # Platform-appropriate permission fix: make writable
                    # without the dangerous 0o777 that grants everyone access
                    current_mode = os.stat(filepath).st_mode
                    if not (current_mode & stat.S_IWRITE):
                        os.chmod(filepath, current_mode | stat.S_IWRITE)
                    os.remove(filepath)
                except OSError as e:
                    logger.warning(
                        "Could not delete original file %s: %s", filepath, e
                    )

            if quarantine_path not in self.files:
                self.files.append(quarantine_path)
            return True

        except OSError as e:
            logger.error("Quarantine error for %s: %s", filepath, e)
            return False
        except Exception as e:
            logger.error("Unexpected quarantine error: %s", e)
            return False

    def count(self) -> int:
        """Return the number of files currently in quarantine.

        Uses a cached value to avoid repeated directory listings.
        """
        with self._lock:
            if self._cached_count is not None:
                return self._cached_count

        # list_files() is outside the lock (it does its own I/O)
        n = len(self.list_files())
        with self._lock:
            self._cached_count = n
        return n

    def list_files(self) -> List[str]:
        """Return a list of absolute paths to quarantined files.

        Handles the case where the quarantine directory does not exist.
        """
        try:
            if not os.path.isdir(self.quarantine_dir):
                return []
            return [
                os.path.join(self.quarantine_dir, filename)
                for filename in os.listdir(self.quarantine_dir)
                if filename != "metadata.json"
                and os.path.isfile(
                    os.path.join(self.quarantine_dir, filename)
                )
            ]
        except OSError as e:
            logger.warning("Cannot list quarantine directory: %s", e)
            return []

    def get_details(self) -> List[Dict[str, Any]]:
        """Return detailed information about all quarantined files."""
        self._load_meta()
        files = self.list_files()
        details: List[Dict[str, Any]] = []

        with self._lock:
            meta_snapshot = dict(self.metadata)

        for fpath in files:
            fname = os.path.basename(fpath)
            meta = meta_snapshot.get(fname, {})
            orig_path = meta.get(
                "original_path",
                fname.replace(
                    f"q_{fname.split('_')[1]}_" if '_' in fname else "", ""
                ),
            )
            threat = meta.get("threat_name", "Угроза")
            tstamp = meta.get("timestamp", 0)
            if tstamp == 0:
                try:
                    tstamp = os.path.getmtime(fpath)
                except OSError:
                    tstamp = 0
            date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(tstamp))
            try:
                size = os.path.getsize(fpath)
            except OSError:
                size = 0

            details.append({
                "quarantine_path": fpath,
                "filename": meta.get("original_name", os.path.basename(orig_path)),
                "original_path": orig_path,
                "threat": threat,
                "date": date_str,
                "size": size,
            })
        return details

    def restore(
        self, quarantined_path: str, target_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Restore a file from quarantine to its original (or custom) location.

        Returns (success: bool, message: str).
        """
        if not quarantined_path or not quarantined_path.strip():
            return False, "Empty quarantine path"

        try:
            if not os.path.exists(quarantined_path):
                return False, "Файл в карантине не найден"

            fname = os.path.basename(quarantined_path)

            with self._lock:
                meta = self.metadata.get(fname, {})

            dest = target_path or meta.get("original_path")

            if not dest:
                # If original path is unknown, restore to cwd
                orig_name = meta.get("original_name") or fname
                dest = os.path.abspath(orig_name)

            dest_dir = os.path.dirname(dest)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)

            shutil.copy2(quarantined_path, dest)
            os.remove(quarantined_path)

            with self._lock:
                if fname in self.metadata:
                    del self.metadata[fname]
                self._save_meta()
                self._cached_count = None

            return True, f"Файл восстановлен: {dest}"

        except OSError as e:
            return False, f"Ошибка восстановления: {e}"
        except Exception as e:
            return False, f"Ошибка восстановления: {e}"

    def remove(self, quarantined_path: str) -> bool:
        """Permanently delete a file from quarantine.

        Returns True on success.
        """
        if not quarantined_path or not quarantined_path.strip():
            return False

        try:
            if os.path.exists(quarantined_path):
                os.remove(quarantined_path)
            fname = os.path.basename(quarantined_path)

            with self._lock:
                if fname in self.metadata:
                    del self.metadata[fname]
                self._save_meta()
                self._cached_count = None

            return True
        except OSError as e:
            logger.error("Failed to remove quarantined file %s: %s",
                         quarantined_path, e)
            return False

    def clear(self) -> bool:
        """Remove all files from quarantine.

        Returns True if all files were removed successfully.
        """
        success = True
        for fpath in self.list_files():
            if not self.remove(fpath):
                success = False

        with self._lock:
            self.metadata.clear()
            self._save_meta()
            self._cached_count = 0

        return success