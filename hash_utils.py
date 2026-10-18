"""File hash computation: single-pass multi-algorithm hashing.

Primary implementation uses Python's hashlib (fast, cross-platform).
CryptoAPI (advapi32) is available as an optional fallback on Windows.
"""
import hashlib
import logging
import math
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# I/O chunk size: 64KB balances syscall overhead vs memory usage
_CHUNK_SIZE: int = 65536


# ---------------------------------------------------------------------------
# Primary: Python hashlib (works on all platforms, handles files >2GB)
# ---------------------------------------------------------------------------

def calculate_all(filepath: str) -> Dict[str, Optional[str]]:
    """Compute MD5, SHA-1, and SHA-256 in a single pass over the file.

    Reads the file once and feeds each chunk to all three hashers
    simultaneously for maximum I/O efficiency.

    Returns a dict with keys 'md5', 'sha1', 'sha256'.
    Values are hex-digest strings, or None on error.
    """
    hashes, _ = calculate_all_with_entropy(filepath)
    return hashes


def calculate_all_with_entropy(
    filepath: str,
) -> Tuple[Dict[str, Optional[str]], Optional[float]]:
    """Compute all supported hashes and entropy from a single file pass."""
    try:
        from native_scanner import NativeScannerError, calculate_file

        try:
            native_result = calculate_file(filepath)
        except NativeScannerError as error:
            logger.warning("Native hashing failed for %s; using Python fallback: %s", filepath, error)
            native_result = None
        if native_result is not None:
            return native_result
    except ImportError:
        logger.debug("Native scanner bridge unavailable; using Python hashing.")

    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    entropy_counts = [0] * 256
    entropy_size = 0

    try:
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(_CHUNK_SIZE)
                if not chunk:
                    break
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
                sample = chunk[:max(0, 10_000 - entropy_size)]
                for value in sample:
                    entropy_counts[value] += 1
                entropy_size += len(sample)

        entropy = 0.0
        if entropy_size:
            for count in entropy_counts:
                if count:
                    probability = count / entropy_size
                    entropy -= probability * math.log2(probability)
        return ({
            'md5': md5.hexdigest(),
            'sha1': sha1.hexdigest(),
            'sha256': sha256.hexdigest(),
        }, entropy)
    except PermissionError:
        logger.warning("Permission denied hashing file: %s", filepath)
        return {'md5': None, 'sha1': None, 'sha256': None}, None
    except FileNotFoundError:
        logger.warning("File not found for hashing: %s", filepath)
        return {'md5': None, 'sha1': None, 'sha256': None}, None
    except OSError as e:
        logger.error("OS error hashing file %s: %s", filepath, e)
        return {'md5': None, 'sha1': None, 'sha256': None}, None


def calculate_md5(filepath: str) -> Optional[str]:
    """Compute MD5 hash of a file.

    Uses hashlib as primary. Falls back to CryptoAPI on Windows if
    hashlib is unavailable for some reason.
    """
    try:
        h = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(_CHUNK_SIZE), b''):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, ValueError) as e:
        logger.debug("hashlib MD5 failed for %s: %s, trying CryptoAPI", filepath, e)
        return _cryptoapi_md5(filepath)


def calculate_sha1(filepath: str) -> Optional[str]:
    """Compute SHA-1 hash of a file."""
    try:
        h = hashlib.sha1()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(_CHUNK_SIZE), b''):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, ValueError) as e:
        logger.error("SHA-1 hashing failed for %s: %s", filepath, e)
        return None


def calculate_sha256(filepath: str) -> Optional[str]:
    """Compute SHA-256 hash of a file.

    Uses hashlib as primary. Falls back to CryptoAPI on Windows if
    hashlib is unavailable for some reason.
    """
    try:
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(_CHUNK_SIZE), b''):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, ValueError) as e:
        logger.debug("hashlib SHA-256 failed for %s: %s, trying CryptoAPI", filepath, e)
        return _cryptoapi_sha256(filepath)


# ---------------------------------------------------------------------------
# Fallback: Windows CryptoAPI via ctypes (optional)
# ---------------------------------------------------------------------------

def _load_advapi32():
    """Lazily load advapi32.dll. Returns the dll handle or None."""
    try:
        import ctypes
        return ctypes.windll.advapi32
    except (AttributeError, OSError):
        return None


# CryptoAPI constants
_PROV_RSA_FULL: int = 1
_PROV_RSA_AES: int = 24
_CRYPT_VERIFYCONTEXT: int = 0xF0000000
_CALG_MD5: int = 0x00008003
_CALG_SHA_256: int = 0x0000800c
_HP_HASHVAL: int = 0x0002


def _cryptoapi_hash(
    filepath: str,
    algorithm: int,
    provider_type: int,
    digest_size: int
) -> Optional[str]:
    """Generic CryptoAPI file hashing. Internal helper.

    Args:
        filepath: Path to the file to hash.
        algorithm: CALG_* constant for the hash algorithm.
        provider_type: PROV_RSA_* constant.
        digest_size: Expected digest length in bytes (16 for MD5, 32 for SHA-256).

    Returns hex digest string or None on failure.
    """
    advapi32 = _load_advapi32()
    if advapi32 is None:
        return None

    import ctypes

    hProv = ctypes.c_void_p()
    hHash = ctypes.c_void_p()
    rgbHash = (ctypes.c_byte * digest_size)()
    cbHash = ctypes.c_uint(digest_size)

    try:
        if not advapi32.CryptAcquireContextA(
            ctypes.byref(hProv), None, None, provider_type, _CRYPT_VERIFYCONTEXT
        ):
            return None

        if not advapi32.CryptCreateHash(hProv, algorithm, 0, 0, ctypes.byref(hHash)):
            advapi32.CryptReleaseContext(hProv, 0)
            return None

        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(_CHUNK_SIZE)
                if not chunk:
                    break
                if not advapi32.CryptHashData(hHash, chunk, len(chunk), 0):
                    advapi32.CryptDestroyHash(hHash)
                    advapi32.CryptReleaseContext(hProv, 0)
                    return None

        if not advapi32.CryptGetHashParam(
            hHash, _HP_HASHVAL, ctypes.byref(rgbHash), ctypes.byref(cbHash), 0
        ):
            advapi32.CryptDestroyHash(hHash)
            advapi32.CryptReleaseContext(hProv, 0)
            return None

        hex_hash = ''.join(f'{b & 0xff:02x}' for b in rgbHash)
        return hex_hash

    except (OSError, ValueError) as e:
        logger.debug("CryptoAPI hash failed: %s", e)
        return None
    finally:
        # Always release handles to prevent resource leaks
        try:
            if hHash:
                advapi32.CryptDestroyHash(hHash)
            if hProv:
                advapi32.CryptReleaseContext(hProv, 0)
        except Exception:
            pass


def _cryptoapi_md5(filepath: str) -> Optional[str]:
    """Compute MD5 via Windows CryptoAPI (fallback)."""
    return _cryptoapi_hash(filepath, _CALG_MD5, _PROV_RSA_FULL, 16)


def _cryptoapi_sha256(filepath: str) -> Optional[str]:
    """Compute SHA-256 via Windows CryptoAPI (fallback)."""
    return _cryptoapi_hash(filepath, _CALG_SHA_256, _PROV_RSA_AES, 32)