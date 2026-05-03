"""Анализатор файлов на угрозы"""
import os
import math

# Подозрительные API вызовы
SUSPICIOUS_APIS = [
    b'CreateRemoteThread',
    b'VirtualAllocEx', 
    b'WriteProcessMemory',
    b'SetWindowsHookEx',
    b'GetAsyncKeyState',
    b'URLDownloadToFile',
]

# Подозрительные имена файлов
SUSPICIOUS_NAMES = [
    'keygen', 'crack', 'patch', 'hacktool', 'activator',
    'injector', 'bypass', 'stealer', 'keylogger', 'miner'
]

class FileAnalyzer:
    def analyze(self, filepath):
        """
        Анализ файла
        Возвращает: (статус, список_угроз)
        """
        threats = []
        
        try:
            filename = os.path.basename(filepath).lower()
            ext = os.path.splitext(filename)[1].lower()
            
            # 1. Проверка имени
            for name in SUSPICIOUS_NAMES:
                if name in filename:
                    threats.append(f"Подозрительное имя: '{name}'")
                    break
            
            # 2. Проверка двойного расширения
            if filename.count('.') > 1:
                parts = filename.split('.')
                if parts[-1] in ['exe', 'scr', 'bat', 'ps1', 'vbs']:
                    threats.append("Двойное расширение (маскировка)")
            
            # 3. Анализ PE файлов
            if ext in ['.exe', '.dll', '.sys', '.scr']:
                pe_threats = self._analyze_pe(filepath)
                threats.extend(pe_threats)
            
            # 4. Проверка расположения
            suspicious_paths = ['\\temp\\', '\\tmp\\', '\\appdata\\local\\temp']
            if any(p in filepath.lower() for p in suspicious_paths):
                if ext in ['.exe', '.scr', '.bat']:
                    threats.append("Подозрительное расположение (временная папка)")
        
        except Exception as e:
            threats.append(f"Ошибка анализа: {str(e)}")
        
        # Определяем статус
        if len(threats) > 0:
            return 'suspicious', threats
        
        return 'clean', []
    
    def _analyze_pe(self, filepath):
        """Анализ PE файла"""
        threats = []
        
        try:
            with open(filepath, 'rb') as f:
                # Проверяем заголовок
                header = f.read(2)
                if header != b'MZ':
                    return threats
                
                # Читаем для анализа
                f.seek(0)
                content = f.read(200 * 1024)  # 200KB
                
                # Поиск подозрительных API
                found_apis = []
                for api in SUSPICIOUS_APIS:
                    if api in content:
                        found_apis.append(api.decode())
                
                if len(found_apis) >= 5:
                    threats.append(f"Много подозрительных API ({len(found_apis)})")
                elif len(found_apis) >= 3:
                    threats.append(f"Подозрительные API: {', '.join(found_apis[:3])}")
                
                # Энтропия
                entropy = self._calculate_entropy(content[:10000])
                if entropy > 7.5:
                    threats.append(f"Высокая энтропия ({entropy:.1f}/8.0)")
                
                # UPX упаковка
                if b'UPX' in content[:1000]:
                    threats.append("UPX упаковка")
        
        except:
            pass
        
        return threats
    
    def _calculate_entropy(self, data):
        """Расчет энтропии"""
        if not data:
            return 0.0
        
        try:
            entropy = 0.0
            for byte in range(256):
                prob = data.count(byte) / len(data)
                if prob > 0:
                    entropy -= prob * math.log2(prob)
            return entropy
        except:
            return 0.0