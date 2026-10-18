"""Desktop shell for the React interface and its local native API."""
from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import logging
from ctypes import wintypes
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from privileges import hide_console_window, is_admin

hide_console_window()

import webview

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
NICKNAME_MIN_LENGTH = 2
NICKNAME_MAX_LENGTH = 32
PASSWORD_MIN_LENGTH = 8
logger = logging.getLogger(__name__)


def _iso_timestamp(value: float | None) -> str:
    if value is None:
        return ""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(value))


def _public_user(row: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(row["id"]),
        "email": str(row["email"]),
        "nickname": str(row["nickname"]),
        "role": str(row["role"]),
        "createdAt": _iso_timestamp(row.get("created_at")),
        "lastLoginAt": _iso_timestamp(row.get("last_login_at")),
    }


def _response(data: Any = None, error: dict[str, str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"success": error is None, "timestamp": int(time.time() * 1000)}
    if error is None:
        result["data"] = data
    else:
        result["error"] = error
    return result


def _error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _validate_email(email: str) -> str | None:
    normalized = email.strip().lower()
    if len(normalized) > 254 or not EMAIL_PATTERN.fullmatch(normalized):
        return None
    return normalized


def _read_access_user(
    access_token: str,
    auth: Any,
    database: Any,
) -> dict[str, Any] | None:
    if not isinstance(access_token, str):
        return None
    payload = auth.decode_token(access_token)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        return None
    return database.get_user_by_id(user_id)


class AegisDesktopBridge:
    """Methods exposed to the trusted, locally bundled WebView."""

    def __init__(self, startup_target: str | None = None) -> None:
        self.window: webview.Window | None = None
        self.startup_target = startup_target
        self.is_maximized = False
        self.auth: Any = None
        self.database: Any = None
        self.scanner: Any = None
        self.quarantine: Any = None
        self.virustotal: Any = None
        self._backend_ready = threading.Event()
        self._backend_error: str | None = None
        self._shutdown_requested = threading.Event()
        self._scan_lock = threading.Lock()
        self._vt_guard = threading.Lock()
        self._vt_invalid_key = False
        self._vt_rate_limited_until = 0.0
        self._scan_cancelled = threading.Event()
        self._scan_resume = threading.Event()
        self._scan_resume.set()
        self._scan_started_at = 0.0
        self._scan_state: dict[str, Any] = {
            "status": "idle",
            "scanType": "quick",
            "currentPath": "",
            "filesScanned": 0,
            "totalFiles": 0,
            "percentage": 0,
            "threatsFound": 0,
            "threats": [],
            "elapsedSeconds": 0,
            "scanSpeed": 0,
        }
        threading.Thread(
            target=self._initialize_backend,
            name="aegis-backend-init",
            daemon=True,
        ).start()

    def _initialize_backend(self) -> None:
        try:
            from backend import auth, database
            from backend import virustotal
            from backend.secrets import protect_secret, unprotect_secret
            from quarantine import QuarantineManager
            from scanner import FileScanner

            if self._shutdown_requested.is_set():
                return
            self.auth = auth
            self.database = database
            self.virustotal = virustotal
            self._protect_secret = protect_secret
            self._unprotect_secret = unprotect_secret
            self.scanner = FileScanner()
            self.quarantine = QuarantineManager()
        except Exception as error:
            self._backend_error = str(error)
            logger.exception("Failed to initialize Aegis backend")
        finally:
            self._backend_ready.set()

    def _backend_error_response(self) -> dict[str, Any] | None:
        while not self._backend_ready.wait(0.1):
            if self._shutdown_requested.is_set():
                return _response(error=_error(
                    "APPLICATION_SHUTTING_DOWN",
                    "The application is shutting down.",
                ))
        if self._shutdown_requested.is_set():
            return _response(error=_error(
                "APPLICATION_SHUTTING_DOWN",
                "The application is shutting down.",
            ))
        if self._backend_error is not None:
            return _response(error=_error(
                "BACKEND_INITIALIZATION_FAILED",
                "Local services could not start. Check the application log for details.",
            ))
        return None

    def login(self, payload: dict[str, Any]) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        auth = self.auth
        database = self.database
        email = _validate_email(str(payload.get("email", "")))
        password = payload.get("password")
        if email is None or not isinstance(password, str) or not password:
            return _response(error=_error("INVALID_CREDENTIALS", "Enter a valid email and password."))

        row = database.get_user_by_email(email)
        if row is None or not auth.verify_password(password, str(row["password_hash"])):
            return _response(error=_error("INVALID_CREDENTIALS", "Email or password is incorrect."))

        database.update_last_login(str(row["id"]))
        row = database.get_user_by_id(str(row["id"])) or row
        remember_me = payload.get("rememberMe") is True
        token_hours = 24 * 30 if remember_me else 24
        return _response({
            "user": _public_user(row),
            "tokens": {
                "accessToken": auth.create_access_token(str(row["id"]), expires_hours=token_hours),
                "refreshToken": auth.create_refresh_token(str(row["id"]), expires_hours=token_hours),
                "expiresIn": token_hours * 3600,
            },
            "message": "Signed in.",
        })

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        auth = self.auth
        database = self.database
        email = _validate_email(str(payload.get("email", "")))
        nickname = payload.get("nickname")
        password = payload.get("password")
        if email is None:
            return _response(error=_error("INVALID_EMAIL", "Enter a valid email address."))
        if not isinstance(nickname, str) or not NICKNAME_MIN_LENGTH <= len(nickname.strip()) <= NICKNAME_MAX_LENGTH:
            return _response(error=_error("INVALID_NICKNAME", "Nickname must be 2–32 characters."))
        if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
            return _response(error=_error("WEAK_PASSWORD", "Password must be at least 8 characters."))

        row = database.add_user(email, auth.hash_password(password), nickname.strip())
        if row is None:
            return _response(error=_error("ACCOUNT_EXISTS", "An account with this email already exists."))
        database.update_last_login(str(row["id"]))
        row = database.get_user_by_id(str(row["id"])) or row
        remember_me = payload.get("rememberMe") is True
        token_hours = 24 * 30 if remember_me else 24
        return _response({
            "user": _public_user(row),
            "tokens": {
                "accessToken": auth.create_access_token(str(row["id"]), expires_hours=token_hours),
                "refreshToken": auth.create_refresh_token(str(row["id"]), expires_hours=token_hours),
                "expiresIn": token_hours * 3600,
            },
            "message": "Account created.",
        })

    def get_current_user(self, access_token: str) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        row = _read_access_user(access_token, self.auth, self.database)
        if row is None:
            return _response(error=_error("UNAUTHORIZED", "Your session has expired. Sign in again."))
        return _response(_public_user(row))

    def update_profile(self, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        auth = self.auth
        database = self.database
        row = _read_access_user(access_token, auth, database)
        if row is None:
            return _response(error=_error("UNAUTHORIZED", "Your session has expired. Sign in again."))

        nickname_value = payload.get("nickname", row["nickname"])
        email_value = payload.get("email", row["email"])
        nickname = nickname_value.strip() if isinstance(nickname_value, str) else ""
        email = _validate_email(email_value) if isinstance(email_value, str) else None
        if not NICKNAME_MIN_LENGTH <= len(nickname) <= NICKNAME_MAX_LENGTH:
            return _response(error=_error("INVALID_NICKNAME", "Nickname must be 2–32 characters."))
        if email is None:
            return _response(error=_error("INVALID_EMAIL", "Enter a valid email address."))

        password_hash = None
        new_password = payload.get("newPassword")
        if new_password:
            current_password = payload.get("currentPassword")
            if not isinstance(current_password, str) or not auth.verify_password(
                current_password, str(row["password_hash"])
            ):
                return _response(error=_error("INVALID_PASSWORD", "Current password is incorrect."))
            if not isinstance(new_password, str) or len(new_password) < PASSWORD_MIN_LENGTH:
                return _response(error=_error("WEAK_PASSWORD", "New password must be at least 8 characters."))
            password_hash = auth.hash_password(new_password)

        updated = database.update_user_profile(
            str(row["id"]), email, nickname, password_hash=password_hash
        )
        if updated is None:
            return _response(error=_error("PROFILE_UPDATE_FAILED", "Email is already in use or the profile could not be saved."))
        return _response(_public_user(updated))

    def logout(self) -> dict[str, Any]:
        return _response({"message": "Signed out."})

    def get_privilege_status(self) -> dict[str, Any]:
        return _response({"isAdmin": is_admin()})

    def scan_file(self, filepath: str) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        if not isinstance(filepath, str) or not filepath.strip() or not os.path.isfile(filepath):
            return _response(error=_error("FILE_NOT_FOUND", "The selected file could not be found."))
        result = self.scanner.scan_file(filepath)
        try:
            settings = self._read_virustotal_settings(include_key=True)
            if settings["enabled"] and settings["apiKey"]:
                result["virusTotal"] = self._scan_virustotal(filepath, settings)
                self._apply_virustotal_detection(result)
        except Exception:
            logger.exception("VirusTotal settings could not be read for file scan")
            result["virusTotal"] = self._virustotal_error_result(
                "VIRUSTOTAL_SETTINGS_ERROR",
                "VirusTotal settings could not be loaded.",
            )
        return _response(result)

    def get_virustotal_settings(self) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        try:
            settings = self._read_virustotal_settings()
        except Exception:
            logger.exception("Failed to read VirusTotal settings")
            return _response(error=_error(
                "VIRUSTOTAL_SETTINGS_ERROR",
                "VirusTotal settings could not be loaded.",
            ))
        return _response({
            "configured": settings["configured"],
            "apiKeyHint": settings["apiKeyHint"],
            "enabled": settings["enabled"],
            "uploadUnknown": settings["uploadUnknown"],
        })

    def test_save_virustotal_key(
        self,
        api_key: str,
        enabled: bool,
        upload_unknown: bool,
    ) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        if not isinstance(api_key, str) or not isinstance(enabled, bool) or not isinstance(upload_unknown, bool):
            return _response(error=_error("VIRUSTOTAL_INVALID_SETTINGS", "Check the VirusTotal settings and try again."))

        candidate = api_key.strip()
        try:
            if candidate:
                key_to_test = candidate
            else:
                key_to_test = self._read_virustotal_api_key()
                if not key_to_test:
                    return _response(error=_error(
                        "VIRUSTOTAL_KEY_REQUIRED",
                        "Enter a VirusTotal API key before enabling the integration.",
                    ))
            self.virustotal.test_api_key(key_to_test)
            if candidate:
                self.database.set_setting("virustotal_api_key", self._protect_secret(candidate))
            self.database.set_setting("virustotal_enabled", "1" if enabled else "0")
            self.database.set_setting("virustotal_upload_unknown", "1" if upload_unknown else "0")
            with self._vt_guard:
                self._vt_invalid_key = False
                self._vt_rate_limited_until = 0.0
        except self.virustotal.VirusTotalError as error:
            return _response(error=_error(error.code, str(error)))
        except Exception:
            logger.exception("Failed to save VirusTotal settings")
            return _response(error=_error(
                "VIRUSTOTAL_SETTINGS_ERROR",
                "VirusTotal settings could not be saved securely.",
            ))
        return _response({
            "configured": True,
            "apiKeyHint": f"••••{key_to_test[-4:]}",
            "enabled": enabled,
            "uploadUnknown": upload_unknown,
            "message": "VirusTotal API key is valid and settings were saved.",
        })

    def set_virustotal_options(self, enabled: bool, upload_unknown: bool) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        if not isinstance(enabled, bool) or not isinstance(upload_unknown, bool):
            return _response(error=_error("VIRUSTOTAL_INVALID_SETTINGS", "Check the VirusTotal settings and try again."))
        try:
            if enabled and not self.database.get_setting("virustotal_api_key"):
                return _response(error=_error(
                    "VIRUSTOTAL_KEY_REQUIRED",
                    "Test and save a VirusTotal API key before enabling scanning.",
                ))
            self.database.set_setting("virustotal_enabled", "1" if enabled else "0")
            self.database.set_setting("virustotal_upload_unknown", "1" if upload_unknown else "0")
            settings = self._read_virustotal_settings()
        except Exception:
            logger.exception("Failed to update VirusTotal options")
            return _response(error=_error("VIRUSTOTAL_SETTINGS_ERROR", "VirusTotal settings could not be saved."))
        return _response({
            "configured": settings["configured"],
            "apiKeyHint": settings["apiKeyHint"],
            "enabled": settings["enabled"],
            "uploadUnknown": settings["uploadUnknown"],
        })

    def _read_virustotal_api_key(self) -> str | None:
        encrypted_key = self.database.get_setting("virustotal_api_key")
        if not encrypted_key:
            return None
        return self._unprotect_secret(encrypted_key)

    def _read_virustotal_settings(self, include_key: bool = False) -> dict[str, Any]:
        encrypted_key = self.database.get_setting("virustotal_api_key")
        decrypted_key = self._unprotect_secret(encrypted_key) if encrypted_key else None
        return {
            "configured": bool(encrypted_key),
            "apiKeyHint": f"••••{decrypted_key[-4:]}" if decrypted_key else "",
            "apiKey": decrypted_key if include_key else None,
            "enabled": self.database.get_setting("virustotal_enabled") == "1",
            "uploadUnknown": self.database.get_setting("virustotal_upload_unknown") == "1",
        }

    def _scan_virustotal(self, filepath: str, settings: dict[str, Any]) -> dict[str, Any]:
        with self._vt_guard:
            if self._vt_invalid_key:
                return self._virustotal_error_result(
                    "VIRUSTOTAL_INVALID_KEY",
                    "VirusTotal API key is invalid.",
                )
            if time.monotonic() < self._vt_rate_limited_until:
                return self._virustotal_error_result(
                    "VIRUSTOTAL_RATE_LIMIT",
                    "VirusTotal rate limit reached. Try again later.",
                )
        try:
            result = self.virustotal.scan_file(
                filepath,
                settings["apiKey"],
                upload_unknown=settings["uploadUnknown"],
            )
            if result.get("errorCode") == "VIRUSTOTAL_INVALID_KEY":
                with self._vt_guard:
                    self._vt_invalid_key = True
            elif result.get("errorCode") == "VIRUSTOTAL_RATE_LIMIT":
                with self._vt_guard:
                    self._vt_rate_limited_until = time.monotonic() + 60
            return result
        except self.virustotal.VirusTotalError as error:
            if error.code == "VIRUSTOTAL_INVALID_KEY":
                with self._vt_guard:
                    self._vt_invalid_key = True
            elif error.code == "VIRUSTOTAL_RATE_LIMIT":
                with self._vt_guard:
                    self._vt_rate_limited_until = time.monotonic() + 60
            return {
                "status": "error",
                "malicious": 0,
                "suspicious": 0,
                "total": 0,
                "detections": [],
                "reportUrl": "",
                "errorCode": error.code,
                "message": str(error),
            }
        except Exception:
            logger.exception("VirusTotal scan failed")
            return {
                "status": "error",
                "malicious": 0,
                "suspicious": 0,
                "total": 0,
                "detections": [],
                "reportUrl": "",
                "errorCode": "VIRUSTOTAL_UNEXPECTED_ERROR",
                "message": "VirusTotal scan could not be completed.",
            }

    @staticmethod
    def _apply_virustotal_detection(result: dict[str, Any]) -> None:
        virus_total = result.get("virusTotal")
        if not isinstance(virus_total, dict) or virus_total.get("status") != "detected":
            return
        result["is_threat"] = True
        if not result.get("threat_name"):
            result["threat_name"] = "VirusTotal detection"
        if "VirusTotal" not in result.setdefault("detected_by", []):
            result["detected_by"].append("VirusTotal")
        result.setdefault("details", []).append(
            f"VirusTotal: {virus_total['malicious']} / {virus_total['total']} engines detected this file."
        )

    def select_scan_target(self) -> dict[str, Any]:
        if self.window is None:
            return _response(error=_error("WINDOW_UNAVAILABLE", "The desktop window is not ready."))
        selected = self.window.create_file_dialog(webview.OPEN_DIALOG)
        if not selected:
            return _response(error=_error("SELECTION_CANCELLED", "No file was selected."))
        return _response({"targetPath": selected[0]})

    def start_scan(self, scan_type: str, target_path: str | None = None) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        if scan_type not in {"quick", "full", "custom", "system"}:
            return _response(error=_error("INVALID_SCAN_TYPE", "Choose a valid scan type."))

        targets: list[tuple[str, int, int]] = []
        if scan_type == "quick":
            temp_dir = os.environ.get("TEMP", "")
            downloads = str(Path.home() / "Downloads")
            desktop = str(Path.home() / "Desktop")
            targets.extend((path, 2, limit) for path, limit in (
                (temp_dir, 200), (downloads, 200), (desktop, 150)
            ) if path and os.path.isdir(path))
        elif scan_type == "full":
            home = str(Path.home())
            program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
            windows_system = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
            targets.append((home, 3, 500))
            targets.extend((path, depth, limit) for path, depth, limit in (
                (program_files, 2, 300), (windows_system, 1, 200)
            ) if os.path.isdir(path))
        elif scan_type == "system":
            targets = [("__FULL_SYSTEM_SCAN__", 0, 0)]
        else:
            if not isinstance(target_path, str) or not target_path.strip():
                return _response(error=_error("TARGET_REQUIRED", "Choose a file or folder to scan."))
            normalized_path = os.path.abspath(target_path)
            if os.path.isfile(normalized_path):
                targets = [(normalized_path, 0, 1)]
            elif os.path.isdir(normalized_path):
                targets = [(normalized_path, 4, 1000)]
            else:
                return _response(error=_error("TARGET_NOT_FOUND", "The selected file or folder no longer exists."))

        if not targets:
            return _response(error=_error("NO_SCAN_TARGETS", "No available folders were found for this scan."))

        with self._scan_lock:
            if self._scan_state["status"] in {"scanning", "paused"}:
                return _response(error=_error("SCAN_IN_PROGRESS", "A scan is already in progress."))
            self.scanner.reset()
            self._scan_cancelled.clear()
            self._scan_resume.set()
            scan_id = str(uuid.uuid4())
            self._scan_started_at = time.monotonic()
            self._scan_state = {
                "scanId": scan_id,
                "status": "scanning",
                "scanType": scan_type,
                "currentPath": "Preparing scan…",
                "filesScanned": 0,
                "totalFiles": sum(limit for _, _, limit in targets),
                "percentage": 0,
                "threatsFound": 0,
                "threats": [],
                "virusTotal": {
                    "status": "enabled" if self.database.get_setting("virustotal_enabled") == "1" else "disabled",
                    "filesChecked": 0,
                    "detections": 0,
                    "rateLimited": 0,
                    "lastError": "",
                },
                "elapsedSeconds": 0,
                "scanSpeed": 0,
            }

        worker = threading.Thread(
            target=self._run_scan,
            args=(targets,),
            name=f"aegis-scan-{scan_id[:8]}",
            daemon=True,
        )
        worker.start()
        return _response({"scanId": scan_id, "status": "scanning"})

    def _run_scan(self, targets: list[tuple[str, int, int]]) -> None:
        vt_settings: dict[str, Any] | None = None
        try:
            vt_settings = self._read_virustotal_settings(include_key=True)
            if vt_settings["enabled"] and not vt_settings["apiKey"]:
                raise RuntimeError("VirusTotal is enabled but its API key is unavailable.")
        except Exception:
            logger.exception("VirusTotal could not be prepared for scanning")
            self._record_virustotal_error("VirusTotal settings could not be loaded.")

        def inspect_with_virustotal(scan_result: dict[str, Any]) -> None:
            if not vt_settings or not vt_settings["enabled"] or not vt_settings["apiKey"]:
                return
            if self._scan_cancelled.is_set():
                return
            virus_total = self._scan_virustotal(scan_result["filepath"], vt_settings)
            scan_result["virusTotal"] = virus_total
            self._record_virustotal_result(virus_total)
            self._apply_virustotal_detection(scan_result)

        def update_progress(
            current_path: str,
            _: bool,
            files_scanned: int,
            total_estimated: int,
        ) -> None:
            with self._scan_lock:
                self._scan_state["currentPath"] = current_path
                current_count = (
                    files_scanned
                    if self._scan_state["scanType"] == "system"
                    else self._scan_state["filesScanned"] + 1
                )
                self._scan_state["filesScanned"] = current_count
                self._scan_state["totalFiles"] = max(
                    self._scan_state["totalFiles"], total_estimated, current_count
                )
                total = self._scan_state["totalFiles"]
                self._scan_state["percentage"] = min(
                    99, int(current_count * 100 / total) if total else 0
                )
                self._scan_state["elapsedSeconds"] = int(
                    time.monotonic() - self._scan_started_at
                )

        def inspect_and_record(scan_result: dict[str, Any]) -> None:
            inspect_with_virustotal(scan_result)
            if scan_result.get("is_threat"):
                filepath = str(scan_result.get("filepath", ""))
                self._record_scan_result(filepath, [scan_result], 0, directory_result=True)

        try:
            if targets and targets[0][0] == "__FULL_SYSTEM_SCAN__":
                self.scanner.scan_full_system(
                    progress_callback=update_progress,
                    result_callback=inspect_and_record,
                    resume_event=self._scan_resume,
                )
                return

            for path, max_depth, max_files in targets:
                while not self._scan_resume.wait(0.1):
                    if self._scan_cancelled.is_set():
                        break
                if self._scan_cancelled.is_set():
                    break
                with self._scan_lock:
                    self._scan_state["currentPath"] = path

                if os.path.isfile(path):
                    result = self.scanner.scan_file(path)
                    inspect_with_virustotal(result)
                    self._record_scan_result(path, [result], 1)
                    continue

                result = self.scanner.scan_directory(
                    path,
                    max_depth=max_depth,
                    max_files=max_files,
                    progress_callback=update_progress,
                    result_callback=inspect_with_virustotal,
                    resume_event=self._scan_resume,
                )
                self._record_scan_result(
                    path,
                    result["results"],
                    result["files_scanned"],
                    directory_result=True,
                )
        except Exception as scan_error:
            with self._scan_lock:
                self._scan_state["status"] = "error"
                self._scan_state["error"] = str(scan_error)
        finally:
            with self._scan_lock:
                if self._scan_state["status"] != "error":
                    cancelled = self._scan_cancelled.is_set()
                    self._scan_state["status"] = "cancelled" if cancelled else "completed"
                    self._scan_state["percentage"] = 100
                    self._scan_state["currentPath"] = (
                        "Scan stopped." if cancelled else "Scan complete."
                    )
                self._scan_state["elapsedSeconds"] = int(
                    time.monotonic() - self._scan_started_at
                )

    def _record_virustotal_result(self, result: dict[str, Any]) -> None:
        with self._scan_lock:
            summary = self._scan_state.get("virusTotal")
            if not isinstance(summary, dict):
                return
            status = result.get("status")
            if status in ("clean", "detected", "not_found", "queued"):
                summary["filesChecked"] += 1
            if status == "detected":
                summary["detections"] += 1
            if result.get("errorCode") == "VIRUSTOTAL_RATE_LIMIT":
                summary["rateLimited"] += 1
                summary["lastError"] = str(result.get("message", ""))
                summary["status"] = "rate_limited"
            elif status == "error":
                summary["lastError"] = str(result.get("message", ""))
                summary["status"] = "error"

    def _record_virustotal_error(self, message: str) -> None:
        with self._scan_lock:
            summary = self._scan_state.get("virusTotal")
            if isinstance(summary, dict):
                summary["status"] = "error"
                summary["lastError"] = message

    @staticmethod
    def _virustotal_error_result(code: str, message: str) -> dict[str, Any]:
        return {
            "status": "error",
            "malicious": 0,
            "suspicious": 0,
            "total": 0,
            "detections": [],
            "reportUrl": "",
            "errorCode": code,
            "message": message,
        }

    def _record_scan_result(
        self,
        path: str,
        results: list[dict[str, Any]],
        files_scanned: int,
        directory_result: bool = False,
    ) -> None:
        with self._scan_lock:
            if not directory_result:
                self._scan_state["filesScanned"] += files_scanned
            for result in results:
                if not result.get("is_threat"):
                    continue
                filepath = result.get("filepath", path)
                threat = {
                    "id": filepath,
                    "filePath": filepath,
                    "fileName": os.path.basename(filepath),
                    "threatName": result.get("threat_name") or "Unclassified threat",
                    "severity": "high",
                    "score": 0,
                    "detectedBy": result.get("detected_by", ["Aegis local scanner"]),
                    "details": result.get("details", []),
                    "hashes": {"md5": "", "sha1": "", "sha256": ""},
                    "timestamp": int(time.time() * 1000),
                    "quarantined": False,
                    "virusTotal": result.get("virusTotal"),
                }
                self._scan_state["threats"].append(threat)
            self._scan_state["threatsFound"] = len(self._scan_state["threats"])
            self._scan_state["elapsedSeconds"] = int(time.monotonic() - self._scan_started_at)

    def get_scan_status(self) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        with self._scan_lock:
            state = dict(self._scan_state)
            state["threats"] = list(self._scan_state["threats"])
            if isinstance(self._scan_state.get("virusTotal"), dict):
                state["virusTotal"] = dict(self._scan_state["virusTotal"])
            elapsed = max(time.monotonic() - self._scan_started_at, 1.0)
            state["scanSpeed"] = round(state["filesScanned"] / elapsed, 1)
        return _response(state)

    def pause_scan(self) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        with self._scan_lock:
            if self._scan_state["status"] != "scanning":
                return _response(error=_error("NO_ACTIVE_SCAN", "There is no active scan to pause."))
            self._scan_resume.clear()
            self._scan_state["status"] = "paused"
        return _response({"status": "paused"})

    def resume_scan(self) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        with self._scan_lock:
            if self._scan_state["status"] != "paused":
                return _response(error=_error("SCAN_NOT_PAUSED", "The scan is not paused."))
            self._scan_resume.set()
            self._scan_state["status"] = "scanning"
        return _response({"status": "scanning"})

    def stop_scan(self) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        with self._scan_lock:
            if self._scan_state["status"] not in {"scanning", "paused"}:
                return _response(error=_error("NO_ACTIVE_SCAN", "There is no scan to stop."))
            self._scan_cancelled.set()
            self._scan_resume.set()
        self.scanner.cancel()
        return _response({"status": "stopping"})

    def get_quarantine_files(self) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        files = []
        for item in self.quarantine.get_details():
            quarantine_path = str(item["quarantine_path"])
            try:
                timestamp = int(os.path.getmtime(quarantine_path) * 1000)
            except OSError:
                timestamp = 0
            files.append({
                "id": quarantine_path,
                "originalPath": str(item["original_path"]),
                "originalName": str(item["filename"]),
                "quarantineName": os.path.basename(quarantine_path),
                "threatName": str(item["threat"]),
                "size": int(item["size"]),
                "timestamp": timestamp,
                "quarantinedAt": str(item["date"]),
            })
        return _response(files)

    def quarantine_file(self, filepath: str, threat_name: str) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        if not isinstance(filepath, str) or not os.path.isfile(filepath):
            return _response(error=_error("FILE_NOT_FOUND", "The file is no longer available."))
        if not self.quarantine.add(filepath, threat_name, remove_original=True):
            return _response(error=_error("QUARANTINE_FAILED", "The file could not be moved to quarantine."))
        return _response({"quarantined": True})

    def restore_quarantine_file(self, quarantine_path: str) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        allowed_paths = {os.path.normcase(path) for path in self.quarantine.list_files()}
        normalized_path = os.path.normcase(os.path.abspath(quarantine_path))
        if normalized_path not in allowed_paths:
            return _response(error=_error("FILE_NOT_FOUND", "That item is not in the quarantine."))
        restored, message = self.quarantine.restore(normalized_path)
        if not restored:
            return _response(error=_error("RESTORE_FAILED", message))
        return _response({"restored": True})

    def delete_quarantine_file(self, quarantine_path: str) -> dict[str, Any]:
        backend_error = self._backend_error_response()
        if backend_error is not None:
            return backend_error
        allowed_paths = {os.path.normcase(path) for path in self.quarantine.list_files()}
        normalized_path = os.path.normcase(os.path.abspath(quarantine_path))
        if normalized_path not in allowed_paths:
            return _response(error=_error("FILE_NOT_FOUND", "That item is not in the quarantine."))
        if not self.quarantine.remove(normalized_path):
            return _response(error=_error("DELETE_FAILED", "The quarantined item could not be removed."))
        return _response({"deleted": True})

    def minimize(self) -> None:
        if self.window is not None:
            self.window.minimize()

    def start_native_drag(self) -> None:
        if os.name != "nt" or self.window is None:
            return

        native_window = getattr(self.window, "native", None)
        handle = getattr(native_window, "Handle", None)
        if handle is None:
            logger.warning("Cannot start native window drag: the native handle is unavailable")
            return
        if hasattr(handle, "ToInt32"):
            handle = handle.ToInt32()

        user32 = ctypes.windll.user32
        user32.ReleaseCapture.argtypes = []
        user32.ReleaseCapture.restype = wintypes.BOOL
        user32.SendMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        ]
        user32.SendMessageW.restype = ctypes.c_ssize_t
        user32.ReleaseCapture()
        user32.SendMessageW(handle, 0x00A1, 2, 0)

    def toggle_maximize(self) -> None:
        if self.window is not None:
            if self.is_maximized:
                self.window.restore()
            else:
                self.window.maximize()
            self.is_maximized = not self.is_maximized

    def close(self) -> None:
        self._request_shutdown()
        if self.window is not None:
            self.window.destroy()

    def on_closing(self) -> None:
        self._request_shutdown()

    def _request_shutdown(self) -> None:
        self._shutdown_requested.set()
        self._scan_cancelled.set()
        self._scan_resume.set()
        if self.scanner is not None:
            self.scanner.shutdown()


def _frontend_index() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "frontend" / "dist" / "index.html"
    return Path(__file__).resolve().parent / "frontend" / "dist" / "index.html"


def _build_frontend(
    index_path: Path,
    shutdown_event: threading.Event | None = None,
) -> None:
    if getattr(sys, "_MEIPASS", None):
        raise FileNotFoundError(
            f"The packaged React interface is missing: {index_path}. "
            "Rebuild the application with `pyinstaller main.spec`."
        )

    frontend_dir = Path(__file__).resolve().parent / "frontend"
    if not (frontend_dir / "package.json").is_file():
        raise FileNotFoundError(
            f"Cannot build the React interface: package.json was not found in {frontend_dir}."
        )
    npm_path = shutil.which("npm") or shutil.which("npm.cmd")
    if npm_path is None:
        default_npm = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / "npm.cmd"
        if default_npm.is_file():
            npm_path = str(default_npm)
    if npm_path is None:
        raise FileNotFoundError(
            "The React interface is not built and npm was not found. "
            "Install Node.js 18 or later, then launch Aegis Core again."
        )

    environment = os.environ.copy()
    npm_directory = str(Path(npm_path).parent)
    environment["PATH"] = npm_directory + os.pathsep + environment.get("PATH", "")
    for arguments in (("install",), ("run", "build")):
        command = [Path(npm_path).name, *arguments]
        if os.name == "nt":
            command = ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(command)]
        logger.info("Building React interface: npm %s", " ".join(arguments))
        creation_flags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        )
        process = subprocess.Popen(
            command,
            cwd=frontend_dir,
            env=environment,
            creationflags=creation_flags,
        )
        while process.poll() is None:
            if shutdown_event is not None and shutdown_event.wait(0.1):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return
            if shutdown_event is None:
                time.sleep(0.1)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
        if shutdown_event is not None and shutdown_event.is_set():
            return

    if not index_path.is_file():
        raise FileNotFoundError(
            f"The frontend build completed without producing the expected file: {index_path}."
        )


