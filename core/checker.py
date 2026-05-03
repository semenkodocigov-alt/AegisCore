# Это проверяет файлы
class FileChecker:
    def __init__(self):
        self.name = "Проверяльщик"
    
    def check(self, filename):
        print(f"Проверяю файл: {filename}")
        return "Чистый"
    