"""
Aegis Core - Запуск приложения
"""
import sys
import os

# Добавляем текущую папку в путь
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Импортируем и запускаем
from gui_app import AegisApp

if __name__ == "__main__":
    print("=" * 40)
    print("🛡️ Aegis Core v2.0")
    print("=" * 40)
    
    try:
        app = AegisApp()
        app.run()
    except Exception as e:
        print(f"❌ Ошибка запуска приложения: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")