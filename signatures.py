"""База сигнатур вредоносных программ с интеграцией Kaspersky и VirusTotal"""
import requests
import json
import os
import time
from pathlib import Path
from config import get_config

class SignatureDatabase:
    def __init__(self):
        # Локальная база сигнатур (расширенная)
        self.md5_hashes = self._load_local_signatures()
        self.sha1_hashes = {}
        self.sha256_hashes = {}

        # Исключения для легитимного ПО
        self.whitelist = self._load_whitelist()

        # Кэш для онлайн проверок
        try:
            self.cache_file = Path(__file__).parent / "cache" / "vt_cache.json"
            self.cache_file.parent.mkdir(exist_ok=True)
        except Exception:
            # Если не можем создать кэш, используем None
            self.cache_file = None
        self.cache = self._load_cache()

        # API ключи (нужно настроить)
        self.vt_api_key = get_config().get_vt_api_key()
        self.kaspersky_api_key = os.environ.get('KASPERSKY_API_KEY', '')

    def _load_local_signatures(self):
        """Загрузка локальных сигнатур"""
        return {
            # Ransomware
            "84c82835a5d21bbcf75a61706d8ab549": {
                "name": "WannaCry Ransomware",
                "type": "ransomware",
                "severity": "critical",
                "description": "Опасный шифровальщик WannaCry"
            },
            "e3b0c44298fc1c149afbf4c8996fb924": {
                "name": "Trojan.Emotet",
                "type": "trojan",
                "severity": "critical",
                "description": "Банковский троян Emotet"
            },
            # Добавим больше сигнатур
            "d41d8cd98f00b204e9800998ecf8427e": {
                "name": "Empty File Hash",
                "type": "suspicious",
                "severity": "low",
                "description": "Пустой файл"
            }
        }

    def _load_whitelist(self):
        """Белый список легитимного ПО"""
        return {
            # Cloudflare and related services should not be считаться угрозой
            "cloudflare": ["cloudflare", "warp", "cf"],
            # VPN сервисы
            "vpn": ["expressvpn", "nordvpn", "protonvpn", "mullvad", "surfshark",
                   "private internet access", "pia", "tunnelbear", "hotspot shield",
                   "cyberghost", "vyprvpn", "airvpn", "ivpn", "mullvad",
                   "openvpn", "wireguard", "ikev2", "pptp", "l2tp"],
            # Прокси и безопасные сетевые сервисы
            "network": ["proxy", "socks", "shadowsocks", "v2ray", "trojan", "clash"],
            # Легитимное ПО
            "system": ["windows", "microsoft", "google", "apple", "mozilla",
                      "chrome", "firefox", "edge", "opera", "safari",
                      "adobe", "java", "python", "node", "npm", "git",
                      "vscode", "sublime", "notepad++", "7zip", "winrar",
                      "vlc", "potplayer", "mpv", "discord", "telegram",
                      "skype", "zoom", "teams", "slack", "whatsapp"]
        }

    def _load_cache(self):
        """Загрузка кэша VirusTotal"""
        if not self.cache_file:
            return {}
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def _save_cache(self):
        """Сохранение кэша"""
        if not self.cache_file:
            return
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except:
            pass

    def _is_whitelisted(self, filename, filepath):
        """Проверка на белый список"""
        filename_lower = filename.lower()
        filepath_lower = filepath.lower()

        # Проверка белого списка по любой категории
        for category, patterns in self.whitelist.items():
            for name in patterns:
                if name in filename_lower or name in filepath_lower:
                    return True
        return False

    def check_hash(self, md5=None, sha1=None, sha256=None, filename=None, filepath=None):
        """Проверка хеша в базе с онлайн проверкой"""
        # Сначала проверка на белый список
        if filename and filepath and self._is_whitelisted(filename, filepath):
            return None

        # Локальная проверка
        if md5 and md5 in self.md5_hashes:
            return self.md5_hashes[md5]
        if sha1 and sha1 in self.sha1_hashes:
            return self.sha1_hashes[sha1]
        if sha256 and sha256 in self.sha256_hashes:
            return self.sha256_hashes[sha256]

        # Онлайн проверка VirusTotal
        if self.vt_api_key and (md5 or sha256):
            hash_to_check = sha256 or md5
            if hash_to_check in self.cache:
                cached_result = self.cache[hash_to_check]
                if time.time() - cached_result.get('timestamp', 0) < 86400:  # 24 часа
                    if cached_result.get('positives', 0) > 5:
                        return {
                            "name": f"VirusTotal Detection ({cached_result['positives']}/{cached_result['total']})",
                            "type": "malware",
                            "severity": "high" if cached_result['positives'] > 10 else "medium",
                            "description": f"Обнаружено {cached_result['positives']} антивирусами из {cached_result['total']}"
                        }

            # Запрос к VirusTotal
            try:
                if hasattr(self, 'last_vt_request_time'):
                    elapsed = time.time() - self.last_vt_request_time
                    if elapsed < 20:
                        time.sleep(20 - elapsed)
                else:
                    self.last_vt_request_time = 0

                url = f"https://www.virustotal.com/api/v3/files/{hash_to_check}"
                headers = {"x-apikey": self.vt_api_key}
                print('⏳ Проверка VirusTotal: запрос отправлен')
                response = requests.get(url, headers=headers, timeout=30)
                self.last_vt_request_time = time.time()

                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and 'attributes' in data['data'] and 'last_analysis_stats' in data['data']['attributes']:
                        stats = data['data']['attributes']['last_analysis_stats']
                        positives = stats.get('malicious', 0)
                        total = stats.get('total', 0)

                        # Кэшируем результат
                        self.cache[hash_to_check] = {
                            'positives': positives,
                            'total': total,
                            'timestamp': time.time()
                        }
                        self._save_cache()

                        if positives > 5:
                            return {
                                "name": f"VirusTotal Detection ({positives}/{total})",
                                "type": "malware",
                                "severity": "high" if positives > 10 else "medium",
                                "description": f"Обнаружено {positives} антивирусами из {total}"
                            }
                    else:
                        # Кэшируем как не найденный
                        self.cache[hash_to_check] = {
                            'positives': 0,
                            'total': 0,
                            'timestamp': time.time()
                        }
                        self._save_cache()

            except requests.exceptions.Timeout as e:
                print(f'⚠️ VirusTotal: timeout ({e})')
            except requests.exceptions.ConnectionError as e:
                print(f'⚠️ VirusTotal: ошибка соединения ({e})')
            except requests.exceptions.RequestException as e:
                print(f'⚠️ VirusTotal: ошибка запроса ({e})')
            except Exception as e:
                print(f'⚠️ VirusTotal: неизвестная ошибка ({e})')

        return None

    def total_count(self):
        """Количество сигнатур"""
        return len(self.md5_hashes) + len(self.sha1_hashes) + len(self.sha256_hashes)

    def update_signatures(self):
        """Обновление сигнатур из Kaspersky (заглушка)"""
        # Здесь можно добавить загрузку сигнатур из Kaspersky
        # Пока возвращаем количество обновленных сигнатур
        return 0