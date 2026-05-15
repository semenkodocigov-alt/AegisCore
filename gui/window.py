#  создает окошко
import tkinter as tk

def create_window():
    window = tk.Tk()
    window.title("AegisCore")
    window.geometry("400x300")
    return window