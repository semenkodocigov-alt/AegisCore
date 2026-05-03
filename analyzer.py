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
    b'CreateProcess',
    b'ShellExecute',
    b'WinExec',
    b'system',
    b'LoadLibrary',
    b'GetProcAddress',
    b'VirtualProtect',
    b'NtCreateThreadEx',
    b'NtWriteVirtualMemory',
    b'CryptEncrypt',
    b'CryptDecrypt',
    b'InternetOpen',
    b'HttpSendRequest',
    b'RegCreateKey',
    b'RegSetValue',
    b'CreateMutex',
    b'OpenMutex',
    b'CreateFileMapping',
    b'MapViewOfFile',
    b'GetModuleFileName',
    b'GetCurrentProcess',
    b'AdjustTokenPrivileges',
    b'LookupPrivilegeValue',
    b'SeDebugPrivilege',
    b'NtSuspendProcess',
    b'NtResumeProcess'
]

# Подозрительные имена файлов
SUSPICIOUS_NAMES = [
    'keygen', 'crack', 'patch', 'hacktool', 'activator',
    'injector', 'bypass', 'stealer', 'keylogger', 'miner',
    'trojan', 'virus', 'worm', 'ransomware', 'backdoor',
    'rootkit', 'spyware', 'adware', 'malware', 'exploit',
    'payload', 'shellcode', 'dropper', 'loader', 'bot',
    'c2', 'command', 'control', 'rat', 'remote',
    'access', 'tool', 'hack', 'cheat', 'aimbot',
    'wallhack', 'speedhack', 'godmode', 'trainer',
    'unpacker', 'deobfuscator', 'obfuscator', 'packer',
    'crypter', 'binder', 'joiner', 'merger', 'splitter'
]

# Подозрительные расширения
SUSPICIOUS_EXTENSIONS = [
    '.exe', '.scr', '.pif', '.com', '.bat', '.cmd', '.vbs',
    '.js', '.jse', '.wsf', '.wsh', '.ps1', '.psm1', '.psd1',
    '.dll', '.ocx', '.sys', '.drv', '.vxd', '.386', '.vxd',
    '.bin', '.dat', '.tmp', '.log', '.ini', '.cfg', '.conf'
]

# Подозрительные пути
SUSPICIOUS_PATHS = [
    '\\temp\\', '\\tmp\\', '\\appdata\\local\\temp',
    '\\windows\\temp\\', '\\system32\\', '\\syswow64\\',
    '\\programdata\\', '\\users\\public\\', '\\downloads\\',
    '\\desktop\\', '\\documents\\', '\\pictures\\', '\\videos\\'
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
            filepath_lower = filepath.lower()
            
            # 1. Проверка имени файла
            for name in SUSPICIOUS_NAMES:
                if name in filename:
                    threats.append(f"Подозрительное имя файла: '{name}'")
                    break
            
            # 2. Проверка двойного расширения
            if filename.count('.') > 1:
                parts = filename.split('.')
                if parts[-1] in ['exe', 'scr', 'bat', 'ps1', 'vbs', 'js', 'jse', 'wsf', 'wsh']:
                    threats.append("Двойное расширение (маскировка)")
            
            # 3. Проверка подозрительного расширения в подозрительном пути
            if ext in SUSPICIOUS_EXTENSIONS:
                for path_pattern in SUSPICIOUS_PATHS:
                    if path_pattern in filepath_lower:
                        threats.append(f"Подозрительное сочетание: {ext} в {path_pattern}")
                        break
            
            # 4. Проверка размера файла (слишком маленький или слишком большой)
            try:
                size = os.path.getsize(filepath)
                if size < 100:  # Слишком маленький файл
                    threats.append("Необычно маленький размер файла")
                elif size > 50 * 1024 * 1024:  # > 50MB
                    threats.append("Необычно большой размер файла")
            except:
                pass
            
            # 5. Анализ PE файлов
            if ext in ['.exe', '.dll', '.sys', '.scr', '.ocx', '.drv']:
                pe_threats = self._analyze_pe(filepath)
                threats.extend(pe_threats)
            
            # 6. Анализ скриптов
            if ext in ['.bat', '.cmd', '.vbs', '.js', '.jse', '.wsf', '.wsh', '.ps1', '.psm1', '.psd1']:
                script_threats = self._analyze_script(filepath)
                threats.extend(script_threats)
            
            # 7. Проверка на скрытые файлы
            if filename.startswith('.') or filename.startswith('$'):
                threats.append("Скрытый файл")
            
            # 8. Проверка на системные имена
            system_names = ['svchost', 'explorer', 'system', 'winlogon', 'csrss', 'smss', 'services']
            if any(name in filename for name in system_names) and ext in ['.exe', '.dll']:
                threats.append("Имя системного процесса")
        
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
    
    def _analyze_script(self, filepath):
        """Анализ скриптовых файлов"""
        threats = []
        
        try:
            with open(filepath, 'rb') as f:
                content = f.read(50 * 1024)  # 50KB для анализа скриптов
                text_content = content.decode('utf-8', errors='ignore').lower()
            
            # Подозрительные команды в скриптах
            suspicious_commands = [
                'downloadstring', 'invoke-webrequest', 'wget', 'curl',
                'net user', 'net localgroup', 'reg add', 'reg delete',
                'schtasks', 'at ', 'bitsadmin', 'powershell',
                'cmd.exe', 'rundll32', 'mshta', 'cscript', 'wscript',
                'certutil', 'msiexec', 'rundll32', 'regsvr32',
                'sc create', 'sc delete', 'netsh', 'route add',
                'net stop', 'net start', 'taskkill', 'tskill',
                'shutdown', 'restart', 'logoff', 'lock',
                'format', 'del ', 'erase', 'rmdir', 'rd ',
                'move ', 'copy ', 'xcopy', 'robocopy',
                'attrib +h', 'attrib -h', 'cacls', 'icacls',
                'takeown', 'runas', 'psexec', 'wmic',
                'vssadmin delete shadows', 'bcdedit', 'bootcfg',
                'diskpart', 'mountvol', 'fsutil', 'cipher'
            ]
            
            found_commands = []
            for cmd in suspicious_commands:
                if cmd in text_content:
                    found_commands.append(cmd)
            
            if len(found_commands) >= 3:
                threats.append(f"Много подозрительных команд ({len(found_commands)})")
            elif len(found_commands) >= 1:
                threats.append(f"Подозрительные команды: {', '.join(found_commands[:3])}")
            
            # Проверка на обфускацию
            if text_content.count(' ') < len(text_content) * 0.1:  # Мало пробелов
                threats.append("Возможная обфускация (мало пробелов)")
            
            # Проверка на base64
            import base64
            import binascii
            try:
                # Ищем потенциальные base64 строки
                words = text_content.split()
                for word in words:
                    if len(word) > 20 and len(word) % 4 == 0:
                        try:
                            decoded = base64.b64decode(word)
                            if len(decoded) > 10:
                                threats.append("Возможный base64 encoded контент")
                                break
                        except (binascii.Error, ValueError):
                            pass
            except:
                pass
            
            # Проверка на URL
            if 'http://' in text_content or 'https://' in text_content or 'ftp://' in text_content:
                threats.append("Содержит URL (потенциальная загрузка)")
            
            # Проверка на IP адреса
            import re
            ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
            if re.search(ip_pattern, text_content):
                threats.append("Содержит IP адреса")
        
        except Exception as e:
            threats.append(f"Ошибка анализа скрипта: {str(e)}")
        
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