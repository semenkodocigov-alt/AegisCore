"""
Главное окно приложения Aegis Core
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
from datetime import datetime
from pathlib import Path

from core.checker import FileScanner
from core.signatures import SignatureDatabase
from core.analyzer import FileAnalyzer
from core.quarantine import QuarantineManager
from utils.hash_utils import HashCalculator


class MainWindow:
    """Главное окно антивируса"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aegis Core - Антивирусная защита")
        self.root.geometry("1050x680")
        self.root.configure(bg='#f0f2f5')
        
        # Инициализация компонентов
        self.signature_db = SignatureDatabase()
        self.file_analyzer = FileAnalyzer()
        self.file_scanner = FileScanner(self.signature_db, self.file_analyzer)
        self.quarantine_manager = QuarantineManager()
        self.hash_calculator = HashCalculator()
        
        # Состояние
        self.is_scanning = False
        self.files_scanned = 0
        self.threats_found = 0
        
        # Цвета
        self.colors = {
            'bg': '#f0f2f5',
            'surface': '#ffffff',
            'header': '#1e272e',
            'green': '#27ae60',
            'red': '#e74c3c',
            'orange': '#f39c12',
            'blue': '#3498db',
            'text': '#2c3e50',
            'text_secondary': '#7f8c8d',
            'border': '#e0e0e0',
            'console_bg': '#1a1f2e',
            'console_fg': '#00e676'
        }
        
        # Контактная информация
        self.author_email = "Kodochigov07@list.ru"
        self.version = "2.0.0"
        
        # Создание интерфейса
        self._create_widgets()
        self._show_welcome_message()
    
    def _create_widgets(self):
        """Создание всех виджетов интерфейса"""
        # Главный контейнер
        self.main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        self._create_header()
        
        # Контент
        content = tk.Frame(self.main_frame, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Левая панель
        left_panel = tk.Frame(content, bg=self.colors['bg'])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 7))
        
        self._create_status_panel(left_panel)
        self._create_scan_buttons(left_panel)
        
        # Правая панель
        right_panel = tk.Frame(content, bg=self.colors['surface'], width=380)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(7, 0))
        right_panel.pack_propagate(False)
        
        self._create_log_panel(right_panel)
        self._create_progress_panel(right_panel)
        
        # Футер
        self._create_footer()
    
    def _create_header(self):
        """Создание верхней панели"""
        header = tk.Frame(self.main_frame, bg=self.colors['header'], height=55)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="🛡️ AEGIS CORE",
            font=("Segoe UI", 18, "bold"),
            bg=self.colors['header'],
            fg='white'
        ).pack(side=tk.LEFT, padx=20, pady=12)
        
        tk.Label(
            header,
            text="Антивирусная защита",
            font=("Segoe UI", 9),
            bg=self.colors['header'],
            fg='#95a5a6'
        ).pack(side=tk.LEFT, pady=12)
    
    def _create_status_panel(self, parent):
        """Создание панели статуса"""
        status_frame = tk.Frame(parent, bg=self.colors['surface'])
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        inner = tk.Frame(status_frame, bg=self.colors['surface'])
        inner.pack(padx=20, pady=15, fill=tk.X)
        
        tk.Label(
            inner,
            text="✅ ЗАЩИТА АКТИВНА",
            font=("Segoe UI", 13, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['green']
        ).pack(anchor='w')
        
        sig_count = self.signature_db.get_total_signatures()
        tk.Label(
            inner,
            text=f"База сигнатур: {sig_count} записей",
            font=("Segoe UI", 9),
            bg=self.colors['surface'],
            fg=self.colors['text_secondary']
        ).pack(anchor='w', pady=(5, 0))
    
    def _create_scan_buttons(self, parent):
        """Создание кнопок сканирования"""
        scans_frame = tk.Frame(parent, bg=self.colors['bg'])
        scans_frame.pack(fill=tk.X)
        
        tk.Label(
            scans_frame,
            text="Сканирование",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(anchor='w', pady=(0, 10))
        
        scan_types = [
            ("⚡ Быстрая проверка", "Критические области системы", "~2-5 мин",
             self._quick_scan, self.colors['green']),
            ("🔍 Полная проверка", "Глубокий анализ всех файлов", "~30-60 мин",
             self._full_scan, self.colors['blue']),
            ("📁 Проверить файл", "Выборочная проверка", "Несколько секунд",
             self._scan_single_file, self.colors['orange'])
        ]
        
        for title, desc, time_val, command, color in scan_types:
            self._create_scan_card(scans_frame, title, desc, time_val, command, color)
    
    def _create_scan_card(self, parent, title, desc, time_val, command, color):
        """Создание карточки сканирования"""
        card = tk.Frame(parent, bg=self.colors['surface'])
        card.pack(fill=tk.X, pady=2)
        
        inner = tk.Frame(card, bg=self.colors['surface'])
        inner.pack(fill=tk.X, padx=20, pady=12)
        
        left = tk.Frame(inner, bg=self.colors['surface'])
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(
            left,
            text=title,
            font=("Segoe UI", 11, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['text']
        ).pack(anchor='w')
        
        tk.Label(
            left,
            text=desc,
            font=("Segoe UI", 8),
            bg=self.colors['surface'],
            fg=self.colors['text_secondary']
        ).pack(anchor='w')
        
        right = tk.Frame(inner, bg=self.colors['surface'])
        right.pack(side=tk.RIGHT)
        
        tk.Label(
            right,
            text=time_val,
            font=("Segoe UI", 8),
            bg=self.colors['surface'],
            fg=self.colors['text_secondary']
        ).pack()
        
        tk.Button(
            right,
            text="Запустить",
            command=command,
            font=("Segoe UI", 9, "bold"),
            bg=color,
            fg='white',
            bd=0,
            padx=20,
            pady=6,
            cursor='hand2'
        ).pack(pady=(5, 0))
    
    def _create_log_panel(self, parent):
        """Создание панели лога"""
        log_header = tk.Frame(parent, bg=self.colors['surface'])
        log_header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(
            log_header,
            text="📋 Журнал событий",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors['surface'],
            fg=self.colors['text']
        ).pack(side=tk.LEFT)
        
        tk.Button(
            log_header,
            text="Очистить",
            command=self._clear_log,
            font=("Segoe UI", 8),
            bg=self.colors['surface'],
            fg=self.colors['blue'],
            bd=0,
            cursor='hand2'
        ).pack(side=tk.RIGHT)
        
        self.log_widget = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=self.colors['console_bg'],
            fg=self.colors['console_fg'],
            insertbackground='white',
            height=18
        )
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
    
    def _create_progress_panel(self, parent):
        """Создание панели прогресса"""
        self.progress_frame = tk.Frame(parent, bg=self.colors['surface'])
        self.progress_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            style="green.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X)
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="Готов к работе",
            font=("Segoe UI", 8),
            bg=self.colors['surface'],
            fg=self.colors['text_secondary']
        )
        self.progress_label.pack(anchor='w')
    
    def _create_footer(self):
        """Создание нижней панели"""
        footer = tk.Frame(self.main_frame, bg=self.colors['header'])
        footer.pack(fill=tk.X)
        
        footer_inner = tk.Frame(footer, bg=self.colors['header'])
        footer_inner.pack(padx=20, pady=8, fill=tk.X)
        
        tk.Label(
            footer_inner,
            text=f"v{self.version} | {self.author_email}",
            font=("Segoe UI", 8),
            bg=self.colors['header'],
            fg='#95a5a6'
        ).pack(side=tk.LEFT)
        
        tk.Label(
            footer_inner,
            text="© 2024 Aegis Core",
            font=("Segoe UI", 8),
            bg=self.colors['header'],
            fg='#95a5a6'
        ).pack(side=tk.RIGHT)
    
    def _show_welcome_message(self):
        """Показать приветственное сообщение"""
        self._log("🛡️ Aegis Core запущен")
        self._log(f"📊 Сигнатур загружено: {self.signature_db.get_total_signatures()}")
        self._log("✅ Система готова к работе")
        self._log("=" * 50)
    
    def _log(self, message: str):
        """Добавить сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            self.log_widget.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_widget.see(tk.END)
        except Exception:
            pass
    
    def _clear_log(self):
        """Очистить лог"""
        try:
            self.log_widget.delete(1.0, tk.END)
            self._log("Журнал очищен")
        except Exception:
            pass
    
    def _update_progress(self, value: int, text: str = ""):
        """Обновить прогресс-бар"""
        try:
            self.progress_bar['value'] = value
            if text:
                self.progress_label.config(text=text)
        except Exception:
            pass
    
    def _quick_scan(self):
        """Быстрая проверка"""
        if self.is_scanning:
            messagebox.showwarning("Сканирование", "Проверка уже выполняется")
            return
        
        self._start_scan("Быстрая проверка", [
            (os.environ.get('TEMP', ''), 2, 100),
            (str(Path.home() / "Downloads"), 2, 100),
            (str(Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"), 1, 20)
        ])
    
    def _full_scan(self):
        """Полная проверка"""
        if self.is_scanning:
            messagebox.showwarning("Сканирование", "Проверка уже выполняется")
            return
        
        scan_areas = []
        if os.path.exists("C:\\Windows\\System32"):
            scan_areas.append(("C:\\Windows\\System32", 2, 300))
        if os.path.exists("C:\\Program Files"):
            scan_areas.append(("C:\\Program Files", 3, 300))
        scan_areas.append((str(Path.home()), 3, 400))
        
        self._start_scan("Полная проверка", scan_areas)
    
    def _scan_single_file(self):
        """Проверка одного файла"""
        filepath = filedialog.askopenfilename(title="Выберите файл для проверки")
        if not filepath:
            return
        
        self._log(f"🔍 Проверка файла: {os.path.basename(filepath)}")
        
        # Вычисляем хеши
        hashes = self.hash_calculator.calculate_all(filepath)
        self._log(f"MD5: {hashes['md5'][:32]}...")
        self._log(f"SHA256: {hashes['sha256'][:32]}...")
        
        # Сканируем
        result = self.file_scanner.scan_file(filepath)
        
        if result.is_threat:
            self._log(f"⚠️ ОБНАРУЖЕНА УГРОЗА: {result.threat_name}")
            for detail in result.details:
                self._log(f"   └─ {detail}")
            
            if messagebox.askyesno("Угроза!", "Файл заражен!\n\nПоместить в карантин?"):
                self.quarantine_manager.add_to_quarantine(filepath)
                self._log("📦 Файл помещен в карантин")
        else:
            self._log("✅ Файл чистый")
            messagebox.showinfo("Проверка", "Угроз не обнаружено")
    
    def _start_scan(self, scan_name: str, areas: list):
        """
        Запуск сканирования
        
        Args:
            scan_name: Название проверки
            areas: Список областей для сканирования [(путь, глубина, макс_файлов), ...]
        """
        self.is_scanning = True
        self.files_scanned = 0
        self.threats_found = 0
        
        self._log("=" * 50)
        self._log(f"ЗАПУЩЕНА {scan_name.upper()}")
        
        thread = threading.Thread(
            target=self._scan_worker,
            args=(scan_name, areas),
            daemon=True
        )
        thread.start()
    
    def _scan_worker(self, scan_name: str, areas: list):
        """
        Рабочий процесс сканирования
        
        Args:
            scan_name: Название проверки
            areas: Список областей для сканирования
        """
        try:
            total_areas = len(areas)
            
            for i, (path, max_depth, max_files) in enumerate(areas):
                if not self.is_scanning:
                    break
                
                if not os.path.exists(path):
                    continue
                
                self._log(f"📂 Сканирование: {os.path.basename(path)}")
                
                # Сканируем директорию
                results = self.file_scanner.scan_directory(
                    path, max_depth=max_depth, max_files=max_files,
                    callback=self._on_file_scanned
                )
                
                # Обновляем прогресс
                progress = ((i + 1) / total_areas) * 100
                self._update_progress(progress, f"Сканирование: {os.path.basename(path)}")
            
            self._update_progress(100, "Завершено")
            self._finish_scan(scan_name)
            
        except Exception as e:
            self._log(f"❌ Ошибка сканирования: {e}")
            self.is_scanning = False
    
    def _on_file_scanned(self, filepath: str, is_threat: bool):
        """
        Callback при сканировании файла
        
        Args:
            filepath: Путь к файлу
            is_threat: Является ли угрозой
        """
        self.files_scanned += 1
        if is_threat:
            self.threats_found += 1
            self._log(f"⚠️ Подозрительный файл: {os.path.basename(filepath)}")
    
    def _finish_scan(self, scan_name: str):
        """Завершение сканирования"""
        self.is_scanning = False
        
        self._log("=" * 50)
        self._log(f"{scan_name} завершена")
        self._log(f"📊 Просканировано файлов: {self.files_scanned}")
        self._log(f"⚠️ Обнаружено угроз: {self.threats_found}")
        
        if self.threats_found > 0:
            self._log("Рекомендуется проверить найденные объекты")
        else:
            self._log("✅ Угроз не обнаружено")
        
        # Показываем результат
        self.root.after(500, lambda: messagebox.showinfo(
            scan_name,
            f"Проверка завершена!\n\n"
            f"Просканировано: {self.files_scanned}\n"
            f"Обнаружено угроз: {self.threats_found}"
        ))
    
    def run(self):
        """Запуск главного цикла приложения"""
        # Настройка стиля
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "green.Horizontal.TProgressbar",
            background='#27ae60',
            troughcolor='#ecf0f1'
        )
        
        # Центрирование окна
        self.root.update_idletasks()
        w, h = 1050, 680
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        
        self.root.mainloop()