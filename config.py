"""
Конфигурация Aegis Core
Позволяет переключаться между версиями и настраивать параметры
"""
import os
import json
from pathlib import Path

class Config:
    """Класс для управления конфигурацией приложения"""
    
    # По умолчанию используем улучшенную версию signatures
    DEFAULT_CONFIG = {
        "use_improved_signatures": True,  # Использовать signatures_improved.py с VirusTotal
        "enable_sound": True,              # Включить звуковые эффекты
        "enable_usb_monitoring": False,    # Включить мониторинг USB по умолчанию
        "enable_autorun_scanning": True,   # Сканирование автозагрузки
        "backup_on_delete": True,          # Создавать резервную копию перед удалением
        "secure_delete_passes": 3,         # Количество проходов для безопасного удаления
        "cache_duration": 604800,          # Время кэширования результатов (7 дней в секундах)
        "max_threads": 4,                  # Максимум потоков для сканирования
        "max_file_size": 104857600,        # Максимальный размер файла (100MB)
        "log_file": None,                  # Сохранять логи в файл (None = не сохранять)
        "vt_api_key_env": "VIRUSTOTAL_API_KEY",  # Имя переменной окружения для API
        "quarantine_dir": "./quarantine",  # Директория для карантина
        "backup_dir": "./backups",         # Директория для резервных копий
    }
    
    def __init__(self, config_file=None):
        """
        Инициализация конфигурации
        config_file: путь к JSON файлу конфигурации
        """
        self.config_file = config_file or Path(__file__).parent / "config.json"
        self.settings = self._load_config()
    
    def _load_config(self):
        """Загрузить конфигурацию из файла"""
        if isinstance(self.config_file, str):
            self.config_file = Path(self.config_file)
        
        # Если файл существует, загружаем его
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Объединяем с дефолтными значениями
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
            except Exception as e:
                print(f"⚠️ Ошибка при загрузке конфигурации: {e}")
                print("📝 Используются параметры по умолчанию")
        
        # Создаем файл конфигурации по умолчанию
        self._save_config(self.DEFAULT_CONFIG)
        return self.DEFAULT_CONFIG.copy()
    
    def _save_config(self, config=None):
        """Сохранить конфигурацию в файл"""
        config = config or self.settings
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✓ Конфигурация сохранена: {self.config_file}")
        except Exception as e:
            print(f"✗ Ошибка при сохранении конфигурации: {e}")
    
    def get(self, key, default=None):
        """Получить значение параметра"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Установить значение параметра"""
        self.settings[key] = value
        self._save_config()
    
    def get_vt_api_key(self):
        """Получить VirusTotal API ключ"""
        env_var = self.get("vt_api_key_env")
        return os.environ.get(env_var, "")
    
    def is_using_improved_signatures(self):
        """Используется ли улучшенная версия signatures"""
        return self.get("use_improved_signatures", True)
    
    def print_config(self):
        """Вывести текущую конфигурацию"""
        print("=" * 50)
        print("📋 КОНФИГУРАЦИЯ AEGIS CORE")
        print("=" * 50)
        for key, value in self.settings.items():
            print(f"{key:.<30} {value}")
        print("=" * 50)


# Глобальный экземпляр конфигурации
_config_instance = None

def get_config(config_file=None):
    """Получить глобальный экземпляр конфигурации"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_file)
    return _config_instance


# Пример использования
if __name__ == "__main__":
    config = get_config()
    config.print_config()
    
    # Пример изменения параметра
    # config.set("enable_sound", False)
    # config.print_config()
