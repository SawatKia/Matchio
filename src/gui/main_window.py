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

logger = get_logger()

class TranslationManager:
    """Handles language translations for the UI"""
    TRANSLATIONS = {
        "en": {
            "window_title": "Transaction Matcher",
            "files_tab": "Files",
            "settings_tab": "Settings",
            "process_tab": "Process",
            "input_files": "Input Files",
            "language": "Language:",
            "thai": "Thai",
            "english": "English",
            "purchase_tax": "Purchase Tax Report (.csv):",
            "sales_tax": "Sales Tax Report (.csv):",
            "withholding_tax": "Withholding Tax Report (.xlsx):",
            "bank_statement": "Bank Statement (.xlsx):",
            "output_dir": "Output Directory:",
            "browse": "Browse",
            "open": "Open",
            "sheet": "Sheet:",
            "font_size": "Font Size",
            "matching_params": "Matching Parameters",
            "credit_days": "Credit Days:",
            "sale_tolerance": "Sale Tolerance:",
            "purchase_tolerance": "Purchase Tolerance:",
            "reset": "Reset",
            "start_processing": "Start Processing",
            "open_output": "Open Output Directory",
            "exit": "Exit",
            "status": "Status",
            "elapsed": "Elapsed:",
            "eta": "ETA:",
            "items": "Items:",
            "ready": "Ready",
            "processing": "Processing...",
            "complete": "Complete",
            "missing_files": "Please select the following files:",
            "error": "Error",
            "developer_error": "Developer Error Details",
            "success": "Success",
            "processing_complete": "Processing complete! Reports saved to: {}"
        },
        "th": {
            "window_title": "โปรแกรมจับคู่ธุรกรรม",
            "files_tab": "ไฟล์",
            "settings_tab": "ตั้งค่า",
            "process_tab": "ประมวลผล",
            "input_files": "ไฟล์นำเข้า",
            "language": "ภาษา:",
            "thai": "ไทย",
            "english": "English",
            "purchase_tax": "รายงานภาษีซื้อ (.csv):",
            "sales_tax": "รายงานภาษีขาย (.csv):",
            "withholding_tax": "รายงานภาษีหัก ณ ที่จ่าย (.xlsx):",
            "bank_statement": "รายการเดินบัญชี (.xlsx):",
            "output_dir": "โฟลเดอร์ผลลัพธ์:",
            "browse": "เลือก",
            "open": "เปิด",
            "sheet": "ชีต:",
            "font_size": "ขนาดตัวอักษร",
            "matching_params": "เงื่อนไขการจับคู่",
            "credit_days": "ระยะเวลาเครดิต:",
            "sale_tolerance": "ความคลาดเคลื่อนการขาย:",
            "purchase_tolerance": "ความคลาดเคลื่อนการซื้อ:",
            "reset": "รีเซ็ต",
            "start_processing": "เริ่มการจับคู่",
            "open_output": "เปิดโฟลเดอร์ผลลัพธ์",
            "exit": "ออก",
            "status": "สถานะ",
            "elapsed": "เวลาที่ใช้:",
            "eta": "เวลาที่คาดว่าเหลือ:",
            "items": "จำนวน:",
            "ready": "พร้อมใช้งาน",
            "processing": "กำลังประมวลผล...",
            "complete": "เสร็จสิ้น",
            "missing_files": "กรุณาเลือกไฟล์ต่อไปนี้:",
            "error": "ข้อผิดพลาด",
            "developer_error": "รายละเอียดข้อผิดพลาดสำหรับนักพัฒนา",
            "success": "สำเร็จ",
            "processing_complete": "ประมวลผลเสร็จสิ้น! บันทึกผลลัพธ์ที่: {}"
        }
    }

    @classmethod
    def get_translation(cls, language: str, key: str, *format_args) -> str:
        """Get translation for a key in the specified language"""
        try:
            translation = cls.TRANSLATIONS[language][key]
            if format_args:
                return translation.format(*format_args)
            return translation
        except KeyError:
            logger.warning(f"Missing translation for key: {key}")
            return key

