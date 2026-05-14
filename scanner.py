"""Сканер файлов"""
import os
from config import get_config
from analyzer import FileAnalyzer
from hash_utils import calculate_all

config = get_config()
if config.is_using_improved_signatures():
    from signatures_improved import SignatureDatabase
else:
    from signatures import SignatureDatabase

class FileScanner:
    SUSPICIOUS_EXTENSIONS = {
        '.exe', '.dll', '.sys', '.scr', '.ocx', '.drv',
        '.bat', '.cmd', '.vbs', '.js', '.jse', '.wsf', '.wsh',
        '.ps1', '.psm1', '.psd1'
    }
    SUSPICIOUS_NAMES = [
        'keygen', 'crack', 'patch', 'hacktool', 'activator',
        'injector', 'bypass', 'stealer', 'keylogger', 'miner',
        'trojan', 'virus', 'worm', 'ransomware', 'backdoor',
        'rootkit', 'spyware', 'adware', 'malware', 'exploit',
        'payload', 'shellcode', 'dropper', 'loader', 'bot',
        'rat', 'remote', 'access', 'hack', 'cheat', 'trainer',
        'packer', 'binder', 'obfuscator', 'deobfuscator'
    ]

    def __init__(self):
        self.sig_db = SignatureDatabase()
        self.analyzer = FileAnalyzer(self.sig_db)

    def _should_analyze_file(self, filepath, filename=None):
        filename = filename or os.path.basename(filepath).lower()
        ext = os.path.splitext(filename)[1].lower()
        if ext in self.SUSPICIOUS_EXTENSIONS:
            return True
        for name in self.SUSPICIOUS_NAMES:
            if name in filename:
                return True
        return False
    
    def scan_file(self, filepath):
        """
        Сканирование одного файла
        Возвращает: словарь с результатом
        """
        result = {
            'filepath': filepath,
            'is_threat': False,
            'threat_name': '',
            'details': []
        }
        
        try:
            # Проверяем существование
            if not os.path.exists(filepath):
                return result
            
            # Проверяем размер
            size = os.path.getsize(filepath)
            if size > 100 * 1024 * 1024 or size == 0:
                return result
            
            # Считаем хеши
            hashes = calculate_all(filepath)
            
            # Проверяем сигнатуры
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
                result['details'].append(f"Найдена сигнатура: {sig_match['name']}")
                return result
            
            # Эвристический анализ только для подозрительных файлов
            if self._should_analyze_file(filepath, filename):
                status, threats, score = self.analyzer.analyze(filepath)
            else:
                status, threats, score = 'clean', [], 0
            
            if status != 'clean':
                result['is_threat'] = True
                result['threat_name'] = 'Подозрительный файл'
                result['details'] = threats + [f"Оценка угрозы: {score}"]
        
        except Exception as e:
            result['details'].append(f"Ошибка: {str(e)}")
        
        return result
    
    def scan_directory(self, path, max_depth=2, max_files=500, callback=None):
        """
        Сканирование папки
        Возвращает: словарь с результатом и количеством просканированных файлов
        """
        results = []
        files_scanned = 0
        
        try:
            for root, dirs, files in os.walk(path):
                if files_scanned >= max_files:
                    break
                
                # Ограничение глубины
                depth = root[len(path):].count(os.sep)
                if depth > max_depth:
                    dirs.clear()
                    continue
                
                for file in files:
                    if files_scanned >= max_files:
                        break
                    
                    filepath = os.path.join(root, file)
                    result = self.scan_file(filepath)
                    
                    if result['is_threat']:
                        results.append(result)
                    
                    if callable(callback):
                        try:
                            callback(filepath, result['is_threat'])
                        except Exception:
                            pass
                    
                    files_scanned += 1
        
        except Exception as e:
            print(f"Ошибка сканирования: {e}")
        
        return {
            'results': results,
            'files_scanned': files_scanned
        }