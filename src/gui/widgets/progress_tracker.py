# src\gui\widgets\progress_tracker.py
import tkinter as tk
from tkinter import ttk
from typing import Optional

class ProgressTracker(ttk.Frame):
    """Widget to display progress bar and timing information"""
    
    def __init__(self, parent, 
                 progress_label: str = "Progress:", 
                 timing_info_label: str = "Timing Info",
                 elapsed_label: str = "Elapsed:",
                 eta_label: str = "ETA:",
                 avg_time_label: str = "Avg Time:",
                 processed_label: str = "Processed:",
                 *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Store label texts
        self.progress_label_text = progress_label
        self.timing_info_label_text = timing_info_label
        self.elapsed_label_text = elapsed_label
        self.eta_label_text = eta_label
        self.avg_time_label_text = avg_time_label
        self.processed_label_text = processed_label
        
        # Progress section
        self.progress_frame = ttk.Frame(self)
        self.progress_frame.pack(fill=tk.X, pady=2)
        
        self.progress_label = ttk.Label(self.progress_frame, text=progress_label)
        self.progress_label.pack(side=tk.LEFT, padx=5)
        
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            orient=tk.HORIZONTAL, 
            length=400, 
            mode='determinate', 
            variable=self.progress_var
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress_percent = ttk.Label(self.progress_frame, text="0.0%")
        self.progress_percent.pack(side=tk.LEFT, padx=5)
        
        # Timing info section
        self.timing_frame = ttk.LabelFrame(self, text=timing_info_label)
        self.timing_frame.pack(fill=tk.X, pady=5)
        
        # Create grid for timing info
        self.elapsed_label = ttk.Label(self.timing_frame, text=elapsed_label)
        self.elapsed_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.elapsed_value = ttk.Label(self.timing_frame, text="0s")
        self.elapsed_value.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.eta_label = ttk.Label(self.timing_frame, text=eta_label)
        self.eta_label.grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.eta_value = ttk.Label(self.timing_frame, text="--")
        self.eta_value.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        self.avg_time_label = ttk.Label(self.timing_frame, text=avg_time_label)
        self.avg_time_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.avg_time_value = ttk.Label(self.timing_frame, text="--")
        self.avg_time_value.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.processed_label = ttk.Label(self.timing_frame, text=processed_label)
        self.processed_label.grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.processed_value = ttk.Label(self.timing_frame, text="0/0")
        self.processed_value.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
    
    def update(self, progress: float, current: int, total: int, 
               elapsed: float, eta: float, avg_time: float):
        """Update progress and timing info"""
        # Update progress bar
        self.progress_var.set(progress * 100)
        self.progress_percent.config(text=f"{progress * 100:.1f}%")
        
        # Update timing info
        self.elapsed_value.config(text=self._format_time(elapsed))
        self.eta_value.config(text=self._format_time(eta))
        self.avg_time_value.config(text=f"{avg_time:.2f}s/item")
        self.processed_value.config(text=f"{current}/{total}")
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds into human-readable time"""
        if seconds < 0 or seconds > 86400:  # More than a day or negative
            return "--"
        
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def reset(self):
        """Reset progress tracker"""
        self.progress_var.set(0)
        self.progress_percent.config(text="0.0%")
        self.elapsed_value.config(text="0s")
        self.eta_value.config(text="--")
        self.avg_time_value.config(text="--")
        self.processed_value.config(text="0/0")
    
    def complete(self):
        """Mark progress as complete"""
        self.progress_var.set(100)
        self.progress_percent.config(text="100.0%")
        self.eta_value.config(text="0s")
    
    def update_texts(self, progress_label: Optional[str] = None, 
                      timing_info_label: Optional[str] = None,
                      elapsed_label: Optional[str] = None,
                      eta_label: Optional[str] = None,
                      avg_time_label: Optional[str] = None,
                      processed_label: Optional[str] = None):
        """Update widget texts for language change"""
        if progress_label:
            self.progress_label_text = progress_label
            self.progress_label.config(text=progress_label)
            
        if timing_info_label:
            self.timing_info_label_text = timing_info_label
            self.timing_frame.config(text=timing_info_label)
            
        if elapsed_label:
            self.elapsed_label_text = elapsed_label
            self.elapsed_label.config(text=elapsed_label)
            
        if eta_label:
            self.eta_label_text = eta_label
            self.eta_label.config(text=eta_label)
            
        if avg_time_label:
            self.avg_time_label_text = avg_time_label
            self.avg_time_label.config(text=avg_time_label)
            
        if processed_label:
            self.processed_label_text = processed_label
            self.processed_label.config(text=processed_label)