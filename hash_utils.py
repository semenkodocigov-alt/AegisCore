"""Вычисление хешей файлов через C++ (CryptoAPI)"""
import ctypes
import os

# Загрузка advapi32.dll
advapi32 = ctypes.windll.advapi32

# Константы
PROV_RSA_FULL = 1
PROV_RSA_AES = 24
CRYPT_VERIFYCONTEXT = 0xF0000000
CALG_MD5 = 0x00008003
CALG_SHA_256 = 0x0000800c
HP_HASHVAL = 0x0002

def calculate_md5(filepath):
    """MD5 хеш файла через CryptoAPI"""
    try:
        hProv = ctypes.c_void_p()
        hHash = ctypes.c_void_p()
        rgbHash = (ctypes.c_byte * 16)()
        cbHash = ctypes.c_uint(16)

        if not advapi32.CryptAcquireContextA(ctypes.byref(hProv), None, None, PROV_RSA_FULL, CRYPT_VERIFYCONTEXT):
            return None

        if not advapi32.CryptCreateHash(hProv, CALG_MD5, 0, 0, ctypes.byref(hHash)):
            advapi32.CryptReleaseContext(hProv, 0)
            return None

        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                if not advapi32.CryptHashData(hHash, chunk, len(chunk), 0):
                    advapi32.CryptDestroyHash(hHash)
                    advapi32.CryptReleaseContext(hProv, 0)
                    return None

        if not advapi32.CryptGetHashParam(hHash, HP_HASHVAL, ctypes.byref(rgbHash), ctypes.byref(cbHash), 0):
            advapi32.CryptDestroyHash(hHash)
            advapi32.CryptReleaseContext(hProv, 0)
            return None

        hex_hash = ''.join(f'{b & 0xff:02x}' for b in rgbHash)

        advapi32.CryptDestroyHash(hHash)
        advapi32.CryptReleaseContext(hProv, 0)
        return hex_hash
    except:
        return None

def calculate_sha1(filepath):
    """SHA1 хеш файла (оставлен на Python для совместимости)"""
    import hashlib
    try:
        hasher = hashlib.sha1()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None

def calculate_sha256(filepath):
    """SHA256 хеш файла через CryptoAPI"""
    try:
        hProv = ctypes.c_void_p()
        hHash = ctypes.c_void_p()
        rgbHash = (ctypes.c_byte * 32)()
        cbHash = ctypes.c_uint(32)

        if not advapi32.CryptAcquireContextA(ctypes.byref(hProv), None, None, PROV_RSA_AES, CRYPT_VERIFYCONTEXT):
            return None

        if not advapi32.CryptCreateHash(hProv, CALG_SHA_256, 0, 0, ctypes.byref(hHash)):
            advapi32.CryptReleaseContext(hProv, 0)
            return None

        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                if not advapi32.CryptHashData(hHash, chunk, len(chunk), 0):
                    advapi32.CryptDestroyHash(hHash)
                    advapi32.CryptReleaseContext(hProv, 0)
                    return None

        if not advapi32.CryptGetHashParam(hHash, HP_HASHVAL, ctypes.byref(rgbHash), ctypes.byref(cbHash), 0):
            advapi32.CryptDestroyHash(hHash)
            advapi32.CryptReleaseContext(hProv, 0)
            return None

        hex_hash = ''.join(f'{b & 0xff:02x}' for b in rgbHash)

        advapi32.CryptDestroyHash(hHash)
        advapi32.CryptReleaseContext(hProv, 0)
        return hex_hash
    except:
        return None

def calculate_all(filepath):
    """Все хеши сразу"""
    return {
        'md5': calculate_md5(filepath),
        'sha1': calculate_sha1(filepath),
        'sha256': calculate_sha256(filepath)
    }