"""Управление карантином"""
import os
import shutil
import time

class QuarantineManager:
    def __init__(self):
        # Папка карантина в домашней директории
        self.quarantine_dir = os.path.join(os.path.expanduser("~"), "AegisCore_Quarantine")
        os.makedirs(self.quarantine_dir, exist_ok=True)
        
        self.files = []
    
    def add(self, filepath):
        """Добавить файл в карантин"""
        try:
            if not os.path.exists(filepath):
                return False
            
            timestamp = int(time.time())
            name = os.path.basename(filepath)
            quarantine_name = f"q_{timestamp}_{name}"
            quarantine_path = os.path.join(self.quarantine_dir, quarantine_name)
            
            shutil.copy2(filepath, quarantine_path)
            self.files.append(quarantine_path)
            
            return True
        except Exception as e:
            print(f"Ошибка карантина: {e}")
            return False
    
    def count(self):
        """Количество файлов в карантине"""
        return len(self.files)
    
    def list_files(self):
        """Список файлов"""
        return self.files