"""Графический интерфейс Aegis Core"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import time
import winsound
import math
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
        self.root.geometry("900x600")
        self.root.configure(bg='#f0f2f5')
        self.root.overrideredirect(True)
        
        # Компоненты
        self.scanner = FileScanner()
        self.quarantine = QuarantineManager()
        
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
            'console_bg': '#1a1f2e',
            'console_fg': '#00e676'
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
        
        self._build_ui()
        self._welcome()
    
    def _build_ui(self):
        """Построение интерфейса"""
        # Главный контейнер
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        header = tk.Frame(main, bg=self.colors['header'], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        header.bind("<Button-1>", self._start_move)
        header.bind("<B1-Motion>", self._move_window)
        
        tk.Label(header, text="🛡️ AEGIS CORE", font=("Segoe UI", 16, "bold"),
                bg=self.colors['header'], fg='white').pack(side=tk.LEFT, padx=20, pady=10)
        
        tk.Label(header, text="Антивирус", font=("Segoe UI", 9),
                bg=self.colors['header'], fg='#95a5a6').pack(side=tk.LEFT, pady=10)
        
        tk.Button(header, text="✕", command=self.root.destroy,
                  font=("Segoe UI", 11, "bold"), bg=self.colors['header'],
                  fg='white', bd=0, activebackground='#c0392b',
                  activeforeground='white', cursor='hand2').pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Контент
        content = tk.Frame(main, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Левая панель
        left = tk.Frame(content, bg=self.colors['bg'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 7))
        
        # Статус
        status = tk.Frame(left, bg=self.colors['surface'])
        status.pack(fill=tk.X, pady=(0, 10))
        
        inner = tk.Frame(status, bg=self.colors['surface'])
        inner.pack(padx=20, pady=15, fill=tk.X)
        
        tk.Label(inner, text="✅ ЗАЩИТА АКТИВНА", font=("Segoe UI", 13, "bold"),
                bg=self.colors['surface'], fg=self.colors['green']).pack(anchor='w')
        
        tk.Label(inner, text=f"Сигнатур: {self.scanner.sig_db.total_count()}",
                font=("Segoe UI", 9), bg=self.colors['surface'],
                fg=self.colors['text_secondary']).pack(anchor='w')
        
        # Анимация сканирования
        self.animation_canvas = tk.Canvas(left, width=100, height=100, bg=self.colors['bg'], highlightthickness=0)
        self.animation_canvas.pack(pady=10)
        self._draw_animation_idle()
        
        # Кнопки
        scans_frame = tk.Frame(left, bg=self.colors['bg'])
        scans_frame.pack(fill=tk.X)
        
        tk.Label(scans_frame, text="Сканирование", font=("Segoe UI", 12, "bold"),
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor='w', pady=(0, 10))
        
        # Карточки сканирования
        scans = [
            ("⚡ Быстрая проверка", "Критические области", self._quick_scan, self.colors['green']),
            ("🔍 Полная проверка", "Глубокий анализ", self._full_scan, self.colors['blue']),
            ("📁 Проверить файл", "Выборочная проверка", self._scan_file, self.colors['orange'])
        ]
        
        for title, desc, cmd, color in scans:
            card = tk.Frame(left, bg=self.colors['surface'])
            card.pack(fill=tk.X, pady=2)
            
            cinner = tk.Frame(card, bg=self.colors['surface'])
            cinner.pack(fill=tk.X, padx=20, pady=10)
            
            tk.Label(cinner, text=title, font=("Segoe UI", 11, "bold"),
                    bg=self.colors['surface'], fg=self.colors['text']).pack(side=tk.LEFT)
            
            tk.Label(cinner, text=desc, font=("Segoe UI", 8),
                    bg=self.colors['surface'], fg=self.colors['text_secondary']).pack(side=tk.LEFT, padx=10)
            
            tk.Button(cinner, text="▶", command=cmd, font=("Segoe UI", 10, "bold"),
                     bg=color, fg='white', bd=0, padx=15, pady=4,
                     cursor='hand2').pack(side=tk.RIGHT)
        
        # USB мониторинг
        usb_frame = tk.Frame(left, bg=self.colors['bg'])
        usb_frame.pack(fill=tk.X, pady=(10, 0))
        
        usb_card = tk.Frame(left, bg=self.colors['surface'])
        usb_card.pack(fill=tk.X, pady=2)
        
        usb_inner = tk.Frame(usb_card, bg=self.colors['surface'])
        usb_inner.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(usb_inner, text="🔌 USB Защита", font=("Segoe UI", 11, "bold"),
                bg=self.colors['surface'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        tk.Label(usb_inner, text="Автопроверка USB", font=("Segoe UI", 8),
                bg=self.colors['surface'], fg=self.colors['text_secondary']).pack(side=tk.LEFT, padx=10)
        
        self.usb_button = tk.Button(usb_inner, text="ВКЛ", command=self._toggle_usb_monitoring,
                                   font=("Segoe UI", 10, "bold"), bg=self.colors['red'],
                                   fg='white', bd=0, padx=15, pady=4, cursor='hand2')
        self.usb_button.pack(side=tk.RIGHT)
        
        # Правая панель - лог + список угроз
        right = tk.Frame(content, bg=self.colors['surface'], width=350)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(7, 0))
        right.pack_propagate(False)
        
        threats_frame = tk.Frame(right, bg=self.colors['surface'])
        threats_frame.pack(fill=tk.X, padx=15, pady=(10, 0))
        
        tk.Label(threats_frame, text="🔴 Обнаруженные файлы", font=("Segoe UI", 11, "bold"),
                bg=self.colors['surface'], fg=self.colors['text']).pack(anchor='w')
        
        list_frame = tk.Frame(threats_frame, bg=self.colors['surface'])
        list_frame.pack(fill=tk.BOTH, expand=False, pady=(5, 8))
        
        self.threats_listbox = tk.Listbox(
            list_frame,
            height=6,
            bg='#f7f9fc',
            fg=self.colors['text'],
            selectbackground=self.colors['blue'],
            bd=1,
            relief='solid'
        )
        self.threats_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        threats_scroll = tk.Scrollbar(list_frame, command=self.threats_listbox.yview)
        threats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.threats_listbox.config(yscrollcommand=threats_scroll.set)
        
        log_header = tk.Frame(right, bg=self.colors['surface'])
        log_header.pack(fill=tk.X, padx=15, pady=(0, 5))
        
        tk.Label(log_header, text="📋 Журнал", font=("Segoe UI", 11, "bold"),
                bg=self.colors['surface'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        tk.Button(log_header, text="✕", command=self._clear_log,
                 font=("Segoe UI", 9), bg=self.colors['surface'],
                 fg=self.colors['red'], bd=0, cursor='hand2').pack(side=tk.RIGHT)
        
        self.log_widget = scrolledtext.ScrolledText(
            right, wrap=tk.WORD, font=("Consolas", 9),
            bg=self.colors['console_bg'], fg=self.colors['console_fg'],
            insertbackground='white', height=18
        )
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        # Прогресс
        self.progress_frame = tk.Frame(right, bg=self.colors['surface'])
        self.progress_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate',
                                            style="green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X)
        
        self.progress_label = tk.Label(self.progress_frame, text="Готов",
                                       font=("Segoe UI", 8), bg=self.colors['surface'],
                                       fg=self.colors['text_secondary'])
        self.progress_label.pack(anchor='w')
        
        # Футер
        footer = tk.Frame(main, bg=self.colors['header'])
        footer.pack(fill=tk.X)
        
        finner = tk.Frame(footer, bg=self.colors['header'])
        finner.pack(padx=20, pady=6, fill=tk.X)
        
        tk.Label(finner, text=f"v{self.version} | {self.author_email}",
                font=("Segoe UI", 8), bg=self.colors['header'],
                fg='#95a5a6').pack(side=tk.LEFT)
        
        tk.Label(finner, text="© 2026 Aegis Core", font=("Segoe UI", 8),
                bg=self.colors['header'], fg='#95a5a6').pack(side=tk.RIGHT)
    
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
            self.progress_bar['value'] = val
            if text:
                self.progress_label.config(text=text)
        except:
            pass
    
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
        """Воспроизведение звука"""
        try:
            if sound_type == "threat":
                # Звук угрозы - низкий тон
                winsound.Beep(800, 300)
                time.sleep(0.1)
                winsound.Beep(600, 300)
            elif sound_type == "scan_complete":
                # Звук завершения - высокий тон
                winsound.Beep(1000, 200)
                time.sleep(0.1)
                winsound.Beep(1200, 200)
            elif sound_type == "usb_detected":
                # Звук USB подключения
                winsound.Beep(1500, 150)
                time.sleep(0.1)
                winsound.Beep(1500, 150)
        except:
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
    
    def run(self):
        """Запуск приложения"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("green.Horizontal.TProgressbar",
                       background='#27ae60', troughcolor='#ecf0f1')
        
        self.root.update_idletasks()
        w, h = 900, 600
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        
        self.root.mainloop()


# Для теста
if __name__ == "__main__":
    print("GUI модуль загружен")
    print(f"Класс AegisApp доступен: {AegisApp}")