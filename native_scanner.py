"""Optional ctypes bridge to the Windows C++ scanner accelerator.

The native DLL is built lazily into the user's temporary directory. Any
compiler or native-runtime failure falls back to the Python implementations.
"""
from __future__ import annotations

import ctypes
import logging
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ENTROPY_SAMPLE_SIZE = 10_000
_build_lock = threading.Lock()
_native: ctypes.CDLL | None = None
_attempted_load = False

_FileCallback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)


class NativeScannerError(RuntimeError):
    """Raised when an available native operation fails."""


def _source_path() -> Path:
    source = Path(__file__).resolve().with_name("native_scanner.cpp")
    if source.is_file():
        return source
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled_source = Path(bundle_root) / "native_scanner.cpp"
        if bundled_source.is_file():
            return bundled_source
    return source


def _compiler() -> tuple[str, str] | None:
    if os.name != "nt":
        return None
    for name in ("g++", "clang++"):
        executable = shutil.which(name)
        if executable:
            return name, executable
    candidates = (
        ("g++", Path(r"C:\mingw64\bin\g++.exe")),
        ("g++", Path(r"C:\msys64\mingw64\bin\g++.exe")),
        ("clang++", Path(r"C:\Program Files\LLVM\bin\clang++.exe")),
    )
    for name, candidate in candidates:
        if candidate.is_file():
            return name, str(candidate)
    return None


def _library_path() -> Path:
    abi = f"{sys.implementation.cache_tag}-{ctypes.sizeof(ctypes.c_void_p) * 8}"
    return Path(tempfile.gettempdir()) / "AegisCore" / f"native-scanner-{abi}-static.dll"


def _configure_library(library: ctypes.CDLL) -> None:
    library.aegis_hash_file.argtypes = (
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_size_t,
    )
    library.aegis_hash_file.restype = ctypes.c_int
    library.aegis_entropy.argtypes = (ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t)
    library.aegis_entropy.restype = ctypes.c_double
    library.aegis_signature_index_create.argtypes = ()
    library.aegis_signature_index_create.restype = ctypes.c_void_p
    library.aegis_signature_index_clear.argtypes = (ctypes.c_void_p,)
    library.aegis_signature_index_add.argtypes = (
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
    )
    library.aegis_signature_index_add.restype = ctypes.c_int
    library.aegis_signature_index_match.argtypes = (
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_size_t,
    )
    library.aegis_signature_index_match.restype = ctypes.c_int
    library.aegis_signature_index_destroy.argtypes = (ctypes.c_void_p,)
    library.aegis_walk_directory.argtypes = (
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_size_t,
        _FileCallback,
        ctypes.c_void_p,
    )
    library.aegis_walk_directory.restype = ctypes.c_longlong


def _load_native() -> ctypes.CDLL | None:
    global _native, _attempted_load
    if _native is not None:
        return _native
    if _attempted_load:
        return None
    with _build_lock:
        if _native is not None:
            return _native
        if _attempted_load:
            return None
        _attempted_load = True
        if os.name != "nt":
            return None

        source = _source_path()
        compiler = _compiler()
        if not source.is_file() or compiler is None:
            logger.info("Native scanner unavailable; using Python scanner.")
            return None

        output = _library_path()
        try:
            if not output.is_file() or output.stat().st_mtime < source.stat().st_mtime:
                output.parent.mkdir(parents=True, exist_ok=True)
                name, executable = compiler
                command = [
                    executable, "-shared", "-static", "-O3", "-std=c++17",
                    str(source), "-o", str(output),
                ]
                if name == "g++":
                    command.append("-lbcrypt")
                else:
                    command.extend(("-lbcrypt",))
                completed = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if completed.returncode != 0:
                    output.unlink(missing_ok=True)
                    raise NativeScannerError(
                        completed.stderr.strip() or "C++ compiler exited unsuccessfully."
                    )
            library = ctypes.CDLL(str(output))
            _configure_library(library)
            _native = library
            logger.info("Native C++ scanner is available.")
        except (OSError, subprocess.SubprocessError, NativeScannerError) as error:
            logger.warning("Could not load native scanner; using Python fallback: %s", error)
            return None
    return _native


def is_available() -> bool:
    """Build and report whether the native library can be used."""
    return _load_native() is not None


