# src/gui/constants.py
import tkinter as tk
# from tkinter import ttk
from tkinter.ttk import Frame, LabelFrame, Label, Spinbox, Button
from typing import Dict, Any

from .translation import TranslationManager
from utils import CONFIG

class MatchingConstants:
    """Holds configurable matching parameters that can be modified by users"""
    
    
    @staticmethod
    def create_config_panel(parent: Frame, config: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Create a panel for configuring matching constants
        
        Args:
            parent: Parent frame to add widgets to
            config: Current configuration dictionary
            
        Returns:
            Dictionary containing tkinter variables and widgets
        """
        # Dictionary to store variables and widgets
        result = {
            'variables': {},
            'widgets': {}
        }
        
        frame = LabelFrame(parent, text=TranslationManager.get_translation(language, "matching_params"))
        frame.pack(fill=tk.X, padx=5, pady=5)
        result['widgets']['frame'] = frame
        
        # Create input for credit days
        credit_label = Label(frame, text=TranslationManager.get_translation(language, "matching_credit_days"))
        credit_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        credit_var = tk.IntVar(value=config.get('matching_credit_days', CONFIG['matching_credit_days']))
        # Trace the variable to update the config when it changes
        credit_var.trace_add("write", 
                lambda *args: CONFIG.update({'matching_credit_days': credit_var.get()})
        )
        credit_entry = Spinbox(frame, from_=1, to=90, textvariable=credit_var, width=10)
        credit_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        result['variables']['matching_credit_days'] = credit_var
        result['widgets']['credit_label'] = credit_label
        
        # Create input for sale tolerance
        sale_tolerance_label = Label(frame, text=TranslationManager.get_translation(language, "matching_sale_tolerance"))
        sale_tolerance_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        sale_var = tk.DoubleVar(value=config.get('matching_sale_tolerance', CONFIG['matching_sale_tolerance']))
        # Trace the variable to update the config when it changes
        sale_var.trace_add("write", 
                lambda *args: CONFIG.update({'matching_sale_tolerance': sale_var.get()})
        )
        sale_entry = Spinbox(frame, from_=0, to=10000, increment=100, textvariable=sale_var, width=10)
        sale_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        result['variables']['matching_sale_tolerance'] = sale_var
        result['widgets']['sale_tolerance_label'] = sale_tolerance_label
        
        # Create input for purchase tolerance
        purchase_tolerance_label = Label(frame, text=TranslationManager.get_translation(language, "matching_purchase_tolerance"))
        purchase_tolerance_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        purchase_var = tk.DoubleVar(value=config.get('matching_purchase_tolerance', CONFIG['matching_purchase_tolerance']))
        # Trace the variable to update the config when it changes
        purchase_var.trace_add("write", 
                 lambda *args: CONFIG.update({'matching_purchase_tolerance': purchase_var.get()})
        )
        purchase_entry = Spinbox(frame, from_=0, to=1000, increment=10, textvariable=purchase_var, width=10)
        purchase_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        result['variables']['matching_purchase_tolerance'] = purchase_var
        result['widgets']['purchase_tolerance_label'] = purchase_tolerance_label
        
        # Reset button
        reset_button = Button(
            frame, 
            text=TranslationManager.get_translation(language, "reset"),
            command=lambda: MatchingConstants._reset_values(result['variables'])
        )
        reset_button.grid(row=3, column=1, sticky=tk.E, padx=5, pady=5)
        result['widgets']['reset_button'] = reset_button
        
        return result
    
    @staticmethod
    def _reset_values(variables: Dict[str, tk.Variable]) -> None:
        """Reset all variables to default values"""
        for key, var in variables.items():
            if key in MatchingConstants.DEFAULT_VALUES:
                var.set(MatchingConstants.DEFAULT_VALUES[key])