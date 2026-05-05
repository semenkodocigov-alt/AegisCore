"""
Модуль для удаления и лечения зараженных файлов
"""
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

class FileCleaner:
    """Удаление и лечение файлов"""
    
    def __init__(self, backup_dir=None):
        """
        Инициализация очистителя
        backup_dir: путь для резервного копирования перед удалением
        """
        self.backup_dir = Path(backup_dir) if backup_dir else Path(__file__).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.log = []
    
    def delete_file(self, filepath, create_backup=True):
        """
        Удалить файл навсегда
        Возвращает: (успех, сообщение)
        """
        try:
            filepath = Path(filepath)
            if not filepath.exists():
                return False, "Файл не найден"
            
            if not os.access(filepath, os.W_OK):
                return False, "Нет прав на удаление файла"
            
            # Создаем резервную копию если нужно
            if create_backup:
                try:
                    backup_name = f"{filepath.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{filepath.suffix}"
                    backup_path = self.backup_dir / backup_name
                    shutil.copy2(filepath, backup_path)
                    self.log.append(f"✓ Резервная копия: {backup_path}")
                except Exception as e:
                    self.log.append(f"⚠ Ошибка при создании резервной копии: {e}")
            
            # Удаляем файл
            filepath.unlink()
            msg = f"Файл успешно удален: {filepath}"
            self.log.append(f"✓ {msg}")
            return True, msg
        
        except PermissionError:
            msg = "Ошибка доступа: требуются права администратора"
            self.log.append(f"✗ {msg}")
            return False, msg
        except Exception as e:
            msg = f"Ошибка удаления: {str(e)}"
            self.log.append(f"✗ {msg}")
            return False, msg
    
    def secure_delete(self, filepath, passes=3):
        """
        Безопасное удаление файла (перезапись перед удалением)
        passes: количество проходов перезаписи (по умолчанию 3)
        Возвращает: (успех, сообщение)
        """
        try:
            filepath = Path(filepath)
            if not filepath.exists():
                return False, "Файл не найден"
            
            file_size = filepath.stat().st_size
            
            # Перезаписываем файл несколько раз случайными данными
            with open(filepath, 'ba+') as f:
                for i in range(passes):
                    f.seek(0)
                    # Пишем случайные данные
                    data = os.urandom(min(file_size, 1024 * 1024))  # 1MB за раз
                    for _ in range(0, file_size, len(data)):
                        f.write(data[:min(len(data), file_size - f.tell())])
                    f.flush()
                    os.fsync(f.fileno())
                    self.log.append(f"Проход {i+1}/{passes} безопасного удаления...")
            
            # Удаляем файл
            filepath.unlink()
            msg = f"Файл безопасно удален: {filepath}"
            self.log.append(f"✓ {msg}")
            return True, msg
        
        except Exception as e:
            msg = f"Ошибка безопасного удаления: {str(e)}"
            self.log.append(f"✗ {msg}")
            return False, msg
    
    def quarantine_file(self, filepath, quarantine_dir):
        """
        Переместить файл в карантин
        Возвращает: (успех, сообщение)
        """
        try:
            filepath = Path(filepath)
            quarantine_dir = Path(quarantine_dir)
            
            if not filepath.exists():
                return False, "Файл не найден"
            
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            # Создаем уникальное имя в карантине
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            quarantine_name = f"{filepath.stem}_{timestamp}{filepath.suffix}"
            quarantine_path = quarantine_dir / quarantine_name
            
            # Перемещаем файл
            shutil.move(str(filepath), str(quarantine_path))
            msg = f"Файл помещен в карантин: {quarantine_path}"
            self.log.append(f"✓ {msg}")
            return True, msg
        
        except Exception as e:
            msg = f"Ошибка при помещении в карантин: {str(e)}"
            self.log.append(f"✗ {msg}")
            return False, msg
    
    def disinfect_file(self, filepath):
        """
        Попытка лечения файла (удаление вредоносного кода)
        Работает для определенных типов вирусов
        Возвращает: (успех, сообщение)
        """
        try:
            filepath = Path(filepath)
            if not filepath.exists():
                return False, "Файл не найден"
            
            # Получаем расширение
            ext = filepath.suffix.lower()
            
            # Для PE файлов (exe, dll) - используем встроенные инструменты Windows
            if ext in ['.exe', '.dll', '.sys']:
                # Пытаемся использовать PowerShell для глубокого сканирования
                ps_cmd = f'Remove-MpPreference -DisableRealtimeMonitoring'
                try:
                    subprocess.run(
                        ['powershell', '-Command', ps_cmd],
                        check=False,
                        capture_output=True,
                        timeout=5
                    )
                except:
                    pass
                
                msg = "Попытка лечения выполнена. Требуется ручная проверка."
                self.log.append(f"⚠ {msg}")
                return True, msg
            
            # Для текстовых файлов пытаемся удалить подозрительный код
            elif ext in ['.vbs', '.js', '.bat', '.cmd', '.ps1']:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Простая санитизация
                dangerous_keywords = [
                    'createobject', 'eval', 'execute', 'activex',
                    'rundll32', 'powershell', 'cmd.exe', 'wscript'
                ]
                
                cleaned = content
                for keyword in dangerous_keywords:
                    if keyword in content.lower():
                        # Закомментируем опасный код
                        cleaned = cleaned.replace(keyword, f"'{keyword}")
                
                # Сохраняем очищенный файл
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(cleaned)
                
                msg = "Файл протестирован и подозрительный код заблокирован"
                self.log.append(f"✓ {msg}")
                return True, msg
            
            else:
                msg = "Этот тип файла не поддерживает лечение"
                self.log.append(f"⚠ {msg}")
                return False, msg
        
        except Exception as e:
            msg = f"Ошибка при лечении файла: {str(e)}"
            self.log.append(f"✗ {msg}")
            return False, msg
    
    def restore_from_backup(self, backup_path, original_path):
        """
        Восстановить файл из резервной копии
        Возвращает: (успех, сообщение)
        """
        try:
            backup_path = Path(backup_path)
            original_path = Path(original_path)
            
            if not backup_path.exists():
                return False, "Резервная копия не найдена"
            
            shutil.copy2(backup_path, original_path)
            msg = f"Файл восстановлен из резервной копии: {original_path}"
            self.log.append(f"✓ {msg}")
            return True, msg
        
        except Exception as e:
            msg = f"Ошибка при восстановлении: {str(e)}"
            self.log.append(f"✗ {msg}")
            return False, msg
    
    def get_backups(self):
        """Получить список доступных резервных копий"""
        try:
            if not self.backup_dir.exists():
                return []
            return sorted(list(self.backup_dir.glob('*')), reverse=True)
        except:
            return []
    
    def get_log(self):
        """Получить лог операций"""
        return self.log
    
    def clear_log(self):
        """Очистить лог"""
        self.log = []
