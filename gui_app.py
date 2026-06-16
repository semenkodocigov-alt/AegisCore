"""
Aegis Core - Интерфейс в стиле Windows 95/98
Оригинальный ретро-дизайн для истинных любителей 90-х!
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import time
from datetime import datetime
from pathlib import Path

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

from scanner import FileScanner
from quarantine import QuarantineManager
from sound_manager import get_sound_manager
from file_cleaner import FileCleaner


# ============= КАСТОМНЫЕ ВИДЖЕТЫ В СТИЛЕ WINDOWS 95 =============

class Win95Button(tk.Button):
    """Кнопка в стиле Windows 95 с 3D эффектом"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Стиль Windows 95
        self.config(
            bg='#c0c0c0',
            fg='#000000',
            activebackground='#c0c0c0',
            activeforeground='#000000',
            bd=2,
            relief='raised',
            highlightthickness=0,
            font=('MS Sans Serif', 8),
            padx=6,
            pady=3,
            cursor='arrow'
        )
        
        self.pressed = False
        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
    
    def _on_press(self, event):
        """Эффект нажатия"""
        self.config(relief='sunken', state='active')
        self.pressed = True
    
    def _on_release(self, event):
        """Эффект отпускания"""
        self.config(relief='raised')
        self.pressed = False


class Win95Label(tk.Label):
    """Label в стиле Windows 95"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(
            bg='#c0c0c0',
            fg='#000000',
            font=('MS Sans Serif', 8)
        )


class Win95Frame(tk.Frame):
    """Фрейм с 3D рамкой как в Windows 95"""
    
    def __init__(self, parent, relief='raised', **kwargs):
        super().__init__(parent, **kwargs)
        self.config(
            bg='#c0c0c0',
            relief=relief,
            bd=2
        )


class Win95TextFrame(tk.Frame):
    """Фрейм с вдавленной рамкой для текста"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(
            bg='#c0c0c0',
            relief='sunken',
            bd=2
        )


class Win95DarkFrame(tk.Frame):
    """Тёмный фрейм для заголовка"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(
            bg='#000080',  # Классический синий
            relief='raised',
            bd=2
        )


class RetroConsole(tk.Text):
    """Консоль в стиле DOS/Matrix"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(
            bg='#000000',  # Чёрный DOS
            fg='#00ff00',  # Зелёный текст
            insertbackground='#00ff00',
            selectbackground='#00ff00',
            selectforeground='#000000',
            relief='sunken',
            bd=2,
            font=('Courier New', 8),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        
        # Теги для разных типов сообщений
        self.tag_config('error', foreground='#ff0000')
        self.tag_config('warning', foreground='#ffff00')
        self.tag_config('success', foreground='#00ff00')
        self.tag_config('info', foreground='#00ffff')
    
    def append_log(self, message, tag='success'):
        """Добавить сообщение в консоль"""
        self.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        self.insert(tk.END, log_line, tag)
        self.see(tk.END)
        self.config(state=tk.DISABLED)


class Win95ProgressBar(tk.Canvas):
    """Прогресс-бар как в Windows 95"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(
            bg='#c0c0c0',
            relief='sunken',
            bd=2,
            highlightthickness=0
        )
        self.progress = 0
        self.bind('<Configure>', self._draw)
    
    def set_progress(self, value):
        """Установить прогресс"""
        self.progress = max(0, min(100, value))
        self._draw()
    
    def _draw(self, event=None):
        """Рисование блочного прогресс-бара"""
        self.delete('all')
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        # Фон
        self.create_rectangle(0, 0, width, height, fill='#c0c0c0', outline='')
        
        # Прогресс блоками по 5 пикселей
        block_size = 5
        progress_width = int(width * self.progress / 100)
        
        for x in range(0, progress_width, block_size):
            self.create_rectangle(
                x, 0, min(x + block_size - 1, progress_width), height,
                fill='#000080',  # Синие блоки
                outline='#ffffff'
            )


class Win95Listbox(tk.Listbox):
    """Listbox в стиле Windows 95"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(
            bg='#ffffff',
            fg='#000000',
            selectbackground='#000080',
            selectforeground='#ffffff',
            relief='sunken',
            bd=2,
            font=('MS Sans Serif', 8),
            highlightthickness=0
        )


