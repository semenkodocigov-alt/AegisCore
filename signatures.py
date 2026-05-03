"""База сигнатур вредоносных программ"""

class SignatureDatabase:
    def __init__(self):
        # Встроенные сигнатуры (MD5 хеши)
        self.md5_hashes = {
            "84c82835a5d21bbcf75a61706d8ab549": {
                "name": "WannaCry Ransomware",
                "type": "ransomware",
                "severity": "critical",
                "description": "Опасный шифровальщик"
            },
            "e3b0c44298fc1c149afbf4c8996fb924": {
                "name": "Trojan.Emotet",
                "type": "trojan",
                "severity": "critical",
                "description": "Банковский троян"
            }
        }
        
        self.sha1_hashes = {}
        self.sha256_hashes = {}
    
    def check_hash(self, md5=None, sha1=None, sha256=None):
        """Проверка хеша в базе"""
        if md5 and md5 in self.md5_hashes:
            return self.md5_hashes[md5]
        if sha1 and sha1 in self.sha1_hashes:
            return self.sha1_hashes[sha1]
        if sha256 and sha256 in self.sha256_hashes:
            return self.sha256_hashes[sha256]
        return None
    
    def total_count(self):
        """Количество сигнатур"""
        return len(self.md5_hashes) + len(self.sha1_hashes) + len(self.sha256_hashes)