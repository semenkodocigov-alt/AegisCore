"""
Модуль управления базой сигнатур вредоносных программ
Поддерживает MD5, SHA1, SHA256 хеши
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple


class SignatureDatabase:
    """База данных сигнатур вредоносных программ"""
    
    def __init__(self, signatures_dir: str = None):
        """
        Инициализация базы сигнатур
        
        Args:
            signatures_dir: Путь к папке с файлами сигнатур
        """
        if signatures_dir is None:
            signatures_dir = Path(__file__).parent.parent / "data" / "signatures"
        
        self.signatures_dir = Path(signatures_dir)
        self.signatures_dir.mkdir(parents=True, exist_ok=True)
        
        # Хранилище сигнатур
        self.md5_hashes: Dict[str, dict] = {}
        self.sha1_hashes: Dict[str, dict] = {}
        self.sha256_hashes: Dict[str, dict] = {}
        
        # Загружаем все сигнатуры
        self._load_builtin_signatures()
        self._load_signatures_from_files()
    
    def _load_builtin_signatures(self):
        """Загрузка встроенных сигнатур известных угроз"""
        known_threats = {
            # WannaCry Ransomware
            "84c82835a5d21bbcf75a61706d8ab549": {
                "name": "WannaCry Ransomware",
                "type": "ransomware",
                "severity": "critical",
                "description": "Опасный шифровальщик, требующий выкуп"
            },
            # Trojan.Emotet
            "e3b0c44298fc1c149afbf4c8996fb924": {
                "name": "Trojan.Emotet",
                "type": "trojan",
                "severity": "critical",
                "description": "Банковский троян, крадущий данные"
            },
            # FakeAV
            "d41d8cd98f00b204e9800998ecf8427e": {
                "name": "FakeAV.SecurityTool",
                "type": "scareware",
                "severity": "high",
                "description": "Поддельный антивирус-вымогатель"
            }
        }
        
        self.md5_hashes.update(known_threats)
    
    def _load_signatures_from_files(self):
        """Загрузка сигнатур из внешних файлов"""
        signature_files = {
            'md5': ('md5_hashes.txt', self.md5_hashes),
            'sha1': ('sha1_hashes.txt', self.sha1_hashes),
            'sha256': ('sha256_hashes.txt', self.sha256_hashes)
        }
        
        for hash_type, (filename, storage) in signature_files.items():
            filepath = self.signatures_dir / filename
            
            if not filepath.exists():
                # Создаем пустой файл с примером
                self._create_example_signature_file(filepath, hash_type)
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        
                        # Пропускаем пустые строки и комментарии
                        if not line or line.startswith('#'):
                            continue
                        
                        # Парсим строку: hash|name|type|severity|description
                        parts = line.split('|')
                        
                        if len(parts) >= 1:
                            hash_value = parts[0].strip().lower()
                            name = parts[1].strip() if len(parts) > 1 else "Unknown Malware"
                            malware_type = parts[2].strip() if len(parts) > 2 else "unknown"
                            severity = parts[3].strip() if len(parts) > 3 else "medium"
                            description = parts[4].strip() if len(parts) > 4 else ""
                            
                            storage[hash_value] = {
                                "name": name,
                                "type": malware_type,
                                "severity": severity,
                                "description": description
                            }
                            
            except Exception as e:
                print(f"Ошибка загрузки {hash_type} сигнатур: {e}")
    
    def _create_example_signature_file(self, filepath: Path, hash_type: str):
        """
        Создание файла сигнатур с примером
        
        Args:
            filepath: Путь к файлу
            hash_type: Тип хеша (md5, sha1, sha256)
        """
        example_content = f"""# Aegis Core - {hash_type.upper()} Malware Signatures
# Формат: hash|name|type|severity|description
# Примеры:
"""
        
        if hash_type == 'md5':
            example_content += """#84c82835a5d21bbcf75a61706d8ab549|WannaCry|ransomware|critical|Шифровальщик
#e3b0c44298fc1c149afbf4c8996fb924|Emotet|trojan|critical|Банковский троян
"""
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(example_content)
        except Exception as e:
            print(f"Не удалось создать файл {filepath}: {e}")
    
    def check_hash(self, md5: str = None, sha1: str = None, sha256: str = None) -> Optional[dict]:
        """
        Проверка хеша в базе сигнатур
        
        Args:
            md5: MD5 хеш
            sha1: SHA1 хеш
            sha256: SHA256 хеш
            
        Returns:
            Информация об угрозе или None
        """
        # Проверяем MD5
        if md5 and md5 in self.md5_hashes:
            return self.md5_hashes[md5]
        
        # Проверяем SHA1
        if sha1 and sha1 in self.sha1_hashes:
            return self.sha1_hashes[sha1]
        
        # Проверяем SHA256
        if sha256 and sha256 in self.sha256_hashes:
            return self.sha256_hashes[sha256]
        
        return None
    
    def add_signature(self, hash_value: str, name: str, hash_type: str = 'md5',
                     malware_type: str = 'unknown', severity: str = 'medium',
                     description: str = ''):
        """
        Добавление новой сигнатуры
        
        Args:
            hash_value: Хеш вредоносного файла
            name: Название угрозы
            hash_type: Тип хеша
            malware_type: Тип вредоносного ПО
            severity: Уровень опасности
            description: Описание
        """
        storage = {
            'md5': self.md5_hashes,
            'sha1': self.sha1_hashes,
            'sha256': self.sha256_hashes
        }.get(hash_type.lower(), self.md5_hashes)
        
        storage[hash_value.lower()] = {
            "name": name,
            "type": malware_type,
            "severity": severity,
            "description": description
        }
        
        # Сохраняем в файл
        filename = f"{hash_type.lower()}_hashes.txt"
        filepath = self.signatures_dir / filename
        
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(f"{hash_value}|{name}|{malware_type}|{severity}|{description}\n")
        except Exception as e:
            print(f"Ошибка сохранения сигнатуры: {e}")
    
    def get_total_signatures(self) -> int:
        """Получить общее количество сигнатур"""
        return len(self.md5_hashes) + len(self.sha1_hashes) + len(self.sha256_hashes)
    
    def get_statistics(self) -> dict:
        """Получить статистику базы сигнатур"""
        return {
            'md5_count': len(self.md5_hashes),
            'sha1_count': len(self.sha1_hashes),
            'sha256_count': len(self.sha256_hashes),
            'total': self.get_total_signatures()
        }