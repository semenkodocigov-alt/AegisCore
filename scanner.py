"""File scanner engine with thread-safe cancellation and async support."""
import os
import logging
import ctypes
import stat
import tempfile
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, Future, wait
from pathlib import Path
from typing import Optional, Callable, Dict, List, Any

from config import get_config
from analyzer import FileAnalyzer
from hash_utils import calculate_all_with_entropy

logger = logging.getLogger(__name__)

config = get_config()
if config.is_using_improved_signatures():
    from signatures_improved import SignatureDatabase
else:
    from signatures import SignatureDatabase


def _full_system_scan_roots() -> list[str]:
    roots: list[str] = []
    if os.name == "nt":
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.GetLogicalDrives.restype = ctypes.c_uint
            kernel32.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
            kernel32.GetDriveTypeW.restype = ctypes.c_uint
            drive_mask = kernel32.GetLogicalDrives()
            for index in range(26):
                if not drive_mask & (1 << index):
                    continue
                drive = f"{chr(ord('A') + index)}:\\"
                if kernel32.GetDriveTypeW(drive) == 3:
                    roots.append(drive)
        except (AttributeError, OSError):
            logger.exception("Could not enumerate fixed Windows drives")

        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        app_data = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        local_app_data = os.environ.get(
            "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
        )
        program_data = os.environ.get("ProgramData", r"C:\ProgramData")
        startup_locations = (
            Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
            Path(program_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "StartUp",
        )
        roots.extend((
            str(Path(system_root) / "System32"),
            app_data,
            local_app_data,
            program_data,
            os.environ.get("TEMP", tempfile.gettempdir()),
            os.environ.get("TMP", tempfile.gettempdir()),
            *(str(path) for path in startup_locations),
        ))
    else:
        roots.extend((str(Path.home()), tempfile.gettempdir()))

    unique_roots: list[str] = []
    seen: set[str] = set()
    for path in roots:
        if not path or not os.path.isdir(path):
            continue
        normalized = os.path.normcase(os.path.abspath(path))
        if normalized not in seen:
            seen.add(normalized)
            unique_roots.append(path)
    return unique_roots


class FileScanner:
    """Thread-safe file scanner with cancellation and progress reporting."""

    # frozenset for O(1) membership testing on extensions
    SUSPICIOUS_EXTENSIONS: frozenset = frozenset({
        '.exe', '.dll', '.sys', '.scr', '.ocx', '.drv',
        '.bat', '.cmd', '.vbs', '.js', '.jse', '.wsf', '.wsh',
        '.ps1', '.psm1', '.psd1'
    })

    # tuple for fast iteration on name fragments
    SUSPICIOUS_NAMES: tuple = (
        'keygen', 'crack', 'patch', 'hacktool', 'activator',
        'injector', 'bypass', 'stealer', 'keylogger', 'miner',
        'trojan', 'virus', 'worm', 'ransomware', 'backdoor',
        'rootkit', 'spyware', 'adware', 'malware', 'exploit',
        'payload', 'shellcode', 'dropper', 'loader', 'bot',
        'rat', 'remote', 'access', 'hack', 'cheat', 'trainer',
        'packer', 'binder', 'obfuscator', 'deobfuscator'
    )

    def __init__(self) -> None:
        """Initialize scanner with signature database and heuristic analyzer."""
        self.sig_db = SignatureDatabase()
        self.analyzer = FileAnalyzer(self.sig_db)
        # Thread-safe event: set() to request graceful scan cancellation
        self._stop_event = threading.Event()
        # Thread pool for async scanning (bounded to avoid resource exhaustion)
        self._executor = ThreadPoolExecutor(
            max_workers=config.get("max_threads", 4)
        )
        self._native_signature_lock = threading.Lock()
        self._native_signature_index: Any = None
        self._native_signature_unavailable = False

    def cancel(self) -> None:
        """Request cancellation of all running scans.

        Any in-progress scan_directory will finish its current file then stop.
        Call reset() or create a new instance to scan again.
        """
        self._stop_event.set()

    def shutdown(self) -> None:
        """Stop accepting async scans and cancel work that has not started."""
        self.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def reset(self) -> None:
        """Clear the cancellation flag so the scanner can be reused."""
        self._stop_event.clear()

    def _should_analyze_file(
        self, filepath: str, filename: Optional[str] = None
    ) -> bool:
        """Determine if a file warrants heuristic analysis.

        Checks file extension against known suspicious types and filename
        against known malware-related name fragments.
        """
        filename = filename or os.path.basename(filepath).lower()
        ext = os.path.splitext(filename)[1].lower()
        if ext in self.SUSPICIOUS_EXTENSIONS:
            return True
        # tuple iteration is fast for short lists
        for name in self.SUSPICIOUS_NAMES:
            if name in filename:
                return True
        return False

    def _match_native_signature(
        self, hashes: Dict[str, Optional[str]]
    ) -> Optional[Dict[str, Any]]:
        if self._native_signature_unavailable:
            return None
        with self._native_signature_lock:
            if self._native_signature_index is None:
                try:
                    from native_scanner import NativeSignatureIndex
                    self._native_signature_index = NativeSignatureIndex(self.sig_db)
                except (ImportError, OSError, RuntimeError) as error:
                    logger.info("Native signature index unavailable; using Python matcher: %s", error)
                    self._native_signature_unavailable = True
                    return None
            index = self._native_signature_index
        try:
            return index.match(hashes)
        except RuntimeError as error:
            logger.warning("Native signature matching failed; using Python matcher: %s", error)
            return None

    def scan_file(self, filepath: str) -> Dict[str, Any]:
        """Scan a single file for threats.

        Returns a dict with keys: filepath, is_threat, threat_name, details.
        Skips symlinks and handles permission / encoding errors gracefully.
        """
        result: Dict[str, Any] = {
            'filepath': filepath,
            'is_threat': False,
            'threat_name': '',
            'details': []
        }

        try:
            # Skip symbolic links to prevent symlink-based evasion attacks
            if os.path.islink(filepath):
                result['details'].append("Skipped: symbolic link")
                return result

            if not os.path.exists(filepath):
                return result

            # Size check: skip empty or oversized files
            try:
                size = os.path.getsize(filepath)
            except OSError as e:
                result['details'].append(f"Cannot stat file: {e}")
                return result

            max_size = config.get("max_file_size", 100 * 1024 * 1024)
            if size > max_size or size == 0:
                return result

            # Compute hashes (single-pass in hash_utils)
            hashes, entropy = calculate_all_with_entropy(filepath)

            # Check against known malware signatures
            filename = os.path.basename(filepath)
            is_whitelisted = self.sig_db._is_whitelisted(filename, filepath)
            sig_match = None if is_whitelisted else self._match_native_signature(hashes)
            if sig_match is None:
                sig_match = self.sig_db.check_hash(
                    md5=hashes['md5'],
                    sha1=hashes['sha1'],
                    sha256=hashes['sha256'],
                    filename=filename,
                    filepath=filepath
                )

            if sig_match:
                result['is_threat'] = True
                result['threat_name'] = sig_match['name']
                result['details'].append(
                    f"Найдена сигнатура: {sig_match['name']}"
                )
                return result

            # Heuristic analysis only for suspicious file types / names
            if self._should_analyze_file(filepath, filename):
                status, threats, score = self.analyzer.analyze(filepath, entropy=entropy)
            else:
                status, threats, score = 'clean', [], 0

            if status != 'clean':
                result['is_threat'] = True
                result['threat_name'] = 'Подозрительный файл'
                result['details'] = threats + [f"Оценка угрозы: {score}"]

        except PermissionError:
            result['details'].append("Permission denied")
        except UnicodeError as e:
            result['details'].append(f"Unicode error in filename: {e}")
        except OSError as e:
            result['details'].append(f"OS error: {e}")
        except Exception as e:
            result['details'].append(f"Ошибка: {e}")

        return result

    def scan_file_async(self, filepath: str) -> Future:
        """Submit a single file scan to the thread pool.

        Returns a concurrent.futures.Future whose result() is the scan dict.
        """
        return self._executor.submit(self.scan_file, filepath)

    def scan_directory(
        self,
        path: str,
        max_depth: int = 2,
        max_files: int = 500,
        callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
        result_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        resume_event: Optional[threading.Event] = None,
    ) -> Dict[str, Any]:
        """Scan a directory tree for threats.

        Args:
            path: Root directory to scan.
            max_depth: Maximum directory recursion depth.
            max_files: Maximum number of files to scan.
            callback: Legacy callback(filepath, is_threat) per file.
            progress_callback: Extended callback(filepath, is_threat,
                               files_scanned, capped_total_estimate) per file.
            resume_event: Optional gate cleared to pause traversal between files.

        Returns a dict with keys: results (list of threat dicts),
        files_scanned (int), cancelled (bool).
        """
        results: List[Dict[str, Any]] = []
        files_scanned: int = 0

        # Use the existing file limit as an upper bound rather than walking
        # the directory tree once just to estimate progress.
        total_estimated: int = max_files if callable(progress_callback) else 0

        def wait_until_resumed() -> bool:
            while resume_event is not None and not resume_event.wait(0.1):
                if self._stop_event.is_set():
                    return False
            return not self._stop_event.is_set()

        def scan_candidate(filepath: str) -> bool:
            nonlocal files_scanned
            if not wait_until_resumed() or files_scanned >= max_files:
                return False
            try:
                scan_result = self.scan_file(filepath)
            except PermissionError:
                logger.debug("Permission denied: %s", filepath)
                return True
            except OSError as error:
                logger.debug("OS error scanning %s: %s", filepath, error)
                return True

            if result_callback is not None:
                result_callback(scan_result)
            if scan_result['is_threat']:
                results.append(scan_result)

            files_scanned += 1

            if callable(callback):
                try:
                    callback(filepath, scan_result['is_threat'])
                except Exception as error:
                    logger.debug("Callback error: %s", error)

            if callable(progress_callback):
                try:
                    progress_callback(
                        filepath,
                        scan_result['is_threat'],
                        files_scanned,
                        total_estimated
                    )
                except Exception as error:
                    logger.debug("Progress callback error: %s", error)
            return not self._stop_event.is_set() and files_scanned < max_files

        try:
            from native_scanner import NativeScannerError, walk_directory
            try:
                native_count = walk_directory(
                    path,
                    max_depth,
                    max_files,
                    scan_candidate,
                )
            except NativeScannerError as error:
                logger.warning("Native directory walk failed; using Python fallback: %s", error)
                native_count = None

            if native_count is None:
                for root, dirs, files in os.walk(path):
                    if self._stop_event.is_set() or files_scanned >= max_files:
                        break

                    relative_root = os.path.relpath(root, path)
                    depth = 0 if relative_root == os.curdir else relative_root.count(os.sep) + 1
                    if depth > max_depth:
                        dirs.clear()
                        continue
                    dirs[:] = [
                        directory for directory in dirs
                        if not os.path.islink(os.path.join(root, directory))
                    ]

                    for filename in files:
                        if self._stop_event.is_set() or files_scanned >= max_files:
                            break
                        filepath = os.path.join(root, filename)
                        if os.path.islink(filepath):
                            continue
                        if not scan_candidate(filepath):
                            break
        except PermissionError:
            logger.warning("Permission denied accessing: %s", path)
        except OSError as error:
            logger.error("Scan directory error: %s", error)

        return {
            'results': results,
            'files_scanned': files_scanned,
            'cancelled': self._stop_event.is_set()
        }

    def scan_full_system(
        self,
        progress_callback: Optional[Callable[[str, bool, int, int], None]] = None,
        result_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        resume_event: Optional[threading.Event] = None,
    ) -> Dict[str, Any]:
        """Scan fixed drives and critical system folders with bounded concurrency."""
        roots = _full_system_scan_roots()
        if not roots:
            raise OSError("No accessible system scan locations were found.")

        max_pending = max(1, int(config.get("max_threads", 4))) * 2
        pending: dict[Future, str] = {}
        visited_directories: set[str] = set()
        discovered = 0
        scanned = 0
        stop = False

        def wait_until_resumed() -> bool:
            while resume_event is not None and not resume_event.wait(0.1):
                if self._stop_event.is_set():
                    return False
            return not self._stop_event.is_set()

        def consume(block: bool) -> None:
            nonlocal scanned
            if not pending:
                return
            completed, _ = wait(
                tuple(pending),
                timeout=None if block else 0,
                return_when=FIRST_COMPLETED,
            )
            for future in completed:
                filepath = pending.pop(future)
                if future.cancelled():
                    continue
                scan_result = future.result()
                scanned += 1
                if result_callback is not None:
                    result_callback(scan_result)
                if progress_callback is not None:
                    progress_callback(
                        filepath,
                        bool(scan_result.get("is_threat")),
                        scanned,
                        discovered,
                    )

        try:
            for root in roots:
                if not wait_until_resumed():
                    stop = True
                    break
                directories = [root]
                while directories and not self._stop_event.is_set():
                    if not wait_until_resumed():
                        stop = True
                        break
                    directory = directories.pop()
                    normalized_directory = os.path.normcase(os.path.abspath(directory))
                    if normalized_directory in visited_directories:
                        continue

                    child_directories: list[str] = []
                    try:
                        with os.scandir(directory) as entries:
                            for entry in entries:
                                try:
                                    metadata = entry.stat(follow_symlinks=False)
                                    attributes = getattr(metadata, "st_file_attributes", 0)
                                    if stat.S_ISLNK(metadata.st_mode) or attributes & 0x400:
                                        continue
                                    if stat.S_ISDIR(metadata.st_mode):
                                        child_directories.append(entry.path)
                                    elif stat.S_ISREG(metadata.st_mode):
                                        discovered += 1
                                        pending[self._executor.submit(self.scan_file, entry.path)] = entry.path
                                        if len(pending) >= max_pending:
                                            consume(block=True)
                                except (PermissionError, OSError):
                                    logger.debug("Skipping inaccessible path: %s", entry.path)
                    except (PermissionError, OSError):
                        logger.debug("Skipping inaccessible directory: %s", directory)
                        continue

                    visited_directories.add(normalized_directory)
                    directories.extend(reversed(child_directories))
                    consume(block=False)

                if stop or self._stop_event.is_set():
                    stop = True
                    break
        finally:
            if stop or self._stop_event.is_set():
                for future in pending:
                    future.cancel()
            while pending:
                consume(block=True)

        return {
            "files_scanned": scanned,
            "files_discovered": discovered,
            "cancelled": self._stop_event.is_set(),
        }
