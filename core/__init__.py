"""
Ядро Aegis Core
Содержит основные компоненты антивирусного движка
"""
import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scanner import FileScanner
from analyzer import FileAnalyzer
from quarantine import QuarantineManager
from config import get_config

cfg = get_config()
if cfg.is_using_improved_signatures():
    from signatures_improved import SignatureDatabase
else:
    from signatures import SignatureDatabase

__all__ = ['FileScanner', 'SignatureDatabase', 'FileAnalyzer', 'QuarantineManager']
