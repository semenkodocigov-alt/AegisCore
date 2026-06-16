"""Графический интерфейс Aegis Core"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import time
import math
import shutil
from datetime import datetime
from pathlib import Path

try:
    import wmi # pyright: ignore[reportMissingImports]
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

from scanner import FileScanner
from quarantine import QuarantineManager
from sound_manager import get_sound_manager
from file_cleaner import FileCleaner


class AegisApp:
    """Главный класс приложения"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aegis Core - Антивирусная защита")
        self.root.geometry("1250x760")  # Увеличено для лучшего вида
        self.root.configure(bg='#0b1228')
        self.root.resizable(True, True)
        
        # Центрирование окна
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 1250) // 2
        y = (screen_height - 760) // 2
        self.root.geometry(f"1250x760+{x}+{y}")
        
        self.root.overrideredirect(True)
        self.root.bind('<Map>', self._on_map)
        
        # Включаем высокое DPI для сглаживания
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        # Компоненты
        self.scanner = FileScanner()
        self.quarantine = QuarantineManager()
        
        # Состояние
        self.is_scanning = False
        self.files_scanned = 0
        self.threats_found = 0
        
        # Ретро-90-х цветовая схема
        self.colors = {
            'bg': '#0b1228',
            'surface': '#111d3d',
            'surface_hover': '#21335f',
            'header': '#00174f',
            'header_gradient': '#580095',
            'green': '#00ff9e',
            'green_hover': '#33ffba',
            'red': '#ff3f6d',
            'red_hover': '#ff6f9b',
            'orange': '#ffd943',
            'orange_hover': '#ffe676',
            'blue': '#47b5ff',
            'blue_hover': '#7fd8ff',
            'purple': '#c56cff',
            'purple_hover': '#e09bff',
            'text': '#f1f5ff',
            'text_secondary': '#b8c6ff',
            'text_muted': '#7a8cd3',
            'border': '#5a7ac8',
            'border_dark': '#09142c',
            'console_bg': '#050b22',
            'console_fg': '#7ef9b0',
            'accent': '#ff73d6',
            'shadow': '#04111e',
            'success': '#00dd86',
            'warning': '#ffc74d',
            'error': '#ff4a6a'
        }
        
        # Ретро-шрифты для 90-х
        self.fonts = {
            'header': ('Verdana', 18, 'bold'),
            'title': ('Verdana', 13, 'bold'),
            'subtitle': ('Verdana', 10),
            'body': ('Verdana', 10),
            'button': ('Verdana', 10, 'bold'),
            'console': ('Courier New', 10),
            'small': ('Verdana', 8)
        }
        
        # Контакты
        self.author_email = "Kodochigov07@list.ru"
        self.version = "2.0.0"
        
        # Анимация сканирования
        self.animation_angle = 0
        self.animation_running = False
        self.animation_canvas = None
        
        # USB мониторинг
        self.usb_monitoring = False
        self.last_usb_devices = set()
        
        # Активный список угроз (для контекстного меню)
        self.active_threats_listbox = None
        
        # Виджеты для обновления тем
        self.header = None
        self.header_canvas = None
        self.footer_canvas = None


        # Плавный прогресс
        self.current_progress = 0
        self.target_progress = 0
        self.progress_animation_id = None
        
        self._build_ui()
        self._welcome()
    
    def _build_ui(self):
        """Построение интерфейса"""
        # Главный контейнер
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок с ретро-стилем
        self.header = tk.Frame(main, bg=self.colors['header'], height=60, relief='raised', bd=2)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)
        self.header.bind("<Button-1>", self._start_move)
        self.header.bind("<B1-Motion>", self._move_window)
        
        self.header_canvas = tk.Canvas(self.header, height=60, bg=self.colors['header'], highlightthickness=0)
        self.header_canvas.pack(fill=tk.X)
        self.header_canvas.bind("<Button-1>", self._start_move)
        self.header_canvas.bind("<B1-Motion>", self._move_window)
        self.header_canvas.bind("<Configure>", self._update_header_text)
        self._draw_header_gradient(self.header_canvas, 60)
        self._update_header_text()
        
        minimize_btn = tk.Button(self.header, text="▁", command=self._iconify_window,
                                 font=("Verdana", 12, "bold"), bg=self.colors['surface'],
                                 fg=self.colors['text'], bd=2, relief='raised',
                                 activebackground=self.colors['surface_hover'],
                                 activeforeground=self.colors['text'], cursor='hand2', width=3, height=1)
        minimize_btn.place(relx=0.88, rely=0.5, anchor='center')

        close_btn = tk.Button(self.header, text="✕", command=self.root.destroy,
                            font=("Verdana", 12, "bold"), bg=self.colors['red'],
                            fg=self.colors['text'], bd=2, relief='raised',
                            activebackground=self.colors['red_hover'],
                            activeforeground=self.colors['text'], cursor='hand2', width=3, height=1)
        close_btn.place(relx=0.95, rely=0.5, anchor='center')
        
        content = tk.Frame(main, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        left = tk.Frame(content, bg=self.colors['bg'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 7))
        
        status = tk.Frame(left, bg=self.colors['surface'], relief='ridge', bd=2)
        status.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(status, bg=self.colors['surface'])
        inner.pack(padx=20, pady=18, fill=tk.X)
        
        status_icon = tk.Label(inner, text="🛡", font=("Verdana", 22, "bold"), 
                             bg=self.colors['surface'], fg=self.colors['accent'])
        status_icon.pack(side=tk.LEFT, padx=(0, 15))
        
        status_text = tk.Frame(inner, bg=self.colors['surface'])
        status_text.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(status_text, text="ЗАЩИТА АКТИВНА", font=self.fonts['title'],
                bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(status_text, text=f"Сигнатур в базе: {self.scanner.sig_db.total_count()}",
                font=self.fonts['small'], bg=self.colors['surface'],
                fg=self.colors['text_secondary']).pack(anchor='w')
        
        # Анимация сканирования с улучшенным дизайном
        self.animation_canvas = tk.Canvas(left, width=120, height=120, bg=self.colors['bg'], highlightthickness=0)
        self.animation_canvas.pack(pady=15)
        self._draw_animation_idle()
        
        # Кнопки с современным дизайном
        scans_frame = tk.Frame(left, bg=self.colors['bg'])
        scans_frame.pack(fill=tk.X)
        
        tk.Label(scans_frame, text="Сканирование", font=self.fonts['title'],
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor='w', pady=(0, 15))
        
        # Карточки сканирования с ретро-стилем
        scans = [
            ("⚡", "Быстрая проверка", "Критические области системы", self._quick_scan, self.colors['green'], self.colors['green_hover']),
            ("🧠", "Полная проверка", "Глубокий анализ всех файлов", self._full_scan, self.colors['blue'], self.colors['blue_hover']),
            ("📄", "Проверить файл", "Выборочная проверка файла", self._scan_file, self.colors['orange'], self.colors['orange_hover'])
        ]
        
        for badge, title, desc, cmd, color, hover_color in scans:
            card = tk.Frame(left, bg=self.colors['surface'], relief='ridge', bd=2)
            card.pack(fill=tk.X, pady=4)
            
            cinner = tk.Frame(card, bg=self.colors['surface'])
            cinner.pack(fill=tk.X, padx=18, pady=12)
            
            badge_label = tk.Label(cinner, text=badge, font=("Verdana", 18, "bold"), 
                                bg=self.colors['surface'], fg=color)
            badge_label.pack(side=tk.LEFT, padx=(0, 15))
            
            text_frame = tk.Frame(cinner, bg=self.colors['surface'])
            text_frame.pack(side=tk.LEFT, fill=tk.Y)
            
            tk.Label(text_frame, text=title, font=self.fonts['body'],
                    bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w')
            
            tk.Label(text_frame, text=desc, font=self.fonts['small'],
                    bg=self.colors['surface'], fg=self.colors['text_secondary']).pack(anchor='w')
            
            btn = tk.Button(cinner, text="Запустить", command=cmd, font=self.fonts['button'],
                          bg=self.colors['border_dark'], fg=self.colors['text'], bd=2,
                          padx=18, pady=7, cursor='hand2', relief='raised', highlightthickness=0)
            btn.pack(side=tk.RIGHT)
            
            def on_enter(e, b=btn, c=color, h=hover_color):
                b.config(bg=h)
            def on_leave(e, b=btn, c=self.colors['border_dark']):
                b.config(bg=c)
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        
        tools_card = tk.Frame(left, bg=self.colors['surface'], relief='ridge', bd=2)
        tools_card.pack(fill=tk.X, pady=4)

        tools_inner = tk.Frame(tools_card, bg=self.colors['surface'])
        tools_inner.pack(fill=tk.X, padx=18, pady=14)

        tk.Button(tools_inner, text="Просмотр карантина", command=self._show_quarantine_window,
                  font=self.fonts['button'], bg=self.colors['purple'], fg=self.colors['text'], bd=2,
                  padx=16, pady=8, cursor='hand2', relief='raised').pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(tools_inner, text="Проверить автозагрузку", command=self._scan_autorun_entries,
                  font=self.fonts['button'], bg=self.colors['blue'], fg=self.colors['text'], bd=2,
                  padx=16, pady=8, cursor='hand2', relief='raised').pack(side=tk.LEFT)

        usb_card = tk.Frame(left, bg=self.colors['surface'], relief='ridge', bd=2)
        usb_card.pack(fill=tk.X, pady=4)
        
        usb_inner = tk.Frame(usb_card, bg=self.colors['surface'])
        usb_inner.pack(fill=tk.X, padx=18, pady=14)
        
        usb_icon = tk.Label(usb_inner, text="🔌", font=("Verdana", 18, "bold"), 
                          bg=self.colors['surface'], fg=self.colors['purple'])
        usb_icon.pack(side=tk.LEFT, padx=(0, 15))
        
        usb_text = tk.Frame(usb_inner, bg=self.colors['surface'])
        usb_text.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(usb_text, text="USB Защита", font=self.fonts['body'],
                bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(usb_text, text="Автопроверка подключенных устройств", font=self.fonts['small'],
                bg=self.colors['surface'], fg=self.colors['text_secondary']).pack(anchor='w')
        
        self.usb_button = tk.Button(usb_inner, text="ВКЛ", command=self._toggle_usb_monitoring,
                                  font=self.fonts['button'], bg=self.colors['red'],
                                  fg=self.colors['text'], bd=2, padx=20, pady=8,
                                  cursor='hand2', relief='raised', highlightthickness=0)
        self.usb_button.pack(side=tk.RIGHT)
        
        def usb_enter(e):
            if self.usb_monitoring:
                self.usb_button.config(bg=self.colors['green_hover'])
            else:
                self.usb_button.config(bg=self.colors['red_hover'])
        
        def usb_leave(e):
            if self.usb_monitoring:
                self.usb_button.config(bg=self.colors['green'])
            else:
                self.usb_button.config(bg=self.colors['red'])
        
        self.usb_button.bind("<Enter>", usb_enter)
        self.usb_button.bind("<Leave>", usb_leave)
        
        cache_card = tk.Frame(left, bg=self.colors['surface'], relief='ridge', bd=2)
        cache_card.pack(fill=tk.X, pady=4)
        
        cache_inner = tk.Frame(cache_card, bg=self.colors['surface'])
        cache_inner.pack(fill=tk.X, padx=18, pady=14)
        
        cache_icon = tk.Label(cache_inner, text="🧹", font=("Verdana", 18, "bold"),
                            bg=self.colors['surface'], fg=self.colors['blue'])
        cache_icon.pack(side=tk.LEFT, padx=(0, 15))
        
        cache_text = tk.Frame(cache_inner, bg=self.colors['surface'])
        cache_text.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(cache_text, text="Очистка кэша", font=self.fonts['body'],
                bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(cache_text, text="Очистить кэш приложений и временные файлы",
                font=self.fonts['small'], bg=self.colors['surface'],
                fg=self.colors['text_secondary']).pack(anchor='w')
        
        cache_btn = tk.Button(cache_inner, text="Очистить", command=self._clear_cache,
                            font=self.fonts['button'], bg=self.colors['blue'], fg=self.colors['text'], bd=2,
                            padx=20, pady=8, cursor='hand2', relief='raised', highlightthickness=0)
        cache_btn.pack(side=tk.RIGHT)
        
        def cache_enter(e):
            cache_btn.config(bg=self.colors['blue_hover'])
        def cache_leave(e):
            cache_btn.config(bg=self.colors['blue'])
        
        cache_btn.bind("<Enter>", cache_enter)
        cache_btn.bind("<Leave>", cache_leave)

        # Правая панель - лог + список угроз в ретро-стиле
        right = tk.Frame(content, bg=self.colors['surface'], relief='flat', bd=0, width=620)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right.pack_propagate(False)
        
        threats_frame = tk.Frame(right, bg=self.colors['surface'])
        threats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(15, 0))
        
        threats_header = tk.Frame(threats_frame, bg=self.colors['surface'])
        threats_header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(threats_header, text="⚠️", font=("Verdana", 16, "bold"), 
                bg=self.colors['surface'], fg=self.colors['error']).pack(side=tk.LEFT)
        
        tk.Label(threats_header, text="Обнаруженные угрозы", font=("Verdana", 14, "bold"),
            bg=self.colors['surface'], fg=self.colors['text']).pack(side=tk.LEFT, padx=10)
        
        tk.Button(threats_header, text="Экспорт", command=self._export_threats_list,
             font=self.fonts['small'], bg=self.colors['surface'],
             fg=self.colors['text_secondary'], bd=2, relief='raised', cursor='hand2').pack(side=tk.RIGHT, padx=(0, 5))
        tk.Button(threats_header, text="Просмотр", command=self._show_suspicious_files_window,
             font=self.fonts['small'], bg=self.colors['surface'],
             fg=self.colors['text_secondary'], bd=2, relief='raised', cursor='hand2').pack(side=tk.RIGHT, padx=(0, 5))
        tk.Button(threats_header, text="Развернуть", command=lambda: self._open_large_threats_window(),
             font=self.fonts['small'], bg=self.colors['surface'],
             fg=self.colors['text_secondary'], bd=2, relief='raised', cursor='hand2').pack(side=tk.RIGHT, padx=(0, 5))
        tk.Button(threats_header, text="Очистить", command=self._clear_threats_list,
             font=self.fonts['small'], bg=self.colors['surface'],
             fg=self.colors['text_secondary'], bd=2, relief='raised', cursor='hand2').pack(side=tk.RIGHT)

        self.pie_canvas = tk.Canvas(threats_frame, width=580, height=200, bg=self.colors['surface'], highlightthickness=0)
        self.pie_canvas.pack(fill=tk.X, pady=(0, 10), padx=20)

        list_frame = tk.Frame(threats_frame, bg=self.colors['surface'], relief='flat', bd=0)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.threats_listbox = tk.Listbox(
            list_frame,
            height=8,
            bg=self.colors['console_bg'],
            fg=self.colors['console_fg'],
            selectbackground=self.colors['purple'],
            selectforeground=self.colors['surface'],
            bd=0,
            relief='flat',
            highlightthickness=0,
            font=self.fonts['console']
        )
        self.threats_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=(2, 0))
        # Enable mouse wheel scrolling for the listbox
        try:
            self._bind_mousewheel(self.threats_listbox)
        except Exception:
            pass
        
        threats_scroll = tk.Scrollbar(list_frame, command=self.threats_listbox.yview,
                                     bg=self.colors['border_dark'], troughcolor=self.colors['surface'])
        threats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        threats_xscroll = tk.Scrollbar(list_frame, orient=tk.HORIZONTAL,
                                      command=self.threats_listbox.xview,
                                      bg=self.colors['border_dark'], troughcolor=self.colors['surface'])
        threats_xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.threats_listbox.config(yscrollcommand=threats_scroll.set, xscrollcommand=threats_xscroll.set)
        self.threats_listbox.bind("<Double-Button-1>", lambda e: self._open_selected_threat_location())
        self.threats_listbox.bind("<Button-3>", self._show_threats_context_menu)
        self._draw_threat_pie_chart()
        
        self.threats_context_menu = tk.Menu(self.root, tearoff=0)
        self.threats_context_menu.add_command(label="Открыть папку", command=self._open_selected_threat_location)
        self.threats_context_menu.add_command(label="Копировать путь", command=self._copy_selected_threat_path)
        self.threats_context_menu.add_command(label="В карантин", command=self._send_selected_to_quarantine)
        self.threats_context_menu.add_command(label="Проверить подпись Microsoft", command=self._check_selected_signature)
        
        self.active_threats_listbox = self.threats_listbox

        footer = tk.Frame(main, bg=self.colors['header'], height=40, relief='raised', bd=2)
        footer.pack(fill=tk.X)
        footer.pack_propagate(False)

        footer_canvas = tk.Canvas(footer, height=40, bg=self.colors['header'], highlightthickness=0)
        footer_canvas.pack(fill=tk.X)
        footer_canvas.bind("<Configure>", self._update_footer_text)
        self.footer_canvas = footer_canvas

        self._draw_footer_gradient(footer_canvas, 40)
        self._update_footer_text()
        
    def _show_threats_context_menu(self, event):
        """Показать контекстное меню для списка угроз"""
        if event.widget == self.threats_listbox:
            self.active_threats_listbox = self.threats_listbox
        elif hasattr(self, 'threats_listbox_window') and event.widget == self.threats_listbox_window:
            self.active_threats_listbox = self.threats_listbox_window
        else:
            return

        try:
            self.active_threats_listbox.selection_clear(0, tk.END)
            self.active_threats_listbox.selection_set(self.active_threats_listbox.nearest(event.y))
            self.threats_context_menu.post(event.x_root, event.y_root)
        except:
            pass

    def _open_selected_threat_location(self):
        """Открыть папку с выбранной угрозой"""
        path = self._get_selected_threat_path()
        if not path:
            return
        try:
            import os
            os.startfile(os.path.dirname(path))
        except Exception:
            messagebox.showerror("Ошибка", "Не удалось открыть папку")

    def _copy_selected_threat_path(self):
        """Копировать путь выбранной угрозы"""
        path = self._get_selected_threat_path()
        if not path:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(path)
            messagebox.showinfo("Скопировано", "Путь скопирован в буфер обмена")
        except Exception:
            messagebox.showerror("Ошибка", "Не удалось скопировать путь")

    def _get_selected_threat_path(self):
        """Получить путь выбранной угрозы"""
        try:
            selection = None
            if hasattr(self, 'active_threats_listbox'):
                selection = self.active_threats_listbox.curselection()
                if selection:
                    item = self.active_threats_listbox.get(selection[0])
                    if " — " in item:
                        return item.split(" — ", 1)[0].strip()
            return None
        except:
            return None

    def _show_quarantine_window(self):
        """Показать содержимое карантина"""
        window = tk.Toplevel(self.root)
        window.title("Файлы в карантине")
        window.geometry("700x450")
        window.configure(bg=self.colors['bg'])

        header = tk.Frame(window, bg=self.colors['header'], height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Карантин", font=self.fonts['header'], bg=self.colors['header'], fg='white').pack(anchor='w', padx=20, pady=15)

        frame = tk.Frame(window, bg=self.colors['surface'], relief='ridge', bd=2)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        quarantine_list = tk.Listbox(frame, bg=self.colors['console_bg'], fg=self.colors['console_fg'],
                                    selectbackground=self.colors['purple'], selectforeground=self.colors['surface'], font=self.fonts['console'], bd=2, relief='ridge')
        quarantine_list.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 10))

        scrollbar = tk.Scrollbar(frame, command=quarantine_list.yview, bg=self.colors['border_dark'], troughcolor=self.colors['surface'])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        quarantine_list.config(yscrollcommand=scrollbar.set)

        files = self.quarantine.list_files()
        if files:
            for path in files:
                quarantine_list.insert(tk.END, path)
        else:
            quarantine_list.insert(tk.END, 'Карантин пуст')

        try:
            self._bind_mousewheel(quarantine_list)
        except Exception:
            pass

        buttons = tk.Frame(window, bg=self.colors['bg'])
        buttons.pack(fill=tk.X, padx=15, pady=(0, 15))

        def open_selected_quarantine():
            sel = quarantine_list.curselection()
            if not sel:
                return
            path = quarantine_list.get(sel[0])
            if os.path.exists(path):
                os.startfile(os.path.dirname(path))
            else:
                messagebox.showerror('Ошибка', 'Файл не найден')

        def delete_selected_quarantine():
            sel = quarantine_list.curselection()
            if not sel:
                return
            path = quarantine_list.get(sel[0])
            if self.quarantine.remove(path):
                quarantine_list.delete(sel[0])
                self._log(f'🗑️ Удалён из карантина: {path}')
                messagebox.showinfo('Карантин', 'Файл удалён из карантина')
            else:
                messagebox.showerror('Ошибка', 'Не удалось удалить файл из карантина')

        tk.Button(buttons, text='Открыть папку', command=open_selected_quarantine,
                  font=self.fonts['button'], bg=self.colors['blue'], fg=self.colors['text'], bd=2,
                  relief='raised', padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT)
        tk.Button(buttons, text='Удалить из карантина', command=delete_selected_quarantine,
                  font=self.fonts['button'], bg=self.colors['red'], fg=self.colors['text'], bd=2,
                  relief='raised', padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=(10, 0))

    def _show_suspicious_files_window(self):
        window = tk.Toplevel(self.root)
        window.title("Подозрительные файлы")
        window.geometry("1050x680")
        window.minsize(940, 560)
        window.configure(bg=self.colors['bg'])
        window.resizable(True, True)

        header = tk.Frame(window, bg=self.colors['header'], height=62, relief='raised', bd=2)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="⚠️ Подозрительные файлы", font=self.fonts['header'],
                 bg=self.colors['header'], fg=self.colors['text']).pack(anchor='w', padx=20, pady=16)

        content_frame = tk.Frame(window, bg=self.colors['surface'], relief='ridge', bd=2)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        left_panel = tk.Frame(content_frame, bg=self.colors['surface'])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_panel = tk.Frame(content_frame, bg=self.colors['surface'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        tk.Label(left_panel, text="Список угроз", font=self.fonts['body'],
                 bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w', padx=12, pady=(8, 6))

        suspicious_list = tk.Listbox(left_panel, bg=self.colors['console_bg'], fg=self.colors['console_fg'],
                                     selectbackground=self.colors['purple'], selectforeground=self.colors['surface'],
                                     font=self.fonts['console'], bd=2, relief='ridge', activestyle='none')
        suspicious_list.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(12, 0), pady=(0, 8))

        scrollbar = tk.Scrollbar(left_panel, command=suspicious_list.yview,
                                 bg=self.colors['border_dark'], troughcolor=self.colors['surface'])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8), padx=(0, 12))
        suspicious_list.config(yscrollcommand=scrollbar.set)

        for item in self.threats_listbox.get(0, tk.END):
            suspicious_list.insert(tk.END, item)
        if suspicious_list.size() == 0:
            suspicious_list.insert(tk.END, 'Угроз не обнаружено')

        try:
            self._bind_mousewheel(suspicious_list)
        except Exception:
            pass

        tk.Label(right_panel, text="Информация", font=self.fonts['body'],
                 bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w', padx=12, pady=(8, 6))

        details_text = tk.Text(right_panel, bg=self.colors['console_bg'], fg=self.colors['console_fg'],
                                font=self.fonts['console'], bd=2, relief='ridge', wrap='word', height=12)
        details_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        details_text.insert(tk.END, "Выберите угрозу в списке, чтобы увидеть путь файла и дополнительные сведения.")
        details_text.config(state=tk.DISABLED)

        summary_label = tk.Label(right_panel, text=f"Всего угроз: {max(0, suspicious_list.size() - (1 if suspicious_list.get(0) == 'Угроз не обнаружено' else 0))}",
                                 font=self.fonts['small'], bg=self.colors['surface'], fg=self.colors['text_secondary'])
        summary_label.pack(anchor='w', padx=12, pady=(0, 8))

        def update_details(event=None):
            selection = suspicious_list.curselection()
            if not selection:
                return
            value = suspicious_list.get(selection[0])
            details_text.config(state=tk.NORMAL)
            details_text.delete('1.0', tk.END)
            if value == 'Угроз не обнаружено':
                details_text.insert(tk.END, "Список не содержит обнаруженных угроз.")
            else:
                details_text.insert(tk.END, f"{value}\n\n")
                if ' — ' in value:
                    path, threat = value.split(' — ', 1)
                    details_text.insert(tk.END, f"Файл: {path}\n")
                    details_text.insert(tk.END, f"Обнаруженная угроза: {threat}\n")
            details_text.config(state=tk.DISABLED)

        def open_selected_from_window(event):
            self.active_threats_listbox = suspicious_list
            self._open_selected_threat_location()

        suspicious_list.bind('<<ListboxSelect>>', update_details)
        suspicious_list.bind('<Double-Button-1>', open_selected_from_window)
        suspicious_list.bind('<Button-3>', self._show_threats_context_menu)
        self.threats_listbox_window = suspicious_list

        buttons = tk.Frame(window, bg=self.colors['bg'])
        buttons.pack(fill=tk.X, padx=15, pady=(0, 15))

        tk.Button(buttons, text='Открыть папку', command=self._open_selected_threat_location,
                  font=self.fonts['button'], bg=self.colors['blue'], fg=self.colors['text'], bd=2,
                  relief='raised', padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT)
        tk.Button(buttons, text='В карантин', command=self._send_selected_to_quarantine,
                  font=self.fonts['button'], bg=self.colors['purple'], fg=self.colors['text'], bd=2,
                  relief='raised', padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(buttons, text='Лечить', command=self._heal_selected_threat,
                  font=self.fonts['button'], bg=self.colors['orange'], fg=self.colors['text'], bd=2,
                  relief='raised', padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(buttons, text='Удалить', command=self._delete_selected_threat,
                  font=self.fonts['button'], bg=self.colors['red'], fg=self.colors['text'], bd=2,
                  relief='raised', padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(buttons, text='Проверить подпись', command=self._check_selected_signature,
                  font=self.fonts['button'], bg=self.colors['green'], fg=self.colors['text'], bd=2,
                  relief='raised', padx=15, pady=8, cursor='hand2').pack(side=tk.LEFT, padx=(10, 0))

    def _is_system_file(self, filepath):
        try:
            absolute_path = os.path.normcase(os.path.abspath(filepath))
            windir = os.environ.get('WINDIR', 'C:\\Windows')
            system_paths = [
                os.path.normcase(os.path.join(windir, 'System32')),
                os.path.normcase(os.path.join(windir, 'SysWOW64')),
                os.path.normcase(os.path.join(windir, 'WinSxS')),
                os.path.normcase(windir)
            ]
            return any(absolute_path == path or absolute_path.startswith(path + os.sep) for path in system_paths)
        except Exception:
            return False

    def _is_signed_by_microsoft(self, filepath):
        if os.name != 'nt' or not os.path.exists(filepath):
            return None
        try:
            import subprocess, json
            safe_path = filepath.replace("'", "''")
            ps_script = (
                f"$sig = Get-AuthenticodeSignature -FilePath '{safe_path}';"
                "$result = [PSCustomObject]@{Status=$sig.Status;"
                "Signer=($sig.SignerCertificate.Subject -join ', ');"
                "Issuer=($sig.SignerCertificate.IssuerName -join ', ')};"
                "ConvertTo-Json $result"
            )
            output = subprocess.check_output(['powershell', '-NoProfile', '-Command', ps_script], stderr=subprocess.DEVNULL, text=True)
            data = json.loads(output)
            status = data.get('Status', '')
            signer = data.get('Signer', '') or ''
            issuer = data.get('Issuer', '') or ''
            if status == 'Valid' and ('Microsoft' in signer or 'Microsoft' in issuer):
                return True
            return False
        except Exception:
            return None

    def _extract_command_path(self, command_string):
        try:
            import re
            match = re.search(r'"([^"]+)"', command_string)
            if match:
                return match.group(1)
            return command_string.split()[0] if command_string else None
        except Exception:
            return None

    def _scan_autorun_entries(self):
        """Проверка подозрительных записей автозагрузки"""
        self._log('🔎 Сканирование автозагрузки')
        suspicious = []
        try:
            startup_paths = [
                os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'),
                os.path.join(os.environ.get('ProgramData', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            ]
            for folder in startup_paths:
                if os.path.isdir(folder):
                    for filename in os.listdir(folder):
                        filepath = os.path.join(folder, filename)
                        if os.path.isfile(filepath):
                            if not self._is_signed_by_microsoft(filepath):
                                suspicious.append((filepath, 'Файл автозагрузки не подписан Microsoft'))

            import winreg
            run_keys = [
                (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run'),
                (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\Run'),
                (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\RunOnce'),
                (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\RunOnce')
            ]
            for hive, subkey in run_keys:
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                target_path = self._extract_command_path(value)
                                if target_path and not os.path.exists(target_path):
                                    suspicious.append((value, 'Автозагрузка указывает на несуществующий путь'))
                                elif target_path and self._is_system_file(target_path) and self._is_signed_by_microsoft(target_path) is False:
                                    suspicious.append((target_path, 'Системный автозапуск без подписи Microsoft'))
                                i += 1
                            except OSError:
                                break
                except Exception:
                    pass
        except Exception as e:
            self._log(f'❌ Ошибка автозагрузки: {e}')

        if suspicious:
            self._log(f'⚠️ Найдено подозрительных автозапусков: {len(suspicious)}')
            for path, reason in suspicious:
                self._log(f'   └─ {path} — {reason}')
            messagebox.showwarning('Автозагрузка', f'Найдены подозрительные записи автозагрузки: {len(suspicious)}')
        else:
            self._log('✅ Автозагрузка не содержит подозрительных записей')
            messagebox.showinfo('Автозагрузка', 'Автозагрузка чиста')

    def scan_file_on_start(self, filepath):
        self._scan_file_path(filepath, ask_quarantine=False)

    def _draw_header_gradient(self, canvas, height):
        canvas.delete("header_gradient")
        width = canvas.winfo_width() or 1100
        for i in range(height):
            color = self._interpolate_color(self.colors['header'], self.colors['header_gradient'], i / height)
            canvas.create_line(0, i, width, i, fill=color, tags="header_gradient")

    def _update_header_text(self, event=None):
        if not self.header_canvas:
            return
        self._draw_header_gradient(self.header_canvas, 60)
        self.header_canvas.delete("header_text")
        self.header_canvas.create_text(30, 22, text="AEGIS CORE",
                                font=self.fonts['header'], fill='white', anchor='w', tags="header_text")
        self.header_canvas.create_text(30, 42, text="Антивирусная защита",
                                font=self.fonts['subtitle'], fill='#94a3b8', anchor='w', tags="header_text")

    def _draw_footer_gradient(self, canvas, height):
        canvas.delete("footer_gradient")
        width = canvas.winfo_width() or 1100
        for i in range(height):
            color = self._interpolate_color(self.colors['header'], self.colors['header_gradient'], i / height)
            canvas.create_line(0, i, width, i, fill=color, tags="footer_gradient")

    def _update_footer_text(self, event=None):
        if not self.footer_canvas:
            return
        self._draw_footer_gradient(self.footer_canvas, 40)
        self.footer_canvas.delete("footer_text")
        width = self.footer_canvas.winfo_width() or 1100
        self.footer_canvas.create_text(30, 20, text=f"v{self.version}",
                                font=self.fonts['small'], fill='#94a3b8', anchor='w', tags="footer_text")
        self.footer_canvas.create_text(width // 2, 20, text="© 2026 Aegis Core",
                                font=self.fonts['small'], fill='#94a3b8', anchor='center', tags="footer_text")
        self.footer_canvas.create_text(width - 30, 20, text=self.author_email,
                                font=self.fonts['small'], fill='#94a3b8', anchor='e', tags="footer_text")

    def _log(self, msg):
        """Логирование"""
        def action():
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_widget.insert(tk.END, f"[{timestamp}] {msg}\n")
                self.log_widget.see(tk.END)
            except Exception:
                pass
        self._safe_ui(action)
    
    def _add_threat_file(self, filepath, threat_name):
        """Добавить зараженный файл в список"""
        def action():
            try:
                entry = f"{filepath} — {threat_name}"
                self.threats_listbox.insert(tk.END, entry)
                self.threats_listbox.see(tk.END)
                self._update_threat_pie_chart()
            except Exception:
                pass
        self._safe_ui(action)

    def _draw_threat_pie_chart(self):
        if not hasattr(self, 'pie_canvas') or not self.pie_canvas:
            return
        self.pie_canvas.delete('all')
        counts = {}
        for i in range(self.threats_listbox.size()):
            item = self.threats_listbox.get(i)
            if ' — ' in item:
                threat_type = item.split(' — ', 1)[1]
            else:
                threat_type = 'Неизвестно'
            counts[threat_type] = counts.get(threat_type, 0) + 1

        if not counts:
            width = self.pie_canvas.winfo_width() or int(self.pie_canvas['width'])
            self.pie_canvas.create_text(width // 2, 80, text='Нет обнаруженных угроз',
                                        font=self.fonts['body'], fill=self.colors['text_muted'])
            return

        total = sum(counts.values())
        start_angle = 0
        colors = [self.colors['red'], self.colors['orange'], self.colors['blue'], self.colors['green'], self.colors['purple']]

        # Dynamic layout based on canvas width
        width = self.pie_canvas.winfo_width() or int(self.pie_canvas['width'])
        pie_left = 20
        pie_top = 20
        pie_right = pie_left + 220
        pie_bottom = pie_top + 160
        legend_x = pie_right + 30
        legend_y = 20
        for index, (threat_type, value) in enumerate(counts.items()):
            extent = int(360 * (value / total))
            self.pie_canvas.create_arc(pie_left, pie_top, pie_right, pie_bottom, start=start_angle,
                                       extent=extent, fill=colors[index % len(colors)], outline='')
            self.pie_canvas.create_rectangle(legend_x, legend_y + index * 22,
                                            legend_x + 14, legend_y + index * 22 + 14,
                                            fill=colors[index % len(colors)], outline='')
            self.pie_canvas.create_text(legend_x + 20, legend_y + index * 22 + 7,
                                       text=f"{threat_type} ({value})",
                                       anchor='w', font=self.fonts['small'], fill=self.colors['text'])
            start_angle += extent

        # Title removed as per user request

    def _update_threat_pie_chart(self):
        self._safe_ui(lambda: self._draw_threat_pie_chart())

    def _open_large_threats_window(self):
        """Открыть безрамочное большое окно со списком обнаруженных угроз"""
        try:
            w = tk.Toplevel(self.root)
            w.overrideredirect(True)
            w.configure(bg=self.colors['bg'])

            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            width = int(sw * 0.85)
            height = int(sh * 0.8)
            x = (sw - width) // 2
            y = (sh - height) // 2
            w.geometry(f"{width}x{height}+{x}+{y}")

            header = tk.Frame(w, bg=self.colors['header'], height=56)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            tk.Label(header, text="Обнаруженные угрозы — Развернуто", font=self.fonts['header'],
                     bg=self.colors['header'], fg=self.colors['text']).pack(side=tk.LEFT, padx=20)
            tk.Button(header, text="✕", command=w.destroy, font=("Verdana", 12, "bold"), bg=self.colors['red'], fg=self.colors['text'], bd=0, relief='flat', cursor='hand2').pack(side=tk.RIGHT, padx=12, pady=8)

            frame = tk.Frame(w, bg=self.colors['surface'])
            frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

            large_list = tk.Listbox(frame, bg=self.colors['console_bg'], fg=self.colors['console_fg'],
                                    font=self.fonts['console'], bd=0, relief='flat', highlightthickness=0)
            large_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            try:
                self._bind_mousewheel(large_list)
            except Exception:
                pass

            scrollbar = tk.Scrollbar(frame, command=large_list.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            large_list.config(yscrollcommand=scrollbar.set)

            # populate
            for i in range(self.threats_listbox.size()):
                large_list.insert(tk.END, self.threats_listbox.get(i))

            def on_double(e):
                try:
                    sel = large_list.curselection()
                    if not sel:
                        return
                    item = large_list.get(sel[0])
                    # reuse existing opener by setting active listbox
                    self.active_threats_listbox = large_list
                    # temporarily insert item into a hidden listbox to parse path, or reuse logic
                    if " — " in item:
                        path = item.split(" — ", 1)[0].strip()
                        if os.path.exists(path):
                            os.startfile(os.path.dirname(path))
                        else:
                            messagebox.showerror('Ошибка', 'Файл не найден')
                except Exception:
                    pass

            def on_right(e):
                try:
                    self.active_threats_listbox = large_list
                    large_list.selection_clear(0, tk.END)
                    large_list.selection_set(large_list.nearest(e.y))
                    self.threats_context_menu.post(e.x_root, e.y_root)
                except Exception:
                    pass

            large_list.bind('<Double-Button-1>', on_double)
            large_list.bind('<Button-3>', on_right)

        except Exception:
            pass

    def _on_mousewheel(self, event, widget):
        try:
            if os.name == 'nt':
                # Windows: event.delta is multiple of 120
                delta = -1 * int(event.delta / 120)
            else:
                # Linux/Unix: use button 4/5
                if hasattr(event, 'num'):
                    delta = 1 if event.num == 5 else -1
                else:
                    delta = 0
            widget.yview_scroll(delta, 'units')
        except Exception:
            pass

    def _bind_mousewheel(self, widget):
        try:
            # Ensure widget receives focus on enter so wheel events target it
            widget.bind('<Enter>', lambda e: widget.focus_set())
            if os.name == 'nt':
                widget.bind('<MouseWheel>', lambda e, w=widget: self._on_mousewheel(e, w))
            else:
                widget.bind('<Button-4>', lambda e, w=widget: self._on_mousewheel(e, w))
                widget.bind('<Button-5>', lambda e, w=widget: self._on_mousewheel(e, w))
        except Exception:
            pass

    def _send_selected_to_quarantine(self):
        path = self._get_selected_threat_path()
        if not path:
            messagebox.showwarning('Карантин', 'Выберите файл для помещения в карантин')
            return
        if self.quarantine.add(path):
            self._log(f'📦 В карантин: {path}')
            messagebox.showinfo('Карантин', 'Файл отправлен в карантин')
        else:
            messagebox.showerror('Карантин', 'Не удалось поместить файл в карантин')

    def _check_selected_signature(self):
        path = self._get_selected_threat_path()
        if not path:
            messagebox.showwarning('Подпись', 'Выберите файл')
            return
        result = self._is_signed_by_microsoft(path)
        if result is True:
            messagebox.showinfo('Подпись', 'Файл подписан Microsoft')
        elif result is False:
            messagebox.showwarning('Подпись', 'Файл не подписан Microsoft или подпись отсутствует')
        else:
            messagebox.showinfo('Подпись', 'Не удалось проверить подпись')

    def _heal_selected_threat(self):
        """Попытка лечения выбранного файла"""
        path = self._get_selected_threat_path()
        if not path:
            messagebox.showwarning('Лечение', 'Выберите файл для лечения')
            return
        
        if not os.path.exists(path):
            messagebox.showerror('Ошибка', 'Файл не найден')
            return
        
        # Подтверждение
        if messagebox.askyesno('Лечение', f'Лечить файл?\n{path}'):
            cleaner = FileCleaner()
            success, message = cleaner.disinfect_file(path)
            
            if success:
                self._log(f'✓ Файл пролечен: {path}')
                messagebox.showinfo('Лечение', message)
            else:
                self._log(f'✗ Ошибка лечения: {message}')
                messagebox.showerror('Ошибка лечения', message)

    def _delete_selected_threat(self):
        """Удаление выбранного файла"""
        path = self._get_selected_threat_path()
        if not path:
            messagebox.showwarning('Удаление', 'Выберите файл для удаления')
            return
        
        if not os.path.exists(path):
            messagebox.showerror('Ошибка', 'Файл не найден')
            return
        
        # Мощное предупреждение
        response = messagebox.askyesnocancel(
            'Удаление файла',
            f'Вы уверены, что хотите удалить файл?\n\n{path}\n\n'
            'Это действие необратимо!\n\n'
            'Yes - Удалить с резервной копией\n'
            'No - Безопасное удаление (перезапись)',
            icon=messagebox.WARNING
        )
        
        if response is None:
            return
        
        cleaner = FileCleaner()
        
        if response:
            # Обычное удаление с резервной копией
            success, message = cleaner.delete_file(path, create_backup=True)
        else:
            # Безопасное удаление
            success, message = cleaner.secure_delete(path, passes=3)
        
        if success:
            self._log(f'🗑️ Файл удален: {path}')
            
            # Удаляем из списка угроз
            try:
                index = self.threats_listbox.curselection()[0]
                self.threats_listbox.delete(index)
            except:
                pass
            
            messagebox.showinfo('Удаление', 'Файл успешно удален')
        else:
            self._log(f'✗ Ошибка удаления: {message}')
            messagebox.showerror('Ошибка удаления', message)

    def _clear_threats_list(self):
        """Очистка списка обнаруженных угроз"""
        def action():
            try:
                self.threats_listbox.delete(0, tk.END)
            except Exception:
                pass
        self._safe_ui(action)
    
    def _clear_log(self):
        """Очистка лога"""
        try:
            self.log_widget.delete(1.0, tk.END)
        except:
            pass

    def _get_selected_threat_path(self):
        try:
            selection = self.threats_listbox.curselection()
            if not selection:
                return None
            selected = self.threats_listbox.get(selection[0])
            return selected.split(' — ', 1)[0]
        except Exception:
            return None



    def _copy_selected_threat_path(self):
        path = self._get_selected_threat_path()
        if not path:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(path)
            messagebox.showinfo("Скопировано", "Путь скопирован в буфер обмена")
        except Exception:
            messagebox.showerror("Ошибка", "Не удалось скопировать путь")

    def _export_threats_list(self):
        try:
            if self.threats_listbox.size() == 0:
                messagebox.showinfo("Экспорт", "Список угроз пуст")
                return
            filename = filedialog.asksaveasfilename(
                title="Сохранить список угроз",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*")]
            )
            if not filename:
                return
            with open(filename, 'w', encoding='utf-8') as f:
                for i in range(self.threats_listbox.size()):
                    f.write(self.threats_listbox.get(i) + '\n')
            messagebox.showinfo("Экспорт", f"Список угроз сохранён в:\n{filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

    def _update_progress(self, val, text=""):
        """Обновление прогресса"""
        def action():
            try:
                self.target_progress = max(0, min(100, val))
                if text:
                    self.progress_label.config(text=text)
                if self.progress_animation_id:
                    self.root.after_cancel(self.progress_animation_id)
                    self.progress_animation_id = None
                self._animate_progress()
            except Exception:
                pass
        self._safe_ui(action)
    
    def _animate_progress(self):
        """Плавное обновление прогресс-бара"""
        if self.current_progress == self.target_progress:
            self.progress_animation_id = None
            return
        
        step = max(1, min(5, abs(self.target_progress - self.current_progress)))
        if self.current_progress < self.target_progress:
            self.current_progress += step
        else:
            self.current_progress -= step
        
        self.progress_bar['value'] = self.current_progress
        self.progress_animation_id = self.root.after(25, self._animate_progress)
    
    def _welcome(self):
        """Приветствие"""
        self._log("Aegis Core запущен")
        self._log(f"Сигнатур: {self.scanner.sig_db.total_count()}")
        self._log("Готов к работе")
        self._log("=" * 50)
    
    def _safe_ui(self, func, *args, **kwargs):
        try:
            if threading.current_thread() is threading.main_thread():
                func(*args, **kwargs)
            else:
                self.root.after(0, lambda: func(*args, **kwargs))
        except Exception:
            pass
    
    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y
    
    def _move_window(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _iconify_window(self):
        self.root.overrideredirect(False)
        self.root.iconify()
        # overrideredirect включится при <Map>

    def _on_map(self, event=None):
        self.root.overrideredirect(True)



    def _interpolate_color(self, color1, color2, factor):
        """Интерполяция между двумя цветами"""
        try:
            # Преобразуем hex в RGB
            r1 = int(color1[1:3], 16)
            g1 = int(color1[3:5], 16)
            b1 = int(color1[5:7], 16)
            
            r2 = int(color2[1:3], 16)
            g2 = int(color2[3:5], 16)
            b2 = int(color2[5:7], 16)
            
            # Интерполяция
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color1
    
    def _draw_animation_idle(self):
        """Рисование статичной иконки"""
        if not self.animation_canvas:
            return
        self.animation_canvas.delete("all")
        # Рисуем щит
        self.animation_canvas.create_oval(20, 20, 80, 80, fill=self.colors['blue'], outline=self.colors['blue'])
        self.animation_canvas.create_polygon(50, 15, 35, 35, 65, 35, fill=self.colors['surface'], outline=self.colors['surface'])
    
    def _draw_animation_scanning(self):
        """Рисование вращающейся иконки"""
        if not self.animation_canvas or not self.animation_running:
            return
        self.animation_canvas.delete("all")
        
        # Вращающиеся сегменты
        center_x, center_y = 50, 50
        radius = 30
        
        for i in range(8):
            angle = math.radians(self.animation_angle + i * 45)
            x1 = center_x + radius * math.cos(angle)
            y1 = center_y + radius * math.sin(angle)
            x2 = center_x + (radius - 10) * math.cos(angle)
            y2 = center_y + (radius - 10) * math.sin(angle)
            
            color = self.colors['green'] if i < 4 else self.colors['blue']
            self.animation_canvas.create_line(x1, y1, x2, y2, fill=color, width=3)
        
        # Центральный щит
        self.animation_canvas.create_oval(35, 35, 65, 65, fill=self.colors['surface'], outline=self.colors['blue'])
        self.animation_canvas.create_polygon(50, 30, 42, 40, 58, 40, fill=self.colors['blue'], outline=self.colors['blue'])
        
        self.animation_angle = (self.animation_angle + 10) % 360
        
        if self.animation_running:
            self.root.after(50, self._draw_animation_scanning)
    
    def _start_animation(self):
        """Запуск анимации"""
        self.animation_running = True
        self._draw_animation_scanning()
    
    def _stop_animation(self):
        """Остановка анимации"""
        self.animation_running = False
        self._draw_animation_idle()
    
    def _play_sound(self, sound_type="threat"):
        """Воспроизведение звука (исправленная версия)"""
        try:
            sound_manager = get_sound_manager(enable_sound=True)
            sound_manager.play_async(sound_type)
        except Exception:
            # Молча игнорируем ошибки звука
            pass
    
    def _get_usb_devices(self):
        """Получение списка USB устройств"""
        if not WMI_AVAILABLE:
            return set()
        
        try:
            c = wmi.WMI()
            usb_devices = set()
            for drive in c.Win32_LogicalDisk():
                if drive.DriveType == 2:  # Removable drive
                    usb_devices.add(drive.DeviceID)
            return usb_devices
        except:
            return set()
    
    def _check_usb_devices(self):
        """Проверка на новые USB устройства"""
        if not self.usb_monitoring:
            return
        
        current_devices = self._get_usb_devices()
        new_devices = current_devices - self.last_usb_devices
        
        if new_devices:
            for device in new_devices:
                self._log(f"USB устройство подключено: {device}")
                self._play_sound("usb_detected")
                
                # Автоматическая проверка USB
                self._scan_usb_device(device)
        
        self.last_usb_devices = current_devices
        
        # Повторная проверка через 2 секунды
        if self.usb_monitoring:
            self.root.after(2000, self._check_usb_devices)
    
    def _scan_usb_device(self, device_id):
        """Сканирование USB устройства"""
        try:
            device_path = f"{device_id}\\"
            if os.path.exists(device_path):
                self._log(f"Автоматическая проверка USB: {device_path}")
                
                # Быстрая проверка USB
                scan_data = self.scanner.scan_directory(device_path, 2, 200)
                
                if scan_data['results']:
                    self._log(f"Найдены угрозы на USB: {len(scan_data['results'])}")
                    for r in scan_data['results']:
                        self._log(f"   └─ {r['filepath']} — {r['threat_name']}")
                        self._add_threat_file(r['filepath'], r['threat_name'])
                        self._play_sound("threat")
                else:
                    self._log("USB устройство чистое")
        except Exception as e:
            self._log(f"Ошибка проверки USB: {e}")
    
    def _toggle_usb_monitoring(self):
        """Включение/выключение мониторинга USB"""
        if not WMI_AVAILABLE:
            messagebox.showerror("Ошибка", "WMI не доступен. Установите pywin32 для мониторинга USB.")
            return
        
        self.usb_monitoring = not self.usb_monitoring
        
        if self.usb_monitoring:
            self.last_usb_devices = self._get_usb_devices()
            self._check_usb_devices()
            self.usb_button.config(text="ВЫКЛ", bg=self.colors['green'])
            self._log("Мониторинг USB включен")
        else:
            self.usb_button.config(text="ВКЛ", bg=self.colors['red'])
            self._log("Мониторинг USB выключен")
    
    def _quick_scan(self):
        """Быстрая проверка"""
        if self.is_scanning:
            messagebox.showwarning("Сканирование", "Уже выполняется!")
            return
        
        self.is_scanning = True
        self.files_scanned = 0
        self.threats_found = 0
        self._clear_threats_list()
        self._start_animation()
        
        self._log("=" * 50)
        self._log("БЫСТРАЯ ПРОВЕРКА")
        
        temp_path = os.environ.get('TEMP', '') or os.environ.get('TMP', '')
        download_path = Path.home() / "Downloads"
        download_ru = Path.home() / "Загрузки"
        desktop_path = Path.home() / "Desktop"
        documents_path = Path.home() / "Documents"
        areas = []

        if temp_path and os.path.exists(temp_path):
            areas.append((temp_path, 2, 100))
        if download_path.exists():
            areas.append((str(download_path), 2, 100))
        elif download_ru.exists():
            areas.append((str(download_ru), 2, 100))
        if desktop_path.exists():
            areas.append((str(desktop_path), 2, 100))
        if documents_path.exists():
            areas.append((str(documents_path), 2, 100))

        if not areas:
            self._log("⚠️ Нет доступных стандартных областей для быстрого сканирования")
            self.root.after(100, lambda: messagebox.showinfo("Быстрая проверка", "Не найдены стандартные папки для быстрого сканирования."))
            self.is_scanning = False
            self._stop_animation()
            return

        threading.Thread(target=self._scan_worker,
                        args=("Быстрая", areas), daemon=True).start()
    
    def _full_scan(self):
        """Полная проверка"""
        if self.is_scanning:
            messagebox.showwarning("Сканирование", "Уже выполняется!")
            return
        
        self.is_scanning = True
        self.files_scanned = 0
        self.threats_found = 0
        self._clear_threats_list()
        self._start_animation()
        
        self._log("=" * 50)
        self._log("🔍 ПОЛНАЯ ПРОВЕРКА")
        
        areas = []
        temp_path = os.environ.get('TEMP') or os.environ.get('TMP')
        if temp_path and os.path.exists(temp_path):
            areas.append((temp_path, 2, 300))
        if os.path.exists("C:\\Windows\\System32"):
            areas.append(("C:\\Windows\\System32", 2, 300))
        if os.path.exists("C:\\Program Files"):
            areas.append(("C:\\Program Files", 3, 300))
        areas.append((str(Path.home()), 3, 400))
        
        threading.Thread(target=self._scan_worker,
                        args=("Полная", areas), daemon=True).start()
    
    def _scan_file(self):
        """Проверка файла"""
        filepath = filedialog.askopenfilename(title="Выберите файл")
        if not filepath:
            return
        self._scan_file_path(filepath)

    def _scan_file_path(self, filepath, ask_quarantine=True):
        """Проверка файла по указанному пути"""
        self._clear_threats_list()
        self._log(f"🔍 Проверка: {filepath}")

        result = self.scanner.scan_file(filepath)
        ms_signed = self._is_signed_by_microsoft(filepath)
        if ms_signed is True:
            result['details'].append('Подпись Microsoft: подтверждена')
        elif ms_signed is False:
            result['details'].append('Подпись Microsoft: отсутствует или неподписан')
        else:
            result['details'].append('Проверка подписи недоступна')

        if self._is_system_file(filepath):
            if ms_signed is False:
                result['details'].append('Внимание: системный файл без подписи Microsoft')
            else:
                result['details'].append('Системный файл проверен')

        if result['is_threat']:
            self._log(f"⚠️ УГРОЗА: {result['threat_name']} в {filepath}")
            self._add_threat_file(filepath, result['threat_name'])
            self._play_sound("threat")
            for d in result['details']:
                self._log(f"   └─ {d}")

            if ask_quarantine and messagebox.askyesno("Угроза!", "Поместить в карантин?"):
                if self.quarantine.add(filepath):
                    self._log("📦 В карантин")
                else:
                    self._log("❌ Не удалось поместить в карантин")
        else:
            self._log("✅ Чистый")
            for d in result['details']:
                self._log(f"   └─ {d}")
            messagebox.showinfo("Проверка", "Угроз не найдено")
    
    def _scan_worker(self, name, areas):
        """Рабочий процесс сканирования"""
        detected_threat_paths = []
        seen_paths = set()

        try:
            total = len(areas)
            if total == 0:
                self._log("⚠️ Нет областей для сканирования")
                self.root.after(100, lambda: messagebox.showinfo(name, "Нет доступных областей для сканирования."))
                self.is_scanning = False
                self._stop_animation()
                return

            for i, (path, depth, max_f) in enumerate(areas):
                if not self.is_scanning:
                    break

                if not os.path.exists(path):
                    self._log(f"⚠️ Путь не найден: {path}")
                    continue

                self._log(f"📂 {os.path.basename(path) or path}")

                progress = (i / total) * 100
                def scan_callback(filepath, is_threat):
                    self._update_progress(progress, f"Сканируется: {os.path.basename(filepath)}")
                scan_data = self.scanner.scan_directory(path, depth, max_f, callback=scan_callback)
                self.files_scanned += scan_data['files_scanned']
                self.threats_found += len(scan_data['results'])

                for r in scan_data['results']:
                    self._log(f"⚠️ Угроза: {r['filepath']} — {r['threat_name']}")
                    self._add_threat_file(r['filepath'], r['threat_name'])
                    self._play_sound("threat")
                    if r['filepath'] not in seen_paths:
                        seen_paths.add(r['filepath'])
                        detected_threat_paths.append(r['filepath'])

                progress = ((i + 1) / total) * 100
                self._update_progress(progress, f"Сканирование...")

            self._update_progress(100, "Завершено")
            self._stop_animation()
            self._play_sound("scan_complete")
            self._log("=" * 50)
            self._log(f"✅ {name} проверка завершена")
            self._log(f"📊 Файлов: {self.files_scanned}")
            self._log(f"⚠️ Угроз: {self.threats_found}")

            def show_completion():
                if detected_threat_paths:
                    if messagebox.askyesno(
                        "Карантин",
                        f"Обнаружено угроз: {len(detected_threat_paths)}.\nПоместить все найденные файлы в карантин?"
                    ):
                        success_count = 0
                        for threat_path in detected_threat_paths:
                            if self.quarantine.add(threat_path):
                                success_count += 1
                                self._log(f"📦 В карантин: {threat_path}")
                        messagebox.showinfo(
                            "Карантин",
                            f"В карантин помещено {success_count} из {len(detected_threat_paths)} файлов."
                        )
                    else:
                        messagebox.showinfo(
                            name,
                            f"Файлов: {self.files_scanned}\nУгроз: {self.threats_found}\nФайлы не помещены в карантин."
                        )
                else:
                    messagebox.showinfo(
                        name, f"Файлов: {self.files_scanned}\nУгроз: {self.threats_found}"
                    )

            self.root.after(500, show_completion)

        except Exception as e:
            self._log(f"❌ Ошибка: {e}")

        finally:
            self.is_scanning = False
            self._stop_animation()
    
    def _clear_cache(self):
        """Очистка кэша приложений"""
        try:
            self._log("🧹 Начинаем очистку кэша...")
            
            cleaned_size = 0
            
            # Очистка только нашего кэша VirusTotal
            try:
                cache_file = Path(__file__).parent / "cache" / "vt_cache.json"
                if cache_file.exists():
                    size = cache_file.stat().st_size
                    cache_file.unlink()
                    cleaned_size += size
                    self._log("✅ Очищен кэш VirusTotal")
            except Exception as e:
                self._log(f"⚠️ Ошибка очистки VT кэша: {e}")
            
            # Безопасная очистка временных файлов (только наши)
            try:
                temp_dir = Path.home() / "AppData" / "Local" / "Temp"
                if temp_dir.exists():
                    # Очищаем только файлы старше 1 дня и меньше 10MB
                    import time
                    current_time = time.time()
                    
                    for file_path in temp_dir.glob("*"):
                        if file_path.is_file():
                            try:
                                stat = file_path.stat()
                                # Файл старше 1 дня и меньше 10MB
                                if (current_time - stat.st_mtime > 86400 and 
                                    stat.st_size < 10 * 1024 * 1024):
                                    file_path.unlink()
                                    cleaned_size += stat.st_size
                            except:
                                pass
                    
                    self._log("✅ Очищены старые временные файлы")
            except Exception as e:
                self._log(f"⚠️ Ошибка очистки temp: {e}")
            
            # Форматирование размера
            if cleaned_size > 1024**3:  # GB
                size_str = f"{cleaned_size / 1024**3:.1f} GB"
            elif cleaned_size > 1024**2:  # MB
                size_str = f"{cleaned_size / 1024**2:.1f} MB"
            elif cleaned_size > 1024:  # KB
                size_str = f"{cleaned_size / 1024:.1f} KB"
            else:
                size_str = f"{cleaned_size} байт"
            
            self._log(f"🧹 Очистка завершена! Освобождено: {size_str}")
            messagebox.showinfo("Очистка кэша", f"Кэш очищен!\nОсвобождено: {size_str}")
            
        except Exception as e:
            self._log(f"❌ Ошибка очистки кэша: {e}")
            messagebox.showerror("Ошибка", f"Не удалось очистить кэш:\n{e}")
    
    def run(self):
        """Запуск приложения"""
        # Установка DPI awareness для Windows
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        # Центрирование окна с новыми размерами
        self.root.update_idletasks()
        w, h = 1100, 700
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        
        self.root.mainloop()


# Для теста
if __name__ == "__main__":
    print("GUI модуль загружен")
    print(f"Класс AegisApp доступен: {AegisApp}")