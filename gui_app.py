"""Графический интерфейс Aegis Core"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
from datetime import datetime
from pathlib import Path

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
        
        # Правая панель - лог
        right = tk.Frame(content, bg=self.colors['surface'], width=350)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(7, 0))
        right.pack_propagate(False)
        
        log_header = tk.Frame(right, bg=self.colors['surface'])
        log_header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
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
    
    def _quick_scan(self):
        """Быстрая проверка"""
        if self.is_scanning:
            messagebox.showwarning("Сканирование", "Уже выполняется!")
            return
        
        self.is_scanning = True
        self.files_scanned = 0
        self.threats_found = 0
        
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
        
        self._log("=" * 50)
        self._log("🔍 ПОЛНАЯ ПРОВЕРКА")
        
        areas = []
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
        
        self._log(f"🔍 Проверка: {os.path.basename(filepath)}")
        
        result = self.scanner.scan_file(filepath)
        
        if result['is_threat']:
            self._log(f"⚠️ УГРОЗА: {result['threat_name']}")
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
                
                results = self.scanner.scan_directory(path, depth, max_f)
                self.files_scanned += max_f
                self.threats_found += len(results)
                
                for r in results:
                    self._log(f"⚠️ {os.path.basename(r['filepath'])}")
                
                progress = ((i + 1) / total) * 100
                self._update_progress(progress, f"Сканирование...")
            
            self._update_progress(100, "Завершено")
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