class AegisDesktopApp:
    def __init__(self, startup_target: str | None = None) -> None:
        self.bridge = AegisDesktopBridge(startup_target)

    def run(self) -> None:
        index_path = _frontend_index()
        query = urlencode({"scan": self.bridge.startup_target}) if self.bridge.startup_target else ""
        entry_url = index_path.as_uri() + (f"?{query}" if query else "")
        needs_build = not index_path.is_file()
        startup_page_shown = threading.Event()
        self.bridge.window = webview.create_window(
            "Aegis Core",
            _startup_page("Preparing the Aegis Core interface…") if needs_build else entry_url,
            js_api=self.bridge,
            width=1240,
            height=820,
            min_size=(960, 640),
            frameless=True,
            easy_drag=True,
            background_color="#11110f",
        )
        self.bridge.window.events.closing += self.bridge.on_closing
        if needs_build:
            self.bridge.window.events.shown += startup_page_shown.set
            threading.Thread(
                target=self._build_and_load_frontend,
                args=(index_path, entry_url, startup_page_shown),
                name="aegis-frontend-build",
                daemon=True,
            ).start()
        webview.start()

    def _build_and_load_frontend(
        self,
        index_path: Path,
        entry_url: str,
        startup_page_shown: threading.Event,
    ) -> None:
        while not startup_page_shown.wait(0.1):
            if self.bridge._shutdown_requested.is_set():
                return
        try:
            _build_frontend(index_path, self.bridge._shutdown_requested)
            if not self.bridge._shutdown_requested.is_set():
                self.bridge.window.load_url(entry_url)
        except Exception:
            logger.exception("Failed to build the React interface")
            if not self.bridge._shutdown_requested.is_set():
                self.bridge.window.load_url(_startup_page(
                    "The interface could not be built. Check the application log for details.",
                    error=True,
                ))


def _startup_page(message: str, error: bool = False) -> str:
    color = "#c16b5b" if error else "#b6a78d"
    page = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Aegis Core</title><style>"
        "html,body{height:100%;margin:0;background:#11110f;color:#e8e5de;"
        "font:14px/1.5 'Segoe UI',sans-serif}"
        "header{height:40px;box-sizing:border-box;padding:10px 16px;"
        "border-bottom:1px solid #ffffff12;-webkit-app-region:drag}"
        "main{height:calc(100% - 40px);display:grid;place-content:center;text-align:center}"
        f"p{{color:{color};margin:12px 0 0}}"
        "</style></head><body><header class=\"pywebview-drag-region\">Aegis Core</header>"
        "<main><strong>Aegis Core</strong>"
        f"<p>{escape(message)}</p></main></body></html>"
    )
    return "data:text/html;charset=utf-8," + quote(page)
