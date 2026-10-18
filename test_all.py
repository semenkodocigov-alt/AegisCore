#!/usr/bin/env python
"""
Тестовый скрипт для проверки Aegis Core 2.0
Проверяет все основные компоненты
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def report(*values: object) -> None:
    logger.info("%s", " ".join(str(value) for value in values))

def test_imports():
    """Тест импортов всех модулей"""
    report("=" * 60)
    report("🧪 ТЕСТИРОВАНИЕ ИМПОРТОВ")
    report("=" * 60)
    
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
            report(f"✓ {module_name:.<40} OK")
        except Exception as e:
            report(f"✗ {module_name:.<40} FAILED: {e}")
            failed.append((module_name, str(e)))
    
    return len(failed) == 0, failed


def test_file_cleaner():
    """Тест модуля удаления файлов"""
    report("\n" + "=" * 60)
    report("🧪 ТЕСТИРОВАНИЕ FILE_CLEANER")
    report("=" * 60)
    
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
                report(f"✓ {method_name:.<40} OK")
            else:
                report(f"✗ {method_name:.<40} FAILED")
                return False
        
        report(f"✓ Директория резервных копий: {cleaner.backup_dir}")
        return True
    except Exception as e:
        report(f"✗ Ошибка инициализации: {e}")
        return False


def test_sound_manager():
    """Тест менеджера звуков"""
    report("\n" + "=" * 60)
    report("🧪 ТЕСТИРОВАНИЕ SOUND_MANAGER")
    report("=" * 60)
    
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
                report(f"✓ {method_name:.<40} OK")
            else:
                report(f"✗ {method_name:.<40} FAILED")
                return False
        
        report(f"✓ Система: {sm.system}")
        report(f"✓ Has winsound: {sm.has_winsound}")
        return True
    except Exception as e:
        report(f"✗ Ошибка инициализации: {e}")
        return False


def test_signatures():
    """Тест улучшенной базы сигнатур"""
    report("\n" + "=" * 60)
    report("🧪 ТЕСТИРОВАНИЕ SIGNATURES_IMPROVED")
    report("=" * 60)
    
    try:
        from signatures_improved import SignatureDatabase, VirusTotalChecker
        
        # Тест VirusTotal чекера
        vt = VirusTotalChecker()
        report(f"✓ VirusTotal enabled: {vt.enabled}")
        report(f"✓ VirusTotal API URL: {vt.API_URL}")
        
        # Тест базы сигнатур
        db = SignatureDatabase()
        report(f"✓ Сигнатур загружено: {db.total_count()}")
        report(f"✓ Статистика: {db.get_statistics()}")
        
        methods = [
            "check_hash",
            "add_signature",
            "remove_signature",
            "get_statistics",
        ]
        
        for method_name in methods:
            if hasattr(db, method_name):
                report(f"✓ {method_name:.<40} OK")
            else:
                report(f"✗ {method_name:.<40} FAILED")
                return False
        
        return True
    except Exception as e:
        report(f"✗ Ошибка инициализации: {e}")
        return False


def test_config():
    """Тест системы конфигурации"""
    report("\n" + "=" * 60)
    report("🧪 ТЕСТИРОВАНИЕ CONFIG")
    report("=" * 60)
    
    try:
        from config import get_config
        cfg = get_config()
        
        report(f"✓ enable_sound: {cfg.get('enable_sound')}")
        report(f"✓ use_improved_signatures: {cfg.get('use_improved_signatures')}")
        report(f"✓ max_file_size: {cfg.get('max_file_size')}")
        report(f"✓ quarantine_dir: {cfg.get('quarantine_dir')}")
        
        methods = [
            "get",
            "set",
            "get_vt_api_key",
            "is_using_improved_signatures",
        ]
        
        for method_name in methods:
            if hasattr(cfg, method_name):
                report(f"✓ {method_name:.<40} OK")
            else:
                report(f"✗ {method_name:.<40} FAILED")
                return False
        
        return True
    except Exception as e:
        report(f"✗ Ошибка инициализации: {e}")
        return False


def test_scanner():
    """Тест сканера файлов"""
    report("\n" + "=" * 60)
    report("🧪 ТЕСТИРОВАНИЕ SCANNER")
    report("=" * 60)
    
    try:
        from scanner import FileScanner
        scanner = FileScanner()
        
        methods = [
            "scan_file",
            "scan_directory",
        ]
        
        for method_name in methods:
            if hasattr(scanner, method_name):
                report(f"✓ {method_name:.<40} OK")
            else:
                report(f"✗ {method_name:.<40} FAILED")
                return False
        
        report(f"✓ Сигнатур в базе: {scanner.sig_db.total_count()}")
        return True
    except Exception as e:
        report(f"✗ Ошибка инициализации: {e}")
        return False


def main():
    """Основной тест"""
    report("\n")
    report("╔" + "=" * 58 + "╗")
    report("║" + " " * 10 + "🧪 AEGIS CORE 2.0 - ТЕСТИРОВАНИЕ" + " " * 15 + "║")
    report("╚" + "=" * 58 + "╝")
    
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
            report(f"\n✗ Ошибка теста {test_name}: {e}")
            results[test_name] = False
    
    # Итоги
    report("\n" + "=" * 60)
    report("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    report("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        report(f"{test_name:.<40} {status}")
    
    report("=" * 60)
    report(f"Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        report("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        report("\nТеперь вы можете запустить приложение:")
        report("  python main.py")
        return 0
    else:
        report("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        report("\nПроверьте ошибки выше")
        return 1


if __name__ == "__main__":
    sys.exit(main())
