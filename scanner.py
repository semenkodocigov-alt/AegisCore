"""Сканер файлов"""
import os
from signatures import SignatureDatabase
from analyzer import FileAnalyzer
from hash_utils import calculate_all

class FileScanner:
    def __init__(self):
        self.sig_db = SignatureDatabase()
        self.analyzer = FileAnalyzer()
    
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
            sig_match = self.sig_db.check_hash(
                md5=hashes['md5'],
                sha1=hashes['sha1'],
                sha256=hashes['sha256']
            )
            
            if sig_match:
                result['is_threat'] = True
                result['threat_name'] = sig_match['name']
                result['details'].append(f"Найдена сигнатура: {sig_match['name']}")
                return result
            
            # Эвристический анализ
            status, threats, score = self.analyzer.analyze(filepath)
            
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