"""
Ядро Aegis Core
Содержит основные компоненты антивирусного движка
"""

from .scanner import FileScanner
from .signatures import SignatureDatabase
from .analyzer import FileAnalyzer
from .quarantine import QuarantineManager

__all__ = ['FileScanner', 'SignatureDatabase', 'FileAnalyzer', 'QuarantineManager']