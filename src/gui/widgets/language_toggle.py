import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

class LanguageToggle(ttk.Button):
    """Widget to toggle between languages"""
    
    def __init__(self, parent, initial_language: str = "en", 
                 command: Optional[Callable[[], None]] = None,
                 text: str = "Switch Language", *args, **kwargs):
        super().__init__(parent, text=text, command=command, *args, **kwargs)
        self.current_language = initial_language
    
    def config_text(self, text: str):
        """Update the button text"""
        self.config(text=text)