# src\gui\main_window.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from pathlib import Path
from utils import get_logger, FileManager, CONFIG

# Get the pre-configured logger
logger = get_logger()

class ApplicationGUI(tk.Tk):
    def __init__(self, app_instance=None):
        """
        Initialize the GUI for the application.
        
        Args:
            app_instance: Reference to the Application class instance from app.py
        """
        super().__init__()
        
        self.app = app_instance  # Store reference to the Application instance
        
        # Configure the main window
        self.title("Transaction Matcher")
        self.geometry("800x600")
        
        # Create main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create and configure UI elements
        self._create_file_inputs()
        self._create_processing_controls()
        self._create_status_area()
        
        logger.info("GUI initialized")

    def _create_file_inputs(self):
        """Create the file input section"""
        file_frame = ttk.LabelFrame(self.main_frame, text="Input Files")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Purchase Tax Report
        self._create_file_input_row(file_frame, "Purchase Tax Report:", "csv_exported_purchase_tax_report", 0)
        
        # Sales Tax Report
        self._create_file_input_row(file_frame, "Sales Tax Report:", "csv_exported_sales_tax_report", 1)
        
        # Withholding Tax Report
        self._create_file_input_row(file_frame, "Withholding Tax Report:", "excel_Withholding_tax_report", 2)
        
        # Bank Statement
        self._create_file_input_row(file_frame, "Bank Statement:", "excel_statement", 3)
        
        # Output Directory
        self._create_dir_input_row(file_frame, "Output Directory:", "output_dir", 4)

    def _create_file_input_row(self, parent, label_text, config_key, row):
        """Create a row with label, entry field and browse button for file selection"""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Create StringVar and entry to display the file path
        var = tk.StringVar(value=CONFIG.get(config_key, ""))
        entry = ttk.Entry(parent, textvariable=var, width=50)
        entry.grid(row=row, column=1, padx=5, pady=5)
        
        # Store the var and entry in instance variables for later access
        setattr(self, f"{config_key}_var", var)
        setattr(self, f"{config_key}_entry", entry)
        
        # Create browse button
        browse_button = ttk.Button(
            parent, 
            text="Browse...", 
            command=lambda: self._browse_file(var, config_key)
        )
        browse_button.grid(row=row, column=2, padx=5, pady=5)

    def _create_dir_input_row(self, parent, label_text, config_key, row):
        """Create a row with label, entry field and browse button for directory selection"""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Create StringVar and entry to display the directory path
        var = tk.StringVar(value=CONFIG.get(config_key, ""))
        entry = ttk.Entry(parent, textvariable=var, width=50)
        entry.grid(row=row, column=1, padx=5, pady=5)
        
        # Store the var and entry in instance variables for later access
        setattr(self, f"{config_key}_var", var)
        setattr(self, f"{config_key}_entry", entry)
        
        # Create browse button
        browse_button = ttk.Button(
            parent, 
            text="Browse...", 
            command=lambda: self._browse_directory(var, config_key)
        )
        browse_button.grid(row=row, column=2, padx=5, pady=5)

    def _create_processing_controls(self):
        """Create processing control buttons"""
        controls_frame = ttk.Frame(self.main_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Load and process files button
        self.process_button = ttk.Button(
            controls_frame, 
            text="Load & Process Files", 
            command=self._process_files
        )
        self.process_button.pack(side=tk.LEFT, padx=5)
        
        # Match transactions button (initially disabled)
        self.match_button = ttk.Button(
            controls_frame, 
            text="Match Transactions", 
            command=self._match_transactions,
            state=tk.DISABLED
        )
        self.match_button.pack(side=tk.LEFT, padx=5)
        
        # Save reports button (initially disabled)
        self.save_button = ttk.Button(
            controls_frame, 
            text="Save Reports", 
            command=self._save_reports,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Exit button
        exit_button = ttk.Button(
            controls_frame, 
            text="Exit", 
            command=self.quit
        )
        exit_button.pack(side=tk.RIGHT, padx=5)

    def _create_status_area(self):
        """Create status display area"""
        status_frame = ttk.LabelFrame(self.main_frame, text="Status")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=5, pady=5)
        
        # Status text display
        self.status_text = tk.Text(status_frame, height=15, width=80)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        # Make text read-only
        self.status_text.config(state=tk.DISABLED)

    def _browse_file(self, stringvar, config_key):
        """Open file browser dialog and update both the entry field and CONFIG"""
        filetypes = [
            ("All Files", "*.*"),
            ("CSV Files", "*.csv"),
            ("Excel Files", "*.xlsx;*.xls")
        ]
        
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            stringvar.set(filename)
            CONFIG[config_key] = filename
            logger.info(f"Set {config_key} to {filename}")

    def _browse_directory(self, stringvar, config_key):
        """Open directory browser dialog and update both the entry field and CONFIG"""
        directory = filedialog.askdirectory()
        if directory:
            stringvar.set(directory)
            CONFIG[config_key] = directory
            logger.info(f"Set {config_key} to {directory}")

    def _update_status(self, message):
        """Update the status text area with a new message"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)  # Auto-scroll to the end
        self.status_text.config(state=tk.DISABLED)
        self.update_idletasks()  # Force GUI update

    def _process_files(self):
        """Handler for the Process Files button"""
        if not self.app:
            messagebox.showerror("Error", "Application reference not initialized")
            return
            
        # Update GUI state
        self._update_status("Starting file processing...")
        self.process_button.config(state=tk.DISABLED)
        self.progress.start()
        
        # Run processing in a separate thread to keep GUI responsive
        def process_thread():
            try:
                # Update CONFIG from GUI before processing
                self._update_config_from_gui()
                
                # Run the processing
                self.app.initialize_services()
                self.app.process_report_files()
                
                # Update GUI on completion
                self.after(0, lambda: self._update_status("File processing completed."))
                self.after(0, lambda: self.match_button.config(state=tk.NORMAL))
            except Exception as e:
                logger.error(f"Error in processing: {e}")
                self.after(0, lambda: messagebox.showerror("Processing Error", f"Error: {str(e)}"))
                self.after(0, lambda: self._update_status(f"ERROR: {str(e)}"))
            finally:
                self.after(0, lambda: self.process_button.config(state=tk.NORMAL))
                self.after(0, lambda: self.progress.stop())
        
        # Start the thread
        threading.Thread(target=process_thread, daemon=True).start()

    def _match_transactions(self):
        """Handler for the Match Transactions button"""
        if not self.app:
            messagebox.showerror("Error", "Application reference not initialized")
            return
            
        # Update GUI state
        self._update_status("Starting transaction matching...")
        self.match_button.config(state=tk.DISABLED)
        self.progress.start()
        
        # Run matching in a separate thread
        def match_thread():
            try:
                # Run the matching process
                report_dfs = self.app.perform_matching_and_generate_reports()
                
                # Store reports for later saving
                self.report_dfs = report_dfs
                
                # Update GUI on completion
                self.after(0, lambda: self._update_status("Transaction matching completed."))
                self.after(0, lambda: self.save_button.config(state=tk.NORMAL))
            except Exception as e:
                logger.error(f"Error in matching: {e}")
                self.after(0, lambda: messagebox.showerror("Matching Error", f"Error: {str(e)}"))
                self.after(0, lambda: self._update_status(f"ERROR: {str(e)}"))
            finally:
                self.after(0, lambda: self.match_button.config(state=tk.NORMAL))
                self.after(0, lambda: self.progress.stop())
        
        # Start the thread
        threading.Thread(target=match_thread, daemon=True).start()

    def _save_reports(self):
        """Handler for the Save Reports button"""
        if not self.app or not hasattr(self, 'report_dfs'):
            messagebox.showerror("Error", "Reports not generated yet")
            return
            
        # Update GUI state
        self._update_status("Saving reports...")
        self.save_button.config(state=tk.DISABLED)
        self.progress.start()
        
        # Run saving in a separate thread
        def save_thread():
            try:
                # Check if output directory exists, create if it doesn't
                output_dir = CONFIG.get('output_dir', '')
                if not output_dir:
                    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
                    CONFIG['output_dir'] = output_dir
                    
                os.makedirs(output_dir, exist_ok=True)
                
                # Save the reports
                self.app.save_reports(self.report_dfs)
                
                # Update GUI on completion
                self.after(0, lambda: self._update_status(f"Reports saved to {output_dir}"))
                self.after(0, lambda: messagebox.showinfo("Success", f"Reports saved to {output_dir}"))
            except Exception as e:
                logger.error(f"Error saving reports: {e}")
                self.after(0, lambda: messagebox.showerror("Save Error", f"Error: {str(e)}"))
                self.after(0, lambda: self._update_status(f"ERROR: {str(e)}"))
            finally:
                self.after(0, lambda: self.save_button.config(state=tk.NORMAL))
                self.after(0, lambda: self.progress.stop())
        
        # Start the thread
        threading.Thread(target=save_thread, daemon=True).start()

    def _update_config_from_gui(self):
        """Update CONFIG dictionary from GUI input fields"""
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