"""File scanner engine with thread-safe cancellation and async support."""
import os
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Callable, Dict, List, Any

from config import get_config
from analyzer import FileAnalyzer
from hash_utils import calculate_all

logger = logging.getLogger(__name__)

config = get_config()
if config.is_using_improved_signatures():
    from signatures_improved import SignatureDatabase
else:
    from signatures import SignatureDatabase


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
            hashes = calculate_all(filepath)

            # Check against known malware signatures
            filename = os.path.basename(filepath)
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
                status, threats, score = self.analyzer.analyze(filepath)
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
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Scan a directory tree for threats.

        Args:
            path: Root directory to scan.
            max_depth: Maximum directory recursion depth.
            max_files: Maximum number of files to scan.
            callback: Legacy callback(filepath, is_threat) per file.
            progress_callback: Extended callback(filepath, is_threat,
                               files_scanned, capped_total_estimate) per file.

        Returns a dict with keys: results (list of threat dicts),
        files_scanned (int), cancelled (bool).
        """
        results: List[Dict[str, Any]] = []
        files_scanned: int = 0

        # Use the existing file limit as an upper bound rather than walking
        # the directory tree once just to estimate progress.
        total_estimated: int = max_files if callable(progress_callback) else 0

        try:
            for root, dirs, files in os.walk(path):
                # Check for cancellation between directories
                if self._stop_event.is_set():
                    break
                if files_scanned >= max_files:
                    break

                # Depth limiting
                depth = root[len(path):].count(os.sep)
                if depth > max_depth:
                    dirs.clear()
                    continue

                for file in files:
                    if self._stop_event.is_set():
                        break
                    if files_scanned >= max_files:
                        break

                    filepath = os.path.join(root, file)

                    # Skip symlinks at directory-walk level too
                    if os.path.islink(filepath):
                        continue

                    # Handle individual file permission errors
                    try:
                        scan_result = self.scan_file(filepath)
                    except PermissionError:
                        logger.debug("Permission denied: %s", filepath)
                        continue
                    except OSError as e:
                        logger.debug("OS error scanning %s: %s", filepath, e)
                        continue

                    if scan_result['is_threat']:
                        results.append(scan_result)

                    files_scanned += 1

                    # Legacy callback: (filepath, is_threat)
                    if callable(callback):
                        try:
                            callback(filepath, scan_result['is_threat'])
                        except Exception as e:
                            logger.debug("Callback error: %s", e)

                    # Extended progress callback
                    if callable(progress_callback):
                        try:
                            progress_callback(
                                filepath,
                                scan_result['is_threat'],
                                files_scanned,
                                total_estimated
                            )
                        except Exception as e:
                            logger.debug("Progress callback error: %s", e)

        except PermissionError:
            logger.warning("Permission denied accessing: %s", path)
        except OSError as e:
            logger.error("Scan directory error: %s", e)

        return {
            'results': results,
            'files_scanned': files_scanned,
            'cancelled': self._stop_event.is_set()
        }
