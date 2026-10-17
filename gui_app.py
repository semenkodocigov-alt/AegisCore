"""
Aegis Core 2.0 - Современный графический интерфейс антивирусной защиты
"""
import sys
import os
import time
import json
import shutil
import threading
import subprocess
from datetime import datetime
from pathlib import Path

# Обеспечиваем корректный вывод UTF-8 в консоли Windows
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import wmi  # pyright: ignore[reportMissingImports]
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

from scanner import FileScanner
from quarantine import QuarantineManager
from sound_manager import get_sound_manager
from file_cleaner import FileCleaner
from config import get_config
from hash_utils import calculate_all


class ModernButton(tk.Canvas):
    """Кастомная кнопка с плавной анимацией наведения, иконкой и скругленными углами"""
    def __init__(self, parent, text, command=None, icon="", bg_color="#1e293b",
                 hover_color="#334155", text_color="#f8fafc", font=("Segoe UI", 10, "bold"),
                 height=40, width=None, corner_radius=8, cursor="hand2", **kwargs):
        super().__init__(parent, height=height, bg=parent.cget("bg"), highlightthickness=0, **kwargs)
        self.text = text
        self.icon = icon
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.current_bg = bg_color
        self.text_color = text_color
        self.font = font
        self.corner_radius = corner_radius
        self.height = height
        self.width_override = width
        self.is_hovered = False

        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.config(cursor=cursor)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return

        r = min(self.corner_radius, h // 2, w // 2)
        # Рисуем скругленный прямоугольник
        self.create_arc((0, 0, 2 * r, 2 * r), start=90, extent=90, fill=self.current_bg, outline=self.current_bg)
        self.create_arc((w - 2 * r, 0, w, 2 * r), start=0, extent=90, fill=self.current_bg, outline=self.current_bg)
        self.create_arc((0, h - 2 * r, 2 * r, h), start=180, extent=90, fill=self.current_bg, outline=self.current_bg)
        self.create_arc((w - 2 * r, h - 2 * r, w, h), start=270, extent=90, fill=self.current_bg, outline=self.current_bg)
        self.create_rectangle((r, 0, w - r, h), fill=self.current_bg, outline=self.current_bg)
        self.create_rectangle((0, r, w, h - r), fill=self.current_bg, outline=self.current_bg)

        # Текст и иконка
        full_text = f"{self.icon}  {self.text}" if self.icon else self.text
        self.create_text(w // 2, h // 2, text=full_text, fill=self.text_color, font=self.font)

    def _on_enter(self, event):
        self.is_hovered = True
        self.current_bg = self.hover_color
        self._draw()

    def _on_leave(self, event):
        self.is_hovered = False
        self.current_bg = self.bg_color
        self._draw()

    def _on_click(self, event):
        if callable(self.command):
            self.command()

    def set_text(self, text, icon=None):
        self.text = text
        if icon is not None:
            self.icon = icon
        self._draw()


class AegisApp:
    """Главный класс приложения Aegis Core"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aegis Core 2.0 — Next-Gen Antivirus Protection")
        self.root.geometry("1180x740")
        self.root.minsize(980, 620)

        # Включение темного оформления строки заголовка в Windows 10/11
        if sys.platform == 'win32':
            try:
                import ctypes
                self.root.update_idletasks()
                # Включение High-DPI awareness
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    pass
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                # DWMWA_USE_IMMERSIVE_DARK_MODE (20 в Win11 / 19 в Win10)
                dark_mode = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
            except Exception:
                pass

        # Центрирование окна
        self._center_window(1180, 740)

        # Палитра цветов (Cyber Modern Dark)
        self.colors = {
            'bg_root': '#090d16',
            'bg_sidebar': '#0f172a',
            'bg_sidebar_active': '#1e293b',
            'bg_card': '#162032',
            'bg_card_hover': '#1e2d44',
            'bg_header': '#0c1424',
            'border': '#1e2d42',
            'border_light': '#334155',
            'text_primary': '#f8fafc',
            'text_secondary': '#94a3b8',
            'text_muted': '#64748b',
            'blue': '#3b82f6',
            'blue_hover': '#2563eb',
            'cyan': '#06b6d4',
            'cyan_hover': '#0891b2',
            'green': '#10b981',
            'green_hover': '#059669',
            'red': '#ef4444',
            'red_hover': '#dc2626',
            'orange': '#f59e0b',
            'orange_hover': '#d97706',
            'purple': '#8b5cf6',
            'console_bg': '#070b14',
            'console_fg': '#38bdf8'
        }

        # Шрифты
        self.fonts = {
            'brand': ('Segoe UI', 15, 'bold'),
            'h1': ('Segoe UI', 16, 'bold'),
            'h2': ('Segoe UI', 12, 'bold'),
            'h3': ('Segoe UI', 11, 'bold'),
            'body': ('Segoe UI', 10),
            'body_bold': ('Segoe UI', 10, 'bold'),
            'small': ('Segoe UI', 8),
            'small_bold': ('Segoe UI', 8, 'bold'),
            'stats_num': ('Segoe UI', 20, 'bold'),
            'console': ('Consolas', 9)
        }

        self.root.configure(bg=self.colors['bg_root'])

        # Модули ядра
        self.config = get_config()
        self.scanner = FileScanner()
        self.quarantine = QuarantineManager()
        self.cleaner = FileCleaner()
        self.sound = get_sound_manager()

        # Состояние приложения
        self.is_scanning = False
        self.stop_scan_flag = False
        self.files_scanned = 0
        self.threats_found = 0
        self.session_threats = []  # Список обнаруженных угроз в текущей сессии
        self.usb_monitoring = self.config.get("enable_usb_monitoring", False)
        self.last_usb_devices = set()

        # Анимация щита / радара
        self.radar_angle = 0
        self.radar_running = True

        # Стили ttk
        self._init_ttk_styles()

        # Конструктор интерфейса
        self._build_ui()

        # Стартовое приветствие в консоль
        self._welcome_message()

        # Запуск анимации статуса
        self._animate_radar()

        # Запуск фонового USB монитора если включен
        if self.usb_monitoring:
            self._start_usb_monitoring()

    def _center_window(self, width, height):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _init_ttk_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Стили прогресс-бара
        style.configure(
            "Cyber.Horizontal.TProgressbar",
            troughcolor=self.colors['bg_sidebar'],
            background=self.colors['cyan'],
            bordercolor=self.colors['border'],
            lightcolor=self.colors['cyan'],
            darkcolor=self.colors['cyan'],
            thickness=10
        )

        # Стили таблицы (Treeview)
        style.configure(
            "Cyber.Treeview",
            background=self.colors['bg_card'],
            foreground=self.colors['text_primary'],
            fieldbackground=self.colors['bg_card'],
            rowheight=30,
            font=self.fonts['body'],
            borderwidth=0
        )
        style.map(
            "Cyber.Treeview",
            background=[('selected', self.colors['blue'])],
            foreground=[('selected', '#ffffff')]
        )
        style.configure(
            "Cyber.Treeview.Heading",
            background=self.colors['bg_sidebar'],
            foreground=self.colors['text_secondary'],
            font=self.fonts['body_bold'],
            borderwidth=1,
            relief='flat'
        )

    def _build_ui(self):
        """Создание главного макета приложения"""
        # Главный контейнер
        main_box = tk.Frame(self.root, bg=self.colors['bg_root'])
        main_box.pack(fill=tk.BOTH, expand=True)

        # --- ВЕРХНЯЯ ШАПКА (HEADER) ---
        self.header = tk.Frame(main_box, bg=self.colors['bg_header'], height=56)
        self.header.pack(fill=tk.X, side=tk.TOP)
        self.header.pack_propagate(False)

        # Логотип и Бренд
        brand_frame = tk.Frame(self.header, bg=self.colors['bg_header'])
        brand_frame.pack(side=tk.LEFT, padx=18, pady=10)

        shield_icon = tk.Label(brand_frame, text="🛡️", font=("Segoe UI", 16),
                               bg=self.colors['bg_header'], fg=self.colors['cyan'])
        shield_icon.pack(side=tk.LEFT, padx=(0, 8))

        brand_title = tk.Label(brand_frame, text="AEGIS CORE", font=self.fonts['brand'],
                               bg=self.colors['bg_header'], fg=self.colors['text_primary'])
        brand_title.pack(side=tk.LEFT)

        version_badge = tk.Label(brand_frame, text=" v2.0 PRO ", font=self.fonts['small_bold'],
                                 bg=self.colors['blue'], fg='#ffffff', padx=4, pady=1)
        version_badge.pack(side=tk.LEFT, padx=10)

        # Индикатор общего статуса системы
        self.header_status_frame = tk.Frame(self.header, bg=self.colors['bg_header'])
        self.header_status_frame.pack(side=tk.LEFT, padx=25)

        self.status_dot = tk.Label(self.header_status_frame, text="●", font=("Segoe UI", 12),
                                   bg=self.colors['bg_header'], fg=self.colors['green'])
        self.status_dot.pack(side=tk.LEFT, padx=(0, 6))

        self.status_text = tk.Label(self.header_status_frame, text="СИСТЕМА ЗАЩИЩЕНА",
                                    font=self.fonts['body_bold'], bg=self.colors['bg_header'],
                                    fg=self.colors['green'])
        self.status_text.pack(side=tk.LEFT)

        # Правая часть шапки: быстрая статистика баз
        db_stat_frame = tk.Frame(self.header, bg=self.colors['bg_header'])
        db_stat_frame.pack(side=tk.RIGHT, padx=20)

        sig_count = self.scanner.sig_db.total_count() if hasattr(self.scanner.sig_db, 'total_count') else len(getattr(self.scanner.sig_db, 'md5_hashes', {}))
        self.sig_label = tk.Label(
            db_stat_frame,
            text=f"Сигнатур в базе: {sig_count}  |  VirusTotal: {'ВКЛ' if self.config.get_vt_api_key() else 'НЕ АКТИВЕН'}",
            font=self.fonts['small'],
            bg=self.colors['bg_header'],
            fg=self.colors['text_secondary']
        )
        self.sig_label.pack(side=tk.RIGHT)

        # Линия-разделитель под шапкой
        sep = tk.Frame(main_box, bg=self.colors['border'], height=1)
        sep.pack(fill=tk.X, side=tk.TOP)

        # --- ОСНОВНАЯ ОБЛАСТЬ (БОКОВАЯ ПАНЕЛЬ + КОНТЕНТ) ---
        body = tk.Frame(main_box, bg=self.colors['bg_root'])
        body.pack(fill=tk.BOTH, expand=True)

        # 1. Боковая навигационная панель (Sidebar)
        self._build_sidebar(body)

        # 2. Контейнер страниц контента
        self.content_container = tk.Frame(body, bg=self.colors['bg_root'])
        self.content_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Страницы приложения
        self.pages = {}
        self._create_pages()

        # По умолчанию открываем страницу "Главная"
        self._switch_page("dashboard")

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=self.colors['bg_sidebar'], width=230)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # Заголовок меню
        tk.Label(sidebar, text="НАВИГАЦИЯ", font=self.fonts['small_bold'],
                 bg=self.colors['bg_sidebar'], fg=self.colors['text_muted']).pack(anchor='w', padx=20, pady=(20, 10))

        # Кнопки навигации
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "🛡️", "Главная панель"),
            ("scanner", "🔍", "Сканирование"),
            ("threats", "⚠️", "Угрозы"),
            ("quarantine", "📦", "Карантин"),
            ("tools", "⚙️", "Инструменты"),
            ("logs", "📋", "Журнал событий")
        ]

        for page_id, icon, label in nav_items:
            btn_frame = tk.Frame(sidebar, bg=self.colors['bg_sidebar'], height=44)
            btn_frame.pack(fill=tk.X, padx=10, pady=2)
            btn_frame.pack_propagate(False)

            # Активный индикатор (полоска слева)
            indicator = tk.Frame(btn_frame, bg=self.colors['bg_sidebar'], width=4)
            indicator.pack(side=tk.LEFT, fill=tk.Y)

            btn = tk.Label(btn_frame, text=f"  {icon}   {label}", font=self.fonts['body_bold'],
                           bg=self.colors['bg_sidebar'], fg=self.colors['text_secondary'],
                           anchor='w', cursor="hand2")
            btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

            # События
            def make_callbacks(pid, b, ind, bf):
                def on_click(e):
                    self._switch_page(pid)
                def on_enter(e):
                    if self.current_page != pid:
                        b.config(bg=self.colors['bg_sidebar_active'], fg=self.colors['text_primary'])
                        bf.config(bg=self.colors['bg_sidebar_active'])
                def on_leave(e):
                    if self.current_page != pid:
                        b.config(bg=self.colors['bg_sidebar'], fg=self.colors['text_secondary'])
                        bf.config(bg=self.colors['bg_sidebar'])
                b.bind("<Button-1>", on_click)
                bf.bind("<Button-1>", on_click)
                b.bind("<Enter>", on_enter)
                b.bind("<Leave>", on_leave)
                return b, ind, bf

            w_btn, w_ind, w_frame = make_callbacks(page_id, btn, indicator, btn_frame)
            self.nav_buttons[page_id] = {'label': w_btn, 'ind': w_ind, 'frame': w_frame}

        # Нижний информационный блок сайдбара
        bottom_frame = tk.Frame(sidebar, bg=self.colors['bg_sidebar'])
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=20)

        tk.Label(bottom_frame, text="Aegis Security Engine", font=self.fonts['small_bold'],
                 bg=self.colors['bg_sidebar'], fg=self.colors['text_secondary']).pack(anchor='w')
        tk.Label(bottom_frame, text="AI Heuristic & Hash Guard", font=self.fonts['small'],
                 bg=self.colors['bg_sidebar'], fg=self.colors['text_muted']).pack(anchor='w')

    def _switch_page(self, page_id):
        self.current_page = page_id
        for pid, widgets in self.nav_buttons.items():
            if pid == page_id:
                widgets['label'].config(bg=self.colors['bg_sidebar_active'], fg=self.colors['cyan'])
                widgets['frame'].config(bg=self.colors['bg_sidebar_active'])
                widgets['ind'].config(bg=self.colors['cyan'])
            else:
                widgets['label'].config(bg=self.colors['bg_sidebar'], fg=self.colors['text_secondary'])
                widgets['frame'].config(bg=self.colors['bg_sidebar'])
                widgets['ind'].config(bg=self.colors['bg_sidebar'])

        for pid, page in self.pages.items():
            if pid == page_id:
                page.pack(fill=tk.BOTH, expand=True)
                if pid == "quarantine":
                    self._refresh_quarantine_table()
                elif pid == "threats":
                    self._refresh_threats_table()
            else:
                page.pack_forget()

    def _create_pages(self):
        """Создание всех страниц контента"""
        self.pages['dashboard'] = self._create_dashboard_page(self.content_container)
        self.pages['scanner'] = self._create_scanner_page(self.content_container)
        self.pages['threats'] = self._create_threats_page(self.content_container)
        self.pages['quarantine'] = self._create_quarantine_page(self.content_container)
        self.pages['tools'] = self._create_tools_page(self.content_container)
        self.pages['logs'] = self._create_logs_page(self.content_container)

    # =========================================================================
    # 1. ГЛАВНАЯ СТРАНИЦА (DASHBOARD)
    # =========================================================================
    def _create_dashboard_page(self, parent):
        page = tk.Frame(parent, bg=self.colors['bg_root'], padx=24, pady=20)

        # Верхний баннер статуса
        hero_card = tk.Frame(page, bg=self.colors['bg_card'], highlightthickness=1,
                             highlightbackground=self.colors['border'])
        hero_card.pack(fill=tk.X, pady=(0, 20))

        hero_inner = tk.Frame(hero_card, bg=self.colors['bg_card'], padx=24, pady=20)
        hero_inner.pack(fill=tk.BOTH, expand=True)

        # Радар / Анимированный виджет щита слева
        self.radar_canvas = tk.Canvas(hero_inner, width=80, height=80, bg=self.colors['bg_card'], highlightthickness=0)
        self.radar_canvas.pack(side=tk.LEFT, padx=(0, 20))

        # Текст геро-блока
        hero_text_box = tk.Frame(hero_inner, bg=self.colors['bg_card'])
        hero_text_box.pack(side=tk.LEFT, fill=tk.Y)

        self.dash_status_title = tk.Label(
            hero_text_box,
            text="Ваше устройство под надежной защитой",
            font=self.fonts['h1'],
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary']
        )
        self.dash_status_title.pack(anchor='w')

        self.dash_status_sub = tk.Label(
            hero_text_box,
            text="Все компоненты мониторинга, сигнатурной проверки и эвристики работают в штатном режиме.",
            font=self.fonts['body'],
            bg=self.colors['bg_card'],
            fg=self.colors['text_secondary']
        )
        self.dash_status_sub.pack(anchor='w', pady=(4, 0))

        # Быстрая кнопка запуска сканирования прямо из геро-блока
        quick_act = ModernButton(
            hero_inner,
            text="Быстрая проверка",
            icon="⚡",
            bg_color=self.colors['green'],
            hover_color=self.colors['green_hover'],
            command=self._start_quick_scan,
            width=170,
            height=42
        )
        quick_act.pack(side=tk.RIGHT, pady=10)

        # Карточки метрик (KPI)
        kpi_row = tk.Frame(page, bg=self.colors['bg_root'])
        kpi_row.pack(fill=tk.X, pady=(0, 20))

        self.kpi_scanned = self._create_kpi_card(kpi_row, "Проверено файлов", "0", "📁", self.colors['blue'])
        self.kpi_threats = self._create_kpi_card(kpi_row, "Найдено угроз", "0", "⚠️", self.colors['red'])
        self.kpi_quarantine = self._create_kpi_card(kpi_row, "В карантине", str(self.quarantine.count()), "📦", self.colors['orange'])
        sig_count = self.scanner.sig_db.total_count() if hasattr(self.scanner.sig_db, 'total_count') else len(getattr(self.scanner.sig_db, 'md5_hashes', {}))
        self.kpi_signatures = self._create_kpi_card(kpi_row, "База сигнатур", str(sig_count), "🛡️", self.colors['cyan'])

        # Секция быстрых действий
        tk.Label(page, text="БЫСТРЫЙ ДОСТУП К ПРОВЕРКЕ", font=self.fonts['small_bold'],
                 bg=self.colors['bg_root'], fg=self.colors['text_muted']).pack(anchor='w', pady=(5, 10))

        actions_grid = tk.Frame(page, bg=self.colors['bg_root'])
        actions_grid.pack(fill=tk.BOTH, expand=True)

        self._create_action_card(
            actions_grid, "Быстрое сканирование",
            "Проверка критических системных областей: Temp, Downloads, Рабочий стол",
            "⚡ Запустить", self._start_quick_scan, self.colors['green'], self.colors['green_hover']
        )
        self._create_action_card(
            actions_grid, "Глубокое сканирование",
            "Полный всесторонний анализ всех системных и пользовательских каталогов",
            "🔍 Запустить", self._start_full_scan, self.colors['blue'], self.colors['blue_hover']
        )
        self._create_action_card(
            actions_grid, "Проверить файл",
            "Выбор и сканирование отдельного файла через проводник",
            "📄 Выбрать", self._select_and_scan_file, self.colors['cyan'], self.colors['cyan_hover']
        )
        self._create_action_card(
            actions_grid, "Проверить папку",
            "Выборочная проверка произвольной папки на диске",
            "📁 Выбрать", self._select_and_scan_folder, self.colors['purple'], self.colors['purple']
        )

        return page

    def _create_kpi_card(self, parent, title, value, icon, color):
        card = tk.Frame(parent, bg=self.colors['bg_card'], highlightthickness=1,
                        highlightbackground=self.colors['border'])
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        inner = tk.Frame(card, bg=self.colors['bg_card'], padx=16, pady=14)
        inner.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(inner, bg=self.colors['bg_card'])
        top.pack(fill=tk.X)

        tk.Label(top, text=title, font=self.fonts['small_bold'], bg=self.colors['bg_card'],
                 fg=self.colors['text_secondary']).pack(side=tk.LEFT)
        tk.Label(top, text=icon, font=("Segoe UI", 12), bg=self.colors['bg_card'],
                 fg=color).pack(side=tk.RIGHT)

        val_label = tk.Label(inner, text=value, font=self.fonts['stats_num'],
                             bg=self.colors['bg_card'], fg=self.colors['text_primary'])
        val_label.pack(anchor='w', pady=(6, 0))
        return val_label

    def _create_action_card(self, parent, title, desc, btn_text, command, color, hover_color):
        card = tk.Frame(parent, bg=self.colors['bg_card'], highlightthickness=1,
                        highlightbackground=self.colors['border'])
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        inner = tk.Frame(card, bg=self.colors['bg_card'], padx=16, pady=16)
        inner.pack(fill=tk.BOTH, expand=True)

        tk.Label(inner, text=title, font=self.fonts['h3'], bg=self.colors['bg_card'],
                 fg=self.colors['text_primary']).pack(anchor='w')
        tk.Label(inner, text=desc, font=self.fonts['small'], bg=self.colors['bg_card'],
                 fg=self.colors['text_secondary'], wraplength=180, justify='left').pack(anchor='w', pady=(6, 12))

        btn = ModernButton(
            inner, text=btn_text, command=command, bg_color=color, hover_color=hover_color,
            font=self.fonts['small_bold'], height=36
        )
        btn.pack(fill=tk.X, side=tk.BOTTOM)

    # =========================================================================
    # 2. СТРАНИЦА СКАНИРОВАНИЯ (SCANNER PAGE)
    # =========================================================================
    def _create_scanner_page(self, parent):
        page = tk.Frame(parent, bg=self.colors['bg_root'], padx=24, pady=20)

        # Заголовок секции
        hdr = tk.Frame(page, bg=self.colors['bg_root'])
        hdr.pack(fill=tk.X, pady=(0, 15))

        tk.Label(hdr, text="Центр сканирования", font=self.fonts['h1'],
                 bg=self.colors['bg_root'], fg=self.colors['text_primary']).pack(side=tk.LEFT)

        # Панель прогресса сканирования (Всегда видна на странице)
        self.scan_panel = tk.Frame(page, bg=self.colors['bg_card'], highlightthickness=1,
                                   highlightbackground=self.colors['border'])
        self.scan_panel.pack(fill=tk.X, pady=(0, 15))

        p_inner = tk.Frame(self.scan_panel, bg=self.colors['bg_card'], padx=20, pady=18)
        p_inner.pack(fill=tk.BOTH, expand=True)

        top_info = tk.Frame(p_inner, bg=self.colors['bg_card'])
        top_info.pack(fill=tk.X, pady=(0, 8))

        self.scan_status_label = tk.Label(top_info, text="Сканер готов к работе", font=self.fonts['h2'],
                                          bg=self.colors['bg_card'], fg=self.colors['text_primary'])
        self.scan_status_label.pack(side=tk.LEFT)

        self.scan_percent_label = tk.Label(top_info, text="0%", font=self.fonts['h2'],
                                           bg=self.colors['bg_card'], fg=self.colors['cyan'])
        self.scan_percent_label.pack(side=tk.RIGHT)

        # Прогресс бар
        self.progress_bar = ttk.Progressbar(p_inner, style="Cyber.Horizontal.TProgressbar",
                                            mode='determinate', value=0)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Текущий файл
        self.current_file_label = tk.Label(p_inner, text="Ожидание запуска...", font=self.fonts['small'],
                                           bg=self.colors['bg_card'], fg=self.colors['text_muted'], anchor='w')
        self.current_file_label.pack(fill=tk.X)

        # Кнопки управления сканированием
        ctrl_bar = tk.Frame(p_inner, bg=self.colors['bg_card'])
        ctrl_bar.pack(fill=tk.X, pady=(12, 0))

        self.btn_stop_scan = ModernButton(
            ctrl_bar, text="Остановить сканирование", icon="⏹",
            bg_color=self.colors['red'], hover_color=self.colors['red_hover'],
            command=self._stop_current_scan, height=36
        )
        self.btn_stop_scan.pack(side=tk.RIGHT)
        self.btn_stop_scan.pack_forget()  # Прячем пока нет сканирования

        # Нижняя часть: консоль вывода в реальном времени
        tk.Label(page, text="ХОД СКАНИРОВАНИЯ И НАЙДЕННЫЕ СОБЫТИЯ", font=self.fonts['small_bold'],
                 bg=self.colors['bg_root'], fg=self.colors['text_muted']).pack(anchor='w', pady=(10, 6))

        log_box = tk.Frame(page, bg=self.colors['console_bg'], highlightthickness=1,
                           highlightbackground=self.colors['border'])
        log_box.pack(fill=tk.BOTH, expand=True)

        self.scan_console = tk.Text(log_box, bg=self.colors['console_bg'], fg=self.colors['console_fg'],
                                    font=self.fonts['console'], wrap=tk.WORD, bd=0, padx=12, pady=12)
        self.scan_console.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        s_scroll = ttk.Scrollbar(log_box, command=self.scan_console.yview)
        s_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.scan_console.config(yscrollcommand=s_scroll.set)

        # Настройка цветовых тегов
        self.scan_console.tag_config('info', foreground='#38bdf8')
        self.scan_console.tag_config('threat', foreground='#ef4444', font=("Consolas", 9, "bold"))
        self.scan_console.tag_config('success', foreground='#10b981')
        self.scan_console.tag_config('warn', foreground='#f59e0b')

        return page

    # =========================================================================
    # 3. СТРАНИЦА УГРОЗ (THREATS PAGE)
    # =========================================================================
    def _create_threats_page(self, parent):
        page = tk.Frame(parent, bg=self.colors['bg_root'], padx=24, pady=20)

        # Заголовок
        hdr = tk.Frame(page, bg=self.colors['bg_root'])
        hdr.pack(fill=tk.X, pady=(0, 15))

        tk.Label(hdr, text="Обнаруженные угрозы", font=self.fonts['h1'],
                 bg=self.colors['bg_root'], fg=self.colors['text_primary']).pack(side=tk.LEFT)

        self.threats_badge = tk.Label(hdr, text="0 угроз", font=self.fonts['small_bold'],
                                      bg=self.colors['border'], fg=self.colors['text_secondary'],
                                      padx=8, pady=3)
        self.threats_badge.pack(side=tk.LEFT, padx=10)

        # Таблица угроз
        table_frame = tk.Frame(page, bg=self.colors['bg_card'], highlightthickness=1,
                               highlightbackground=self.colors['border'])
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        columns = ("name", "path", "details")
        self.threats_tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                         style="Cyber.Treeview")
        self.threats_tree.heading("name", text="Обнаруженная угроза")
        self.threats_tree.heading("path", text="Путь к файлу")
        self.threats_tree.heading("details", text="Детали / Детект")

        self.threats_tree.column("name", width=220, anchor='w')
        self.threats_tree.column("path", width=460, anchor='w')
        self.threats_tree.column("details", width=260, anchor='w')

        self.threats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        t_scroll = ttk.Scrollbar(table_frame, command=self.threats_tree.yview)
        t_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.threats_tree.config(yscrollcommand=t_scroll.set)

        # Кнопки действий
        btn_bar = tk.Frame(page, bg=self.colors['bg_root'])
        btn_bar.pack(fill=tk.X)

        ModernButton(
            btn_bar, text="В карантин (выбранное)", icon="📦",
            bg_color=self.colors['orange'], hover_color=self.colors['orange_hover'],
            command=self._quarantine_selected_threat, height=38
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            btn_bar, text="Изолировать ВСЕ в карантин", icon="🛡️",
            bg_color=self.colors['red'], hover_color=self.colors['red_hover'],
            command=self._quarantine_all_threats, height=38
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            btn_bar, text="Безопасное удаление (Wipe)", icon="🗑️",
            bg_color=self.colors['border_light'], hover_color=self.colors['red'],
            command=self._secure_delete_selected_threat, height=38
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            btn_bar, text="Открыть папку", icon="📂",
            bg_color=self.colors['bg_card'], hover_color=self.colors['border_light'],
            command=self._open_selected_threat_folder, height=38
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            btn_bar, text="Очистить список", icon="🧹",
            bg_color=self.colors['bg_card'], hover_color=self.colors['border_light'],
            command=self._clear_threats_list, height=38
        ).pack(side=tk.RIGHT)

        return page

    # =========================================================================
    # 4. СТРАНИЦА КАРАНТИНА (QUARANTINE PAGE)
    # =========================================================================
    def _create_quarantine_page(self, parent):
        page = tk.Frame(parent, bg=self.colors['bg_root'], padx=24, pady=20)

        hdr = tk.Frame(page, bg=self.colors['bg_root'])
        hdr.pack(fill=tk.X, pady=(0, 15))

        tk.Label(hdr, text="Изолированные объекты (Карантин)", font=self.fonts['h1'],
                 bg=self.colors['bg_root'], fg=self.colors['text_primary']).pack(side=tk.LEFT)

        self.quarantine_badge = tk.Label(hdr, text="0 файлов", font=self.fonts['small_bold'],
                                         bg=self.colors['border'], fg=self.colors['text_secondary'],
                                         padx=8, pady=3)
        self.quarantine_badge.pack(side=tk.LEFT, padx=10)

        # Таблица карантина
        table_frame = tk.Frame(page, bg=self.colors['bg_card'], highlightthickness=1,
                               highlightbackground=self.colors['border'])
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        columns = ("filename", "threat", "orig_path", "date", "size")
        self.quarantine_tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                            style="Cyber.Treeview")
        self.quarantine_tree.heading("filename", text="Имя файла")
        self.quarantine_tree.heading("threat", text="Угроза")
        self.quarantine_tree.heading("orig_path", text="Исходное расположение")
        self.quarantine_tree.heading("date", text="Дата изоляции")
        self.quarantine_tree.heading("size", text="Размер")

        self.quarantine_tree.column("filename", width=180, anchor='w')
        self.quarantine_tree.column("threat", width=160, anchor='w')
        self.quarantine_tree.column("orig_path", width=360, anchor='w')
        self.quarantine_tree.column("date", width=140, anchor='center')
        self.quarantine_tree.column("size", width=100, anchor='e')

        self.quarantine_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        q_scroll = ttk.Scrollbar(table_frame, command=self.quarantine_tree.yview)
        q_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.quarantine_tree.config(yscrollcommand=q_scroll.set)

        # Кнопки
        btn_bar = tk.Frame(page, bg=self.colors['bg_root'])
        btn_bar.pack(fill=tk.X)

        ModernButton(
            btn_bar, text="Восстановить файл", icon="🔄",
            bg_color=self.colors['green'], hover_color=self.colors['green_hover'],
            command=self._restore_quarantined_file, height=38
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            btn_bar, text="Удалить навсегда", icon="🗑️",
            bg_color=self.colors['red'], hover_color=self.colors['red_hover'],
            command=self._delete_quarantined_file, height=38
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            btn_bar, text="Очистить весь карантин", icon="🧹",
            bg_color=self.colors['border_light'], hover_color=self.colors['red'],
            command=self._clear_entire_quarantine, height=38
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            btn_bar, text="Открыть папку карантина", icon="📁",
            bg_color=self.colors['bg_card'], hover_color=self.colors['border_light'],
            command=self._open_quarantine_folder, height=38
        ).pack(side=tk.RIGHT)

        return page

    # =========================================================================
    # 5. СТРАНИЦА ИНСТРУМЕНТОВ И НАСТРОЕК (TOOLS PAGE)
    # =========================================================================
    def _create_tools_page(self, parent):
        page = tk.Frame(parent, bg=self.colors['bg_root'], padx=24, pady=20)

        tk.Label(page, text="Инструменты безопасности и Настройки", font=self.fonts['h1'],
                 bg=self.colors['bg_root'], fg=self.colors['text_primary']).pack(anchor='w', pady=(0, 20))

        # Сетка инструментов
        grid = tk.Frame(page, bg=self.colors['bg_root'])
        grid.pack(fill=tk.BOTH, expand=True)

        # 1. Автозагрузка
        c1 = self._create_tool_card(grid, "Анализ автозагрузки Windows",
                                    "Сканирование реестра (Run, RunOnce) и папок Startup на наличие подозрительных и неподписанных программ.")
        ModernButton(c1, text="Сканировать автозагрузку", icon="🚀", bg_color=self.colors['blue'],
                     hover_color=self.colors['blue_hover'], command=self._scan_autorun, height=36).pack(anchor='w', pady=(10, 0))

        # 2. USB Защита
        c2 = self._create_tool_card(grid, "Мониторинг USB накопителей",
                                    "Автоматическое обнаружение подключенных съемных флеш-накопителей и их фоновая проверка.")
        self.usb_toggle_btn = ModernButton(
            c2, text="USB Защита: ВКЛ" if self.usb_monitoring else "USB Защита: ВЫКЛ",
            icon="🔌", bg_color=self.colors['green'] if self.usb_monitoring else self.colors['border_light'],
            hover_color=self.colors['green_hover'], command=self._toggle_usb_guard, height=36
        )
        self.usb_toggle_btn.pack(anchor='w', pady=(10, 0))

        # 3. VirusTotal Интеграция
        c3 = self._create_tool_card(grid, "Облачная база VirusTotal",
                                    "Интеграция с официальным API VirusTotal для онлайн-проверки подозрительных хешей файлов.")
        vt_row = tk.Frame(c3, bg=self.colors['bg_card'])
        vt_row.pack(fill=tk.X, pady=(10, 0))

        self.vt_entry = tk.Entry(vt_row, bg=self.colors['bg_sidebar'], fg=self.colors['text_primary'],
                                 font=self.fonts['body'], insertbackground=self.colors['cyan'], bd=0, relief='flat')
        self.vt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 10))
        cur_vt = self.config.get_vt_api_key()
        if cur_vt:
            self.vt_entry.insert(0, cur_vt)

        ModernButton(vt_row, text="Сохранить ключ", bg_color=self.colors['cyan'],
                     hover_color=self.colors['cyan_hover'], command=self._save_vt_key, height=34).pack(side=tk.RIGHT)

        # 4. Звуковые уведомления
        c4 = self._create_tool_card(grid, "Звуковые оповещения",
                                    "Звуковые сигналы при обнаружении угроз, окончании сканирования и системных событиях.")
        sound_row = tk.Frame(c4, bg=self.colors['bg_card'])
        sound_row.pack(fill=tk.X, pady=(10, 0))

        self.sound_btn = ModernButton(
            sound_row,
            text="Звуки: ВКЛ" if self.sound.enabled else "Звуки: ВЫКЛ",
            icon="🔊",
            bg_color=self.colors['green'] if self.sound.enabled else self.colors['border_light'],
            hover_color=self.colors['green_hover'],
            command=self._toggle_sound,
            height=36
        )
        self.sound_btn.pack(side=tk.LEFT, padx=(0, 10))

        ModernButton(
            sound_row, text="Тестовый сигнал", icon="🔔",
            bg_color=self.colors['border_light'], hover_color=self.colors['cyan'],
            command=lambda: self.sound.play_async("notification"), height=36
        ).pack(side=tk.LEFT)

        return page

    def _create_tool_card(self, parent, title, desc):
        card = tk.Frame(parent, bg=self.colors['bg_card'], highlightthickness=1,
                        highlightbackground=self.colors['border'])
        card.pack(fill=tk.X, pady=6)

        inner = tk.Frame(card, bg=self.colors['bg_card'], padx=20, pady=16)
        inner.pack(fill=tk.BOTH, expand=True)

        tk.Label(inner, text=title, font=self.fonts['h3'], bg=self.colors['bg_card'],
                 fg=self.colors['text_primary']).pack(anchor='w')
        tk.Label(inner, text=desc, font=self.fonts['small'], bg=self.colors['bg_card'],
                 fg=self.colors['text_secondary'], wraplength=700, justify='left').pack(anchor='w', pady=(4, 6))

        return inner

    # =========================================================================
    # 6. СТРАНИЦА ЖУРНАЛА (LOGS PAGE)
    # =========================================================================
    def _create_logs_page(self, parent):
        page = tk.Frame(parent, bg=self.colors['bg_root'], padx=24, pady=20)

        hdr = tk.Frame(page, bg=self.colors['bg_root'])
        hdr.pack(fill=tk.X, pady=(0, 15))

        tk.Label(hdr, text="Журнал системных событий (Log)", font=self.fonts['h1'],
                 bg=self.colors['bg_root'], fg=self.colors['text_primary']).pack(side=tk.LEFT)

        btn_box = tk.Frame(hdr, bg=self.colors['bg_root'])
        btn_box.pack(side=tk.RIGHT)

        ModernButton(btn_box, text="Копировать", icon="📋", bg_color=self.colors['bg_card'],
                     hover_color=self.colors['border_light'], command=self._copy_logs, height=32).pack(side=tk.LEFT, padx=4)
        ModernButton(btn_box, text="Экспорт в TXT", icon="💾", bg_color=self.colors['bg_card'],
                     hover_color=self.colors['border_light'], command=self._export_logs, height=32).pack(side=tk.LEFT, padx=4)
        ModernButton(btn_box, text="Очистить", icon="🧹", bg_color=self.colors['bg_card'],
                     hover_color=self.colors['border_light'], command=self._clear_logs, height=32).pack(side=tk.LEFT, padx=4)

        log_container = tk.Frame(page, bg=self.colors['console_bg'], highlightthickness=1,
                                 highlightbackground=self.colors['border'])
        log_container.pack(fill=tk.BOTH, expand=True)

        self.full_log_console = tk.Text(log_container, bg=self.colors['console_bg'], fg=self.colors['console_fg'],
                                        font=self.fonts['console'], wrap=tk.WORD, bd=0, padx=14, pady=14)
        self.full_log_console.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_container, command=self.full_log_console.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.full_log_console.config(yscrollcommand=scrollbar.set)

        self.full_log_console.tag_config('info', foreground='#38bdf8')
        self.full_log_console.tag_config('threat', foreground='#ef4444', font=("Consolas", 9, "bold"))
        self.full_log_console.tag_config('success', foreground='#10b981')
        self.full_log_console.tag_config('warn', foreground='#f59e0b')

        return page

    # =========================================================================
    # РАБОТА С ЛОГАМИ И АНИМАЦИЕЙ
    # =========================================================================
    def _log(self, text, tag='info'):
        """Потокобезопасная запись в логи приложения"""
        def _append():
            ts = datetime.now().strftime("%H:%M:%S")
            line = f"[{ts}] {text}\n"

            for console in (getattr(self, 'scan_console', None), getattr(self, 'full_log_console', None)):
                if console and console.winfo_exists():
                    console.insert(tk.END, line, tag)
                    console.see(tk.END)

        self.root.after(0, _append)

    def _welcome_message(self):
        sig_count = self.scanner.sig_db.total_count() if hasattr(self.scanner.sig_db, 'total_count') else len(getattr(self.scanner.sig_db, 'md5_hashes', {}))
        self._log("==============================================================", 'info')
        self._log("🛡️ Aegis Core v2.0 Next-Gen Protection Engine запущен", 'success')
        self._log(f"Загружено локальных сигнатур: {sig_count}", 'info')
        self._log(f"Платформа: {sys.platform} | Python {sys.version.split()[0]}", 'info')
        self._log("Антивирусный монитор и модуль эвристического анализа активны", 'success')
        self._log("==============================================================", 'info')

    def _animate_radar(self):
        """Анимация радара на главной панели"""
        if hasattr(self, 'radar_canvas') and self.radar_canvas.winfo_exists():
            self.radar_canvas.delete("all")
            cx, cy, r = 40, 40, 32

            # Внешние круги
            color_pulse = self.colors['cyan'] if self.is_scanning else (self.colors['red'] if self.threats_found > 0 else self.colors['green'])
            self.radar_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=self.colors['border'], width=2)
            self.radar_canvas.create_oval(cx - r + 10, cy - r + 10, cx + r - 10, cy + r - 10, outline=self.colors['border'], width=1)

            # Вращающийся луч если идет сканирование
            if self.is_scanning:
                import math
                rad = math.radians(self.radar_angle)
                x2 = cx + r * math.cos(rad)
                y2 = cy + r * math.sin(rad)
                self.radar_canvas.create_line(cx, cy, x2, y2, fill=self.colors['cyan'], width=2)
                self.radar_angle = (self.radar_angle + 12) % 360

            # Центральный символ щита
            self.radar_canvas.create_text(cx, cy, text="🛡️", font=("Segoe UI", 16))

        self.root.after(50, self._animate_radar)

    # =========================================================================
    # ЛОГИКА СКАНИРОВАНИЯ
    # =========================================================================
    def _start_quick_scan(self):
        if self.is_scanning:
            messagebox.showwarning("Сканирование", "Сканирование уже выполняется!")
            return

        targets = []
        temp_dir = os.environ.get('TEMP', '')
        if temp_dir and os.path.exists(temp_dir):
            targets.append((temp_dir, 2, 200))

        downloads = str(Path.home() / "Downloads")
        if os.path.exists(downloads):
            targets.append((downloads, 2, 200))

        desktop = str(Path.home() / "Desktop")
        if os.path.exists(desktop):
            targets.append((desktop, 2, 150))

        self._run_scan_thread("Быстрое сканирование", targets)

    def _start_full_scan(self):
        if self.is_scanning:
            messagebox.showwarning("Сканирование", "Сканирование уже выполняется!")
            return

        targets = []
        # Пользовательские и системные папки
        home = str(Path.home())
        targets.append((home, 3, 500))

        prog_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        if os.path.exists(prog_files):
            targets.append((prog_files, 2, 300))

        win_sys = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
        if os.path.exists(win_sys):
            targets.append((win_sys, 1, 200))

        self._run_scan_thread("Глубокое сканирование", targets)

    def _select_and_scan_file(self):
        fpath = filedialog.askopenfilename(title="Выберите файл для сканирования")
        if fpath:
            self._switch_page("scanner")
            self._run_single_file_scan(fpath)

    def _select_and_scan_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку для сканирования")
        if folder:
            self._run_scan_thread(f"Папка: {os.path.basename(folder)}", [(folder, 4, 1000)])

    def _run_single_file_scan(self, fpath):
        def _worker():
            self._set_scan_ui_state(True, f"Проверка файла: {os.path.basename(fpath)}")
            self._log(f"Начата проверка файла: {fpath}", 'info')
            self.sound.play_async("notification")

            res = self.scanner.scan_file(fpath)
            self.files_scanned += 1
            self._update_kpi()

            if res['is_threat']:
                self.threats_found += 1
                self.session_threats.append(res)
                self.sound.play_async("threat")
                self._log(f"⚠️ ОБНАРУЖЕНА УГРОЗА: {res['threat_name']} -> {fpath}", 'threat')
                self._set_system_status("THREAT")
                messagebox.showwarning("Обнаружена угроза!", f"Файл заражен:\n{fpath}\n\nУгроза: {res['threat_name']}")
            else:
                self.sound.play_async("success")
                self._log(f"✓ Файл чист: {fpath}", 'success')
                messagebox.showinfo("Проверка завершена", "Файл полностью безопасен. Угроз не обнаружено.")

            self._set_scan_ui_state(False, "Проверка завершена")
            self.progress_bar['value'] = 100
            self.scan_percent_label.config(text="100%")

        threading.Thread(target=_worker, daemon=True).start()

    def _run_scan_thread(self, scan_name, targets):
        self._switch_page("scanner")
        self.stop_scan_flag = False

        def _worker():
            self._set_scan_ui_state(True, f"{scan_name}...")
            self.sound.play_async("notification")
            self._log(f"=== ЗАПУСК: {scan_name} ===", 'info')

            total_targets = len(targets)
            session_files = 0
            session_threats = 0

            for idx, (path, depth, max_files) in enumerate(targets):
                if self.stop_scan_flag:
                    self._log("Сканирование прервано пользователем.", 'warn')
                    break

                self._log(f"Сканирование каталога: {path} (глубина: {depth})", 'info')

                def file_callback(cur_filepath, is_threat):
                    # Обновление пути в UI
                    short_path = cur_filepath if len(cur_filepath) < 65 else "..." + cur_filepath[-62:]
                    self.root.after(0, lambda: self.current_file_label.config(text=f"Файл: {short_path}"))

                scan_res = self.scanner.scan_directory(path, max_depth=depth, max_files=max_files, callback=file_callback)
                session_files += scan_res['files_scanned']
                self.files_scanned += scan_res['files_scanned']

                for threat in scan_res['results']:
                    session_threats += 1
                    self.threats_found += 1
                    self.session_threats.append(threat)
                    self.sound.play_async("threat")
                    self._log(f"⚠️ УГРОЗА: {threat['threat_name']} -> {threat['filepath']}", 'threat')
                    self._set_system_status("THREAT")

                # Обновление прогресс-бара
                prog = int(((idx + 1) / total_targets) * 100)
                self.root.after(0, lambda p=prog: self._update_progress_ui(p))
                self._update_kpi()

            self._set_scan_ui_state(False, "Сканирование завершено")
            self.progress_bar['value'] = 100
            self.scan_percent_label.config(text="100%")

            self._log(f"=== {scan_name} завершено ===", 'success')
            self._log(f"Проверено файлов в этой сессии: {session_files} | Угроз обнаружено: {session_threats}", 'info')

            if session_threats > 0:
                self.sound.play_async("threat")
                if messagebox.askyesno("Обнаружены угрозы",
                                       f"Найдено {session_threats} вредоносных объектов!\nПоместить их в карантин немедленно?"):
                    self._quarantine_all_threats()
            else:
                self.sound.play_async("success")
                messagebox.showinfo("Сканирование завершено", "Проверка завершена. Все проверенные объекты чисты!")

        threading.Thread(target=_worker, daemon=True).start()

    def _stop_current_scan(self):
        if self.is_scanning:
            self.stop_scan_flag = True
            self.btn_stop_scan.config(state='disabled')
            self._log("Отправлен сигнал остановки сканирования...", 'warn')

    def _set_scan_ui_state(self, running, status_msg):
        self.is_scanning = running
        def _update():
            if running:
                self.btn_stop_scan.pack(side=tk.RIGHT)
                self.scan_status_label.config(text=status_msg, fg=self.colors['cyan'])
                self._set_system_status("SCANNING")
            else:
                self.btn_stop_scan.pack_forget()
                self.scan_status_label.config(text=status_msg, fg=self.colors['text_primary'])
                if self.threats_found == 0:
                    self._set_system_status("PROTECTED")
        self.root.after(0, _update)

    def _update_progress_ui(self, value):
        self.progress_bar['value'] = value
        self.scan_percent_label.config(text=f"{value}%")

    def _set_system_status(self, mode):
        def _apply():
            if mode == "PROTECTED":
                self.status_dot.config(text="●", fg=self.colors['green'])
                self.status_text.config(text="СИСТЕМА ЗАЩИЩЕНА", fg=self.colors['green'])
                self.dash_status_title.config(text="Ваше устройство под надежной защитой", fg=self.colors['text_primary'])
            elif mode == "SCANNING":
                self.status_dot.config(text="●", fg=self.colors['cyan'])
                self.status_text.config(text="ИДЕТ СКАНИРОВАНИЕ...", fg=self.colors['cyan'])
                self.dash_status_title.config(text="Выполняется проверка файлов системы...", fg=self.colors['cyan'])
            elif mode == "THREAT":
                self.status_dot.config(text="▲", fg=self.colors['red'])
                self.status_text.config(text="ОБНАРУЖЕНЫ УГРОЗЫ", fg=self.colors['red'])
                self.dash_status_title.config(text="Внимание! Найдена вредоносная активность!", fg=self.colors['red'])
        self.root.after(0, _apply)

    def _update_kpi(self):
        def _apply():
            self.kpi_scanned.config(text=str(self.files_scanned))
            self.kpi_threats.config(text=str(self.threats_found))
            self.kpi_quarantine.config(text=str(self.quarantine.count()))
            self.threats_badge.config(text=f"{len(self.session_threats)} угроз")
            self.quarantine_badge.config(text=f"{self.quarantine.count()} файлов")
        self.root.after(0, _apply)

    # =========================================================================
    # РАБОТА С УГРОЗАМИ И КАРАНТИНОМ
    # =========================================================================
    def _refresh_threats_table(self):
        for item in self.threats_tree.get_children():
            self.threats_tree.delete(item)

        for t in self.session_threats:
            details_str = ", ".join(t.get('details', [])) if isinstance(t.get('details'), list) else str(t.get('details', ''))
            self.threats_tree.insert("", tk.END, values=(t.get('threat_name', 'Угроза'), t.get('filepath', ''), details_str))

        self.threats_badge.config(text=f"{len(self.session_threats)} угроз")

    def _quarantine_selected_threat(self):
        selected = self.threats_tree.selection()
        if not selected:
            messagebox.showinfo("Выбор", "Выберите угрозу в таблице для перемещения в карантин.")
            return

        for item_id in selected:
            val = self.threats_tree.item(item_id, 'values')
            threat_name, fpath = val[0], val[1]
            if self.quarantine.add(fpath, threat_name=threat_name, remove_original=True):
                self._log(f"Файл успешно изолирован в карантин: {fpath}", 'success')
                self.session_threats = [x for x in self.session_threats if x.get('filepath') != fpath]
            else:
                self._log(f"Не удалось переместить в карантин: {fpath}", 'warn')

        self._refresh_threats_table()
        self._update_kpi()
        self.sound.play_async("success")

    def _quarantine_all_threats(self):
        if not self.session_threats:
            messagebox.showinfo("Карантин", "Список угроз пуст.")
            return

        count = 0
        for t in list(self.session_threats):
            fpath = t.get('filepath')
            tname = t.get('threat_name', 'Угроза')
            if self.quarantine.add(fpath, threat_name=tname, remove_original=True):
                count += 1

        self.session_threats.clear()
        self._refresh_threats_table()
        self._update_kpi()
        self._log(f"Все обнаруженные угрозы ({count}) успешно изолированы в карантин.", 'success')
        self.sound.play_async("success")
        messagebox.showinfo("Карантин", f"Успешно изолировано объектов: {count}")

    def _secure_delete_selected_threat(self):
        selected = self.threats_tree.selection()
        if not selected:
            messagebox.showinfo("Выбор", "Выберите файл для безопасного удаления.")
            return

        if not messagebox.askyesno("Безопасное удаление", "Файл будет безвозвратно перезаписан и удален.\nПродолжить?"):
            return

        for item_id in selected:
            val = self.threats_tree.item(item_id, 'values')
            fpath = val[1]
            success, msg = self.cleaner.secure_delete(fpath, passes=3)
            if success:
                self._log(f"Файл безвозвратно стерт: {fpath}", 'success')
                self.session_threats = [x for x in self.session_threats if x.get('filepath') != fpath]
            else:
                self._log(f"Ошибка удаления: {msg}", 'warn')

        self._refresh_threats_table()
        self._update_kpi()

    def _open_selected_threat_folder(self):
        selected = self.threats_tree.selection()
        if not selected:
            return
        fpath = self.threats_tree.item(selected[0], 'values')[1]
        folder = os.path.dirname(fpath)
        if os.path.exists(folder):
            os.startfile(folder)

    def _clear_threats_list(self):
        self.session_threats.clear()
        self._refresh_threats_table()
        self._update_kpi()

    def _refresh_quarantine_table(self):
        for item in self.quarantine_tree.get_children():
            self.quarantine_tree.delete(item)

        items = self.quarantine.get_details()
        for it in items:
            sz_str = f"{it['size'] / 1024:.1f} KB" if it['size'] > 1024 else f"{it['size']} B"
            self.quarantine_tree.insert("", tk.END, values=(
                it['filename'], it['threat'], it['original_path'], it['date'], sz_str
            ), tags=(it['quarantine_path'],))

        self.quarantine_badge.config(text=f"{len(items)} файлов")
        self._update_kpi()

    def _restore_quarantined_file(self):
        selected = self.quarantine_tree.selection()
        if not selected:
            messagebox.showinfo("Карантин", "Выберите файл для восстановления.")
            return

        for item_id in selected:
            tags = self.quarantine_tree.item(item_id, 'tags')
            if tags:
                qpath = tags[0]
                success, msg = self.quarantine.restore(qpath)
                if success:
                    self._log(f"Файл успешно восстановлен из карантина: {msg}", 'success')
                else:
                    self._log(f"Ошибка восстановления: {msg}", 'warn')

        self._refresh_quarantine_table()
        self.sound.play_async("success")

    def _delete_quarantined_file(self):
        selected = self.quarantine_tree.selection()
        if not selected:
            messagebox.showinfo("Карантин", "Выберите файл для окончательного удаления.")
            return

        if not messagebox.askyesno("Удаление", "Окончательно удалить выбранный файл из карантина?"):
            return

        for item_id in selected:
            tags = self.quarantine_tree.item(item_id, 'tags')
            if tags:
                qpath = tags[0]
                if self.quarantine.remove(qpath):
                    self._log(f"Файл окончательно удален из карантина: {qpath}", 'info')

        self._refresh_quarantine_table()

    def _clear_entire_quarantine(self):
        if not messagebox.askyesno("Очистить карантин", "Вы действительно хотите удалить ВСЕ файлы из карантина навсегда?"):
            return
        self.quarantine.clear()
        self._refresh_quarantine_table()
        self._log("Карантин полностью очищен.", 'info')

    def _open_quarantine_folder(self):
        if os.path.exists(self.quarantine.quarantine_dir):
            os.startfile(self.quarantine.quarantine_dir)

    # =========================================================================
    # ИНСТРУМЕНТЫ: АВТОЗАГРУЗКА, USB, НАСТРОЙКИ
    # =========================================================================
    def _scan_autorun(self):
        """Сканирование реестра и папок автозагрузки"""
        self._log("--- Запуск сканирования автозагрузки Windows ---", 'info')
        suspicious = []

        try:
            # 1. Папки Startup
            startup_paths = [
                os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'),
                os.path.join(os.environ.get('ProgramData', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            ]
            for folder in startup_paths:
                if os.path.isdir(folder):
                    for filename in os.listdir(folder):
                        fpath = os.path.join(folder, filename)
                        if os.path.isfile(fpath):
                            # Проверяем антивирусным сканером
                            scan_res = self.scanner.scan_file(fpath)
                            if scan_res['is_threat']:
                                suspicious.append((fpath, f"Угроза: {scan_res['threat_name']}"))
                            else:
                                self._log(f"Автозагрузка (Папка): {filename} — Чист", 'info')

            # 2. Реестр Windows Run / RunOnce
            if sys.platform == 'win32':
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
                            idx = 0
                            while True:
                                try:
                                    name, value, _ = winreg.EnumValue(key, idx)
                                    # Извлекаем путь к исполняемому файлу
                                    exe_path = value.strip('"').split('"')[0].strip()
                                    if ' ' in exe_path and not os.path.exists(exe_path):
                                        exe_path = exe_path.split()[0]

                                    if os.path.exists(exe_path):
                                        res = self.scanner.scan_file(exe_path)
                                        if res['is_threat']:
                                            suspicious.append((exe_path, f"Вредоносный автозапуск: {res['threat_name']}"))
                                        else:
                                            self._log(f"Автозагрузка (Реестр): {name} -> {exe_path} — Чист", 'info')
                                    elif exe_path and not exe_path.startswith(('http', 'cmd', 'powershell')):
                                        suspicious.append((value, "Указывает на несуществующий файл (фантомная запись)"))
                                    idx += 1
                                except OSError:
                                    break
                    except Exception:
                        pass

        except Exception as e:
            self._log(f"Ошибка проверки автозагрузки: {e}", 'warn')

        if suspicious:
            self.sound.play_async("threat")
            self._log(f"⚠️ Обнаружено подозрительных записей автозагрузки: {len(suspicious)}", 'threat')
            for p, r in suspicious:
                self._log(f"   └─ {p} ({r})", 'threat')
            messagebox.showwarning("Автозагрузка", f"Обнаружено {len(suspicious)} подозрительных записей в автозагрузке!")
        else:
            self.sound.play_async("success")
            self._log("✓ Автозагрузка полностью чиста. Подозрительных программ не обнаружено.", 'success')
            messagebox.showinfo("Автозагрузка", "Проверка завершена. Все элементы автозагрузки легитимны!")

    def _toggle_usb_guard(self):
        self.usb_monitoring = not self.usb_monitoring
        self.config.set("enable_usb_monitoring", self.usb_monitoring)

        if self.usb_monitoring:
            self.usb_toggle_btn.set_text("USB Защита: ВКЛ")
            self.usb_toggle_btn.bg_color = self.colors['green']
            self.usb_toggle_btn.hover_color = self.colors['green_hover']
            self.usb_toggle_btn._draw()
            self._log("Мониторинг USB накопителей ВКЛЮЧЕН", 'success')
            self._start_usb_monitoring()
        else:
            self.usb_toggle_btn.set_text("USB Защита: ВЫКЛ")
            self.usb_toggle_btn.bg_color = self.colors['border_light']
            self.usb_toggle_btn.hover_color = self.colors['green_hover']
            self.usb_toggle_btn._draw()
            self._log("Мониторинг USB накопителей ВЫКЛЮЧЕН", 'warn')

    def _get_removable_drives(self):
        drives = set()
        if sys.platform == 'win32' and WMI_AVAILABLE:
            try:
                c = wmi.WMI()
                for disk in c.Win32_LogicalDisk():
                    if disk.DriveType == 2:  # 2 = Removable drive
                        drives.add(disk.DeviceID + "\\")
            except Exception:
                pass
        return drives

    def _start_usb_monitoring(self):
        self.last_usb_devices = self._get_removable_drives()

        def _usb_loop():
            if not self.usb_monitoring:
                return
            try:
                current = self._get_removable_drives()
                new_drives = current - self.last_usb_devices
                if new_drives:
                    for d in new_drives:
                        self._log(f"🔌 Подключен съемный диск: {d}", 'info')
                        self.sound.play_async("question")
                        self.root.after(0, lambda drv=d: self._prompt_scan_usb(drv))
                self.last_usb_devices = current
            except Exception:
                pass

            if self.usb_monitoring:
                self.root.after(3000, _usb_loop)

        self.root.after(2000, _usb_loop)

    def _prompt_scan_usb(self, drive_path):
        if messagebox.askyesno("USB Устройство", f"Обнаружен съемный накопитель {drive_path}.\nВыполнить проверку на вирусы прямо сейчас?"):
            self._run_scan_thread(f"USB Диск {drive_path}", [(drive_path, 3, 500)])

    def _save_vt_key(self):
        key = self.vt_entry.get().strip()
        self.config.set("vt_api_key", key)
        self._log(f"Ключ VirusTotal обновлен ({key[:6]}...{key[-4:] if len(key) > 10 else ''})", 'success')
        messagebox.showinfo("VirusTotal", "API ключ VirusTotal успешно сохранен в конфигурации.")

    def _toggle_sound(self):
        new_val = not self.sound.enabled
        self.sound.enabled = new_val
        self.config.set("enable_sound", new_val)

        if new_val:
            self.sound_btn.set_text("Звуки: ВКЛ")
            self.sound_btn.bg_color = self.colors['green']
            self.sound.play_async("notification")
        else:
            self.sound_btn.set_text("Звуки: ВЫКЛ")
            self.sound_btn.bg_color = self.colors['border_light']
        self.sound_btn._draw()

    def _copy_logs(self):
        try:
            content = self.full_log_console.get("1.0", tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            messagebox.showinfo("Лог", "Журнал событий скопирован в буфер обмена.")
        except Exception:
            pass

    def _export_logs(self):
        fpath = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Text files", "*.txt")],
                                             title="Экспорт лога событий")
        if fpath:
            try:
                content = self.full_log_console.get("1.0", tk.END)
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Экспорт", f"Журнал успешно сохранен:\n{fpath}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def _clear_logs(self):
        for c in (self.scan_console, self.full_log_console):
            c.delete("1.0", tk.END)
        self._welcome_message()

    def scan_file_on_start(self, filepath):
        """Метод вызова при запуске приложения с аргументом файла (контекстное меню)"""
        if os.path.exists(filepath):
            self.root.after(500, lambda: self._run_single_file_scan(filepath))

    def run(self):
        """Запуск главного цикла приложения"""
        self.root.mainloop()


def main():
    app = AegisApp()
    app.run()


if __name__ == "__main__":
    main()
