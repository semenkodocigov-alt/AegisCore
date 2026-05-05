#!/usr/bin/env python
"""
Тестовый скрипт для проверки Aegis Core 2.0
Проверяет все основные компоненты
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Тест импортов всех модулей"""
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ИМПОРТОВ")
    print("=" * 60)
    
    modules = [
        ("scanner", "FileScanner"),
        ("analyzer", "FileAnalyzer"),
        ("quarantine", "QuarantineManager"),
        ("hash_utils", "calculate_all"),
        ("file_cleaner", "FileCleaner"),
        ("sound_manager", "get_sound_manager"),
        ("signatures_improved", "SignatureDatabase"),
        ("config", "get_config"),
    ]
    
    failed = []
    for module_name, class_name in modules:
        try:
            mod = __import__(module_name)
            obj = getattr(mod, class_name)
            print(f"✓ {module_name:.<40} OK")
        except Exception as e:
            print(f"✗ {module_name:.<40} FAILED: {e}")
            failed.append((module_name, str(e)))
    
    return len(failed) == 0, failed


def test_file_cleaner():
    """Тест модуля удаления файлов"""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ FILE_CLEANER")
    print("=" * 60)
    
    try:
        from file_cleaner import FileCleaner
        cleaner = FileCleaner()
        
        # Тест методов
        methods = [
            ("delete_file", "Method exists"),
            ("secure_delete", "Method exists"),
            ("disinfect_file", "Method exists"),
            ("quarantine_file", "Method exists"),
            ("restore_from_backup", "Method exists"),
            ("get_backups", "Method exists"),
            ("get_log", "Method exists"),
        ]
        
        for method_name, expected in methods:
            if hasattr(cleaner, method_name):
                print(f"✓ {method_name:.<40} OK")
            else:
                print(f"✗ {method_name:.<40} FAILED")
                return False
        
        print(f"✓ Директория резервных копий: {cleaner.backup_dir}")
        return True
    except Exception as e:
        print(f"✗ Ошибка инициализации: {e}")
        return False


def test_sound_manager():
    """Тест менеджера звуков"""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ SOUND_MANAGER")
    print("=" * 60)
    
    try:
        from sound_manager import get_sound_manager
        sm = get_sound_manager(enable=False)  # Отключаем звук для теста
        
        methods = [
            "play_async",
            "play_sync",
            "test_sound",
        ]
        
        for method_name in methods:
            if hasattr(sm, method_name):
                print(f"✓ {method_name:.<40} OK")
            else:
                print(f"✗ {method_name:.<40} FAILED")
                return False
        
        print(f"✓ Система: {sm.system}")
        print(f"✓ Has winsound: {sm.has_winsound}")
        return True
    except Exception as e:
        print(f"✗ Ошибка инициализации: {e}")
        return False


def test_signatures():
    """Тест улучшенной базы сигнатур"""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ SIGNATURES_IMPROVED")
    print("=" * 60)
    
    try:
        from signatures_improved import SignatureDatabase, VirusTotalChecker
        
        # Тест VirusTotal чекера
        vt = VirusTotalChecker()
        print(f"✓ VirusTotal enabled: {vt.enabled}")
        print(f"✓ VirusTotal API URL: {vt.API_URL}")
        
        # Тест базы сигнатур
        db = SignatureDatabase()
        print(f"✓ Сигнатур загружено: {db.total_count()}")
        print(f"✓ Статистика: {db.get_statistics()}")
        
        methods = [
            "check_hash",
            "add_signature",
            "remove_signature",
            "get_statistics",
        ]
        
        for method_name in methods:
            if hasattr(db, method_name):
                print(f"✓ {method_name:.<40} OK")
            else:
                print(f"✗ {method_name:.<40} FAILED")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Ошибка инициализации: {e}")
        return False


def test_config():
    """Тест системы конфигурации"""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ CONFIG")
    print("=" * 60)
    
    try:
        from config import get_config
        cfg = get_config()
        
        print(f"✓ enable_sound: {cfg.get('enable_sound')}")
        print(f"✓ use_improved_signatures: {cfg.get('use_improved_signatures')}")
        print(f"✓ max_file_size: {cfg.get('max_file_size')}")
        print(f"✓ quarantine_dir: {cfg.get('quarantine_dir')}")
        
        methods = [
            "get",
            "set",
            "get_vt_api_key",
            "is_using_improved_signatures",
        ]
        
        for method_name in methods:
            if hasattr(cfg, method_name):
                print(f"✓ {method_name:.<40} OK")
            else:
                print(f"✗ {method_name:.<40} FAILED")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Ошибка инициализации: {e}")
        return False


def test_scanner():
    """Тест сканера файлов"""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ SCANNER")
    print("=" * 60)
    
    try:
        from scanner import FileScanner
        scanner = FileScanner()
        
        methods = [
            "scan_file",
            "scan_directory",
        ]
        
        for method_name in methods:
            if hasattr(scanner, method_name):
                print(f"✓ {method_name:.<40} OK")
            else:
                print(f"✗ {method_name:.<40} FAILED")
                return False
        
        print(f"✓ Сигнатур в базе: {scanner.sig_db.total_count()}")
        return True
    except Exception as e:
        print(f"✗ Ошибка инициализации: {e}")
        return False


def main():
    """Основной тест"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "🧪 AEGIS CORE 2.0 - ТЕСТИРОВАНИЕ" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    
    tests = [
        ("Импорты", test_imports),
        ("FileCleaner", test_file_cleaner),
        ("SoundManager", test_sound_manager),
        ("Signatures", test_signatures),
        ("Config", test_config),
        ("Scanner", test_scanner),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            if isinstance(result, tuple):
                results[test_name] = result[0]
            else:
                results[test_name] = result
        except Exception as e:
            print(f"\n✗ Ошибка теста {test_name}: {e}")
            results[test_name] = False
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print("=" * 60)
    print(f"Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\nТеперь вы можете запустить приложение:")
        print("  python main.py")
        return 0
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("\nПроверьте ошибки выше")
        return 1


if __name__ == "__main__":
    sys.exit(main())
