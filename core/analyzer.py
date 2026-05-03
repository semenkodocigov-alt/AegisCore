"""
Модуль анализа файлов на наличие угроз
Включает эвристический анализ и анализ PE-файлов
"""

import os
import math
from typing import List, Tuple, Dict


class FileAnalyzer:
    """Анализатор файлов на подозрительную активность"""
    
    # Подозрительные API-вызовы в Windows
    SUSPICIOUS_API_CALLS = [
        b'CreateRemoteThread',
        b'VirtualAllocEx',
        b'WriteProcessMemory',
        b'SetWindowsHookEx',
        b'GetAsyncKeyState',
        b'URLDownloadToFile',
        b'WinHttpOpen',
        b'InternetOpenUrl',
        b'NtCreateThreadEx',
        b'RtlCreateUserThread',
        b'QueueUserAPC',
        b'OpenProcess',
        b'ReadProcessMemory',
        b'LoadLibraryA',
        b'GetProcAddress'
    ]
    
    # Подозрительные имена файлов
    SUSPICIOUS_NAMES = [
        'keygen', 'crack', 'patch', 'hacktool', 'activator',
        'injector', 'bypass', 'stealer', 'keylogger', 'miner',
        'ransomware', 'trojan', 'backdoor', 'exploit', 'payload',
        'cheat', 'hack', 'unlocker', 'generator'
    ]
    
    # Подозрительные строки в бинарных файлах
    SUSPICIOUS_STRINGS = [
        'keylog', 'backdoor', 'trojan', 'exploit', 'inject',
        'bypass', 'crack', 'hack', 'password', 'credential',
        'bitcoin', 'wallet', 'ransom', 'encrypt', 'steal'
    ]
    
    # Опасные расширения файлов
    DANGEROUS_EXTENSIONS = {
        '.exe': 'Исполняемый файл Windows',
        '.scr': 'Заставка (может содержать вирус)',
        '.bat': 'Пакетный файл',
        '.cmd': 'Командный файл',
        '.ps1': 'Скрипт PowerShell',
        '.vbs': 'Скрипт Visual Basic',
        '.js': 'JavaScript файл',
        '.jar': 'Java архив',
        '.dll': 'Динамическая библиотека',
        '.sys': 'Системный драйвер'
    }
    
    def __init__(self):
        """Инициализация анализатора"""
        self.min_suspicious_apis = 3  # Минимум API для подозрения
        self.high_entropy_threshold = 7.5  # Порог высокой энтропии
    
    def analyze(self, filepath: str) -> Tuple[str, List[str]]:
        """
        Полный анализ файла
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            (статус, список угроз)
            Статус: 'clean', 'suspicious', 'malicious'
        """
        threats = []
        
        try:
            # Базовая информация
            filename = os.path.basename(filepath).lower()
            extension = os.path.splitext(filename)[1].lower()
            file_size = os.path.getsize(filepath)
            
            # 1. Проверка имени файла
            name_threats = self._check_filename(filename)
            threats.extend(name_threats)
            
            # 2. Проверка расширения
            ext_threats = self._check_extension(filename, extension)
            threats.extend(ext_threats)
            
            # 3. Проверка расположения
            location_threats = self._check_location(filepath, extension)
            threats.extend(location_threats)
            
            # 4. Анализ PE-файлов
            if extension in ['.exe', '.dll', '.sys', '.scr']:
                pe_threats = self._analyze_pe_file(filepath)
                threats.extend(pe_threats)
            
            # 5. Проверка размера
            size_threats = self._check_file_size(file_size, extension)
            threats.extend(size_threats)
            
        except Exception as e:
            threats.append(f"Ошибка анализа: {str(e)}")
        
        # Определяем статус
        if len(threats) >= 3:
            return 'suspicious', threats
        elif len(threats) >= 1:
            return 'suspicious', threats
        
        return 'clean', []
    
    def _check_filename(self, filename: str) -> List[str]:
        """Проверка имени файла"""
        threats = []
        
        # Проверка на подозрительные имена
        for suspicious_name in self.SUSPICIOUS_NAMES:
            if suspicious_name in filename:
                threats.append(f"Подозрительное имя файла: содержит '{suspicious_name}'")
                break
        
        # Проверка на двойное расширение
        if filename.count('.') > 1:
            parts = filename.split('.')
            last_extension = parts[-1]
            if last_extension in ['exe', 'scr', 'bat', 'cmd', 'ps1', 'vbs']:
                threats.append(f"Двойное расширение (маскировка под {parts[-2]})")
        
        return threats
    
    def _check_extension(self, filename: str, extension: str) -> List[str]:
        """Проверка расширения файла"""
        threats = []
        
        if extension in self.DANGEROUS_EXTENSIONS:
            threats.append(f"Потенциально опасный тип файла: {self.DANGEROUS_EXTENSIONS[extension]}")
        
        return threats
    
    def _check_location(self, filepath: str, extension: str) -> List[str]:
        """Проверка расположения файла"""
        threats = []
        path_lower = filepath.lower()
        
        suspicious_locations = [
            ('\\temp\\', 'Временная папка'),
            ('\\tmp\\', 'Временная папка'),
            ('\\appdata\\local\\temp', 'Временная папка приложений'),
            ('\\downloads\\', 'Папка загрузок'),
            ('\\public\\', 'Общедоступная папка')
        ]
        
        for location, description in suspicious_locations:
            if location in path_lower and extension in ['.exe', '.scr', '.bat']:
                threats.append(f"Подозрительное расположение: {description}")
                break
        
        return threats
    
    def _analyze_pe_file(self, filepath: str) -> List[str]:
        """Анализ Portable Executable файла"""
        threats = []
        
        try:
            with open(filepath, 'rb') as f:
                # Проверяем PE заголовок
                header = f.read(2)
                if header != b'MZ':
                    return threats
                
                # Читаем содержимое для анализа (первые 200KB)
                f.seek(0)
                content = f.read(200 * 1024)
                
                # Поиск подозрительных API-вызовов
                api_threats = self._check_suspicious_apis(content)
                threats.extend(api_threats)
                
                # Проверка энтропии
                entropy_threats = self._check_entropy(content)
                threats.extend(entropy_threats)
                
                # Проверка упаковки
                packer_threats = self._check_packers(content)
                threats.extend(packer_threats)
                
                # Поиск подозрительных строк
                string_threats = self._check_suspicious_strings(content)
                threats.extend(string_threats)
                
        except Exception as e:
            threats.append(f"Ошибка анализа PE: {str(e)}")
        
        return threats
    
    def _check_suspicious_apis(self, content: bytes) -> List[str]:
        """Поиск подозрительных API-вызовов"""
        threats = []
        found_apis = []
        
        for api in self.SUSPICIOUS_API_CALLS:
            if api in content:
                found_apis.append(api.decode())
        
        if len(found_apis) >= 5:
            threats.append(f"Обнаружено множество подозрительных API ({len(found_apis)})")
        elif len(found_apis) >= self.min_suspicious_apis:
            threats.append(f"Подозрительные API: {', '.join(found_apis[:3])}")
        
        return threats
    
    def _check_entropy(self, content: bytes) -> List[str]:
        """Проверка энтропии файла"""
        threats = []
        
        # Анализируем первые 10KB
        sample = content[:10000]
        if len(sample) > 0:
            entropy = self._calculate_entropy(sample)
            
            if entropy > self.high_entropy_threshold:
                threats.append(f"Очень высокая энтропия ({entropy:.1f}/8.0) - возможно шифрование")
            elif entropy > 7.0:
                threats.append(f"Повышенная энтропия ({entropy:.1f}/8.0) - возможно упаковка")
        
        return threats
    
    def _check_packers(self, content: bytes) -> List[str]:
        """Проверка на использование упаковщиков"""
        threats = []
        
        known_packers = {
            b'UPX': 'UPX',
            b'ASPack': 'ASPack',
            b'Themida': 'Themida',
            b'VMProtect': 'VMProtect'
        }
        
        for signature, name in known_packers.items():
            if signature in content[:2000]:
                threats.append(f"Обнаружен упаковщик: {name}")
                break
        
        return threats
    
    def _check_suspicious_strings(self, content: bytes) -> List[str]:
        """Поиск подозрительных строк в бинарном файле"""
        threats = []
        content_lower = content.lower()
        found_strings = []
        
        for string in self.SUSPICIOUS_STRINGS:
            if string.encode() in content_lower:
                found_strings.append(string)
        
        if len(found_strings) >= 3:
            threats.append(f"Обнаружены подозрительные строки: {', '.join(found_strings[:3])}")
        
        return threats
    
    def _check_file_size(self, size: int, extension: str) -> List[str]:
        """Проверка размера файла"""
        threats = []
        
        # Подозрительно маленькие исполняемые файлы
        if extension == '.exe' and size < 1024:  # Меньше 1KB
            threats.append("Подозрительно маленький размер EXE файла")
        
        # Очень большие файлы
        if size > 500 * 1024 * 1024:  # Больше 500MB
            threats.append("Очень большой размер файла (>500MB)")
        
        return threats
    
    def _calculate_entropy(self, data: bytes) -> float:
        """
        Расчет энтропии Шеннона
        
        Args:
            data: Бинарные данные
            
        Returns:
            Значение энтропии от 0 до 8
        """
        if not data:
            return 0.0
        
        try:
            entropy = 0.0
            data_length = len(data)
            
            for byte_value in range(256):
                probability = data.count(byte_value) / data_length
                if probability > 0:
                    entropy -= probability * math.log2(probability)
            
            return entropy
        except Exception:
            return 0.0