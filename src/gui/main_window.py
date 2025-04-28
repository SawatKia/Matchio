# src\gui\main_window.py
import tkinter as tk
import pandas as pd
from tkinter import ttk, messagebox, filedialog
import time
import traceback
from pathlib import Path
import threading

from .widgets import ThemeSelector, LanguageToggle, FileInput, DirectoryInput, LogViewer, ProgressTracker
from utils import get_logger

logger = get_logger()

# Theme definitions
THEME_COLORS = {
    "Dark+ (default dark)": {"bg": "#1E1E1E", "fg": "#D4D4D4", "select_bg": "#264F78", "button": "#333333"},
    "Light+ (default light)": {"bg": "#FFFFFF", "fg": "#000000", "select_bg": "#ADD6FF", "button": "#E0E0E0"},
    "Monokai": {"bg": "#272822", "fg": "#F8F8F2", "select_bg": "#49483E", "button": "#3E3D32"},
    "Solarized Dark": {"bg": "#002B36", "fg": "#839496", "select_bg": "#073642", "button": "#586E75"},
    "Solarized Light": {"bg": "#FDF6E3", "fg": "#657B83", "select_bg": "#EEE8D5", "button": "#93A1A1"},
    "Dracula Official": {"bg": "#282A36", "fg": "#F8F8F2", "select_bg": "#44475A", "button": "#6272A4"},
    "Material Theme": {"bg": "#263238", "fg": "#EEFFFF", "select_bg": "#314549", "button": "#546E7A"},
    "Nord": {"bg": "#2E3440", "fg": "#D8DEE9", "select_bg": "#3B4252", "button": "#434C5E"},
    "One Dark Pro": {"bg": "#282C34", "fg": "#ABB2BF", "select_bg": "#3E4451", "button": "#565C64"},
    "Night Owl": {"bg": "#011627", "fg": "#D6DEEB", "select_bg": "#1D3B53", "button": "#7E57C2"},
    "Shades of Purple": {"bg": "#1E1E3F","fg": "#C7C7C7","select_bg": "#B362FF","button": "#5A00A1"},
    "Atom One Dark": {"bg": "#282C34","fg": "#ABB2BF","select_bg": "#3E4451","button": "#61AFEF"},
    "Cobalt2": {"bg": "#193549","fg": "#FFFFFF","select_bg": "#003B4F","button": "#FF9D00"},
    "Material Palenight": {"bg": "#292D3E","fg": "#A6ACCD","select_bg": "#3E4451","button": "#82AAFF"},
    "Rosé Pine": {"bg": "#191724","fg": "#E0DEF4","select_bg": "#403D52","button": "#EBBCBA"},
    "Tokyo Night": {"bg": "#1A1B26","fg": "#C0CAF5","select_bg": "#33467C","button": "#7AA2F7"},
    "Winter is Coming": {"bg": "#1E1E1E","fg": "#DCDCDC","select_bg": "#264F78","button": "#007ACC"},
    "One Monokai": {"bg": "#222430","fg": "#ABB2BF","select_bg": "#3E4451","button": "#61AFEF"},
    "Bluloco Light": {"bg": "#F5F5F5","fg": "#4D4D4C","select_bg": "#D6D6D6","button": "#A1B56C"}
}
DEFAULT_THEME = "Light+ (default light)"

class ApplicationGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("โปรแกรมจับคู่ใบแจ้งหนี้และรายการธนาคาร")
        self.geometry("900x700")
        
        # Initialize language settings
        self.language = "th"
        self.texts = {
            "en": {
                "title": "Payment Matching System",
                "process_button": "Process Data",
                "toggle_language": "Switch to Thai",
                "log_label": "Processing Log",
                "progress_label": "Progress",
                "error_title": "Error Occurred",
                "user_error_label": "For Regular User:",
                "dev_error_label": "For Developer:",
                "files_section": "Input Files",
                "purchase_report_file": "Purchase Report File(.csv):",
                "sale_report_file": "Sale Report File(.csv):",
                "withholding_tax_report_file": "Withholding Tax Report File(.xlsx):",
                "withholding_tax_sheet": "Withholding Tax Sheet(select one):",
                "statement_file": "Statement File(.xlsx):",
                "statement_sheet": "Statement Sheet(select one):",
                "output_dir": "Output Directory:",
                "browse": "Browse",
                "select_file": "Select File",
                "select_directory": "Select Directory",
                "excel_files": "Excel Files",
                "pdf_files": "PDF Files",
                "all_files": "All Files",
                "open_results": "Open Matching Results",
                "theme_label": "Theme:",
                "timing_info": "Timing Info",
                "elapsed": "Elapsed:",
                "eta": "ETA:",
                "avg_time": "Avg Time:",
                "processed": "Processed:"
            },
            "th": {
                "title": "ระบบจับคู่การชำระเงิน",
                "process_button": "ประมวลผลข้อมูล",
                "toggle_language": "เปลี่ยนเป็นภาษาอังกฤษ",
                "log_label": "บันทึกการประมวลผล",
                "progress_label": "ความคืบหน้า",
                "error_title": "เกิดข้อผิดพลาด",
                "user_error_label": "สำหรับผู้ใช้ทั่วไป:",
                "dev_error_label": "สำหรับนักพัฒนา:",
                "files_section": "ไฟล์ข้อมูลนำเข้า",
                "purchase_report_file": "ไฟล์รายงานภาษีซื้อ(.csv):",
                "sale_report_file": "ไฟล์รายงานภาษีขาย(.csv):",
                "withholding_tax_report_file": "สรุปรายการหัก ณ ที่จ่าย(.xlsx):",
                "withholding_tax_sheet": "ชีทสรุปรายการหัก ณ ที่จ่าย(เลือกจากรายการ):",
                "statement_file": "ไฟล์รายการเดินบัญชี(.xlsx):",
                "statement_sheet": "ชีทรายการเดินบัญชี(เลือกจากรายการ):",
                "output_dir": "ไดเรกทอรีผลลัพธ์:",
                "browse": "เรียกดู",
                "select_file": "เลือกไฟล์",
                "select_directory": "เลือกไดเรกทอรี",
                "excel_files": "ไฟล์ Excel",
                "pdf_files": "ไฟล์ PDF",
                "all_files": "ไฟล์ทั้งหมด",
                "open_results": "เปิดดูผลลัพธ์การจับคู่",
                "theme_label": "ธีม:",
                "timing_info": "ข้อมูลเวลาประมวลผล",
                "elapsed": "เวลาที่ใช้ไป:",
                "eta": "เวลาที่เหลือ:",
                "avg_time": "เวลาเฉลี่ย:",
                "processed": "ประมวลผลแล้ว:"
            }
        }
        
        # Initialize theme
        self.current_theme = DEFAULT_THEME
        self.apply_theme(self.current_theme)
        
        # Set up main frames
        self.create_frames()
        
        # Set up widgets
        self.setup_language_toggle()
        self.setup_theme_selector()
        self.setup_file_inputs()
        self.setup_process_button()
        self.setup_log_viewer()
        self.setup_progress_tracker()
        
        # Initialize file paths and other variables
        self.file_paths = {
            "purchase_report": "",
            "sale_report": "",
            "withholding_tax_report": "",
            "statement_file": "",
            "output_dir": ""
        }
        
        self.sheet_selections = {
            "withholding_tax_sheet": "",
            "statement_sheet": ""
        }
        
        # Processing variables
        self.processing = False
        self.process_start_time = 0
        
        logger.info("GUI initialized successfully")

    def create_frames(self):
        """Create main frames for the application"""
        # Header frame
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Files frame
        self.files_frame = ttk.LabelFrame(self)
        self.files_frame.pack(fill=tk.X, padx=10, pady=5, ipady=5)
        
        # Processing frame
        self.processing_frame = ttk.Frame(self)
        self.processing_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Log frame
        self.log_frame = ttk.LabelFrame(self)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def setup_language_toggle(self):
        """Set up language toggle button"""
        self.language_toggle = LanguageToggle(
            self.header_frame, 
            initial_language=self.language,
            command=self.toggle_language,
            text=self.texts[self.language]["toggle_language"]
        )
        self.language_toggle.pack(side=tk.RIGHT, padx=5, pady=5)

    def setup_theme_selector(self):
        """Set up theme selector"""
        # Label for theme selector
        self.theme_label = ttk.Label(
            self.header_frame, 
            text=self.texts[self.language]["theme_label"]
        )
        self.theme_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Theme selector widget
        self.theme_selector = ThemeSelector(
            self.header_frame,
            themes=THEME_COLORS,
            command=self.change_theme,
            initial_theme=self.current_theme
        )
        self.theme_selector.pack(side=tk.LEFT, padx=5, pady=5)

    def setup_file_inputs(self):
        """Set up file input fields"""
        # Title for files section
        self.files_label = ttk.Label(
            self.files_frame, 
            text=self.texts[self.language]["files_section"],
            font=("TkDefaultFont", 12, "bold")
        )
        self.files_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        # Purchase report file
        self.purchase_report_input = FileInput(
            self.files_frame,
            label_text=self.texts[self.language]["purchase_report_file"],
            file_types=[(self.texts[self.language]["all_files"], "*.*"), 
                        ("CSV", "*.csv")],
            button_text=self.texts[self.language]["browse"],
            row=1,
            command=lambda path: self.update_file_path("purchase_report", path)
        )
        
        # Sale report file
        self.sale_report_input = FileInput(
            self.files_frame,
            label_text=self.texts[self.language]["sale_report_file"],
            file_types=[(self.texts[self.language]["all_files"], "*.*"), 
                        ("CSV", "*.csv")],
            button_text=self.texts[self.language]["browse"],
            row=2,
            command=lambda path: self.update_file_path("sale_report", path)
        )
        
        # Withholding tax report file
        self.withholding_tax_input = FileInput(
            self.files_frame,
            label_text=self.texts[self.language]["withholding_tax_report_file"],
            file_types=[(self.texts[self.language]["excel_files"], "*.xlsx *.xls"), 
                        (self.texts[self.language]["all_files"], "*.*")],
            button_text=self.texts[self.language]["browse"],
            row=3,
            has_dropdown=True,
            dropdown_label=self.texts[self.language]["withholding_tax_sheet"],
            command=lambda path: self.update_file_path("withholding_tax_report", path),
            dropdown_command=lambda sheet: self.update_sheet_selection("withholding_tax_sheet", sheet)
        )
        
        # Statement file
        self.statement_input = FileInput(
            self.files_frame,
            label_text=self.texts[self.language]["statement_file"],
            file_types=[(self.texts[self.language]["excel_files"], "*.xlsx *.xls"), 
                        (self.texts[self.language]["all_files"], "*.*")],
            button_text=self.texts[self.language]["browse"],
            row=4,
            has_dropdown=True,
            dropdown_label=self.texts[self.language]["statement_sheet"],
            command=lambda path: self.update_file_path("statement_file", path),
            dropdown_command=lambda sheet: self.update_sheet_selection("statement_sheet", sheet)
        )
        
        # Output directory
        self.output_dir_input = DirectoryInput(
            self.files_frame,
            label_text=self.texts[self.language]["output_dir"],
            button_text=self.texts[self.language]["browse"],
            row=5,
            command=lambda path: self.update_file_path("output_dir", path)
        )

    def setup_process_button(self):
        """Set up process button and open results button"""
        self.button_frame = ttk.Frame(self.processing_frame)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Process button
        self.process_button = ttk.Button(
            self.button_frame,
            text=self.texts[self.language]["process_button"],
            command=self.start_processing
        )
        self.process_button.pack(side=tk.LEFT, padx=5)
        
        # Open results button
        self.open_results_button = ttk.Button(
            self.button_frame,
            text=self.texts[self.language]["open_results"],
            command=self.open_results,
            state=tk.DISABLED
        )
        self.open_results_button.pack(side=tk.LEFT, padx=5)

    def setup_log_viewer(self):
        """Set up log viewer"""
        self.log_label = ttk.Label(
            self.log_frame, 
            text=self.texts[self.language]["log_label"]
        )
        self.log_label.pack(anchor=tk.W, padx=5, pady=2)
        
        self.log_viewer = LogViewer(self.log_frame)
        self.log_viewer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_progress_tracker(self):
        """Set up progress bar and timing info"""
        self.progress_frame = ttk.Frame(self.processing_frame)
        self.progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_tracker = ProgressTracker(
            self.progress_frame,
            progress_label=self.texts[self.language]["progress_label"],
            timing_info_label=self.texts[self.language]["timing_info"],
            elapsed_label=self.texts[self.language]["elapsed"],
            eta_label=self.texts[self.language]["eta"],
            avg_time_label=self.texts[self.language]["avg_time"],
            processed_label=self.texts[self.language]["processed"]
        )

    def toggle_language(self):
        """Toggle between Thai and English languages"""
        self.language = "en" if self.language == "th" else "th"
        logger.info(f"Language changed to {self.language}")
        
        # Update UI text
        self.title(self.texts[self.language]["title"])
        
        # Update language toggle button
        self.language_toggle.config_text(self.texts[self.language]["toggle_language"])
        
        # Update theme label
        self.theme_label.config(text=self.texts[self.language]["theme_label"])
        
        # Update files section
        self.files_label.config(text=self.texts[self.language]["files_section"])
        
        # Update file inputs
        self.purchase_report_input.update_texts(
            label_text=self.texts[self.language]["purchase_report_file"],
            button_text=self.texts[self.language]["browse"]
        )
        
        self.sale_report_input.update_texts(
            label_text=self.texts[self.language]["sale_report_file"],
            button_text=self.texts[self.language]["browse"]
        )
        
        self.withholding_tax_input.update_texts(
            label_text=self.texts[self.language]["withholding_tax_report_file"],
            button_text=self.texts[self.language]["browse"],
            dropdown_label=self.texts[self.language]["withholding_tax_sheet"]
        )
        
        self.statement_input.update_texts(
            label_text=self.texts[self.language]["statement_file"],
            button_text=self.texts[self.language]["browse"],
            dropdown_label=self.texts[self.language]["statement_sheet"]
        )
        
        self.output_dir_input.update_texts(
            label_text=self.texts[self.language]["output_dir"],
            button_text=self.texts[self.language]["browse"]
        )
        
        # Update buttons
        self.process_button.config(text=self.texts[self.language]["process_button"])
        self.open_results_button.config(text=self.texts[self.language]["open_results"])
        
        # Update log viewer
        self.log_label.config(text=self.texts[self.language]["log_label"])
        
        # Update progress tracker
        self.progress_tracker.update_texts(
            progress_label=self.texts[self.language]["progress_label"],
            timing_info_label=self.texts[self.language]["timing_info"],
            elapsed_label=self.texts[self.language]["elapsed"],
            eta_label=self.texts[self.language]["eta"],
            avg_time_label=self.texts[self.language]["avg_time"],
            processed_label=self.texts[self.language]["processed"]
        )

    def change_theme(self, theme_name):
        """Change the application theme"""
        self.current_theme = theme_name
        self.apply_theme(theme_name)
        logger.info(f"Theme changed to {theme_name}")

    def apply_theme(self, theme_name):
        """Apply the selected theme to the application"""
        theme = THEME_COLORS.get(theme_name, THEME_COLORS[DEFAULT_THEME])
        
        # Update root window
        self.configure(bg=theme["bg"])
        
        # Create a custom ttk style
        style = ttk.Style(self)
        
        # Configure the ttk styles
        style.configure("TFrame", background=theme["bg"])
        style.configure("TLabelframe", background=theme["bg"])
        style.configure("TLabelframe.Label", background=theme["bg"], foreground=theme["fg"])
        style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        style.configure("TButton", background=theme["button"], foreground=theme["fg"])
        style.configure("TEntry", selectbackground=theme["select_bg"], fieldbackground=theme["bg"], foreground=theme["fg"])
        style.configure("TCombobox", selectbackground=theme["select_bg"], fieldbackground=theme["bg"], foreground=theme["fg"])
        style.configure("Vertical.TScrollbar", background=theme["button"], troughcolor=theme["bg"])
        style.configure("Horizontal.TScrollbar", background=theme["button"], troughcolor=theme["bg"])
        style.configure("TProgressbar", background=theme["select_bg"], troughcolor=theme["bg"])
        
        # Map styles for different states
        style.map("TButton",
                background=[("active", theme["select_bg"])],
                foreground=[("active", theme["fg"])])
        
        style.map("TCombobox",
                fieldbackground=[("readonly", theme["bg"])],
                selectbackground=[("readonly", theme["select_bg"])])
        
        # Update any custom widgets that need theme updates
        if hasattr(self, "log_viewer"):
            self.log_viewer.update_theme(bg=theme["bg"], fg=theme["fg"])
        
        if hasattr(self, "theme_selector"):
            self.theme_selector.update_theme(theme_name)

    def update_file_path(self, file_key, path):
        """Update file path in the dictionary"""
        self.file_paths[file_key] = path
        logger.debug(f"Updated {file_key} path to: {path}")
        
        # If it's an Excel file, update the available sheets
        if file_key in ["withholding_tax_report", "statement_file"] and path.endswith((".xlsx", ".xls")):
            try:
                xl = pd.ExcelFile(path)
                sheets = xl.sheet_names
                
                if file_key == "withholding_tax_report":
                    self.withholding_tax_input.update_dropdown_values(sheets)
                elif file_key == "statement_file":
                    self.statement_input.update_dropdown_values(sheets)
                    
                logger.debug(f"Updated sheets for {file_key}: {sheets}")
            except Exception as e:
                self.show_error(f"Could not read sheets from {path}", str(e))

    def update_sheet_selection(self, sheet_key, sheet_name):
        """Update selected sheet name in the dictionary"""
        self.sheet_selections[sheet_key] = sheet_name
        logger.debug(f"Selected {sheet_key}: {sheet_name}")

    def validate_inputs(self):
        """Validate all inputs before processing"""
        required_fields = {
            "purchase_report": self.texts[self.language]["purchase_report_file"],
            "sale_report": self.texts[self.language]["sale_report_file"],
            "output_dir": self.texts[self.language]["output_dir"]
        }
        
        # Check required fields
        for field, label in required_fields.items():
            if not self.file_paths[field]:
                return False, f"{label} is required."
        
        # Check if the files exist
        for field in ["purchase_report", "sale_report"]:
            if not Path(self.file_paths[field]).exists():
                return False, f"{required_fields[field]} does not exist."
        
        # Check output directory
        if not Path(self.file_paths["output_dir"]).exists():
            try:
                Path(self.file_paths["output_dir"]).mkdir(parents=True, exist_ok=True)
                logger.info(f"Created output directory: {self.file_paths['output_dir']}")
            except Exception as e:
                return False, f"Could not create output directory: {str(e)}"
        
        # Check optional files if provided
        optional_files = {
            "withholding_tax_report": self.texts[self.language]["withholding_tax_report_file"],
            "statement_file": self.texts[self.language]["statement_file"]
        }
        
        for field, label in optional_files.items():
            if self.file_paths[field] and not Path(self.file_paths[field]).exists():
                return False, f"{label} does not exist."
        
        # Check sheet selections for Excel files
        if self.file_paths["withholding_tax_report"] and not self.sheet_selections["withholding_tax_sheet"]:
            return False, f"{self.texts[self.language]['withholding_tax_sheet']} is required."
            
        if self.file_paths["statement_file"] and not self.sheet_selections["statement_sheet"]:
            return False, f"{self.texts[self.language]['statement_sheet']} is required."
        
        return True, ""

    def start_processing(self):
        """Start the data processing"""
        # Validate inputs
        valid, message = self.validate_inputs()
        if not valid:
            self.show_error("Invalid Input", message)
            return
        
        # Disable process button
        self.process_button.config(state=tk.DISABLED)
        
        # Reset progress
        self.progress_tracker.reset()
        
        # Clear log
        self.log_viewer.clear()
        
        # Log start of processing
        logger.info("Starting data processing")
        self.log_viewer.add_message("Starting data processing...")
        
        # Set processing flag and start time
        self.processing = True
        self.process_start_time = time.time()
        
        # Start processing in a separate thread
        threading.Thread(target=self.process_data, daemon=True).start()

    def process_data(self):
        """Process the data (placeholder for actual processing)"""
        try:
            # This would be replaced with your actual processing logic
            total_items = 100
            
            for i in range(total_items + 1):
                if not self.processing:
                    break
                
                # Update progress
                progress = i / total_items
                elapsed = time.time() - self.process_start_time
                
                # Calculate timing info
                if i > 0:
                    avg_time = elapsed / i
                    eta = avg_time * (total_items - i)
                else:
                    avg_time = 0
                    eta = 0
                
                # Log progress
                if i % 10 == 0:
                    self.log_viewer.add_message(f"Processing item {i} of {total_items}")
                
                # Update UI with progress
                self.update_progress(progress, i, total_items, elapsed, eta, avg_time)
                
                # Simulate processing time
                time.sleep(0.1)
            
            # Complete processing
            if self.processing:
                self.complete_processing()
                
        except Exception as e:
            # Handle any errors
            self.show_error("Processing Error", str(e))
            logger.error(f"Error during processing: {str(e)}")
            self.reset_processing()

    def update_progress(self, progress, current, total, elapsed, eta, avg_time):
        """Update progress bar and timing info"""
        # Use after() to update UI from the worker thread
        self.after(0, lambda: self.progress_tracker.update(
            progress, 
            current, 
            total, 
            elapsed, 
            eta, 
            avg_time
        ))

    def complete_processing(self):
        """Handle completion of processing"""
        # Calculate total elapsed time
        elapsed = time.time() - self.process_start_time
        
        # Log completion
        completion_message = f"Processing completed in {elapsed:.2f} seconds"
        logger.info(completion_message)
        self.log_viewer.add_message(completion_message)
        
        # Update UI
        self.after(0, lambda: self.progress_tracker.complete())
        self.after(0, lambda: self.enable_results_button())
        
        # Reset processing state
        self.reset_processing()

    def reset_processing(self):
        """Reset processing state"""
        self.processing = False
        self.after(0, lambda: self.process_button.config(state=tk.NORMAL))

    def enable_results_button(self):
        """Enable the open results button"""
        self.open_results_button.config(state=tk.NORMAL)

    def open_results(self):
        """Open the results file or directory"""
        import os
        import subprocess
        
        try:
            output_dir = self.file_paths["output_dir"]
            
            # Check if directory exists
            if not Path(output_dir).exists():
                self.show_error("Error", "Output directory does not exist")
                return
            
            # Open the directory
            if os.name == 'nt':  # Windows
                os.startfile(output_dir)
            elif os.uname().sysname == 'Darwin':  # macOS
                subprocess.call(['open', output_dir])
            else:  # Linux
                subprocess.call(['xdg-open', output_dir])
                    
            logger.info(f"Opened results directory: {output_dir}")
        except Exception as e:
            self.show_error("Error Opening Results", str(e))

    def show_error(self, title, message, detailed_error=None):
        """Show error dialog with user-friendly and developer versions"""
        logger.error(f"Error: {title} - {message}")
        
        if detailed_error is None:
            detailed_error = traceback.format_exc()
            
        # Create custom error dialog
        error_window = tk.Toplevel(self)
        error_window.title(self.texts[self.language]["error_title"])
        error_window.geometry("600x400")
        error_window.transient(self)
        error_window.grab_set()
        
        # Apply the current theme
        theme = THEME_COLORS.get(self.current_theme, THEME_COLORS[DEFAULT_THEME])
        error_window.configure(bg=theme["bg"])
        
        # User error frame
        user_frame = ttk.LabelFrame(
            error_window, 
            text=self.texts[self.language]["user_error_label"]
        )
        user_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        user_error = ttk.Label(
            user_frame, 
            text=message,
            wraplength=550
        )
        user_error.pack(padx=10, pady=10, fill=tk.X)
        
        # Developer error frame
        dev_frame = ttk.LabelFrame(
            error_window, 
            text=self.texts[self.language]["dev_error_label"]
        )
        dev_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a text widget for detailed error
        error_text = tk.Text(
            dev_frame, 
            wrap=tk.WORD,
            background=theme["bg"],
            foreground=theme["fg"],
            height=10
        )
        error_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        error_text.insert(tk.END, detailed_error)
        error_text.config(state=tk.DISABLED)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(error_text, command=error_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        error_text.config(yscrollcommand=scrollbar.set)
        
        # Close button
        close_button = ttk.Button(
            error_window,
            text="Close",
            command=error_window.destroy
        )
        close_button.pack(pady=10)