"""
Aegis Core - Запуск приложения
"""
import sys
import os

# Обеспечиваем корректный вывод UTF-8 в консоли Windows
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Добавляем текущую папку в путь
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def register_shell_context_menu():
    if os.name != 'nt':
        print('Регистрация контекстного меню доступна только в Windows')
        return

    try:
        import winreg
        key_path = r"*\shell\AegisCoreScan"
        command = f'"{sys.executable}" "{os.path.abspath(__file__)}" "%1"'

        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
            winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'Проверить с Aegis Core')
            winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, sys.executable)

        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command") as cmd_key:
            winreg.SetValueEx(cmd_key, '', 0, winreg.REG_SZ, command)

        print('Пункт "Проверить с Aegis Core" зарегистрирован')
    except Exception as e:
        print(f'Ошибка регистрации: {e}')


def unregister_shell_context_menu():
    if os.name != 'nt':
        print('Регистрация контекстного меню доступна только в Windows')
        return

    try:
        import winreg
        key_path = r"*\shell\AegisCoreScan\command"
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\AegisCoreScan")
        print('Пункт контекстного меню удалён')
    except Exception as e:
        print(f'Ошибка удаления: {e}')


if __name__ == "__main__":
    print("=" * 40)
    print("🛡️ Aegis Core ")
    print("=" * 40)

    try:
        scan_target = None
        if len(sys.argv) > 1:
            first_arg = sys.argv[1]
            if first_arg == '--register-shell':
                register_shell_context_menu()
                sys.exit(0)
            elif first_arg == '--unregister-shell':
                unregister_shell_context_menu()
                sys.exit(0)
            elif os.path.exists(first_arg):
                scan_target = first_arg

        from desktop_app import AegisDesktopApp

        app = AegisDesktopApp(scan_target)
        app.run()
    except Exception as e:
        print(f"❌ Ошибка запуска приложения: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")