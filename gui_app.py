"""Графический интерфейс Aegis Core"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import time
import winsound
import math
import shutil
from datetime import datetime
from pathlib import Path

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

from scanner import FileScanner
from quarantine import QuarantineManager


class AegisApp:
    """Главный класс приложения"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aegis Core - Антивирусная защита")
        self.root.geometry("1100x700")  # Увеличено для лучшего вида
        self.root.configure(bg='#f8fafc')
        self.root.overrideredirect(True)
        
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
        
        # Современная цветовая схема
        self.colors = {
            'bg': '#f8fafc',           # Более светлый фон
            'surface': '#ffffff',      # Чистый белый
            'surface_hover': '#f1f5f9', # Светло-серый для hover
            'header': '#0f172a',       # Темно-синий заголовок
            'header_gradient': '#1e293b', # Градиент для заголовка
            'green': '#10b981',        # Современный зеленый
            'green_hover': '#059669',  # Темнее для hover
            'red': '#ef4444',          # Современный красный
            'red_hover': '#dc2626',    # Темнее для hover
            'orange': '#f97316',       # Современный оранжевый
            'orange_hover': '#ea580c', # Темнее для hover
            'blue': '#3b82f6',         # Современный синий
            'blue_hover': '#2563eb',   # Темнее для hover
            'purple': '#8b5cf6',       # Фиолетовый для акцентов
            'text': '#1e293b',         # Темно-синий текст
            'text_secondary': '#64748b', # Серый текст
            'text_muted': '#94a3b8',   # Светло-серый текст
            'border': '#e2e8f0',       # Светлая граница
            'border_hover': '#cbd5e1', # Граница при hover
            'console_bg': '#0f172a',   # Темный фон консоли
            'console_fg': '#38bdf8',   # Голубой текст консоли
            'shadow': '#000000',       # Тень
            'success': '#22c55e',      # Успех
            'warning': '#f59e0b',      # Предупреждение
            'error': '#ef4444'         # Ошибка
        }
        
        # Современные шрифты
        self.fonts = {
            'header': ('Segoe UI', 18, 'bold'),
            'title': ('Segoe UI', 14, 'bold'),
            'subtitle': ('Segoe UI', 10),
            'body': ('Segoe UI', 10),
            'button': ('Segoe UI', 10, 'bold'),
            'console': ('Consolas', 9),
            'small': ('Segoe UI', 8)
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
        
        # Заголовок с градиентом
        header = tk.Frame(main, bg=self.colors['header'], height=60)  # Увеличена высота
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        header.bind("<Button-1>", self._start_move)
        header.bind("<B1-Motion>", self._move_window)
        
        # Градиентный эффект для заголовка
        header_canvas = tk.Canvas(header, height=60, bg=self.colors['header'], highlightthickness=0)
        header_canvas.pack(fill=tk.X)
        
        # Градиент от header к header_gradient
        for i in range(60):
            color = self._interpolate_color(self.colors['header'], self.colors['header_gradient'], i/60)
            header_canvas.create_line(0, i, 1100, i, fill=color)
        
        # Текст заголовка
        header_canvas.create_text(30, 30, text="🛡️ AEGIS CORE", 
                                font=self.fonts['header'], fill='white', anchor='w')
        header_canvas.create_text(30, 45, text="Антивирусная защита", 
                                font=self.fonts['subtitle'], fill='#94a3b8', anchor='w')
        
        # Кнопка закрытия с hover эффектом
        close_btn = tk.Button(header, text="✕", command=self.root.destroy,
                            font=("Segoe UI", 12, "bold"), bg=self.colors['header'],
                            fg='white', bd=0, activebackground=self.colors['red'],
                            activeforeground='white', cursor='hand2', width=3, height=1)
        close_btn.place(x=1050, y=15)
        
        # Контент
        content = tk.Frame(main, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Левая панель
        left = tk.Frame(content, bg=self.colors['bg'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 7))
        
        # Статус с современным дизайном
        status = tk.Frame(left, bg=self.colors['surface'], relief='flat', bd=1)
        status.pack(fill=tk.X, pady=(0, 15))
        
        # Тень для статуса
        status_shadow = tk.Frame(left, bg=self.colors['shadow'], height=1)
        status_shadow.pack(fill=tk.X, pady=(0, 1))
        
        inner = tk.Frame(status, bg=self.colors['surface'])
        inner.pack(padx=25, pady=20, fill=tk.X)
        
        # Иконка статуса
        status_icon = tk.Label(inner, text="🛡️", font=("Segoe UI", 20), 
                             bg=self.colors['surface'], fg=self.colors['success'])
        status_icon.pack(side=tk.LEFT, padx=(0, 15))
        
        # Текст статуса
        status_text = tk.Frame(inner, bg=self.colors['surface'])
        status_text.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(status_text, text="ЗАЩИТА АКТИВНА", font=self.fonts['title'],
                bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(status_text, text=f"Сигнатур в базе: {self.scanner.sig_db.total_count()}",
                font=self.fonts['small'], bg=self.colors['surface'],
                fg=self.colors['text_muted']).pack(anchor='w')
        
        # Анимация сканирования с улучшенным дизайном
        self.animation_canvas = tk.Canvas(left, width=120, height=120, bg=self.colors['bg'], highlightthickness=0)
        self.animation_canvas.pack(pady=15)
        self._draw_animation_idle()
        
        # Кнопки с современным дизайном
        scans_frame = tk.Frame(left, bg=self.colors['bg'])
        scans_frame.pack(fill=tk.X)
        
        tk.Label(scans_frame, text="Сканирование", font=self.fonts['title'],
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor='w', pady=(0, 15))
        
        # Карточки сканирования с улучшенным дизайном
        scans = [
            ("⚡ Быстрая проверка", "Критические области системы", self._quick_scan, self.colors['green'], self.colors['green_hover']),
            ("🔍 Полная проверка", "Глубокий анализ всех файлов", self._full_scan, self.colors['blue'], self.colors['blue_hover']),
            ("📁 Проверить файл", "Выборочная проверка файла", self._scan_file, self.colors['orange'], self.colors['orange_hover'])
        ]
        
        for title, desc, cmd, color, hover_color in scans:
            card = tk.Frame(left, bg=self.colors['surface'], relief='flat', bd=1)
            card.pack(fill=tk.X, pady=3)
            
            # Тень для карточки
            card_shadow = tk.Frame(left, bg=self.colors['shadow'], height=1)
            card_shadow.pack(fill=tk.X, pady=(0, 1))
            
            cinner = tk.Frame(card, bg=self.colors['surface'])
            cinner.pack(fill=tk.X, padx=25, pady=15)
            
            # Иконка и текст
            icon_label = tk.Label(cinner, text=title.split()[0], font=("Segoe UI", 16), 
                                bg=self.colors['surface'], fg=color)
            icon_label.pack(side=tk.LEFT, padx=(0, 15))
            
            text_frame = tk.Frame(cinner, bg=self.colors['surface'])
            text_frame.pack(side=tk.LEFT, fill=tk.Y)
            
            tk.Label(text_frame, text=title[2:], font=self.fonts['body'],
                    bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w')
            
            tk.Label(text_frame, text=desc, font=self.fonts['small'],
                    bg=self.colors['surface'], fg=self.colors['text_muted']).pack(anchor='w')
            
            # Кнопка с hover эффектом
            btn = tk.Button(cinner, text="Запустить", command=cmd, font=self.fonts['button'],
                          bg=color, fg='white', bd=0, padx=20, pady=8,
                          cursor='hand2', relief='flat')
            btn.pack(side=tk.RIGHT)
            
            # Hover эффекты
            def on_enter(e, b=btn, c=color, h=hover_color):
                b.config(bg=h)
            def on_leave(e, b=btn, c=color):
                b.config(bg=c)
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        
        # USB мониторинг с современным дизайном
        usb_card = tk.Frame(left, bg=self.colors['surface'], relief='flat', bd=1)
        usb_card.pack(fill=tk.X, pady=3)
        
        # Тень для USB карточки
        usb_shadow = tk.Frame(left, bg=self.colors['shadow'], height=1)
        usb_shadow.pack(fill=tk.X, pady=(0, 1))
        
        usb_inner = tk.Frame(usb_card, bg=self.colors['surface'])
        usb_inner.pack(fill=tk.X, padx=25, pady=15)
        
        # USB иконка
        usb_icon = tk.Label(usb_inner, text="🔌", font=("Segoe UI", 16), 
                          bg=self.colors['surface'], fg=self.colors['purple'])
        usb_icon.pack(side=tk.LEFT, padx=(0, 15))
        
        # USB текст
        usb_text = tk.Frame(usb_inner, bg=self.colors['surface'])
        usb_text.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(usb_text, text="USB Защита", font=self.fonts['body'],
                bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(usb_text, text="Автопроверка подключенных устройств", font=self.fonts['small'],
                bg=self.colors['surface'], fg=self.colors['text_muted']).pack(anchor='w')
        
        # USB кнопка с hover
        self.usb_button = tk.Button(usb_inner, text="ВКЛ", command=self._toggle_usb_monitoring,
                                  font=self.fonts['button'], bg=self.colors['red'],
                                  fg='white', bd=0, padx=20, pady=8, cursor='hand2', relief='flat')
        self.usb_button.pack(side=tk.RIGHT)
        
        # Hover для USB кнопки
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
        
        # Кнопка очистки кэша
        cache_card = tk.Frame(left, bg=self.colors['surface'], relief='flat', bd=1)
        cache_card.pack(fill=tk.X, pady=3)
        
        cache_shadow = tk.Frame(left, bg=self.colors['shadow'], height=1)
        cache_shadow.pack(fill=tk.X, pady=(0, 1))
        
        cache_inner = tk.Frame(cache_card, bg=self.colors['surface'])
        cache_inner.pack(fill=tk.X, padx=25, pady=15)
        
        # Иконка кэша
        cache_icon = tk.Label(cache_inner, text="🗂️", font=("Segoe UI", 16),
                            bg=self.colors['surface'], fg=self.colors['blue'])
        cache_icon.pack(side=tk.LEFT, padx=(0, 15))
        
        cache_text = tk.Frame(cache_inner, bg=self.colors['surface'])
        cache_text.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(cache_text, text="Очистка кэша", font=self.fonts['body'],
                bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(cache_text, text="Очистить кэш приложений и временные файлы",
                font=self.fonts['small'], bg=self.colors['surface'],
                fg=self.colors['text_muted']).pack(anchor='w')
        
        # Кнопка очистки кэша
        cache_btn = tk.Button(cache_inner, text="Очистить", command=self._clear_cache,
                            font=self.fonts['button'], bg=self.colors['blue'], fg='white',
                            bd=0, padx=20, pady=8, cursor='hand2', relief='flat')
        cache_btn.pack(side=tk.RIGHT)
        
        # Hover эффекты для кнопки кэша
        def cache_enter(e):
            cache_btn.config(bg=self.colors['blue_hover'])
        def cache_leave(e):
            cache_btn.config(bg=self.colors['blue'])
        
        cache_btn.bind("<Enter>", cache_enter)
        cache_btn.bind("<Leave>", cache_leave)
        
        # Правая панель - лог + список угроз с современным дизайном
        right = tk.Frame(content, bg=self.colors['surface'], width=400)  # Увеличена ширина
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right.pack_propagate(False)
        
        # Список угроз с улучшенным дизайном
        threats_frame = tk.Frame(right, bg=self.colors['surface'])
        threats_frame.pack(fill=tk.X, padx=20, pady=(15, 0))
        
        # Заголовок угроз
        threats_header = tk.Frame(threats_frame, bg=self.colors['surface'])
        threats_header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(threats_header, text="🚨", font=("Segoe UI", 16), 
                bg=self.colors['surface'], fg=self.colors['error']).pack(side=tk.LEFT)
        
        tk.Label(threats_header, text="Обнаруженные угрозы", font=self.fonts['title'],
                bg=self.colors['surface'], fg=self.colors['text']).pack(side=tk.LEFT, padx=10)
        
        tk.Button(threats_header, text="🗑️", command=self._clear_threats_list,
                 font=self.fonts['small'], bg=self.colors['surface'],
                 fg=self.colors['text_muted'], bd=0, cursor='hand2').pack(side=tk.RIGHT)
        
        # Список угроз
        list_frame = tk.Frame(threats_frame, bg=self.colors['surface'], relief='sunken', bd=1)
        list_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 15))
        
        self.threats_listbox = tk.Listbox(
            list_frame,
            height=8,  # Увеличена высота
            bg=self.colors['console_bg'],
            fg=self.colors['console_fg'],
            selectbackground=self.colors['blue'],
            selectforeground='white',
            bd=0,
            relief='flat',
            font=self.fonts['console']
        )
        self.threats_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        threats_scroll = tk.Scrollbar(list_frame, command=self.threats_listbox.yview,
                                    bg=self.colors['border'], troughcolor=self.colors['surface'])
        threats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.threats_listbox.config(yscrollcommand=threats_scroll.set)
        
        # Лог с улучшенным дизайном
        log_header = tk.Frame(right, bg=self.colors['surface'])
        log_header.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        log_title_frame = tk.Frame(log_header, bg=self.colors['surface'])
        log_title_frame.pack(side=tk.LEFT)
        
        tk.Label(log_title_frame, text="📋", font=("Segoe UI", 16), 
                bg=self.colors['surface'], fg=self.colors['blue']).pack(side=tk.LEFT)
        
        tk.Label(log_title_frame, text="Журнал сканирования", font=self.fonts['title'],
                bg=self.colors['surface'], fg=self.colors['text']).pack(side=tk.LEFT, padx=10)
        
        tk.Button(log_header, text="🗑️", command=self._clear_log,
                 font=self.fonts['small'], bg=self.colors['surface'],
                 fg=self.colors['text_muted'], bd=0, cursor='hand2').pack(side=tk.RIGHT)
        
        # Виджет лога
        self.log_widget = scrolledtext.ScrolledText(
            right, wrap=tk.WORD, font=self.fonts['console'],
            bg=self.colors['console_bg'], fg=self.colors['console_fg'],
            insertbackground=self.colors['console_fg'], 
            selectbackground=self.colors['blue'], selectforeground='white',
            bd=0, relief='flat', padx=10, pady=5
        )
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        # Прогресс с современным дизайном
        self.progress_frame = tk.Frame(right, bg=self.colors['surface'])
        self.progress_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Прогресс-бар с кастомным стилем
        style = ttk.Style()
        style.configure("Modern.Horizontal.TProgressbar",
                       background=self.colors['success'],
                       troughcolor=self.colors['surface'],
                       borderwidth=0,
                       lightcolor=self.colors['success'],
                       darkcolor=self.colors['success'])
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate',
                                            style="Modern.Horizontal.TProgressbar",
                                            length=400)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.progress_label = tk.Label(self.progress_frame, text="Готов к работе",
                                       font=self.fonts['small'], bg=self.colors['surface'],
                                       fg=self.colors['text_muted'])
        self.progress_label.pack(anchor='w')
        
        # Футер с градиентом
        footer = tk.Frame(main, bg=self.colors['header'], height=40)
        footer.pack(fill=tk.X)
        footer.pack_propagate(False)
        
        # Градиент для футера
        footer_canvas = tk.Canvas(footer, height=40, bg=self.colors['header'], highlightthickness=0)
        footer_canvas.pack(fill=tk.X)
        
        for i in range(40):
            color = self._interpolate_color(self.colors['header'], self.colors['header_gradient'], i/40)
            footer_canvas.create_line(0, i, 1100, i, fill=color)
        
        # Информация в футере
        footer_canvas.create_text(30, 20, text=f"v{self.version}", 
                                font=self.fonts['small'], fill='#94a3b8', anchor='w')
        footer_canvas.create_text(550, 20, text="© 2026 Aegis Core", 
                                font=self.fonts['small'], fill='#94a3b8', anchor='center')
        footer_canvas.create_text(1070, 20, text=self.author_email, 
                                font=self.fonts['small'], fill='#94a3b8', anchor='e')
    
    def _log(self, msg):
        """Логирование"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_widget.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_widget.see(tk.END)
        except:
            pass
    
    def _add_threat_file(self, filepath, threat_name):
        """Добавить зараженный файл в список"""
        try:
            self.threats_listbox.insert(tk.END, f"{filepath} — {threat_name}")
            self.threats_listbox.see(tk.END)
        except:
            pass
    
    def _clear_threats_list(self):
        """Очистка списка обнаруженных угроз"""
        try:
            self.threats_listbox.delete(0, tk.END)
        except:
            pass
    
    def _clear_log(self):
        """Очистка лога"""
        try:
            self.log_widget.delete(1.0, tk.END)
        except:
            pass
    
    def _update_progress(self, val, text=""):
        """Обновление прогресса"""
        try:
            self.target_progress = max(0, min(100, val))
            if text:
                self.progress_label.config(text=text)
            if self.progress_animation_id:
                self.root.after_cancel(self.progress_animation_id)
                self.progress_animation_id = None
            self._animate_progress()
        except:
            pass
    
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
        self._log("🛡️ Aegis Core запущен")
        self._log(f"Сигнатур: {self.scanner.sig_db.total_count()}")
        self._log("✅ Готов к работе")
        self._log("=" * 50)
    
    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y
    
    def _move_window(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")
    
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
        """Воспроизведение системного звука Windows"""
        try:
            if sound_type == "threat":
                winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
            elif sound_type == "scan_complete":
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
            elif sound_type == "usb_detected":
                winsound.PlaySound("SystemQuestion", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:
            try:
                if sound_type == "threat":
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                elif sound_type == "scan_complete":
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                elif sound_type == "usb_detected":
                    winsound.MessageBeep(winsound.MB_ICONQUESTION)
            except Exception:
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
                self._log(f"🔌 USB устройство подключено: {device}")
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
                self._log(f"🔍 Автоматическая проверка USB: {device_path}")
                
                # Быстрая проверка USB
                scan_data = self.scanner.scan_directory(device_path, 2, 200)
                
                if scan_data['results']:
                    self._log(f"⚠️ Найдены угрозы на USB: {len(scan_data['results'])}")
                    for r in scan_data['results']:
                        self._log(f"   └─ {r['filepath']} — {r['threat_name']}")
                        self._add_threat_file(r['filepath'], r['threat_name'])
                        self._play_sound("threat")
                else:
                    self._log("✅ USB устройство чистое")
        except Exception as e:
            self._log(f"❌ Ошибка проверки USB: {e}")
    
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
            self._log("🔌 Мониторинг USB включен")
        else:
            self.usb_button.config(text="ВКЛ", bg=self.colors['red'])
            self._log("🔌 Мониторинг USB выключен")
    
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
        self._log("⚡ БЫСТРАЯ ПРОВЕРКА")
        
        areas = [
            (os.environ.get('TEMP', ''), 2, 100),
            (str(Path.home() / "Downloads"), 2, 100)
        ]
        
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
        
        self._clear_threats_list()
        self._log(f"🔍 Проверка: {filepath}")
        
        result = self.scanner.scan_file(filepath)
        
        if result['is_threat']:
            self._log(f"⚠️ УГРОЗА: {result['threat_name']} в {filepath}")
            self._add_threat_file(filepath, result['threat_name'])
            self._play_sound("threat")
            for d in result['details']:
                self._log(f"   └─ {d}")
            
            if messagebox.askyesno("Угроза!", "Поместить в карантин?"):
                self.quarantine.add(filepath)
                self._log("📦 В карантин")
        else:
            self._log("✅ Чистый")
            messagebox.showinfo("Проверка", "Угроз не найдено")
    
    def _scan_worker(self, name, areas):
        """Рабочий процесс сканирования"""
        try:
            total = len(areas)
            for i, (path, depth, max_f) in enumerate(areas):
                if not self.is_scanning:
                    break
                
                if not os.path.exists(path):
                    continue
                
                self._log(f"📂 {os.path.basename(path)}")
                
                scan_data = self.scanner.scan_directory(path, depth, max_f)
                self.files_scanned += scan_data['files_scanned']
                self.threats_found += len(scan_data['results'])
                
                for r in scan_data['results']:
                    self._log(f"⚠️ Угроза: {r['filepath']} — {r['threat_name']}")
                    self._add_threat_file(r['filepath'], r['threat_name'])
                    self._play_sound("threat")
                
                progress = ((i + 1) / total) * 100
                self._update_progress(progress, f"Сканирование...")
            
            self._update_progress(100, "Завершено")
            self._stop_animation()
            self._play_sound("scan_complete")
            self._log("=" * 50)
            self._log(f"✅ {name} проверка завершена")
            self._log(f"📊 Файлов: {self.files_scanned}")
            self._log(f"⚠️ Угроз: {self.threats_found}")
            
            self.root.after(500, lambda: messagebox.showinfo(
                name, f"Файлов: {self.files_scanned}\nУгроз: {self.threats_found}"
            ))
            
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