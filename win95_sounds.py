"""
Ретро-звуки в стиле Windows 95/98
Генерирует звуки программно без использования внешних файлов
"""
import winsound
import threading


class Win95Sounds:
    """Класс для воспроизведения ретро-звуков"""
    
    @staticmethod
    def startup():
        """Звук при запуске (как в Windows 98)"""
        # Три нотки вверх
        winsound.Beep(400, 100)
        winsound.Beep(600, 100)
        winsound.Beep(800, 150)
    
    @staticmethod
    def success():
        """Звук успеха"""
        # Две красивые нотки
        winsound.Beep(800, 100)
        winsound.Beep(1000, 150)
    
    @staticmethod
    def error():
        """Звук ошибки"""
        # Низкая нота
        winsound.Beep(200, 200)
    
    @staticmethod
    def warning():
        """Звук предупреждения"""
        # Две нотки вверх-вниз
        winsound.Beep(800, 100)
        winsound.Beep(600, 100)
    
    @staticmethod
    def threat_detected():
        """Звук обнаружения угрозы"""
        # Быстрые пиксели как в старых играх
        for _ in range(3):
            winsound.Beep(1000, 50)
            winsound.Beep(500, 50)
    
    @staticmethod
    def scan_complete():
        """Звук завершения сканирования"""
        # Торжественный звук
        winsound.Beep(800, 150)
        winsound.Beep(1000, 150)
        winsound.Beep(1200, 200)
    
    @staticmethod
    def click():
        """Звук нажатия кнопки"""
        winsound.Beep(600, 50)
    
    @staticmethod
    def play_async(sound_name):
        """Воспроизведение звука в отдельном потоке"""
        def play():
            try:
                if sound_name == 'startup':
                    Win95Sounds.startup()
                elif sound_name == 'success':
                    Win95Sounds.success()
                elif sound_name == 'error':
                    Win95Sounds.error()
                elif sound_name == 'warning':
                    Win95Sounds.warning()
                elif sound_name == 'threat':
                    Win95Sounds.threat_detected()
                elif sound_name == 'complete':
                    Win95Sounds.scan_complete()
                elif sound_name == 'click':
                    Win95Sounds.click()
            except:
                pass  # Игнорируем ошибки звука
        
        thread = threading.Thread(target=play, daemon=True)
        thread.start()
