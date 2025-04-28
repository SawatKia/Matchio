# src\gui\widgets\theme_selector.py
import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable, Optional
import math

class ThemeSelector(ttk.Frame):
    """Widget to select application theme with color gradient circles"""
    
    def __init__(self, parent, themes: Dict[str, Dict[str, str]], 
                 command: Callable[[str], None], initial_theme: str,
                 *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.themes = themes
        self.command = command
        self.selected_theme = initial_theme
        self.theme_buttons = {}
        
        # Create theme selection frame
        self.theme_frame = ttk.Frame(self)
        self.theme_frame.pack(fill=tk.X)
        
        # Create theme buttons
        self._create_theme_buttons()
    
    def _create_theme_buttons(self):
        # Clear existing buttons if any
        for widget in self.theme_frame.winfo_children():
            widget.destroy()
        
        # Calculate layout - number of buttons per row
        button_size = 20
        padding = 2
        max_buttons_per_row = min(8, len(self.themes))  # Max 8 buttons per row
        
        # Create theme buttons in rows
        row, col = 0, 0
        for theme_name, colors in self.themes.items():
            # Create a canvas for the theme button
            canvas = tk.Canvas(
                self.theme_frame, 
                width=button_size, 
                height=button_size, 
                highlightthickness=1,
                highlightbackground="gray"
            )
            canvas.grid(row=row, column=col, padx=padding, pady=padding)
            
            # Create gradient circle representing theme colors
            self._draw_theme_circle(canvas, colors, theme_name, theme_name == self.selected_theme)
            
            # Store canvas and bind click event
            self.theme_buttons[theme_name] = canvas
            canvas.bind("<Button-1>", lambda e, tn=theme_name: self._on_theme_select(tn))
            
            # Add tooltip
            self._create_tooltip(canvas, theme_name)
            
            # Move to next column or row
            col += 1
            if col >= max_buttons_per_row:
                col = 0
                row += 1
    
    def _draw_theme_circle(self, canvas, colors, theme_name, is_selected):
        # Clear canvas
        canvas.delete("all")
        
        # Get canvas dimensions
        width = int(canvas.winfo_reqwidth())
        height = int(canvas.winfo_reqheight())
        
        # Calculate center and radius
        center_x, center_y = width // 2, height // 2
        radius = min(width, height) // 2 - 2
        
        # Create gradient background for the circle
        color_list = list(colors.values())
        color_count = len(color_list)
        
        # Draw background circle
        canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            fill=color_list[0], outline=""
        )
        
        # Angle for gradient (30 degrees as requested)
        angle = 30
        gradient_width = radius * 2
        
        # Draw gradient lines across the circle
        for i in range(gradient_width):
            # Calculate color index based on position
            color_idx = min(int(i / gradient_width * color_count), color_count - 1)
            color = color_list[color_idx]
            
            # Calculate line start and end positions with 30-degree tilt
            x_offset = i - radius
            y_offset_start = -math.tan(math.radians(angle)) * x_offset - radius
            y_offset_end = -math.tan(math.radians(angle)) * x_offset + radius
            
            # Draw the line
            x1 = center_x + x_offset
            y1 = center_y + y_offset_start
            x2 = center_x + x_offset
            y2 = center_y + y_offset_end
            
            # Only draw if within the circle bounds
            if (x1 - center_x)**2 + (y1 - center_y)**2 <= radius**2 or \
            (x2 - center_x)**2 + (y2 - center_y)**2 <= radius**2:
                canvas.create_line(x1, y1, x2, y2, fill=color)
        
        # Create circular boundary
        canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline="gray", width=1
        )
        
        # Draw selection indicator if this is the current theme
        if is_selected:
            selection_ring = canvas.create_oval(
                center_x - radius - 2, center_y - radius - 2,
                center_x + radius + 2, center_y + radius + 2,
                outline="#0078D7", width=2
            )
            # Store the selection ring reference
            if theme_name not in self.theme_buttons:
                self.theme_buttons[theme_name] = {"canvas": canvas, "ring": selection_ring}
            else:
                self.theme_buttons[theme_name]["ring"] = selection_ring    

    def _on_theme_select(self, theme_name: str):
        """Handle theme selection"""
        # Hide previous selection
        old_canvas = self.theme_buttons[self.selected_theme]
        # Find the selection ring in the old canvas
        old_rings = [item for item in old_canvas.find_all() if old_canvas.itemcget(item, "outline") == "#0078D7"]
        if old_rings:
            old_canvas.itemconfigure(old_rings[0], state='hidden')
        
        # Show new selection
        new_canvas = self.theme_buttons[theme_name]
        # Find the selection ring in the new canvas
        new_rings = [item for item in new_canvas.find_all() if new_canvas.itemcget(item, "outline") == "#0078D7"]
        if new_rings:
            new_canvas.itemconfigure(new_rings[0], state='normal')
        
        # Update selected theme
        self.selected_theme = theme_name
        
        # Call command
        if self.command:
            self.command(theme_name)
    
    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry("+0+0")
        tooltip.withdraw()
        
        label = ttk.Label(tooltip, text=text, relief="solid", borderwidth=1, padding=2)
        label.pack()
        
        def show_tooltip(event):
            x, y, _, _ = widget.bbox("all")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            tooltip.wm_geometry(f"+{x}+{y}")
            tooltip.deiconify()
            
        def hide_tooltip(event):
            tooltip.withdraw()
            
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def update_theme(self, current_theme=None):
        """Update the theme buttons when theme changes"""
        if current_theme:
            self.selected_theme = current_theme
        
        # Redraw all buttons to reflect new colors
        for theme_name, colors in self.themes.items():
            if theme_name in self.theme_buttons:
                canvas = self.theme_buttons[theme_name]
                self._draw_theme_circle(canvas, colors, theme_name, theme_name == self.selected_theme)