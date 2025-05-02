# src\gui\main_window.py
import threading
import time
import os
import webbrowser
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tkinter import ttk, filedialog, messagebox, font
import tkinter as tk
from utils import get_logger, FileManager, CONFIG
from .constants import MatchingConstants
from .translation import TranslationManager

logger = get_logger()

class ApplicationGUI(tk.Tk):
    def __init__(self, app_instance=None):
        super().__init__()
        
        self.app = app_instance
        self.report_dfs = None
        self.processing_thread = None
        self.language = tk.StringVar(value="th")
        self.sheet_vars = {}
        self.constant_vars = {}
        self.start_time = None
        self.is_processing = False
        self.current_step = 0
        self.total_steps = 2  # Cleaning and matching steps
        self.avg_times = {'cleaning': 0, 'matching': 0}
        # FIXME - get the actual statement length
        self.total_items = {'cleaning': 4, 'matching': 605}  # 4 files , 605 statement to clean 100% matching progress
        self.processed_items = {'cleaning': 0, 'matching': 0}
        
        # Configure the main window
        self.title(TranslationManager.get_translation(self.language.get(), "window_title"))
        self.geometry("900x700")
        
        # Set default font
        self.default_font = font.nametofont("TkDefaultFont")
        self.font_size = tk.IntVar(value=11)
        self.update_font_size()
        
        # Create main frame with notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.files_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.process_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.files_tab, text=TranslationManager.get_translation(self.language.get(), "files_tab"))
        self.notebook.add(self.settings_tab, text=TranslationManager.get_translation(self.language.get(), "settings_tab"))
        self.notebook.add(self.process_tab, text=TranslationManager.get_translation(self.language.get(), "process_tab"))
        
        # Create and configure UI elements
        self._create_file_inputs()
        self._create_settings_panel()
        self._create_processing_panel()
        self._create_status_bar()

        # Bind language change to update UI
        self.language.trace_add("write", self._update_all_text)
        
        logger.info("GUI initialized")
    

    def _update_all_text(self, *args):
        """Update all text elements in the UI based on current language"""
        lang = self.language.get()
        
        # Update window title
        self.title(TranslationManager.get_translation(lang, "window_title"))
        
        # Update tab names
        self.notebook.tab(0, text=TranslationManager.get_translation(lang, "files_tab"))
        self.notebook.tab(1, text=TranslationManager.get_translation(lang, "settings_tab"))
        self.notebook.tab(2, text=TranslationManager.get_translation(lang, "process_tab"))
        
        # Update file input labels
        if hasattr(self, 'files_tab'):
            for widget in self.files_tab.winfo_children():
                if isinstance(widget, ttk.LabelFrame):
                    widget.configure(text=TranslationManager.get_translation(lang, "input_files"))
                    
        # Update all buttons
        if hasattr(self, 'process_button'):
            self.process_button.config(text=TranslationManager.get_translation(lang, "start_processing"))
        if hasattr(self, 'exit_button'):
            self.exit_button.config(text=TranslationManager.get_translation(lang, "exit"))
        if hasattr(self, 'browse_file_button'):
            self.browse_file_button.config(text=TranslationManager.get_translation(lang, "browse"))
        if hasattr(self, 'open_dir_button'):
            self.open_dir_button.config(text=TranslationManager.get_translation(lang, "open"))
        if hasattr(self, 'reset_button'):
            self.reset_button.config(text=TranslationManager.get_translation(lang, "reset"))
        if hasattr(self, 'copy_button'):
            self.copy_button.config(text=TranslationManager.get_translation(lang, "copy_clipboard"))
        
        
        self.font_frame.configure(text=TranslationManager.get_translation(lang, "font_size"))
        
        # Update matching parameters labels
        if hasattr(self, 'constant_widgets'):
            self.constant_widgets['frame'].configure(text=TranslationManager.get_translation(lang, "matching_params"))
            self.constant_widgets['credit_label'].configure(text=TranslationManager.get_translation(lang, "credit_days"))
            self.constant_widgets['sale_tolerance_label'].configure(text=TranslationManager.get_translation(lang, "sale_tolerance"))
            self.constant_widgets['purchase_tolerance_label'].configure(text=TranslationManager.get_translation(lang, "purchase_tolerance"))
            self.constant_widgets['reset_button'].configure(text=TranslationManager.get_translation(lang, "reset"))

        
        # Update file input fields
        self._update_file_labels(lang)
        
        # Update status area labels
        if hasattr(self, 'process_tab'):
            for widget in self.process_tab.winfo_children():
                if isinstance(widget, ttk.LabelFrame):
                    widget.configure(text=TranslationManager.get_translation(lang, "status"))
        
        # Update timing info
        self.elapsed_var.set(TranslationManager.get_translation(lang, "elapsed") + " --:--:--")
        self.eta_var.set(TranslationManager.get_translation(lang, "eta") + " --:--:--")
        self.items_var.set(TranslationManager.get_translation(lang, "items") + " 0/0")
        
        # Update status bar
        self.status_bar.config(text=TranslationManager.get_translation(lang, "ready"))

    def _update_file_labels(self, lang):
        """Update file input field labels with translated text"""
        file_labels = [
            ("csv_exported_purchase_tax_report", "purchase_tax"),
            ("csv_exported_sales_tax_report", "sales_tax"),
            ("excel_Withholding_tax_report", "withholding_tax"),
            ("excel_statement", "bank_statement"),
            ("output_dir", "output_dir")
        ]
        
        # Find file input frame
        for widget in self.files_tab.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Frame):
                        for i, (key, label_key) in enumerate(file_labels):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Frame) and grandchild.grid_info().get('row') == i:
                                    for label in grandchild.winfo_children():
                                        if isinstance(label, ttk.Label) and not "sheet" in label.cget("text").lower():
                                            label.configure(text=TranslationManager.get_translation(lang, label_key))
                                        elif isinstance(label, ttk.Label) and "sheet" in label.cget("text").lower():
                                            label.configure(text=TranslationManager.get_translation(lang, "sheet"))

    def _update_language(self):
        """Update the UI language based on the selected language"""
        lang = self.language.get()
        logger.info(f"Language switched to: {lang}")
        self._update_all_text()

    def _create_file_inputs(self):
        """Create the file input section"""
        file_frame = ttk.LabelFrame(self.files_tab, text=TranslationManager.get_translation(self.language.get(), "input_files"))
        file_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Language toggle
        lang_frame = ttk.Frame(file_frame)
        lang_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(lang_frame, text=TranslationManager.get_translation(self.language.get(), "language")).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(lang_frame, text=TranslationManager.get_translation(self.language.get(), "thai"), variable=self.language, value="th", 
                        command=self._update_language).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(lang_frame, text=TranslationManager.get_translation(self.language.get(), "english"), variable=self.language, value="en", 
                        command=self._update_language).pack(side=tk.LEFT, padx=5)
        
        # File input container
        input_frame = ttk.Frame(file_frame)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Purchase Tax Report
        self._create_file_input_row(input_frame, TranslationManager.get_translation(self.language.get(), "purchase_tax"), "csv_exported_purchase_tax_report", 0)
        
        # Sales Tax Report
        self._create_file_input_row(input_frame, TranslationManager.get_translation(self.language.get(), "sales_tax"), "csv_exported_sales_tax_report", 1)
        
        # Withholding Tax Report
        self._create_file_input_row(input_frame, TranslationManager.get_translation(self.language.get(), "withholding_tax"), "excel_Withholding_tax_report", 2, is_excel=True)
        
        # Bank Statement
        self._create_file_input_row(input_frame, TranslationManager.get_translation(self.language.get(), "bank_statement"), "excel_statement", 3, is_excel=True)
        
        # Output Directory
        self._create_dir_input_row(input_frame, TranslationManager.get_translation(self.language.get(), "output_dir"), "output_dir", 4)

    def _create_settings_panel(self):
        """Create the settings panel"""
        # Font size control
        self.font_frame = ttk.LabelFrame(self.settings_tab, text=TranslationManager.get_translation(self.language.get(), "font_size"))
        self.font_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(self.font_frame, text="−", width=3, 
                  command=lambda: self.change_font_size(-1)).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(self.font_frame, textvariable=self.font_size).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(self.font_frame, text="+", width=3,
                  command=lambda: self.change_font_size(1)).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Create matching constants panel
        constants_result = MatchingConstants.create_config_panel(self.settings_tab, CONFIG, self.language.get())
        self.constant_vars = constants_result['variables']
        self.constant_widgets = constants_result['widgets']

    def _create_processing_panel(self):
        """Create the processing panel"""
        controls_frame = ttk.Frame(self.process_tab)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Start processing button
        self.process_button = ttk.Button(
            controls_frame, 
            text=TranslationManager.get_translation(self.language.get(), "start_processing"),
            command=self._start_full_process
        )
        self.process_button.pack(side=tk.LEFT, padx=5)
        
        # Open output directory button
        self.open_dir_button = ttk.Button(
            controls_frame, 
            text=TranslationManager.get_translation(self.language.get(), "open_output"),
            command=self._open_output_directory
        )
        self.open_dir_button.pack(side=tk.LEFT, padx=5)
        
        # Exit button
        self.exit_button = ttk.Button(
            controls_frame, 
            text=TranslationManager.get_translation(self.language.get(), "exit"),
            command=self.quit
        )
        self.exit_button.pack(side=tk.RIGHT, padx=5)
        
        # Create status display area
        self._create_status_area()

    def _create_status_area(self):
        """Create status display area"""
        status_frame = ttk.LabelFrame(self.process_tab, text=TranslationManager.get_translation(self.language.get(), "status"))
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Progress frame
        progress_frame = ttk.Frame(status_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Progress indicator (Spinner)
        self.spinner_label = ttk.Label(progress_frame, text="")  # Start empty
        self.spinner_label.pack(side=tk.LEFT, padx=5)
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]  # More standard spinner
        self.spinner_idx = 0
        
        # Progress bar
        self.progress = ttk.Progressbar(progress_frame, mode="determinate", length=300)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Progress percentage
        self.progress_var = tk.StringVar(value="0%")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.pack(side=tk.RIGHT, padx=5)
        
        # Timing information
        self.timing_frame = ttk.Frame(status_frame)
        self.timing_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Elapsed time
        self.elapsed_var = tk.StringVar(value=TranslationManager.get_translation(self.language.get(), "elapsed") + " --:--:--")
        ttk.Label(self.timing_frame, textvariable=self.elapsed_var).pack(side=tk.LEFT, padx=5)
        
        # ETA
        self.eta_var = tk.StringVar(value=TranslationManager.get_translation(self.language.get(), "eta") + " --:--:--")
        ttk.Label(self.timing_frame, textvariable=self.eta_var).pack(side=tk.LEFT, padx=5)
        
        # Average time
        self.avg_time_var = tk.StringVar(value=TranslationManager.get_translation(self.language.get(), "avg_time", "--:--:--"))
        ttk.Label(self.timing_frame, textvariable=self.avg_time_var).pack(side=tk.LEFT, padx=5)
        
        # Items progress
        self.items_var = tk.StringVar(value=TranslationManager.get_translation(self.language.get(), "items_processed", "0", "0"))
        ttk.Label(self.timing_frame, textvariable=self.items_var).pack(side=tk.RIGHT, padx=5)
        
        # Status text display
        self.status_text = tk.Text(status_frame, height=15, width=80)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        # Make text read-only
        self.status_text.config(state=tk.DISABLED)

    def _create_status_bar(self):
        """Create status bar at bottom of window"""
        self.status_bar = ttk.Label(self, text=TranslationManager.get_translation(self.language.get(), "ready"), relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_file_input_row(self, parent, label_text, config_key, row, is_excel=False):
        """Create a row with label, entry field and browse button for file selection"""
        row_frame = ttk.Frame(parent)
        row_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        parent.columnconfigure(0, weight=1)
        
        ttk.Label(row_frame, text=label_text).pack(side=tk.LEFT, padx=5)
        
        # Create StringVar and entry to display the file path
        var = tk.StringVar(value=CONFIG.get(config_key, ""))
        entry = ttk.Entry(row_frame, textvariable=var, width=50)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Store the var and entry in instance variables for later access
        setattr(self, f"{config_key}_var", var)
        setattr(self, f"{config_key}_entry", entry)
        
        # Create browse button
        self.browse_file_button = ttk.Button(
            row_frame, 
            text=TranslationManager.get_translation(self.language.get(), "browse"), 
            command=lambda: self._browse_file(var, config_key, is_excel)
        )
        self.browse_file_button.pack(side=tk.LEFT, padx=5)
        
        # If Excel file, add sheet selector
        if is_excel:
            self._add_sheet_selector(row_frame, config_key)

    def _add_sheet_selector(self, parent, config_key):
        """Add a sheet selector dropdown for Excel files"""
        sheet_frame = ttk.Frame(parent)
        sheet_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(sheet_frame, text=TranslationManager.get_translation(self.language.get(), "sheet")).pack(side=tk.LEFT, padx=2)
        
        # Create combobox for sheet selection
        sheet_var = tk.StringVar()
        sheet_combo = ttk.Combobox(sheet_frame, textvariable=sheet_var, width=15, state="readonly")
        sheet_combo.pack(side=tk.LEFT, padx=2)
        
        # Store references
        sheet_key = f"{config_key}_sheet"
        self.sheet_vars[config_key] = {
            'var': sheet_var,
            'combo': sheet_combo
        }
        
        # Update sheet list when file path changes
        getattr(self, f"{config_key}_var").trace_add("write", 
            lambda *args, key=config_key: self._update_sheet_list(key))

    def _create_dir_input_row(self, parent, label_text, config_key, row):
        """Create a row with label, entry field and browse button for directory selection"""
        row_frame = ttk.Frame(parent)
        row_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        
        ttk.Label(row_frame, text=label_text).pack(side=tk.LEFT, padx=5)
        
        # Create StringVar and entry to display the directory path
        var = tk.StringVar(value=CONFIG.get(config_key, ""))
        entry = ttk.Entry(row_frame, textvariable=var, width=50)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Store the var and entry in instance variables for later access
        setattr(self, f"{config_key}_var", var)
        setattr(self, f"{config_key}_entry", entry)
        
        # Create browse button
        self.browse_dir_button = ttk.Button(
            row_frame, 
            text=TranslationManager.get_translation(self.language.get(), "browse"), 
            command=lambda: self._browse_directory(var, config_key)
        )
        self.browse_dir_button.pack(side=tk.LEFT, padx=5)
        
        # Add open directory button
        open_button = ttk.Button(
            row_frame,
            text=TranslationManager.get_translation(self.language.get(), "open"),
            command=lambda: self._open_directory(var.get())
        )
        open_button.pack(side=tk.LEFT, padx=5)

    def _browse_file(self, stringvar, config_key, is_excel=False):
        """Open file browser dialog and update both the entry field and CONFIG"""
        if is_excel:
            filetypes = [
                ("Excel Files", "*.xlsx;*.xls"),
                ("All Files", "*.*")
            ]
        else:
            filetypes = [
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ]
        
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            stringvar.set(filename)
            CONFIG[config_key] = filename
            logger.info(f"Set {config_key} to {filename}")
            
            # If Excel, update sheet list
            if is_excel and filename:
                self._update_sheet_list(config_key)

    def _update_sheet_list(self, config_key):
        """Update sheet list for Excel files"""
        if config_key not in self.sheet_vars:
            return
            
        file_path = getattr(self, f"{config_key}_var").get()
        sheet_info = self.sheet_vars[config_key]
        
        if not file_path or not os.path.exists(file_path):
            sheet_info['combo']['values'] = []
            sheet_info['var'].set("")
            return
            
        try:
            # Get sheet names
            sheets = FileManager.list_excel_sheets(file_path)
            
            if sheets:
                sheet_info['combo']['values'] = sheets
                
                # If there's a sheet name stored in CONFIG, use it
                sheet_key = f"{config_key}_sheet"
                if sheet_key in CONFIG and CONFIG[sheet_key] in sheets:
                    sheet_info['var'].set(CONFIG[sheet_key])
                else:
                    # Otherwise select the first sheet
                    sheet_info['var'].set(sheets[0])
                    CONFIG[sheet_key] = sheets[0]
            else:
                sheet_info['combo']['values'] = []
                sheet_info['var'].set("")
        except Exception as e:
            logger.error(f"Error listing Excel sheets: {e}")
            self._show_error(f"Error listing Excel sheets: {str(e)}", is_developer=True)

    def _browse_directory(self, stringvar, config_key):
        """Open directory browser dialog and update both the entry field and CONFIG"""
        directory = filedialog.askdirectory()
        if directory:
            stringvar.set(directory)
            CONFIG[config_key] = directory
            logger.info(f"Set {config_key} to {directory}")

    def _open_directory(self, directory_path):
        """Open the specified directory in file explorer"""
        if directory_path and os.path.exists(directory_path):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(directory_path)
                elif os.name == 'posix':  # macOS and Linux
                    webbrowser.open(f'file://{directory_path}')
            except Exception as e:
                self._show_error(f"Error opening directory: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Directory does not exist")

    def _open_output_directory(self):
        """Open the output directory in file explorer"""
        output_dir = CONFIG.get('output_dir', '')
        if not output_dir:
            messagebox.showwarning("Warning", "Output directory not specified")
            return
            
        self._open_directory(output_dir)

    def change_font_size(self, delta):
        """Change the font size by the given delta"""
        new_size = self.font_size.get() + delta
        if 7 <= new_size <= 20:  # Reasonable font size limits
            self.font_size.set(new_size)
            self.update_font_size()

    def update_font_size(self):
        """Update the application font size"""
        size = self.font_size.get()
        default_font = font.nametofont("TkDefaultFont")
        text_font = font.nametofont("TkTextFont")
        fixed_font = font.nametofont("TkFixedFont")
        
        default_font.configure(size=size)
        text_font.configure(size=size)
        fixed_font.configure(size=size)
        
        # Update status text font
        if hasattr(self, 'status_text'):
            self.status_text.configure(font=('TkTextFont', size))

    def _validate_input_files(self):
        """Validate that all required input files are specified"""
        missing_files = []
        
        # Check required files
        required_files = [
            ('csv_exported_purchase_tax_report', TranslationManager.get_translation(self.language.get(), "purchase_tax")),
            ('csv_exported_sales_tax_report', TranslationManager.get_translation(self.language.get(), "sales_tax")),
            ('excel_Withholding_tax_report', TranslationManager.get_translation(self.language.get(), "withholding_tax")),
            ('excel_statement', TranslationManager.get_translation(self.language.get(), "bank_statement"))
        ]
        
        for key, label in required_files:
            file_path = getattr(self, f"{key}_var").get()
            if not file_path or not os.path.exists(file_path):
                missing_files.append(label)
        
        # Check output directory
        output_dir = getattr(self, "output_dir_var").get()
        if not output_dir:
            missing_files.append(TranslationManager.get_translation(self.language.get(), "output_dir"))
        
        if missing_files:
            message = TranslationManager.get_translation(self.language.get(), "missing_files") + "\n- " + "\n- ".join(missing_files)
            messagebox.showerror(TranslationManager.get_translation(self.language.get(), "error"), message)
            self._update_status(message)
            return False
            
        return True

    def _update_config_from_gui(self):
        """Update CONFIG dictionary from GUI input fields"""
        # Update file paths
        for key in [
            'csv_exported_purchase_tax_report',
            'csv_exported_sales_tax_report',
            'excel_Withholding_tax_report',
            'excel_statement',
            'output_dir'
        ]:
            var = getattr(self, f"{key}_var", None)
            if var:
                CONFIG[key] = var.get()
        
        # Update Excel sheet selections
        for config_key, sheet_info in self.sheet_vars.items():
            sheet_key = f"{config_key}_sheet"
            CONFIG[sheet_key] = sheet_info['var'].get()
        
        # Update matching constants
        for key, var in self.constant_vars.items():
            CONFIG[key] = var.get()

    def _update_status(self, message):
        """Update the status text area with a new message"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)  # Auto-scroll to the end
        self.status_text.config(state=tk.DISABLED)
        self.update_idletasks()  # Force GUI update
        
        # Also update status bar
        self.status_bar.config(text=message)

    def _update_progress_spinner(self):
        """Update the progress spinner animation"""
        if self.is_processing:
            self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
            self.spinner_label.config(text=self.spinner_chars[self.spinner_idx])
            self.after(100, self._update_progress_spinner)  # Make animation faster for better visual feedback

    def _update_progress(self, step, progress):
        """Update progress bar and percentage"""
        if step == 0:  # Cleaning step
            self.processed_items['cleaning'] = progress
            self.progress["value"] = (progress / self.total_items['cleaning']) * 50  # Cleaning is 50% of total
            self.progress_var.set(f"{int((progress / self.total_items['cleaning']) * 50)}%")
            self._update_status(TranslationManager.get_translation(self.language.get(), "cleaning_progress", progress))
        else:  # Matching step
            self.processed_items['matching'] = progress
            self.progress["value"] = 50 + (progress * 0.5)  # Matching is 50% of total
            self.progress_var.set(f"{50 + int(progress * 0.5)}%")
            self._update_status(TranslationManager.get_translation(self.language.get(), "matching_progress", progress))
        
        # Update items processed
        total_processed = self.processed_items['cleaning'] + self.processed_items['matching']
        total_items = self.total_items['cleaning'] + self.total_items['matching']
        self.items_var.set(TranslationManager.get_translation(self.language.get(), "items_processed", f"{total_processed}", f"{total_items}"))
        
        # Update ETA
        self._update_eta(step)
    
    def _update_eta(self, step):
        """Update estimated time of arrival"""
        if not self.start_time:
            return
            
        elapsed = time.time() - self.start_time
        
        # Calculate progress percentage (0-1)
        if step == 0:  # Cleaning
            progress_pct = self.processed_items['cleaning'] / self.total_items['cleaning']
            step_progress = progress_pct * 0.5  # Cleaning is 50% of total
        else:  # Matching
            progress_pct = self.processed_items['matching'] / 100
            step_progress = 0.5 + (progress_pct * 0.5)  # Matching is 50% of total
        
        # Avoid division by zero
        if step_progress > 0.01:
            # Calculate total estimated time based on current progress
            total_estimated = elapsed / step_progress
            remaining = max(0, total_estimated - elapsed)
            
            # Format times
            hours, remainder = divmod(int(remaining), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.eta_var.set(f"{TranslationManager.get_translation(self.language.get(), 'eta')} {hours:02}:{minutes:02}:{seconds:02}")
            
            # Calculate and update average time per percent
            avg_time = elapsed / (step_progress * 100)  # time per percent
            self.avg_times[step] = avg_time  # Store for future reference
            
            total_avg = sum(self.avg_times.values()) / len([t for t in self.avg_times.values() if t > 0])
            self.avg_time_var.set(f"{TranslationManager.get_translation(self.language.get(), 'avg_time')} {total_avg:.2f}s/item")

    def _update_elapsed_time(self):
        """Update the elapsed time display"""
        if self.is_processing and self.start_time:
            elapsed = time.time() - self.start_time
            hours, remainder = divmod(int(elapsed), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            self.elapsed_var.set(f"{TranslationManager.get_translation(self.language.get(), 'elapsed')} {hours:02}:{minutes:02}:{seconds:02}")
            self.after(1000, self._update_elapsed_time)

    def _start_full_process(self):
        """Start the entire processing workflow"""
        if not self._validate_input_files():
            return
            
        # Update GUI state
        self._update_status(TranslationManager.get_translation(self.language.get(), "processing"))
        self.process_button.config(state=tk.DISABLED)
        self.progress["value"] = 0
        self.progress.config(mode="determinate")  # Use determinate mode for precise progress
        self.progress_var.set("0%")
        self.is_processing = True
        self.start_time = time.time()
        self.current_step = 0
        self.processed_items = {'cleaning': 0, 'matching': 0}
        self.avg_times = {'cleaning': 0, 'matching': 0}
        
        # Start progress updates
        self._update_progress_spinner()
        self._update_elapsed_time()
        
        # Run processing in a separate thread
        def process_thread():
            try:
                # Update CONFIG from GUI before processing
                self._update_config_from_gui()
                
                # Initialize services
                self.after(0, lambda: self._update_status("Initializing services..."))
                self.app.initialize_services()
                
                # Process reports (cleaning step)
                cleaning_start = time.time()
                self.after(0, lambda: self._update_status("Processing report files..."))
                
                # Process each file individually with progress updates
                files = [
                    'csv_exported_purchase_tax_report',
                    'csv_exported_sales_tax_report', 
                    'excel_Withholding_tax_report', 
                    'excel_statement'
                ]
                
                for i, file_key in enumerate(files, 1):
                    file_path = CONFIG.get(file_key, "")
                    file_name = os.path.basename(file_path)
                    self.after(0, lambda msg=f"Processing {file_name}...": self._update_status(msg))
                    
                    # Here we'd actually process the file - for now just update progress
                    time.sleep(0.5)  # Simulate file processing
                    self.after(0, lambda i=i: self._update_progress(0, i))
                
                # Call the actual processing method
                self.app.process_report_files()
                cleaning_time = time.time() - cleaning_start
                self.avg_times['cleaning'] = cleaning_time / 4  # Average time per file
                
                # Perform matching (matching step)
                matching_start = time.time()
                self.current_step = 1
                self.after(0, lambda: self._update_status("Performing transaction matching..."))
                
                # Simulate progressive matching updates at 5% intervals
                total_iterations = 20  # 5% increments
                for i in range(1, total_iterations + 1):
                    progress = i * 5
                    time.sleep(0.1)  # Simulate processing time
                    self.after(0, lambda p=progress: self._update_progress(1, p))
                    self.after(0, lambda p=progress: self._update_status(
                        f"Matching transactions: {p}% complete - Processing items..."
                    ))
                
                # Actual matching call
                report_dfs = self.app.perform_matching_and_generate_reports()
                self.report_dfs = report_dfs
                matching_time = time.time() - matching_start
                self.avg_times['matching'] = matching_time / 100  # Time per percent
                
                # Save reports
                self.after(0, lambda: self._update_status("Saving reports..."))
                self.app.save_reports(report_dfs)
                
                # Final status update
                output_dir = CONFIG.get('output_dir', '')
                complete_msg = TranslationManager.get_translation(self.language.get(), "processing_complete", output_dir)
                self.after(0, lambda: self._update_status(complete_msg))
                self.after(0, lambda: self.status_bar.config(
                    text=TranslationManager.get_translation(self.language.get(), "complete")
                ))
                self.after(0, lambda: messagebox.showinfo(
                    TranslationManager.get_translation(self.language.get(), "success"), 
                    complete_msg
                ))
                
            except Exception as e:
                logger.error(f"Error in processing: {e}")
                self.after(0, lambda: self._show_error(f"Error during processing: {str(e)}", is_developer=True))
                
            finally:
                # Update GUI on completion
                self.after(0, self._process_complete)
                
        # Start the thread
        self.processing_thread = threading.Thread(target=process_thread, daemon=True)
        self.processing_thread.start()

    def _process_complete(self):
        """Reset GUI state after processing completes"""
        self.is_processing = False
        self.process_button.config(state=tk.NORMAL)
        self.progress.stop()
        
        # Final timing update
        if self.start_time:
            elapsed = time.time() - self.start_time
            hours, remainder = divmod(int(elapsed), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.elapsed_var.set(f"Total time: {hours:02}:{minutes:02}:{seconds:02}")
            self.eta_var.set("Complete")

    def _show_error(self, message, is_developer=False):
        """Show error message with appropriate detail level"""
        lang = self.language.get()
        
        if is_developer:
            # For developer: detailed error with stack trace
            error_text = f"Error: {message}\n\n"
            error_text += traceback.format_exc()
            
            # Create detailed error dialog
            error_dialog = tk.Toplevel(self)
            error_dialog.title(TranslationManager.get_translation(lang, "developer_error"))
            error_dialog.geometry("800x400")
            
            # Error text widget with scrollbar
            error_frame = ttk.Frame(error_dialog)
            error_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            error_text_widget = tk.Text(error_frame, wrap=tk.WORD)
            error_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar = ttk.Scrollbar(error_frame, command=error_text_widget.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            error_text_widget.config(yscrollcommand=scrollbar.set)
            
            error_text_widget.insert(tk.END, error_text)
            error_text_widget.config(state=tk.DISABLED)
            
            # Copy to clipboard button
            self.copy_button = ttk.Button(
                error_dialog, 
                text="Copy to Clipboard",
                command=lambda: self.clipboard_clear() or self.clipboard_append(error_text)
            )
            self.copy_button.pack(pady=5)
            
            # Also log to status text
            self._update_status(f"Error: {message}")
        else:
            # For user: simple error message
            messagebox.showerror(TranslationManager.get_translation(lang, "error"), message)
            self._update_status(f"Error: {message}")
            
        # Update GUI state
        self.is_processing = False
        self.process_button.config(state=tk.NORMAL)
        self.progress.stop()