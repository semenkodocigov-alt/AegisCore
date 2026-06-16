"""Модуль анимаций и визуальных эффектов для Aegis Core"""
import tkinter as tk
import math
import time


class SmoothAnimator:
    """Класс для создания плавных анимаций"""
    
    def __init__(self, target, duration=300, easing='ease-in-out'):
        self.target = target
        self.duration = duration
        self.easing = easing
        self.start_time = None
        self.animation_id = None
    
    def start(self, callback):
        """Запуск анимации"""
        self.start_time = time.time()
        self._animate(callback)
    
    def _animate(self, callback):
        """Выполнение шага анимации"""
        elapsed = time.time() - self.start_time
        progress = min(1.0, elapsed / (self.duration / 1000))
        
        # Применение easing функции
        if self.easing == 'ease-in-out':
            eased = self._ease_in_out(progress)
        elif self.easing == 'ease-in':
            eased = progress ** 2
        elif self.easing == 'ease-out':
            eased = 1 - (1 - progress) ** 2
        else:
            eased = progress
        
        callback(eased)
        
        if progress < 1.0:
            self.animation_id = self.target.after(16, lambda: self._animate(callback))
    
    def _ease_in_out(self, t):
        """Ease-in-out cubic функция"""
        if t < 0.5:
            return 2 * t * t
        else:
            return 1 - (-2 * t + 2) ** 2 / 2


class GradientFrame(tk.Canvas):
    """Фрейм с градиентом"""
    
    def __init__(self, parent, from_color, to_color, **kwargs):
        super().__init__(parent, **kwargs)
        self.from_color = from_color
        self.to_color = to_color
        self.bind('<Configure>', self._draw_gradient)
    
    def _draw_gradient(self, event):
        """Рисование градиента"""
        self.delete('all')
        width = event.width
        height = event.height
        
        for i in range(height):
            ratio = i / height
            color = self._interpolate_color(self.from_color, self.to_color, ratio)
            self.create_line(0, i, width, i, fill=color)
    
    def _interpolate_color(self, color1, color2, ratio):
        """Интерполяция между двумя цветами"""
        try:
            r1 = int(color1[1:3], 16)
            g1 = int(color1[3:5], 16)
            b1 = int(color1[5:7], 16)
            
            r2 = int(color2[1:3], 16)
            g2 = int(color2[3:5], 16)
            b2 = int(color2[5:7], 16)
            
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color1


class RotatingSpinner:
    """Вращающийся спиннер для загрузки"""
    
    def __init__(self, canvas, center_x, center_y, radius=20, color='#47b5ff'):
        self.canvas = canvas
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.color = color
        self.angle = 0
        self.running = False
        self.animation_id = None
    
    def start(self):
        """Запуск спиннера"""
        self.running = True
        self._spin()
    
    def stop(self):
        """Остановка спиннера"""
        self.running = False
        if self.animation_id:
            self.canvas.after_cancel(self.animation_id)
        self.canvas.delete('spinner')
    
    def _spin(self):
        """Выполнение шага вращения"""
        if not self.running:
            return
        
        self.canvas.delete('spinner')
        
        # Рисование вращающихся сегментов
        for i in range(8):
            angle = math.radians(self.angle + i * 45)
            x1 = self.center_x + self.radius * math.cos(angle)
            y1 = self.center_y + self.radius * math.sin(angle)
            x2 = self.center_x + (self.radius - 5) * math.cos(angle)
            y2 = self.center_y + (self.radius - 5) * math.sin(angle)
            
            # Постепенное затемнение
            alpha = int(255 * (i / 8))
            color = self.color
            
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=3, tags='spinner')
        
        self.angle = (self.angle + 15) % 360
        self.animation_id = self.canvas.after(50, self._spin)


class PulsingButton(tk.Button):
    """Кнопка с пульсирующим эффектом"""
    
    def __init__(self, parent, normal_color, hover_color, pulse_color=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.normal_color = normal_color
        self.hover_color = hover_color
        self.pulse_color = pulse_color or hover_color
        self.pulsing = False
        self.pulse_level = 0
        self.pulse_direction = 1
        self.pulse_id = None
        
        self.config(bg=normal_color)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
    
    def _on_enter(self, event):
        """При наведении"""
        if not self.pulsing:
            self.config(bg=self.hover_color)
    
    def _on_leave(self, event):
        """При убирании курсора"""
        if not self.pulsing:
            self.config(bg=self.normal_color)
    
    def pulse(self):
        """Начало пульсирующей анимации"""
        self.pulsing = True
        self._pulse_step()
    
    def stop_pulse(self):
        """Остановка пульсирующей анимации"""
        self.pulsing = False
        if self.pulse_id:
            self.after_cancel(self.pulse_id)
        self.config(bg=self.normal_color)
    
    def _pulse_step(self):
        """Один шаг пульсации"""
        if not self.pulsing:
            return
        
        self.pulse_level += self.pulse_direction * 0.1
        if self.pulse_level >= 1 or self.pulse_level <= 0:
            self.pulse_direction *= -1
        
        # Интерполяция цвета
        color = self._interpolate_color(self.normal_color, self.pulse_color, self.pulse_level)
        self.config(bg=color)
        
        self.pulse_id = self.after(30, self._pulse_step)
    
    def _interpolate_color(self, color1, color2, ratio):
        """Интерполяция между двумя цветами"""
        try:
            r1 = int(color1[1:3], 16)
            g1 = int(color1[3:5], 16)
            b1 = int(color1[5:7], 16)
            
            r2 = int(color2[1:3], 16)
            g2 = int(color2[3:5], 16)
            b2 = int(color2[5:7], 16)
            
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color1


class ProgressBar(tk.Canvas):
    """Анимированный прогресс-бар"""
    
    def __init__(self, parent, width=300, height=8, bg_color='#2d3d52', 
                 fill_color='#47b5ff', **kwargs):
        super().__init__(parent, width=width, height=height, bg=bg_color,
                        highlightthickness=0, **kwargs)
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.progress = 0
        self.target_progress = 0
        self.animation_id = None
    
    def set_progress(self, value):
        """Установка прогресса (с анимацией)"""
        self.target_progress = max(0, min(100, value))
        self._animate()
    
    def _animate(self):
        """Анимация прогресса"""
        if abs(self.progress - self.target_progress) < 1:
            self.progress = self.target_progress
        else:
            step = max(1, abs(self.target_progress - self.progress) // 5)
            if self.progress < self.target_progress:
                self.progress += step
            else:
                self.progress -= step
        
        self._draw()
        
        if self.progress != self.target_progress:
            self.animation_id = self.after(20, self._animate)
    
    def _draw(self):
        """Рисование прогресс-бара"""
        self.delete('all')
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Фон
        self.create_rectangle(0, 0, width, height, fill=self.bg_color, outline='')
        
        # Прогресс с градиентом
        progress_width = int(width * self.progress / 100)
        if progress_width > 0:
            self.create_rectangle(0, 0, progress_width, height,
                                fill=self.fill_color, outline='')


class SlideInFrame(tk.Frame):
    """Фрейм, который выезжает снизу"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.offset = 0
        self.max_offset = 300
        self.animation_id = None
    
    def slide_in(self):
        """Анимация въезда"""
        self.animation_id = self.after(0, self._slide_step)
    
    def _slide_step(self):
        """Один шаг анимации"""
        self.offset += 20
        if self.offset >= self.max_offset:
            self.offset = self.max_offset
        else:
            self.animation_id = self.after(20, self._slide_step)
        
        # Применение трансформации (упрощённо для Tkinter)
        # В реальном приложении нужно использовать place или grid с relative координатами
