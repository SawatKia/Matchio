# src\gui\main_window.py
import threading
import time
import os
import webbrowser
import traceback
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, font
import tkinter as tk

from utils import get_logger, FileManager, CONFIG
from .constants import MatchingConstants
from .translation import TranslationManager

logger = get_logger()

class ApplicationGUI(tk.Tk):
    def __init__(self, app_instance=None):
        super().__init__()

        try:
            icon_path = Path(__file__).parent.parent.parent / "icon" / "finished-icon.ico"
            self.iconbitmap(icon_path)
        except Exception as e:
            logger.warning(f"Could not load application icon: {e}")

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
        
        # Initialize with default values
        self.total_items = {'cleaning': 4, 'matching': 0}  # 4 files, will update matching later
        self.processed_items = {'cleaning': 0, 'matching': 0}

        # Dictionary to store all widgets that need language updates
        self.widgets = {
            'labels': {},
            'buttons': {},
            'frames': {},
            'tabs': {}
        }
        
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
        self._register_widget(0, 'tabs', 'files_tab')  # Register tab by index
        
        self.notebook.add(self.settings_tab, text=TranslationManager.get_translation(self.language.get(), "settings_tab"))
        self._register_widget(1, 'tabs', 'settings_tab')
        
        self.notebook.add(self.process_tab, text=TranslationManager.get_translation(self.language.get(), "process_tab"))
        self._register_widget(2, 'tabs', 'process_tab')
        
        # Create and configure UI elements
        self._create_file_inputs_panel()
        self._create_settings_panel()
        self._create_processing_panel()
        self._create_status_bar()

        # Bind language change to update UI
        self.language.trace_add("write", self._update_all_text)
        
        logger.info("GUI initialized")
    
    # NOTE - language ui
    def _update_all_text(self, *args):
        """Update all text elements in the UI based on current language"""
        lang = self.language.get()
        
        # Update window title
        try:
            logger.info("updating window title")
            self.title(TranslationManager.get_translation(lang, "window_title"))
        except Exception as e:
            logger.error(f"Error updating window title: {e}")
        
        # Update all registered widgets
        for widget_type, widgets in self.widgets.items():
            for key, widget_info in widgets.items():
                try:
                    widget = widget_info['widget']
                    translation_key = widget_info['key']
                    
                    translated_text = TranslationManager.get_translation(lang, translation_key, widget_info['default'])
                    
                    if widget_type == 'labels':
                        logger.debug("updating labels lang by loop through self.widgets")
                        widget.configure(text=translated_text)
                    elif widget_type == 'buttons':
                        logger.debug("updating buttons lang by loop through self.widgets")
                        widget.configure(text=translated_text)
                    elif widget_type == 'frames':
                        logger.debug("updating frames lang by loop through self.widgets")
                        widget.configure(text=translated_text)
                    elif widget_type == 'tabs':
                        logger.debug("updating tabs lang by loop through self.widgets")
                        self.notebook.tab(widget, text=translated_text)
                except Exception as e:
                    logger.error(f"Error updating {key} widget: {e}")
                    logger.error(f"Widget info: {widget_info}")
                    logger.error(f"trace: {traceback.format_exc()}")
        
        # self._update_file_labels(lang)

        # Update status bar
        try:
            self.status_bar.config(text=TranslationManager.get_translation(lang, "ready"))
        except Exception as e:
            logger.error(f"Error updating status bar: {e}")
        
        # Update timing info variables
        try:
            self.elapsed_var.set(TranslationManager.get_translation(lang, "elapsed") + " --:--:--")
            self.eta_var.set(TranslationManager.get_translation(lang, "eta") + " --:--:--")
            self.avg_time_var.set(TranslationManager.get_translation(lang, "avg_time") + " --:--:--")
            self.items_var.set(TranslationManager.get_translation(lang, "items") + " 0/0")
        except Exception as e:
            logger.error(f"Error updating timing info variables: {e}")

    def _update_language(self):
        """Update the UI language based on the selected language"""
        lang = self.language.get()
        logger.info(f"Language switched to: {lang}")
        self._update_all_text()

    # NOTE - 3 panels ui
    def _create_file_inputs_panel(self):
        """Create the file input section"""

        file_frame = ttk.LabelFrame(self.files_tab, text=TranslationManager.get_translation(self.language.get(), "input_files"))
        self._register_widget(file_frame, 'frames', 'input_files')
        file_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Language toggle
        lang_frame = ttk.Frame(file_frame)
        lang_frame.pack(fill=tk.X, padx=5, pady=5)
        
        lang_label = ttk.Label(lang_frame, text=TranslationManager.get_translation(self.language.get(), "language"))
        self._register_widget(lang_label, 'labels', 'language')
        lang_label.pack(side=tk.LEFT, padx=5)
        
        thai_radio = ttk.Radiobutton(lang_frame, text=TranslationManager.get_translation(self.language.get(), "thai"), 
                        variable=self.language, value="th", command=self._update_language)
        self._register_widget(thai_radio, 'buttons', 'thai')
        thai_radio.pack(side=tk.LEFT, padx=5)
        
        english_radio = ttk.Radiobutton(lang_frame, text=TranslationManager.get_translation(self.language.get(), "english"), 
                        variable=self.language, value="en", command=self._update_language)
        self._register_widget(english_radio, 'buttons', 'english')
        english_radio.pack(side=tk.LEFT, padx=5)
        
        # File input container
        input_frame = ttk.Frame(file_frame)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Purchase Tax Report
        self._create_file_input_row(input_frame, "purchase_tax", "csv_exported_purchase_tax_report", 0)
        
        # Sales Tax Report
        self._create_file_input_row(input_frame, "sales_tax", "csv_exported_sales_tax_report", 1)
        
        # Withholding Tax Report
        self._create_file_input_row(input_frame, "withholding_tax", "excel_Withholding_tax_report", 2, is_excel=True)
        
        # Bank Statement
        self._create_file_input_row(input_frame, "bank_statement", "excel_statement", 3, is_excel=True)
        
        # Output Directory
        self._create_dir_input_row(input_frame, "output_dir", "output_dir", 4)
        
    def _create_settings_panel(self):
        """Create the settings panel"""
        # Font size control
        self.font_frame = ttk.LabelFrame(self.settings_tab, text=TranslationManager.get_translation(self.language.get(), "font_size"))
        self._register_widget(self.font_frame, 'frames', 'font_size')
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
        
        # Register each widget from constants_result with appropriate type and key
        for widget_key, widget in constants_result['widgets'].items():
            if widget is None:
                continue
                
            if widget_key == 'frame':
                self._register_widget(widget, 'frames', 'matching_params')
            elif widget_key == 'credit_label':
                self._register_widget(widget, 'labels', 'matching_credit_days')
            elif widget_key == 'sale_tolerance_label':
                self._register_widget(widget, 'labels', 'matching_sale_tolerance')
            elif widget_key == 'purchase_tolerance_label':
                self._register_widget(widget, 'labels', 'matching_purchase_tolerance')
            elif widget_key == 'reset_button':
                self._register_widget(widget, 'buttons', 'reset')

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
        self._register_widget(self.process_button, 'buttons', 'start_processing')
        self.process_button.pack(side=tk.LEFT, padx=5)
        
        # Open output directory button
        self.open_dir_button = ttk.Button(
            controls_frame, 
            text=TranslationManager.get_translation(self.language.get(), "open_output"),
            command=self._open_output_directory
        )
        self._register_widget(self.open_dir_button, 'buttons', 'open_output')
        self.open_dir_button.pack(side=tk.LEFT, padx=5)
        
        # Exit button
        self.exit_button = ttk.Button(
            controls_frame, 
            text=TranslationManager.get_translation(self.language.get(), "exit"),
            command=self.quit
        )
        self._register_widget(self.exit_button, 'buttons', 'exit')
        self.exit_button.pack(side=tk.RIGHT, padx=5)
        
        # Create status display area
        self._create_status_area()

    # NOTE - all widgets
    def _register_widget(self, widget, widget_type, key, instance_id=None, default_text=""):
        """Register a widget for language updates
        
        Args:
            widget: The widget instance
            widget_type: Type of widget ('labels', 'buttons', 'frames', 'tabs')
            key: Translation key
            instance_id: Optional unique identifier for this widget instance
            default_text: Default text if translation is not found
        """
        if widget_type not in self.widgets:
            self.widgets[widget_type] = {}
        
        # Create a unique key for the widget in the dictionary
        # If instance_id is provided, use it to create a unique dictionary key
        dict_key = f"{key}_{instance_id}" if instance_id is not None else key
        
        logger.debug(f"Registering {widget_type} widget: {dict_key} with translation key: {key}")
        self.widgets[widget_type][dict_key] = {
            'widget': widget,
            'key': key,  # This is the translation key
            'default': default_text
        }
        
        return widget

    # NOTE - file input widgets
    def _create_file_input_row(self, parent, translation_key, config_key, row, is_excel=False):
        """Create a row with label, entry field and browse button for file selection"""
        row_frame = ttk.Frame(parent)
        row_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        parent.columnconfigure(0, weight=1)
        logger.debug(f"Creating file input row for '{translation_key}'+'{config_key}' at row {row}")
        
        input_label = ttk.Label(row_frame, text=TranslationManager.get_translation(self.language.get(), translation_key))
        self._register_widget(input_label, 'labels', translation_key, config_key)
        input_label.pack(side=tk.LEFT, padx=5)
        
        # Create StringVar and entry to display the file path
        var = tk.StringVar(value=CONFIG.get(config_key, ""))
        entry = ttk.Entry(row_frame, textvariable=var, width=50)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Store the var and entry in instance variables for later access
        setattr(self, f"{config_key}_var", var)
        setattr(self, f"{config_key}_entry", entry)
        
        # Create browse button
        browse_file_button = ttk.Button(
            row_frame, 
            text=TranslationManager.get_translation(self.language.get(), "browse_file"), 
            command=lambda: self._browse_file(var, config_key, is_excel)
        )
        self._register_widget(browse_file_button, 'buttons', "browse_file", config_key)
        browse_file_button.pack(side=tk.LEFT, padx=5)
        
        # If Excel file, add sheet selector
        if is_excel:
            self._add_sheet_selector(row_frame, config_key)

    def _add_sheet_selector(self, parent, config_key):
        """Add a sheet selector dropdown for Excel files"""
        sheet_frame = ttk.Frame(parent)
        sheet_frame.pack(side=tk.LEFT, padx=5)
        
        sheet_label =ttk.Label(sheet_frame, text=TranslationManager.get_translation(self.language.get(), "sheet"))
        self._register_widget(sheet_label, 'labels', "sheet", config_key)
        sheet_label.pack(side=tk.LEFT, padx=2)
        
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

    def _create_dir_input_row(self, parent, translation_key, config_key, row):
        """Create a row with label, entry field and browse button for directory selection"""
        row_frame = ttk.Frame(parent)
        row_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        
        label = ttk.Label(row_frame, text=TranslationManager.get_translation(self.language.get(), translation_key))
        self._register_widget(label, 'labels', translation_key, config_key)  # Register the label instead of frame
        label.pack(side=tk.LEFT, padx=5)
        
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
            text=TranslationManager.get_translation(self.language.get(), "browse_dir"), 
            command=lambda: self._browse_directory(var, config_key)
        )
        self._register_widget(self.browse_dir_button, 'buttons', "browse_dir", config_key)
        self.browse_dir_button.pack(side=tk.LEFT, padx=5)
        
        # Add open directory button
        open_button = ttk.Button(
            row_frame,
            text=TranslationManager.get_translation(self.language.get(), "open"),
            command=lambda: self._open_directory(var.get())
        )
        self._register_widget(open_button, 'buttons', "open_dir", config_key)
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
            self._show_error(f"Error listing Excel sheets: {str(e)}")

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

    # NOTE - settings widgets
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

    # NOTE - processing widgets
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
        # FIXME - how many items per sec instead
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

    def _update_status(self, message):
        """Update the status text area with a new message"""
        current_time = time.strftime("%H:%M:%S")  # Get current time in HH:MM:SS format
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"[{current_time}] {message}\n")
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

    # properly handle statement items
    def _update_progress(self, step, progress):
        """
        Update progress bar and percentage
        
        Args:
            step (int): 0 for cleaning, 1 for matching
            progress (int): Number of items processed in this step
        """
        if step == 0:  # Cleaning step
            self.processed_items['cleaning'] = progress
            progress_percent = float((progress / self.total_items['cleaning']) * 50)
            self.progress["value"] = progress_percent  # Cleaning is 50% of total
            self.progress_var.set(f"{progress_percent}%")
        else:  # Matching step
            self.processed_items['matching'] = progress
            
            # Calculate matching progress as percentage of total matching items
            if self.total_items['matching'] > 0:
                matching_percent = float((progress / self.total_items['matching']) * 100)
                progress_value = float(50 + (matching_percent * 0.5))  # Matching is 50% of total
                self.progress["value"] = progress_value
                self.progress_var.set(f"{int(progress_value)}%")
                
            else:
                # Fallback if total_items['matching'] is 0
                progress_value = 50 + (progress * 0.5)  # Use progress directly as percentage
                self.progress["value"] = progress_value
                self.progress_var.set(f"{int(progress_value)}%")
                
                self._update_status(TranslationManager.get_translation(
                    self.language.get(), 
                    "matching_progress", 
                    f"{int(progress_value)}"
                ))
            
        # Update items processed
        total_processed = self.processed_items['cleaning'] + self.processed_items['matching']
        total_items = self.total_items['cleaning'] + self.total_items['matching']
        self.items_var.set(TranslationManager.get_translation(
            self.language.get(), 
            "items_processed", 
            f"{total_processed}", 
            f"{total_items}"
        ))
        
        # Update ETA
        self._update_eta(step)
    
    # calculate progress percentage
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
            if self.total_items['matching'] > 0:
                progress_pct = self.processed_items['matching'] / self.total_items['matching']
            else:
                progress_pct = 0
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
            
            # Calculate and update average time per item
            if step == 0:
                if self.processed_items['cleaning'] > 0:
                    avg_time = elapsed / self.processed_items['cleaning']  # time per file
                    self.avg_times['cleaning'] = avg_time
            else:
                if self.processed_items['matching'] > 0:
                    avg_time = elapsed / self.processed_items['matching']  # time per match
                    self.avg_times['matching'] = avg_time
            
            # Calculate total average across all processed items
            total_processed = self.processed_items['cleaning'] + self.processed_items['matching']
            if total_processed > 0:
                total_avg = elapsed / total_processed
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
        self._update_status(TranslationManager.get_translation(self.language.get(), "start_processing"))
        self.process_button.config(state=tk.DISABLED)
        self.progress["value"] = 0
        self.progress.config(mode="determinate")
        self.progress_var.set("0%")
        self.is_processing = True
        self.start_time = time.time()
        self.current_step = 0
        self.processed_items = {'cleaning': 0, 'matching': 0}
        self.avg_times = {'cleaning': 0, 'matching': 0}
        
        # Reset total items to default
        self.total_items = {'cleaning': 4, 'matching': 0}
        
        # Start progress updates
        self._update_progress_spinner()
        self._update_elapsed_time()
        
        # Run processing in a separate thread
        def process_thread():
            try:
                # Update CONFIG from GUI before processing
                self._update_config_from_gui()
                
                # Initialize services
                self.after(0, lambda: self._update_status(
                    TranslationManager.get_translation(self.language.get(), "initializing_services")
                ))
                
                # Handle potential initialization errors
                try:
                    self.app.initialize_services()
                except Exception as e:
                    logger.error(f"Error initializing services: {e}")
                    raise RuntimeError(f"Failed to initialize services: {str(e)}")
                
                # Process reports (cleaning step)
                cleaning_start = time.time()
                self.after(0, lambda: self._update_status(
                    TranslationManager.get_translation(self.language.get(), "cleaning")
                ))
                
                def file_processing_callback(file_type, current, total):
                    file_names = {
                        "purchase": os.path.basename(CONFIG.get('csv_exported_purchase_tax_report', "")),
                        "sale": os.path.basename(CONFIG.get('csv_exported_sales_tax_report', "")),
                        "withholding": os.path.basename(CONFIG.get('excel_Withholding_tax_report', "")),
                        "statement": os.path.basename(CONFIG.get('excel_statement', ""))
                    }
                    file_name = file_names.get(file_type, "file")
                    self.after(0, lambda msg=TranslationManager.get_translation(
                        self.language.get(), "cleaning_files", file_name, current, total
                    ): self._update_status(msg))
                    self.after(0, lambda i=current: self._update_progress(0, i))
                
                # Safely process report files
                try:
                    self.app.process_report_files(progress_callback=file_processing_callback)
                    cleaning_time = time.time() - cleaning_start
                    self.avg_times['cleaning'] = cleaning_time / 4
                except Exception as e:
                    logger.error(f"Error processing report files: {e}")
                    raise RuntimeError(f"Failed to process report files: {str(e)}")
                
                # Safely get statement length
                try:
                    statement_length = 500  # Default fallback
                    if self.app and self.app.report_processor:
                        if hasattr(self.app.report_processor, 'statement_length'):
                            statement_length = self.app.report_processor.statement_length or 500
                    
                    self.total_items['matching'] = statement_length
                    self.after(0, lambda: self._update_status(
                        TranslationManager.get_translation(
                            self.language.get(),
                            "statement_items_found" if statement_length != 500 else "statement_length_warning",
                            str(statement_length)
                        )
                    ))
                    logger.debug(f"Using statement length: {statement_length}")
                except Exception as e:
                    logger.warning(f"Error getting statement length: {e}, using default")
                    self.total_items['matching'] = 500
                
                # Perform matching (matching step)
                matching_start = time.time()
                self.current_step = 1
                self.after(0, lambda: self._update_status(
                    TranslationManager.get_translation(
                        self.language.get(),
                        "performing_matching"
                    )
                ))
                
                def progress_callback(current, total):
                    progress = float((current / total) * 100)
                    self.after(0, lambda: self._update_progress(2, current))
                    self.after(0, lambda: self._update_status(
                        TranslationManager.get_translation(
                            self.language.get(),
                            "matching_details",
                            progress,
                            current,
                            total
                        )
                    ))
                
                # Safely perform matching and generate reports
                try:
                    self.app.perform_matching(
                        progress_callback=progress_callback
                    )
                    matching_time = time.time() - matching_start
                    self.avg_times['matching'] = matching_time / 100
                except Exception as e:
                    logger.error(f"Error in matching process: {e}")
                    raise RuntimeError(f"Failed during matching process: {str(e)}")
                
                # Safely save reports
                try:
                    self.after(0, lambda: self._update_status(
                        TranslationManager.get_translation(
                            self.language.get(),
                            "saving_reports"
                        )
                    ))
                    report_dfs = self.app.generate_report()
                    if not report_dfs:
                        raise RuntimeError("No report data generated")
                        
                    self.report_dfs = report_dfs
                    self.app.save_reports(report_dfs)
                except Exception as e:
                    logger.error(f"Error saving reports: {e}")
                    raise RuntimeError(f"Failed to save reports: {str(e)}")
                
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
                self.after(0, lambda e=e: self._show_error(str(e)))
                
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

    # NOTE - show error box
    def _show_error(self, message):
        """Show error message with appropriate detail level"""
        lang = self.language.get()
        is_developer = os.getenv("ENV", "development").lower() == "development"
        
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