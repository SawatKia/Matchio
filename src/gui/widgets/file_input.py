import tkinter as tk
from tkinter import ttk, filedialog
from typing import List, Tuple, Callable, Optional

class FileInput(ttk.Frame):
    """Widget for file selection with optional dropdown for sheets"""
    
    def __init__(self, parent, label_text: str = "Select File:", 
                 file_types: List[Tuple[str, str]] = None,
                 button_text: str = "Browse", row: int = 0,
                 has_dropdown: bool = False, dropdown_label: str = "Select Sheet:",
                 command: Optional[Callable[[str], None]] = None,
                 dropdown_command: Optional[Callable[[str], None]] = None,
                 *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.row = row
        self.command = command
        self.dropdown_command = dropdown_command
        self.file_types = file_types if file_types else [("All Files", "*.*")]
        self.has_dropdown = has_dropdown
        
        # Create label
        self.label = ttk.Label(parent, text=label_text)
        self.label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Create entry field for file path
        self.path_var = tk.StringVar()
        self.entry = ttk.Entry(parent, textvariable=self.path_var, width=50)
        self.entry.grid(row=row, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Create browse button
        self.browse_button = ttk.Button(parent, text=button_text, command=self._browse_file)
        self.browse_button.grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Create dropdown for sheet selection if needed
        if has_dropdown:
            self.dropdown_label = ttk.Label(parent, text=dropdown_label)
            self.dropdown_label.grid(row=row+1, column=0, sticky=tk.W, padx=5, pady=2)
            
            self.dropdown_var = tk.StringVar()
            self.dropdown = ttk.Combobox(parent, textvariable=self.dropdown_var, state="readonly", width=30)
            self.dropdown.grid(row=row+1, column=1, sticky=tk.W, padx=5, pady=2)
            self.dropdown.bind("<<ComboboxSelected>>", self._on_dropdown_select)
    
    def _browse_file(self):
        """Open file dialog and update path"""
        file_path = filedialog.askopenfilename(filetypes=self.file_types)
        if file_path:
            self.path_var.set(file_path)
            if self.command:
                self.command(file_path)
    
    def _on_dropdown_select(self, event):
        """Handle dropdown selection"""
        if self.dropdown_command:
            self.dropdown_command(self.dropdown_var.get())
    
    def update_dropdown_values(self, values: List[str]):
        """Update the dropdown with new values"""
        if self.has_dropdown:
            self.dropdown["values"] = values
            if values and not self.dropdown_var.get():
                self.dropdown.current(0)
                if self.dropdown_command:
                    self.dropdown_command(self.dropdown_var.get())
    
    def update_texts(self, label_text: Optional[str] = None, 
                    button_text: Optional[str] = None,
                    dropdown_label: Optional[str] = None):
        """Update widget texts for language change"""
        if label_text:
            self.label.config(text=label_text)
        
        if button_text:
            self.browse_button.config(text=button_text)
        
        if dropdown_label and self.has_dropdown:
            self.dropdown_label.config(text=dropdown_label)