# Then modify the ApplicationGUI class
class ApplicationGUI(tk.Tk):
    def __init__(self, app_instance=None):
        """
        Initialize the GUI for the application.
        
        Args:
            app_instance: Reference to the Application class instance from app.py
        """
        super().__init__()
        
        self.app = app_instance  # Store reference to the Application instance
        self.report_dfs = None   # Storage for generated reports
        self.processing_thread = None  # Reference to processing thread
        self.language = tk.StringVar(value="en")  # Language toggle
        self.sheet_vars = {}  # Excel sheet selection variables
        self.constant_vars = {}  # Matching constant variables
        self.start_time = None  # For tracking processing time
        self.is_processing = False  # Flag to track processing state
        
        # Configure the main window
        self.title("Transaction Matcher")
        self.geometry("900x700")
        
        # Set default font
        self.default_font = font.nametofont("TkDefaultFont")
        self.font_size = tk.IntVar(value=9)  # Default font size
        self.update_font_size()
        
        # Create main frame with notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.files_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.process_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.files_tab, text="ไฟล์ / Files")
        self.notebook.add(self.settings_tab, text="ตั้งค่า / Settings")
        self.notebook.add(self.process_tab, text="ประมวลผล / Process")
        
        # Create and configure UI elements
        self._create_file_inputs()
        self._create_settings_panel()
        self._create_processing_panel()
        
        # Create status bar
        self._create_status_bar()
        
        logger.info("GUI initialized")

    def _create_file_inputs(self):
        """Create the file input section"""
        file_frame = ttk.LabelFrame(self.files_tab, text="ไฟล์นำเข้า / Input Files")
        file_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Language toggle
        lang_frame = ttk.Frame(file_frame)
        lang_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(lang_frame, text="ภาษา / Language:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(lang_frame, text="ไทย", variable=self.language, value="th", 
                        command=self._update_language).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(lang_frame, text="English", variable=self.language, value="en", 
                        command=self._update_language).pack(side=tk.LEFT, padx=5)
        
        # File input container
        input_frame = ttk.Frame(file_frame)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Purchase Tax Report
        self._create_file_input_row(input_frame, "รายงานภาษีซื้อ / Purchase Tax Report (.csv):", "csv_exported_purchase_tax_report", 0)
        
        # Sales Tax Report
        self._create_file_input_row(input_frame, "รายงานภาษีขาย / Sales Tax  (.csv):", "csv_exported_sales_tax_report", 1)
        
        # Withholding Tax Report
        self._create_file_input_row(input_frame, "รายงานภาษีหัก ณ ที่จ่าย / Withholding Tax Report (.xlsx):", "excel_Withholding_tax_report", 2, is_excel=True)
        
        # Bank Statement
        self._create_file_input_row(input_frame, "รายการเดินบัญชี / Bank Statement (.xlsx):", "excel_statement", 3, is_excel=True)
        
        # Output Directory
        self._create_dir_input_row(input_frame, "โฟลเดอร์ผลลัพธ์ / Output Directory:", "output_dir", 4)

    def _create_settings_panel(self):
        """Create the settings panel"""
        # Font size control
        font_frame = ttk.LabelFrame(self.settings_tab, text="ขนาดตัวอักษร / Font Size")
        font_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(font_frame, text="−", width=3, 
                  command=lambda: self.change_font_size(-1)).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(font_frame, textvariable=self.font_size).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(font_frame, text="+", width=3,
                  command=lambda: self.change_font_size(1)).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Create matching constants panel
        self.constant_vars = MatchingConstants.create_config_panel(self.settings_tab, CONFIG)

    def _create_processing_panel(self):
        """Create the processing panel"""
        controls_frame = ttk.Frame(self.process_tab)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Start processing button
        self.process_button = ttk.Button(
            controls_frame, 
            text="เริ่มการจับคู่ / Start Processing", 
            command=self._start_full_process
        )
        self.process_button.pack(side=tk.LEFT, padx=5)
        
        # Open output directory button
        self.open_dir_button = ttk.Button(
            controls_frame, 
            text="เปิดโฟลเดอร์ผลลัพธ์ / Open Output Directory", 
            command=self._open_output_directory
        )
        self.open_dir_button.pack(side=tk.LEFT, padx=5)
        
        # Exit button
        exit_button = ttk.Button(
            controls_frame, 
            text="ออก / Exit", 
            command=self.quit
        )
        exit_button.pack(side=tk.RIGHT, padx=5)
        
        # Create status display area
        self._create_status_area()

    def _create_status_area(self):
        """Create status display area"""
        status_frame = ttk.LabelFrame(self.process_tab, text="สถานะ / Status")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Progress frame
        progress_frame = ttk.Frame(status_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Progress indicator (Spinner)
        self.spinner_label = ttk.Label(progress_frame, text="") # Start empty
        self.spinner_label.pack(side=tk.LEFT, padx=5)
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"] # More standard spinner
        self.spinner_idx = 0
        
        # Progress bar
        self.progress = ttk.Progressbar(progress_frame, mode="indeterminate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Progress percentage
        self.progress_var = tk.StringVar(value="0%")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.pack(side=tk.RIGHT, padx=5)
        
        # Timing information
        self.timing_frame = ttk.Frame(status_frame)
        self.timing_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Elapsed time
        self.elapsed_var = tk.StringVar(value="Elapsed: 00:00:00")
        ttk.Label(self.timing_frame, textvariable=self.elapsed_var).pack(side=tk.LEFT, padx=5)
        
        # ETA
        self.eta_var = tk.StringVar(value="ETA: --:--:--")
        ttk.Label(self.timing_frame, textvariable=self.eta_var).pack(side=tk.LEFT, padx=5)
        
        # Items progress
        self.items_var = tk.StringVar(value="Items: 0/0")
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
        self.status_bar = ttk.Label(self, text="พร้อมใช้งาน / Ready", relief=tk.SUNKEN, anchor=tk.W)
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
        browse_button = ttk.Button(
            row_frame, 
            text="เลือก / Browse", 
            command=lambda: self._browse_file(var, config_key, is_excel)
        )
        browse_button.pack(side=tk.LEFT, padx=5)
        
        # If Excel file, add sheet selector
        if is_excel:
            self._add_sheet_selector(row_frame, config_key)

    def _add_sheet_selector(self, parent, config_key):
        """Add a sheet selector dropdown for Excel files"""
        sheet_frame = ttk.Frame(parent)
        sheet_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(sheet_frame, text="ชีต / Sheet:").pack(side=tk.LEFT, padx=2)
        
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
        browse_button = ttk.Button(
            row_frame, 
            text="เลือก / Browse", 
            command=lambda: self._browse_directory(var, config_key)
        )
        browse_button.pack(side=tk.LEFT, padx=5)
        
        # Add open directory button
        open_button = ttk.Button(
            row_frame,
            text="เปิด / Open",
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

    def _update_language(self):
        """Update the UI language based on the selected language"""
        # This is a placeholder for language switching
        # In a complete implementation, you would update all UI text elements
        # This just demonstrates the concept
        lang = self.language.get()
        logger.info(f"Language switched to: {lang}")
        self.status_bar.config(text="พร้อมใช้งาน / Ready" if lang == "th" else "Ready / พร้อมใช้งาน")

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
        for key, label in [
            ('csv_exported_purchase_tax_report', 'รายงานภาษีซื้อ / Purchase Tax Report'),
            ('csv_exported_sales_tax_report', 'รายงานภาษีขาย / Sales Tax Report'),
            ('excel_Withholding_tax_report', 'รายงานภาษีหัก ณ ที่จ่าย / Withholding Tax Report'),
            ('excel_statement', 'รายการเดินบัญชี / Bank Statement')
        ]:
            file_path = getattr(self, f"{key}_var").get()
            if not file_path or not os.path.exists(file_path):
                missing_files.append(label)
        
        # Check output directory
        output_dir = getattr(self, "output_dir_var").get()
        if not output_dir:
            missing_files.append('โฟลเดอร์ผลลัพธ์ / Output Directory')
        
        if missing_files:
            message = "กรุณาเลือกไฟล์ต่อไปนี้:\n" + "\n".join(missing_files)
            messagebox.showerror("Missing Files", message)
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
            self.after(500, self._update_progress_spinner)

    def _update_elapsed_time(self):
        """Update the elapsed time display"""
        if self.is_processing and self.start_time:
            elapsed = time.time() - self.start_time
            hours, remainder = divmod(int(elapsed), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            self.elapsed_var.set(f"Elapsed: {hours:02}:{minutes:02}:{seconds:02}")
            self.after(1000, self._update_elapsed_time)

    def _start_full_process(self):
        """Start the entire processing workflow"""
        # Validate input files first
        if not self._validate_input_files():
            return
            
        # Update GUI state
        self._update_status("Starting full processing workflow...")
        self.process_button.config(state=tk.DISABLED)
        self.progress.start()
        self.is_processing = True
        self.start_time = time.time()
        
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
                
                # Process reports
                self.after(0, lambda: self._update_status("Processing report files..."))
                self.app.process_report_files()
                
                # Perform matching and generate reports
                self.after(0, lambda: self._update_status("Performing transaction matching..."))
                report_dfs = self.app.perform_matching_and_generate_reports()
                self.report_dfs = report_dfs
                
                # Save reports
                self.after(0, lambda: self._update_status("Saving reports..."))
                self.app.save_reports(report_dfs)
                
                # Final status update
                output_dir = CONFIG.get('output_dir', '')
                self.after(0, lambda: self._update_status(f"Processing complete! Reports saved to: {output_dir}"))
                self.after(0, lambda: messagebox.showinfo("Success", f"All processing steps completed.\nReports saved to: {output_dir}"))
                
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
        if is_developer:
            # For developer: detailed error with stack trace
            error_text = f"Error: {message}\n\n"
            error_text += traceback.format_exc()
            
            # Create detailed error dialog
            error_dialog = tk.Toplevel(self)
            error_dialog.title("Developer Error Details")
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
        else:
            # For user: simple error message
            messagebox.showerror("Error", message)
            self._update_status(f"Error: {message}")
            
        # Update GUI state
        self.is_processing = False
        self.process_button.config(state=tk.NORMAL)
        self.progress.stop()