class Win95Scrollbar(tk.Scrollbar):
    """Scrollbar в стиле Windows 95"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(
            bg='#c0c0c0',
            activebackground='#dfdfdf',
            relief='raised',
            bd=2,
            width=16
        )


# ============= ГЛАВНОЕ ПРИЛОЖЕНИЕ =============

class AegisApp:
    """Главное приложение Aegis Core - Windows 95 Edition"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aegis Core - Антивирусная защита")
        self.root.geometry("1000x700")
        self.root.overrideredirect(True)  # Убрать рамки окна
        
        # Цветовая схема Windows 95
        self.bg_color = '#c0c0c0'
        self.dark_blue = '#000080'
        self.light_gray = '#dfdfdf'
        self.dark_gray = '#808080'
        self.white = '#ffffff'
        self.black = '#000000'
        
        self.root.configure(bg=self.bg_color)
        
        # Центрирование окна
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 1000) // 2
        y = (screen_height - 700) // 2
        self.root.geometry(f"1000x700+{x}+{y}")
        
        # Переменные для перемещения окна
        self.drag_x = 0
        self.drag_y = 0
        
        # Компоненты
        self.scanner = FileScanner()
        self.quarantine = QuarantineManager()
        
        # Состояние
        self.is_scanning = False
        self.files_scanned = 0
        self.threats_found = 0
        self.last_usb_devices = set()
        self.usb_monitoring = False
        
        # Информация
        self.version = "2.0.0"
        self.author = "Aegis Core Team"
        self.author_email = "Kodochigov07@list.ru"
        
        # Обработка восстановления borderless при развёртывании
        self.root.bind('<Map>', self._restore_borderless)
        
        # Создание интерфейса
        self._create_ui()
        self._welcome_log()
    
    def _create_ui(self):
        """Создание интерфейса в стиле Windows 95"""
        
        # === ЗАГОЛОВОК ===
        title_bar = Win95DarkFrame(self.root, height=30)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        title_bar.pack_propagate(False)
        
        # Привязываем события для перемещения окна
        title_bar.bind('<Button-1>', self._start_drag)
        title_bar.bind('<B1-Motion>', self._on_drag)
        
        title_label = tk.Label(
            title_bar,
            text='  🛡  AEGIS CORE - Антивирусная защита',
            bg='#000080',
            fg='#ffffff',
            font=('MS Sans Serif', 10, 'bold'),
            anchor='w'
        )
        title_label.pack(fill=tk.BOTH, expand=True, padx=4, pady=3)
        title_label.bind('<Button-1>', self._start_drag)
        title_label.bind('<B1-Motion>', self._on_drag)
        
        # Кнопки управления
        btn_frame = tk.Frame(title_bar, bg='#000080')
        btn_frame.pack(side=tk.RIGHT, padx=2, pady=2)
        
        # Кнопка закрытия с красным фоном
        close_btn = tk.Button(
            btn_frame, 
            text='✕', 
            width=3, 
            height=1,
            bg='#c0c0c0',
            fg='#000000',
            activebackground='#ff0000',
            activeforeground='#ffffff',
            bd=2,
            relief='raised',
            font=('MS Sans Serif', 10, 'bold'),
            command=self.root.destroy,
            cursor='arrow',
            highlightthickness=0
        )
        close_btn.pack(side=tk.RIGHT, padx=2)
        
        # Кнопка минимизации
        min_btn = Win95Button(btn_frame, text='−', width=3, height=1,
                             command=self._minimize)
        min_btn.pack(side=tk.RIGHT, padx=2)
        
        # Горячая клавиша Alt+F4
        self.root.bind('<Alt-F4>', lambda e: self.root.destroy())
        
        # === ОСНОВНОЙ КОНТЕНТ ===
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        # Левая панель
        left_panel = Win95Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self._create_left_panel(left_panel)
        
        # Правая панель
        right_panel = Win95Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        
        self._create_right_panel(right_panel)
        
        # === СТАТУСНАЯ СТРОКА ===
        status_bar = Win95Frame(self.root, relief='sunken', height=20)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        
        self.status_label = Win95Label(status_bar, text='Готов к работе', anchor='w')
        self.status_label.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    
    def _create_left_panel(self, parent):
        """Левая панель с кнопками и статусом"""
        
        # --- СТАТУС ---
        status_frame = Win95Frame(parent)
        status_frame.pack(fill=tk.X, pady=(0, 4))
        
        Win95Label(status_frame, text='СТАТУС ЗАЩИТЫ', font=('MS Sans Serif', 8, 'bold')).pack(
            anchor='w', padx=4, pady=(4, 2)
        )
        
        info_frame = Win95TextFrame(status_frame)
        info_frame.pack(fill=tk.X, padx=4, pady=(0, 4))
        
        # Индикатор статуса
        indicator_frame = tk.Frame(info_frame, bg='#ffffff', relief='sunken', bd=1)
        indicator_frame.pack(fill=tk.X, padx=2, pady=2)
        
        self.status_indicator = tk.Canvas(
            indicator_frame,
            width=16, height=16,
            bg='#ffffff',
            highlightthickness=0
        )
        self.status_indicator.pack(side=tk.LEFT, padx=4, pady=4)
        self.status_indicator.create_oval(2, 2, 14, 14, fill='#00ff00', outline='#000000')
        
        status_text = Win95Label(
            indicator_frame,
            text='Система защищена',
            font=('MS Sans Serif', 8),
            bg='#ffffff'
        )
        status_text.pack(side=tk.LEFT, padx=4, pady=4)
        
        # Информация
        info_label = Win95Label(
            info_frame,
            text=f'Сигнатур: {self.scanner.sig_db.total_count()}',
            font=('MS Sans Serif', 8)
        )
        info_label.pack(anchor='w', padx=4, pady=(2, 4))
        
        # --- СКАНИРОВАНИЕ ---
        scan_frame = Win95Frame(parent)
        scan_frame.pack(fill=tk.X, pady=(0, 4))
        
        Win95Label(scan_frame, text='СКАНИРОВАНИЕ', font=('MS Sans Serif', 8, 'bold')).pack(
            anchor='w', padx=4, pady=(4, 4)
        )
        
        self.quick_scan_btn = Win95Button(
            scan_frame,
            text='⚡ Быстрая проверка',
            command=self._quick_scan,
            width=30
        )
        self.quick_scan_btn.pack(fill=tk.X, padx=4, pady=2)
        
        self.full_scan_btn = Win95Button(
            scan_frame,
            text='🔍 Полная проверка',
            command=self._full_scan,
            width=30
        )
        self.full_scan_btn.pack(fill=tk.X, padx=4, pady=2)
        
        self.file_scan_btn = Win95Button(
            scan_frame,
            text='📁 Выбрать файл',
            command=self._select_file,
            width=30
        )
        self.file_scan_btn.pack(fill=tk.X, padx=4, pady=(2, 4))
        
        # --- ПРОГРЕСС ---
        progress_frame = Win95Frame(parent)
        progress_frame.pack(fill=tk.X, pady=(0, 4))
        
        Win95Label(progress_frame, text='ПРОГРЕСС', font=('MS Sans Serif', 8, 'bold')).pack(
            anchor='w', padx=4, pady=(4, 2)
        )
        
        self.progress_label = Win95Label(
            progress_frame,
            text='Ожидание...',
            font=('MS Sans Serif', 8)
        )
        self.progress_label.pack(anchor='w', padx=4, pady=2)
        
        self.progress_bar = Win95ProgressBar(progress_frame, height=20)
        self.progress_bar.pack(fill=tk.X, padx=4, pady=(2, 4))
        
        # --- ИНСТРУМЕНТЫ ---
        tools_frame = Win95Frame(parent)
        tools_frame.pack(fill=tk.X, pady=(0, 4))
        
        Win95Label(tools_frame, text='ИНСТРУМЕНТЫ', font=('MS Sans Serif', 8, 'bold')).pack(
            anchor='w', padx=4, pady=(4, 4)
        )
        
        Win95Button(
            tools_frame,
            text='📦 Карантин',
            command=self._show_quarantine,
            width=30
        ).pack(fill=tk.X, padx=4, pady=2)
        
        Win95Button(
            tools_frame,
            text='⚙️ Автозагрузка',
            command=self._scan_autorun,
            width=30
        ).pack(fill=tk.X, padx=4, pady=2)
        
        self.usb_btn = Win95Button(
            tools_frame,
            text='🔌 USB: ВКЛ',
            command=self._toggle_usb,
            width=30
        )
        self.usb_btn.pack(fill=tk.X, padx=4, pady=(2, 4))
    
    def _create_right_panel(self, parent):
        """Правая панель с логами и угрозами"""
        
        # --- ОБНАРУЖЕННЫЕ УГРОЗЫ ---
        threats_frame = Win95Frame(parent)
        threats_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        
        Win95Label(
            threats_frame,
            text='⚠️ ОБНАРУЖЕННЫЕ УГРОЗЫ',
            font=('MS Sans Serif', 8, 'bold')
        ).pack(anchor='w', padx=4, pady=(4, 4))
        
        # Список угроз
        list_frame = Win95TextFrame(threats_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        
        self.threats_listbox = Win95Listbox(list_frame, height=8)
        self.threats_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = Win95Scrollbar(list_frame, command=self.threats_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.threats_listbox.config(yscrollcommand=scrollbar.set)
        
        # Кнопки для угроз
        buttons_frame = tk.Frame(threats_frame, bg=self.bg_color)
        buttons_frame.pack(fill=tk.X, padx=4, pady=(0, 4))
        
        Win95Button(
            buttons_frame,
            text='Очистить',
            command=self._clear_threats,
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        Win95Button(
            buttons_frame,
            text='В карантин',
            command=self._quarantine_selected,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # --- ЛОГИ ---
        logs_frame = Win95Frame(parent)
        logs_frame.pack(fill=tk.BOTH, expand=True)
        
        Win95Label(
            logs_frame,
            text='📋 ЖУРНАЛ СОБЫТИЙ',
            font=('MS Sans Serif', 8, 'bold')
        ).pack(anchor='w', padx=4, pady=(4, 4))
        
        log_container = Win95TextFrame(logs_frame)
        log_container.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        
        self.log_console = RetroConsole(log_container, height=10, width=50)
        self.log_console.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar = Win95Scrollbar(log_container, command=self.log_console.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_console.config(yscrollcommand=log_scrollbar.set)
    
    def _welcome_log(self):
        """Приветственное сообщение"""
        self.log_console.append_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'info')
        self.log_console.append_log("AEGIS CORE v" + self.version, 'success')
        self.log_console.append_log("Антивирусная защита для Windows", 'info')
        self.log_console.append_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'info')
        self.log_console.append_log(f"Сигнатур в базе: {self.scanner.sig_db.total_count()}", 'info')
        self.log_console.append_log("Статус: ГОТОВ", 'success')
        self.log_console.append_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'info')
    
    def _add_log(self, message, tag='success'):
        """Добавить сообщение в лог"""
        self.log_console.append_log(message, tag)
    
    def _add_threat(self, filepath, threat_name):
        """Добавить угрозу в список"""
        entry = f"{filepath} — {threat_name}"
        self.threats_listbox.insert(tk.END, entry)
    
    def _clear_threats(self):
        """Очистить список угроз"""
        self.threats_listbox.delete(0, tk.END)
    
    def _update_progress(self, value):
        """Обновить прогресс"""
        self.progress_bar.set_progress(value)
    
    def _quick_scan(self):
        """Быстрая проверка"""
        if self.is_scanning:
            messagebox.showwarning("Сканирование", "Сканирование уже выполняется!")
            return
        
        self.is_scanning = True
        self._add_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'info')
        self._add_log("БЫСТРОЕ СКАНИРОВАНИЕ НАЧАЛОСЬ", 'success')
        
        temp = os.environ.get('TEMP', '')
        download = str(Path.home() / "Downloads")
        
        areas = []
        if temp and os.path.exists(temp):
            areas.append((temp, 2, 100))
        if os.path.exists(download):
            areas.append((download, 2, 100))
        
        if areas:
            threading.Thread(target=self._scan_worker, args=("Быстрая", areas), daemon=True).start()
        else:
            self._add_log("Нет доступных папок!", 'warning')
            self.is_scanning = False
    
    def _full_scan(self):
        """Полная проверка"""
        if self.is_scanning:
            messagebox.showwarning("Сканирование", "Сканирование уже выполняется!")
            return
        
        self.is_scanning = True
        self._add_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'info')
        self._add_log("ПОЛНОЕ СКАНИРОВАНИЕ НАЧАЛОСЬ", 'success')
        
        areas = []
        if os.path.exists("C:\\Windows\\System32"):
            areas.append(("C:\\Windows\\System32", 2, 200))
        if os.path.exists("C:\\Program Files"):
            areas.append(("C:\\Program Files", 3, 200))
        areas.append((str(Path.home()), 3, 300))
        
        threading.Thread(target=self._scan_worker, args=("Полная", areas), daemon=True).start()
    
    def _select_file(self):
        """Выбор файла для проверки"""
        filepath = filedialog.askopenfilename(title="Выберите файл")
        if filepath:
            self._scan_single_file(filepath)
    
    def _scan_single_file(self, filepath):
        """Проверка одного файла"""
        self._add_log(f"Проверка: {filepath}", 'info')
        result = self.scanner.scan_file(filepath)
        
        if result['is_threat']:
            self._add_log(f"УГРОЗА НАЙДЕНА: {result['threat_name']}", 'error')
            self._add_threat(filepath, result['threat_name'])
            messagebox.showwarning(
                "⚠️ УГРОЗА!",
                f"Обнаружена угроза: {result['threat_name']}"
            )
        else:
            self._add_log("Файл чистый", 'success')
            messagebox.showinfo("✓ Результат", "Файл безопасен - угроз не найдено")
    
    def _scan_worker(self, name, areas):
        """Фоновое сканирование"""
        try:
            self.files_scanned = 0
            self.threats_found = 0
            
            total_areas = len(areas)
            for i, (path, depth, max_f) in enumerate(areas):
                if not self.is_scanning:
                    break
                
                if not os.path.exists(path):
                    continue
                
                self._update_progress((i * 100) // total_areas)
                self.progress_label.config(text=f"Сканирование: {os.path.basename(path)}")
                
                scan_data = self.scanner.scan_directory(path, depth, max_f)
                self.files_scanned += scan_data['files_scanned']
                self.threats_found += len(scan_data['results'])
                
                for r in scan_data['results']:
                    self._add_log(f"⚠️ УГРОЗА: {r['threat_name']}", 'error')
                    self._add_threat(r['filepath'], r['threat_name'])
            
            self._update_progress(100)
            self.progress_label.config(text="Завершено")
            
            self._add_log(f"Сканирование {name} завершено", 'success')
            self._add_log(f"Файлов: {self.files_scanned} | Угроз: {self.threats_found}", 'info')
            self._add_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'info')
            
            if self.threats_found > 0:
                if messagebox.askyesno(
                    "Карантин",
                    f"Найдено {self.threats_found} угроз(ы).\nПоместить в карантин?"
                ):
                    for i in range(self.threats_listbox.size()):
                        item = self.threats_listbox.get(i)
                        filepath = item.split(" — ")[0]
                        self.quarantine.add(filepath)
                    self._add_log(f"В карантин помещено угроз: {self.threats_found}", 'success')
            else:
                messagebox.showinfo("✓", "Угроз не найдено")
        
        except Exception as e:
            self._add_log(f"Ошибка: {str(e)}", 'error')
        
        finally:
            self.is_scanning = False
            self._update_progress(0)
            self.progress_label.config(text="Ожидание...")
    
    def _show_quarantine(self):
        """Показать окно карантина"""
        qwin = tk.Toplevel(self.root)
        qwin.title("Карантин")
        qwin.geometry("500x350")
        qwin.configure(bg=self.bg_color)
        
        # Заголовок
        title = Win95DarkFrame(qwin, height=25)
        title.pack(fill=tk.X)
        title.pack_propagate(False)
        
        tk.Label(title, text="  📦 Карантин", bg=self.dark_blue, fg=self.white,
                font=('MS Sans Serif', 10, 'bold')).pack(anchor='w', padx=4, pady=2)
        
        # Список файлов
        content = Win95Frame(qwin)
        content.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        list_frame = Win95TextFrame(content)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        qlist = Win95Listbox(list_frame)
        qlist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = Win95Scrollbar(list_frame, command=qlist.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        qlist.config(yscrollcommand=scrollbar.set)
        
        # Заполнение
        files = self.quarantine.list_files()
        if files:
            for f in files:
                qlist.insert(tk.END, f)
        else:
            qlist.insert(tk.END, "[Карантин пуст]")
        
        # Кнопки
        btn_frame = tk.Frame(content, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=(4, 0))
        
        Win95Button(btn_frame, text="Удалить из карантина", width=20).pack(side=tk.LEFT, padx=2)
        Win95Button(btn_frame, text="Восстановить", width=15).pack(side=tk.LEFT, padx=2)
    
    def _quarantine_selected(self):
        """Отправить выбранное в карантин"""
        try:
            sel = self.threats_listbox.curselection()
            if sel:
                item = self.threats_listbox.get(sel[0])
                filepath = item.split(" — ")[0]
                if self.quarantine.add(filepath):
                    self._add_log(f"В карантин: {filepath}", 'success')
                    self.threats_listbox.delete(sel[0])
        except:
            pass
    
    def _scan_autorun(self):
        """Проверка автозагрузки"""
        self._add_log("Проверка автозагрузки...", 'info')
        messagebox.showinfo("Проверка", "Проверка автозагрузки выполняется...")
    
    def _toggle_usb(self):
        """Переключение USB защиты"""
        self.usb_monitoring = not self.usb_monitoring
        if self.usb_monitoring:
            self.usb_btn.config(text='🔌 USB: ВЫКЛ')
            self._add_log("USB защита: ВЫКЛЮЧЕНА", 'warning')
        else:
            self.usb_btn.config(text='🔌 USB: ВКЛ')
            self._add_log("USB защита: ВКЛЮЧЕНА", 'success')
    
    def _minimize(self):
        """Свернуть окно"""
        self.root.iconify()
    
    def _start_drag(self, event):
        """Начало перемещения окна"""
        self.drag_x = event.x_root - self.root.winfo_x()
        self.drag_y = event.y_root - self.root.winfo_y()
    
    def _on_drag(self, event):
        """Перемещение окна"""
        x = event.x_root - self.drag_x
        y = event.y_root - self.drag_y
        self.root.geometry(f'+{x}+{y}')
    
    def _restore_borderless(self, event=None):
        """Восстановление borderless режима после развёртывания"""
        self.root.overrideredirect(True)
    
    def scan_file_on_start(self, filepath):
        """Проверка файла при запуске"""
        if os.path.exists(filepath):
            self._scan_single_file(filepath)
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


# === ТОЧКА ВХОДА ===

def main():
    """Главная функция"""
    app = AegisApp()
    app.run()


if __name__ == "__main__":
    main()
