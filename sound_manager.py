"""
Улучшенный модуль для воспроизведения звуков без ошибок
Поддерживает Windows, Linux и macOS
"""
import os
import sys
import threading
import platform

class SoundManager:
    """Менеджер звуков с кроссплатформенной поддержкой"""
    
    def __init__(self, enable_sound=True):
        self.enabled = enable_sound
        self.system = platform.system()
        self.sound_cache = {}
        
        # Инициализируем в зависимости от ОС
        if self.system == "Windows":
            try:
                import winsound
                self.winsound = winsound
                self.has_winsound = True
            except ImportError:
                self.has_winsound = False
        else:
            self.has_winsound = False
    
    def play_async(self, sound_type="notification"):
        """Воспроизвести звук асинхронно (в отдельном потоке)"""
        if not self.enabled:
            return
        
        thread = threading.Thread(
            target=self._play_sound_internal,
            args=(sound_type,),
            daemon=True
        )
        thread.start()
    
    def play_sync(self, sound_type="notification"):
        """Воспроизвести звук синхронно (блокирует до окончания)"""
        if not self.enabled:
            return
        self._play_sound_internal(sound_type)
    
    def _play_sound_internal(self, sound_type):
        """Внутренний метод для воспроизведения звука"""
        try:
            if self.system == "Windows":
                self._play_windows_sound(sound_type)
            elif self.system == "Darwin":
                self._play_macos_sound(sound_type)
            elif self.system == "Linux":
                self._play_linux_sound(sound_type)
        except Exception as e:
            # Молча игнорируем ошибки звука
            pass
    
    def _play_windows_sound(self, sound_type):
        """Воспроизведение звука в Windows"""
        if not self.has_winsound:
            return
        
        try:
            sound_map = {
                "threat": "SystemHand",           # Критическая угроза
                "warning": "SystemExclamation",   # Предупреждение
                "success": "SystemAsterisk",      # Успех/сканирование завершено
                "question": "SystemQuestion",     # Вопрос/USB обнаружен
                "notification": "SystemDefault",  # Обычное уведомление
                "error": "SystemHand"             # Ошибка
            }
            
            sound_alias = sound_map.get(sound_type, "SystemDefault")
            
            try:
                # Пытаемся воспроизвести с использованием alias
                self.winsound.PlaySound(
                    sound_alias,
                    self.winsound.SND_ALIAS | self.winsound.SND_ASYNC
                )
            except RuntimeError:
                # Если alias не работает, используем MessageBeep
                beep_map = {
                    "threat": self.winsound.MB_ICONHAND,
                    "warning": self.winsound.MB_ICONEXCLAMATION,
                    "success": self.winsound.MB_ICONASTERISK,
                    "question": self.winsound.MB_ICONQUESTION,
                    "notification": 0,
                    "error": self.winsound.MB_ICONHAND
                }
                
                beep_type = beep_map.get(sound_type, 0)
                if beep_type:
                    self.winsound.MessageBeep(beep_type)
                else:
                    self.winsound.Beep(1000, 200)
        
        except AttributeError:
            # winsound не доступен, используем стандартный beep
            try:
                self.winsound.Beep(1000, 100)
            except:
                pass
        except Exception:
            # Игнорируем любые остальные ошибки
            pass
    
    def _play_macos_sound(self, sound_type):
        """Воспроизведение звука в macOS"""
        try:
            import os
            sound_map = {
                "threat": "Glass",
                "warning": "Blow",
                "success": "Ping",
                "question": "Morse",
                "notification": "Bottle",
                "error": "Sosumi"
            }
            
            sound_name = sound_map.get(sound_type, "Bottle")
            os.system(f"afplay /System/Library/Sounds/{sound_name}.aiff 2>/dev/null &")
        except Exception:
            pass
    
    def _play_linux_sound(self, sound_type):
        """Воспроизведение звука в Linux"""
        try:
            # Пытаемся использовать paplay (PulseAudio)
            frequency_map = {
                "threat": 1000,
                "warning": 800,
                "success": 1200,
                "question": 600,
                "notification": 900,
                "error": 500
            }
            
            freq = frequency_map.get(sound_type, 900)
            
            # Используем встроенные средства Linux для создания звука
            os.system(f"beep -f {freq} -l 200 2>/dev/null &")
        except Exception:
            pass
    
    def test_sound(self):
        """Проверить работу звука"""
        print("🔊 Тестирование звука...")
        self.play_sync("notification")
        return True


# Глобальный экземпляр
_sound_manager = None

def get_sound_manager(enable=True):
    """Получить глобальный экземпляр менеджера звука"""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager(enable)
    return _sound_manager