def calculate_file(filepath: str) -> tuple[dict[str, str], float] | None:
    """Return native hashes and sampled entropy, or None if unavailable."""
    library = _load_native()
    if library is None:
        return None
    md5 = ctypes.create_string_buffer(33)
    sha1 = ctypes.create_string_buffer(41)
    sha256 = ctypes.create_string_buffer(65)
    entropy = ctypes.c_double()
    error = ctypes.create_string_buffer(512)
    try:
        status = library.aegis_hash_file(
            os.fsencode(filepath), md5, sha1, sha256, ctypes.byref(entropy), error, len(error)
        )
    except (OSError, ctypes.ArgumentError) as native_error:
        raise NativeScannerError("Native hashing call failed.") from native_error
    if status != 0:
        raise NativeScannerError(error.value.decode("utf-8", errors="replace"))
    hashes = {"md5": md5.value.decode("ascii"), "sha1": sha1.value.decode("ascii"),
              "sha256": sha256.value.decode("ascii")}
    return hashes, entropy.value


def calculate_all(filepath: str) -> dict[str, str] | None:
    """Return native MD5, SHA-1, and SHA-256 values, or None if unavailable."""
    result = calculate_file(filepath)
    return result[0] if result is not None else None


def calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy using native code when it has been loaded."""
    if not data:
        return 0.0
    sample = data[:_ENTROPY_SAMPLE_SIZE]
    library = _native
    if library is not None:
        buffer = (ctypes.c_ubyte * len(sample)).from_buffer_copy(sample)
        return float(library.aegis_entropy(buffer, len(sample)))

    counts = [0] * 256
    for value in sample:
        counts[value] += 1
    size = len(sample)
    return -sum(
        (count / size) * math.log2(count / size)
        for count in counts
        if count
    )


class NativeSignatureIndex:
    """Native local hash index initialized from a scanner's signature database."""

    def __init__(self, database: Any) -> None:
        library = _load_native()
        if library is None:
            raise NativeScannerError("Native scanner is unavailable.")
        self._library = library
        self._handle = library.aegis_signature_index_create()
        if not self._handle:
            raise NativeScannerError("Could not allocate the native signature index.")
        self._sha256_first = hasattr(database, "signatures")
        try:
            self.refresh(database)
        except Exception:
            library.aegis_signature_index_destroy(self._handle)
            self._handle = None
            raise

    def refresh(self, database: Any) -> None:
        self._library.aegis_signature_index_clear(self._handle)
        maps = (
            (getattr(database, "signatures", None),)
            if self._sha256_first
            else tuple(
                getattr(database, name, None)
                for name in ("md5_hashes", "sha1_hashes", "sha256_hashes")
            )
        )
        for signatures in maps:
            if not isinstance(signatures, Mapping):
                continue
            for file_hash, details in signatures.items():
                if isinstance(details, Mapping):
                    name = details.get("name", details.get("threat_name", file_hash))
                else:
                    name = details
                encoded_hash = str(file_hash).lower().encode("ascii", errors="ignore")
                encoded_name = str(name).encode("utf-8")
                if not self._library.aegis_signature_index_add(
                    self._handle, encoded_hash, encoded_name
                ):
                    raise NativeScannerError("Could not add a native signature.")

    def match(self, hashes: Mapping[str, str | None]) -> dict[str, str] | None:
        name = ctypes.create_string_buffer(1024)
        try:
            matched = self._library.aegis_signature_index_match(
                self._handle,
                (hashes.get("md5") or "").encode("ascii"),
                (hashes.get("sha1") or "").encode("ascii"),
                (hashes.get("sha256") or "").encode("ascii"),
                int(self._sha256_first),
                name,
                len(name),
            )
        except (OSError, ctypes.ArgumentError) as native_error:
            raise NativeScannerError("Native signature matching call failed.") from native_error
        if matched < 0:
            raise NativeScannerError("Native signature matching failed.")
        return {"name": name.value.decode("utf-8")} if matched else None

    def close(self) -> None:
        handle = getattr(self, "_handle", None)
        if handle:
            self._library.aegis_signature_index_destroy(self._handle)
            self._handle = None

    def __del__(self) -> None:
        self.close()


def walk_directory(
    path: str,
    max_depth: int,
    max_files: int,
    callback: Callable[[str], bool],
) -> int | None:
    """Walk files natively; return None when native support is unavailable."""
    library = _load_native()
    if library is None:
        return None

    callback_error: list[BaseException] = []

    @_FileCallback
    def visit(encoded_path: bytes, _: int) -> int:
        try:
            return int(bool(callback(os.fsdecode(encoded_path))))
        except BaseException as error:
            callback_error.append(error)
            return 0

    try:
        count = library.aegis_walk_directory(
            os.fsencode(path), max_depth, max_files, visit, None
        )
    except (OSError, ctypes.ArgumentError) as native_error:
        raise NativeScannerError("Native directory traversal call failed.") from native_error
    if callback_error:
        raise callback_error[0]
    if count < 0:
        raise NativeScannerError(f"Native directory traversal could not open: {path}")
    return int(count)
