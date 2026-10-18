"""Windows DPAPI-backed protection for locally stored integration secrets."""
from __future__ import annotations

import base64
import ctypes
import os
from ctypes import wintypes


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _protect(data: bytes, unprotect: bool) -> bytes:
    if os.name != "nt":
        raise OSError("Windows DPAPI is required to protect the VirusTotal API key.")

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    input_buffer = ctypes.create_string_buffer(data, len(data))
    input_blob = _DataBlob(
        len(data),
        ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    output_blob = _DataBlob()
    protect = crypt32.CryptUnprotectData if unprotect else crypt32.CryptProtectData
    protect.restype = wintypes.BOOL
    protect.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR) if unprotect else wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    kernel32.LocalFree.restype = ctypes.c_void_p
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    if unprotect:
        success = protect(
            ctypes.byref(input_blob), None, None, None, None, 0x1,
            ctypes.byref(output_blob),
        )
    else:
        success = protect(
            ctypes.byref(input_blob),
            "Aegis Core VirusTotal API key",
            None, None, None, 0x1,
            ctypes.byref(output_blob),
        )
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(output_blob.pbData, ctypes.c_void_p))


def protect_secret(secret: str) -> str:
    encrypted = _protect(secret.encode("utf-8"), unprotect=False)
    return base64.b64encode(encrypted).decode("ascii")


def unprotect_secret(encrypted_secret: str) -> str:
    encrypted = base64.b64decode(encrypted_secret, validate=True)
    return _protect(encrypted, unprotect=True).decode("utf-8")
