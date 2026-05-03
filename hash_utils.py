"""Вычисление хешей файлов"""
import hashlib

def calculate_md5(filepath):
    """MD5 хеш файла"""
    try:
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None

def calculate_sha1(filepath):
    """SHA1 хеш файла"""
    try:
        hasher = hashlib.sha1()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None

def calculate_sha256(filepath):
    """SHA256 хеш файла"""
    try:
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None

def calculate_all(filepath):
    """Все хеши сразу"""
    return {
        'md5': calculate_md5(filepath),
        'sha1': calculate_sha1(filepath),
        'sha256': calculate_sha256(filepath)
    }