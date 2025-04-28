import tkinter as tk
from tkinter import ttk
import time
from datetime import datetime

class LogViewer(ttk.Frame):
    """Widget to display log messages"""
    
    def __init__(self, parent, max_lines: int = 1000, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.max_lines = max_lines
        self.line_count = 0
        
        # Create text widget with scrollbar
        self.text = tk.Text(self, wrap=tk.WORD, height=10, width=50)
        self.scrollbar = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack widgets
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure text widget
        self.text.config(state=tk.DISABLED)
    
    def add_message(self, message: str, add_timestamp: bool = True):
        """Add a message to the log viewer"""
        self.text.config(state=tk.NORMAL)
        
        # Add timestamp if requested
        if add_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            full_message = f"[{timestamp}] {message}\n"
        else:
            full_message = f"{message}\n"
        
        # Add message
        self.text.insert(tk.END, full_message)
        
        # Increment line count
        self.line_count += 1
        
        # Remove old lines if over max_lines
        if self.line_count > self.max_lines:
            self.text.delete("1.0", "2.0")
            self.line_count -= 1
        
        # Scroll to end
        self.text.see(tk.END)
        
        # Disable text widget again
        self.text.config(state=tk.DISABLED)
    
    def clear(self):
        """Clear all log messages"""
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.config(state=tk.DISABLED)
        self.line_count = 0
    
    def update_theme(self, bg, fg):
        """Update the theme colors for the log viewer"""
        self.text_widget.config(
            background=bg,
            foreground=fg
        )
        
        # Update scrollbar if needed
        if hasattr(self, 'scrollbar'):
            # Scrollbar styling might need to be handled by the ttk.Style in main window
            pass