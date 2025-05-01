# src/gui/constants.py
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

class MatchingConstants:
    """Holds configurable matching parameters that can be modified by users"""
    
    DEFAULT_VALUES = {
        'matching_credit_days': 30,
        'matching_sale_tolerance': 1000.0,
        'matching_purchase_tolerance': 50.0
    }
    
    @staticmethod
    def create_config_panel(parent: ttk.Frame, config: Dict[str, Any]) -> Dict[str, tk.Variable]:
        """Create a panel for configuring matching constants
        
        Args:
            parent: Parent frame to add widgets to
            config: Current configuration dictionary
            
        Returns:
            Dictionary of tkinter variables bound to the widgets
        """
        frame = ttk.LabelFrame(parent, text="เงื่อนไขการจับคู่ / Matching Parameters")
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Dictionary to store variables
        variables = {}
        
        # Create input for credit days
        ttk.Label(frame, text="ระยะเวลาเครดิต / Credit Days:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        credit_var = tk.IntVar(value=config.get('matching_credit_days', MatchingConstants.DEFAULT_VALUES['matching_credit_days']))
        credit_entry = ttk.Spinbox(frame, from_=1, to=90, textvariable=credit_var, width=10)
        credit_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        variables['matching_credit_days'] = credit_var
        
        # Create input for sale tolerance
        ttk.Label(frame, text="ความคลาดเคลื่อนการขาย / Sale Tolerance:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        sale_var = tk.DoubleVar(value=config.get('matching_sale_tolerance', MatchingConstants.DEFAULT_VALUES['matching_sale_tolerance']))
        sale_entry = ttk.Spinbox(frame, from_=0, to=10000, increment=100, textvariable=sale_var, width=10)
        sale_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        variables['matching_sale_tolerance'] = sale_var
        
        # Create input for purchase tolerance
        ttk.Label(frame, text="ความคลาดเคลื่อนการซื้อ / Purchase Tolerance:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        purchase_var = tk.DoubleVar(value=config.get('matching_purchase_tolerance', MatchingConstants.DEFAULT_VALUES['matching_purchase_tolerance']))
        purchase_entry = ttk.Spinbox(frame, from_=0, to=1000, increment=10, textvariable=purchase_var, width=10)
        purchase_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        variables['matching_purchase_tolerance'] = purchase_var
        
        # Reset button
        reset_button = ttk.Button(
            frame, 
            text="รีเซ็ต / Reset", 
            command=lambda: MatchingConstants._reset_values(variables)
        )
        reset_button.grid(row=3, column=1, sticky=tk.E, padx=5, pady=5)
        
        return variables
    
    @staticmethod
    def _reset_values(variables: Dict[str, tk.Variable]) -> None:
        """Reset all variables to default values"""
        for key, var in variables.items():
            if key in MatchingConstants.DEFAULT_VALUES:
                var.set(MatchingConstants.DEFAULT_VALUES[key])