import tkinter as tk
from tkinter import ttk, filedialog
from typing import Callable, Optional

class DirectoryInput(ttk.Frame):
    """Widget for directory selection"""
    
    def __init__(self, parent, label_text: str = "Select Directory:", 
                 button_text: str = "Browse", row: int = 0,
                 command: Optional[Callable[[str], None]] = None,
                 *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.row = row
        self.command = command
        
        # Create label
        self.label = ttk.Label(parent, text=label_text)
        self.label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Create entry field for directory path
        self.path_var = tk.StringVar()
        self.entry = ttk.Entry(parent, textvariable=self.path_var, width=50)
        self.entry.grid(row=row, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Create browse button
        self.browse_button = ttk.Button(parent, text=button_text, command=self._browse_directory)
        self.browse_button.grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
    
    def _browse_directory(self):
        """Open directory dialog and update path"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.path_var.set(dir_path)
            if self.command:
                self.command(dir_path)
    
    def update_texts(self, label_text: Optional[str] = None, button_text: Optional[str] = None):
        """Update widget texts for language change"""
        if label_text:
            self.label.config(text=label_text)
        
        if button_text:
            self.browse_button.config(text=button_text)