"""
Oil Gauge BLE Monitor
A modern desktop application for monitoring oil pressure via Bluetooth LE.
"""

import asyncio
import threading
import struct
import json
import math
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from collections import deque

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from bleak import BleakScanner, BleakClient


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME = "Oil Gauge Monitor"
APP_VERSION = "1.0.0"

# BLE UUIDs (must match ble_service.py on Pico)
SERVICE_UUID = "e7c9c910-7f6f-4b02-bc6d-1d9d3f3b0010"
CHAR_UUID = "e7c9c911-7f6f-4b02-bc6d-1d9d3f3b0010"
DEFAULT_DEVICE = "OilGauge"

# Error codes from Pico
ERROR_MAP = {
    0: None, 1: "VHIGH", 2: "VLOW", 3: "SENSOR_OOR", 4: "FLOATING"
}
ERROR_DESC = {
    "VHIGH": "⚠️ Over-voltage detected",
    "VLOW": "⚠️ Under-voltage detected",
    "SENSOR_OOR": "⚠️ Sensor out of range",
    "FLOATING": "⚠️ Floating signal",
    "INVALID_DATA": "⚠️ Invalid data",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Theme
# ═══════════════════════════════════════════════════════════════════════════════

class Theme:
    BG_DARK = "#0d1117"
    BG_CARD = "#161b22"
    BG_INPUT = "#21262d"
    
    PRIMARY = "#58a6ff"
    SUCCESS = "#3fb950"
    WARNING = "#d29922"
    DANGER = "#f85149"
    
    TEXT = "#e6edf3"
    TEXT_DIM = "#7d8590"
    TEXT_MUTED = "#484f58"
    
    GAUGE_SAFE = "#3fb950"
    GAUGE_WARN = "#d29922"
    GAUGE_DANGER = "#f85149"
    
    GRAPH_LINE = "#58a6ff"
    GRAPH_GRID = "#30363d"
    
    FONT_MONO = ("Consolas", "Monaco", "Courier New")
    FONT_UI = ("Segoe UI", "SF Pro Display", "Arial")


# ═══════════════════════════════════════════════════════════════════════════════
# Data Decoder
# ═══════════════════════════════════════════════════════════════════════════════

def decode_ble_data(data: bytearray) -> tuple:
    """Decode BLE data from the Pico."""
    try:
        text = data.decode('utf-8').strip()
        if text.startswith("ERR:"):
            return 0.0, text[4:]
        return float(text), None
    except (UnicodeDecodeError, ValueError):
        pass
    
    if len(data) >= 3:
        psi_raw, err = struct.unpack("<HB", data[:3])
        return psi_raw / 10.0, ERROR_MAP.get(err)
    if len(data) >= 2:
        psi_raw = struct.unpack("<H", data[:2])[0]
        return psi_raw / 10.0, None
    
    return 0.0, "INVALID_DATA"


# ═══════════════════════════════════════════════════════════════════════════════
# Data Log Viewer Dialog
# ═══════════════════════════════════════════════════════════════════════════════

class DataLogViewer(tk.Toplevel):
    """Dialog to view and analyze recorded data logs."""
    
    def __init__(self, parent, data: dict):
        super().__init__(parent)
        self.title("Data Log Viewer")
        self.configure(bg=Theme.BG_DARK)
        self.geometry("800x600")
        self.transient(parent)
        
        self.data = data
        self._build_ui()
    
    def _build_ui(self):
        # Header info
        header = tk.Frame(self, bg=Theme.BG_CARD, padx=20, pady=15)
        header.pack(fill=tk.X, side=tk.TOP)
        
        tk.Label(header, text="📊 DATA LOG", font=(Theme.FONT_MONO[0], 14, "bold"),
                bg=Theme.BG_CARD, fg=Theme.PRIMARY).pack(anchor=tk.W)
        
        info_text = f"""Device: {self.data.get('device', 'Unknown')}   |   Start: {self.data.get('start_time', 'N/A')[:19] if self.data.get('start_time') else 'N/A'}   |   Samples: {self.data.get('samples', len(self.data.get('data', [])))}"""
        
        tk.Label(header, text=info_text, font=(Theme.FONT_UI[0], 9),
                bg=Theme.BG_CARD, fg=Theme.TEXT_DIM).pack(anchor=tk.W, pady=(5, 0))
        
        # Footer buttons - pack BEFORE notebook so it's always visible at bottom
        footer = tk.Frame(self, bg=Theme.BG_CARD, padx=15, pady=12)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Label(footer, text="ACTIONS:", font=(Theme.FONT_MONO[0], 10, "bold"),
                bg=Theme.BG_CARD, fg=Theme.PRIMARY).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(footer, text="📄 Export CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(footer, text="🖨️ Print Report", command=self._print_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(footer, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Notebook for tabs - pack AFTER footer
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Graph
        graph_frame = tk.Frame(notebook, bg=Theme.BG_CARD)
        notebook.add(graph_frame, text="  📈 Graph  ")
        self._build_graph(graph_frame)
        
        # Tab 2: Table
        table_frame = tk.Frame(notebook, bg=Theme.BG_CARD)
        notebook.add(table_frame, text="  📋 Data Table  ")
        self._build_table(table_frame)
        
        # Tab 3: Summary
        summary_frame = tk.Frame(notebook, bg=Theme.BG_CARD)
        notebook.add(summary_frame, text="  📊 Summary  ")
        self._build_summary(summary_frame)
    
    def _build_graph(self, parent):
        """Build the graph view."""
        if not HAS_MATPLOTLIB:
            tk.Label(parent, text="matplotlib required for graph",
                    bg=Theme.BG_CARD, fg=Theme.TEXT_DIM).pack(expand=True)
            return
        
        samples = self.data.get('data', [])
        if not samples:
            tk.Label(parent, text="No data to display",
                    bg=Theme.BG_CARD, fg=Theme.TEXT_DIM).pack(expand=True)
            return
        
        fig = Figure(figsize=(7, 4), dpi=100, facecolor=Theme.BG_CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(Theme.BG_DARK)
        
        psi_values = [s.get('psi', 0) for s in samples]
        ax.fill_between(range(len(psi_values)), psi_values, alpha=0.3, color=Theme.GRAPH_LINE)
        ax.plot(psi_values, color=Theme.GRAPH_LINE, linewidth=1.5)
        
        ax.set_xlabel("Sample", color=Theme.TEXT_DIM)
        ax.set_ylabel("PSI", color=Theme.TEXT_DIM)
        ax.tick_params(colors=Theme.TEXT_DIM)
        ax.grid(True, color=Theme.GRAPH_GRID, alpha=0.5)
        for spine in ax.spines.values():
            spine.set_color(Theme.GRAPH_GRID)
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def _build_table(self, parent):
        """Build the data table view."""
        # Create treeview with scrollbar
        container = tk.Frame(parent, bg=Theme.BG_CARD)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Index", "Time", "PSI", "Error")
        tree = ttk.Treeview(container, columns=columns, show="headings", height=20)
        
        tree.heading("Index", text="#")
        tree.heading("Time", text="Timestamp")
        tree.heading("PSI", text="PSI")
        tree.heading("Error", text="Error")
        
        tree.column("Index", width=60, anchor=tk.CENTER)
        tree.column("Time", width=200, anchor=tk.W)
        tree.column("PSI", width=100, anchor=tk.CENTER)
        tree.column("Error", width=150, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate data
        for i, sample in enumerate(self.data.get('data', [])):
            time_str = sample.get('time', '')
            if 'T' in time_str:
                time_str = time_str.replace('T', ' ').split('.')[0]
            
            tree.insert("", tk.END, values=(
                i + 1,
                time_str,
                f"{sample.get('psi', 0):.2f}",
                sample.get('error', '') or ''
            ))
    
    def _build_summary(self, parent):
        """Build the summary statistics view."""
        samples = self.data.get('data', [])
        psi_values = [s.get('psi', 0) for s in samples if s.get('error') is None]
        
        if not psi_values:
            tk.Label(parent, text="No valid data for analysis",
                    bg=Theme.BG_CARD, fg=Theme.TEXT_DIM).pack(expand=True)
            return
        
        # Calculate statistics
        avg_psi = sum(psi_values) / len(psi_values)
        min_psi = min(psi_values)
        max_psi = max(psi_values)
        range_psi = max_psi - min_psi
        
        # Count errors
        errors = [s.get('error') for s in samples if s.get('error')]
        error_count = len(errors)
        
        # Build summary text
        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║                    SESSION SUMMARY REPORT                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  DEVICE:     {self.data.get('device', 'Unknown'):<47} ║
║  START:      {str(self.data.get('start_time', 'N/A'))[:47]:<47} ║
║  END:        {str(self.data.get('end_time', 'N/A'))[:47]:<47} ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                       PRESSURE DATA                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Total Samples:    {len(samples):<42} ║
║  Valid Readings:   {len(psi_values):<42} ║
║  Error Count:      {error_count:<42} ║
║                                                              ║
║  Minimum PSI:      {min_psi:<42.2f} ║
║  Maximum PSI:      {max_psi:<42.2f} ║
║  Average PSI:      {avg_psi:<42.2f} ║
║  Range:            {range_psi:<42.2f} ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """.strip()
        
        text = tk.Text(parent, font=(Theme.FONT_MONO[0], 10), bg=Theme.BG_DARK,
                      fg=Theme.TEXT, relief=tk.FLAT, padx=20, pady=20)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", summary)
        text.config(state=tk.DISABLED)
    
    def _export_csv(self):
        """Export data to CSV file."""
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"oilgauge_export_{datetime.now():%Y%m%d_%H%M%S}.csv"
        )
        if path:
            with open(path, 'w') as f:
                f.write("Index,Timestamp,PSI,Error\n")
                for i, sample in enumerate(self.data.get('data', [])):
                    f.write(f"{i+1},{sample.get('time','')},{sample.get('psi',0):.2f},{sample.get('error','')}\n")
            messagebox.showinfo("Exported", f"Data exported to:\n{path}")
    
    def _print_report(self):
        """Generate and print a report."""
        samples = self.data.get('data', [])
        psi_values = [s.get('psi', 0) for s in samples if s.get('error') is None]
        
        avg_psi = sum(psi_values) / len(psi_values) if psi_values else 0
        min_psi = min(psi_values) if psi_values else 0
        max_psi = max(psi_values) if psi_values else 0
        
        report = f"""
================================================================================
                         OIL GAUGE DATA LOG REPORT
================================================================================

Generated: {datetime.now():%Y-%m-%d %H:%M:%S}

DEVICE INFORMATION
------------------
Device Name:    {self.data.get('device', 'Unknown')}
Session Start:  {self.data.get('start_time', 'N/A')}
Session End:    {self.data.get('end_time', 'N/A')}

STATISTICS
----------
Total Samples:  {len(samples)}
Valid Readings: {len(psi_values)}
Error Count:    {len(samples) - len(psi_values)}

Minimum PSI:    {min_psi:.2f}
Maximum PSI:    {max_psi:.2f}
Average PSI:    {avg_psi:.2f}

DATA SAMPLES (First 100)
------------------------
{"#":<6} {"Timestamp":<25} {"PSI":<10} {"Error":<15}
{"-"*6} {"-"*25} {"-"*10} {"-"*15}
"""
        for i, sample in enumerate(samples[:100]):
            time_str = sample.get('time', '')
            if 'T' in time_str:
                time_str = time_str.replace('T', ' ').split('.')[0]
            report += f"{i+1:<6} {time_str:<25} {sample.get('psi',0):<10.2f} {sample.get('error','') or '':<15}\n"
        
        if len(samples) > 100:
            report += f"\n... and {len(samples) - 100} more samples\n"
        
        report += "\n" + "=" * 80 + "\n"
        
        # Show print options dialog
        self._show_print_dialog(report)
    
    def _show_print_dialog(self, report: str):
        """Show dialog with print options."""
        dialog = tk.Toplevel(self)
        dialog.title("Print Report")
        dialog.configure(bg=Theme.BG_DARK)
        dialog.geometry("700x500")
        dialog.transient(self)
        
        # Preview
        tk.Label(dialog, text="📄 PRINT PREVIEW", font=(Theme.FONT_MONO[0], 12, "bold"),
                bg=Theme.BG_DARK, fg=Theme.PRIMARY).pack(anchor=tk.W, padx=15, pady=(15, 5))
        
        text = tk.Text(dialog, font=(Theme.FONT_MONO[0], 9), bg=Theme.BG_CARD,
                      fg=Theme.TEXT, relief=tk.FLAT, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        text.insert("1.0", report)
        text.config(state=tk.DISABLED)
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=Theme.BG_DARK)
        btn_frame.pack(fill=tk.X, padx=15, pady=15)
        
        def save_txt():
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                initialfile=f"oilgauge_report_{datetime.now():%Y%m%d_%H%M%S}.txt"
            )
            if path:
                with open(path, 'w') as f:
                    f.write(report)
                messagebox.showinfo("Saved", f"Report saved to:\n{path}")
        
        def print_to_printer():
            # Save to temp file and print
            import tempfile
            import os
            import subprocess
            
            try:
                # Create temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(report)
                    temp_path = f.name
                
                # Platform-specific print
                if sys.platform == 'win32':
                    # Windows: use notepad to print
                    os.startfile(temp_path, 'print')
                    messagebox.showinfo("Print", "Sending to printer via Notepad...\n\nThe print dialog should appear.")
                elif sys.platform == 'darwin':
                    # macOS
                    subprocess.run(['lpr', temp_path])
                    messagebox.showinfo("Print", "Sent to default printer.")
                else:
                    # Linux
                    subprocess.run(['lpr', temp_path])
                    messagebox.showinfo("Print", "Sent to default printer.")
            except Exception as e:
                messagebox.showerror("Print Error", f"Could not print:\n{e}\n\nTry saving as text file instead.")
        
        def copy_to_clipboard():
            self.clipboard_clear()
            self.clipboard_append(report)
            messagebox.showinfo("Copied", "Report copied to clipboard!")
        
        ttk.Button(btn_frame, text="🖨️ Print", command=print_to_printer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 Save as TXT", command=save_txt).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📋 Copy", command=copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)


# ═══════════════════════════════════════════════════════════════════════════════
# Gauge Widget
# ═══════════════════════════════════════════════════════════════════════════════

class PressureGauge(tk.Canvas):
    """Custom radial gauge widget."""
    
    def __init__(self, parent, size=280, min_val=0, max_val=100):
        super().__init__(parent, width=size, height=size, 
                        bg=Theme.BG_CARD, highlightthickness=0)
        self.size = size
        self.min_val = min_val
        self.max_val = max_val
        self.value = 0
        self.cx = size // 2
        self.cy = size // 2
        self.radius = size // 2 - 35
        
        self._draw_static()
        self._draw_needle()
    
    def _draw_static(self):
        """Draw static gauge elements."""
        cx, cy, r = self.cx, self.cy, self.radius
        
        # Outer glow
        for i in range(2):
            self.create_oval(cx - r - 12 + i*4, cy - r - 12 + i*4,
                           cx + r + 12 - i*4, cy + r + 12 - i*4,
                           outline=Theme.PRIMARY, width=1)
        
        # Background arc
        self.create_arc(cx - r, cy - r, cx + r, cy + r,
                       start=225, extent=-270, style="arc",
                       outline=Theme.BG_INPUT, width=18)
        
        # Colored zones
        zones = [(225, -90, Theme.GAUGE_SAFE), (135, -90, Theme.GAUGE_WARN), (45, -90, Theme.GAUGE_DANGER)]
        for start, extent, color in zones:
            self.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=start, extent=extent, style="arc",
                          outline=color, width=10)
        
        # Ticks and labels
        for i in range(11):
            angle = math.radians(225 - 27 * i)
            x1 = cx + (r - 22) * math.cos(angle)
            y1 = cy - (r - 22) * math.sin(angle)
            x2 = cx + (r - 8) * math.cos(angle)
            y2 = cy - (r - 8) * math.sin(angle)
            self.create_line(x1, y1, x2, y2, fill=Theme.TEXT_DIM, width=2 if i % 2 == 0 else 1)
            
            if i % 2 == 0:
                val = self.min_val + (self.max_val - self.min_val) * i // 10
                lx = cx + (r - 38) * math.cos(angle)
                ly = cy - (r - 38) * math.sin(angle)
                self.create_text(lx, ly, text=str(val), fill=Theme.TEXT_DIM,
                               font=(Theme.FONT_MONO[0], 9, "bold"))
        
        self.create_text(cx, cy + 45, text="PSI", fill=Theme.TEXT_MUTED,
                        font=(Theme.FONT_MONO[0], 11))
    
    def _draw_needle(self):
        """Draw the gauge needle."""
        self.delete("needle")
        cx, cy = self.cx, self.cy
        
        pct = max(0, min(1, (self.value - self.min_val) / (self.max_val - self.min_val)))
        angle = math.radians(225 - 270 * pct)
        
        tip_x = cx + (self.radius - 28) * math.cos(angle)
        tip_y = cy - (self.radius - 28) * math.sin(angle)
        
        self.create_line(cx + 2, cy + 2, tip_x + 2, tip_y + 2, fill="#000", width=5, tags="needle")
        self.create_line(cx, cy, tip_x, tip_y, fill=Theme.DANGER, width=3, tags="needle")
        self.create_oval(cx - 10, cy - 10, cx + 10, cy + 10,
                        fill=Theme.BG_DARK, outline=Theme.DANGER, width=2, tags="needle")
        self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=Theme.DANGER, tags="needle")
    
    def set_value(self, value: float):
        self.value = value
        self._draw_needle()


# ═══════════════════════════════════════════════════════════════════════════════
# Main Application
# ═══════════════════════════════════════════════════════════════════════════════

class OilGaugeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.configure(bg=Theme.BG_DARK)
        self.root.geometry("1000x750")
        self.root.minsize(900, 650)
        
        # State
        self.client = None
        self.connected = False
        self.current_psi = 0.0
        self.current_error = None
        self.recording = False
        self.session_start = None
        
        # Stats
        self.min_psi = float('inf')
        self.max_psi = float('-inf')
        
        # Data
        self.history = deque(maxlen=2000)
        self.graph_data = deque(maxlen=150)
        
        self._configure_styles()
        self._build_ui()
        self._start_updates()
    
    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background=Theme.BG_DARK)
        style.configure("Card.TFrame", background=Theme.BG_CARD)
        style.configure("TLabel", background=Theme.BG_DARK, foreground=Theme.TEXT, font=(Theme.FONT_UI[0], 10))
        style.configure("Card.TLabel", background=Theme.BG_CARD)
        style.configure("Title.TLabel", font=(Theme.FONT_MONO[0], 11, "bold"), foreground=Theme.PRIMARY)
        style.configure("Value.TLabel", font=(Theme.FONT_MONO[0], 32, "bold"))
        style.configure("Stat.TLabel", font=(Theme.FONT_MONO[0], 14, "bold"))
        style.configure("StatLabel.TLabel", font=(Theme.FONT_UI[0], 9), foreground=Theme.TEXT_DIM)
        style.configure("TButton", font=(Theme.FONT_UI[0], 10), padding=(12, 6))
        style.configure("Primary.TButton", font=(Theme.FONT_UI[0], 10, "bold"))
        style.map("Primary.TButton",
                 background=[("active", Theme.PRIMARY), ("!active", "#1f6feb")],
                 foreground=[("active", "#fff"), ("!active", "#fff")])
        style.configure("Record.TButton", font=(Theme.FONT_UI[0], 10, "bold"))
        style.map("Record.TButton",
                 background=[("active", Theme.DANGER), ("!active", "#8b0000")],
                 foreground=[("active", "#fff"), ("!active", "#fff")])
    
    def _build_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Row 1: Connection
        self._build_connection_bar(main)
        
        # Row 2: Main content
        content = ttk.Frame(main)
        content.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        # Left: Gauge
        left = ttk.Frame(content, style="Card.TFrame")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self._build_gauge_panel(left)
        
        # Right: Graph
        right = ttk.Frame(content, style="Card.TFrame")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self._build_graph_panel(right)
        
        # Row 3: Controls
        self._build_control_bar(main)
    
    def _build_connection_bar(self, parent):
        bar = ttk.Frame(parent, style="Card.TFrame", padding=12)
        bar.pack(fill=tk.X)
        
        # Left side
        left = ttk.Frame(bar, style="Card.TFrame")
        left.pack(side=tk.LEFT, fill=tk.X)
        
        ttk.Label(left, text="DEVICE", style="Title.TLabel", background=Theme.BG_CARD).pack(side=tk.LEFT)
        
        self.device_var = tk.StringVar(value=DEFAULT_DEVICE)
        ttk.Entry(left, textvariable=self.device_var, width=15).pack(side=tk.LEFT, padx=(15, 10))
        
        self.connect_btn = ttk.Button(left, text="Connect", style="Primary.TButton", command=self._toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(left, text="Scan", command=self._scan_devices).pack(side=tk.LEFT, padx=5)
        
        # Right side - Status
        self.status_var = tk.StringVar(value="● Disconnected")
        self.status_label = ttk.Label(bar, textvariable=self.status_var,
                                     font=(Theme.FONT_UI[0], 11, "bold"),
                                     foreground=Theme.DANGER, background=Theme.BG_CARD)
        self.status_label.pack(side=tk.RIGHT, padx=10)
    
    def _build_gauge_panel(self, parent):
        parent.configure(padding=20)
        
        ttk.Label(parent, text="PRESSURE", style="Title.TLabel", background=Theme.BG_CARD).pack(anchor=tk.W)
        
        self.gauge = PressureGauge(parent, size=280)
        self.gauge.pack(pady=15)
        
        self.psi_var = tk.StringVar(value="0.0")
        ttk.Label(parent, textvariable=self.psi_var, style="Value.TLabel", background=Theme.BG_CARD).pack()
        ttk.Label(parent, text="PSI", font=(Theme.FONT_UI[0], 11), foreground=Theme.TEXT_DIM, background=Theme.BG_CARD).pack()
        
        self.error_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.error_var, foreground=Theme.DANGER, background=Theme.BG_CARD,
                 font=(Theme.FONT_UI[0], 10, "bold")).pack(pady=(10, 0))
        
        # Stats row
        stats = ttk.Frame(parent, style="Card.TFrame")
        stats.pack(fill=tk.X, pady=(20, 0))
        
        for side, label, color, var_name in [
            (tk.LEFT, "MIN", Theme.SUCCESS, "min_var"),
            (tk.RIGHT, "MAX", Theme.DANGER, "max_var")
        ]:
            f = ttk.Frame(stats, style="Card.TFrame")
            f.pack(side=side, expand=True)
            ttk.Label(f, text=label, style="StatLabel.TLabel", background=Theme.BG_CARD).pack()
            var = tk.StringVar(value="--")
            setattr(self, var_name, var)
            ttk.Label(f, textvariable=var, style="Stat.TLabel", foreground=color, background=Theme.BG_CARD).pack()
    
    def _build_graph_panel(self, parent):
        parent.configure(padding=20)
        
        ttk.Label(parent, text="HISTORY", style="Title.TLabel", background=Theme.BG_CARD).pack(anchor=tk.W)
        
        if HAS_MATPLOTLIB:
            self.fig = Figure(figsize=(6, 4), dpi=100, facecolor=Theme.BG_CARD)
            self.ax = self.fig.add_subplot(111)
            self._style_graph()
            self.canvas = FigureCanvasTkAgg(self.fig, parent)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        else:
            ttk.Label(parent, text="Graph requires matplotlib\npip install matplotlib",
                     background=Theme.BG_CARD, foreground=Theme.TEXT_DIM).pack(expand=True)
    
    def _style_graph(self):
        self.ax.set_facecolor(Theme.BG_DARK)
        self.ax.tick_params(colors=Theme.TEXT_DIM, labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color(Theme.GRAPH_GRID)
        self.ax.set_ylim(0, 100)
        self.ax.set_ylabel("PSI", color=Theme.TEXT_DIM, fontsize=9)
        self.ax.grid(True, color=Theme.GRAPH_GRID, alpha=0.5, linestyle='-', linewidth=0.5)
        self.fig.tight_layout(pad=2)
    
    def _build_control_bar(self, parent):
        bar = ttk.Frame(parent, style="Card.TFrame", padding=12)
        bar.pack(fill=tk.X, pady=(15, 0))
        
        # Left: Session controls
        left = ttk.Frame(bar, style="Card.TFrame")
        left.pack(side=tk.LEFT)
        
        ttk.Label(left, text="SESSION", style="Title.TLabel", background=Theme.BG_CARD).pack(side=tk.LEFT)
        
        self.record_btn = ttk.Button(left, text="● Record", style="Record.TButton", command=self._toggle_recording)
        self.record_btn.pack(side=tk.LEFT, padx=(20, 5))
        
        ttk.Button(left, text="Save", command=self._save_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(left, text="Open Log", command=self._open_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(left, text="Reset", command=self._reset_stats).pack(side=tk.LEFT, padx=5)
        
        # Right: Info
        right = ttk.Frame(bar, style="Card.TFrame")
        right.pack(side=tk.RIGHT)
        
        self.info_var = tk.StringVar(value="Ready")
        ttk.Label(right, textvariable=self.info_var, foreground=Theme.TEXT_DIM, background=Theme.BG_CARD).pack(side=tk.RIGHT)
        
        self.record_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.record_var, foreground=Theme.DANGER, background=Theme.BG_CARD,
                 font=(Theme.FONT_UI[0], 10, "bold")).pack(side=tk.RIGHT, padx=(0, 15))

    # ═══════════════════════════════════════════════════════════════════════════
    # BLE Methods
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _toggle_connection(self):
        if self.connected:
            self.connected = False
        else:
            self.connect_btn.config(state=tk.DISABLED)
            self._set_status("Connecting...", Theme.WARNING)
            threading.Thread(target=self._ble_thread, daemon=True).start()
    
    def _ble_thread(self):
        asyncio.run(self._ble_connect())
    
    async def _ble_connect(self):
        try:
            name = self.device_var.get()
            self._set_status(f"Scanning for {name}...", Theme.WARNING)
            
            devices = await BleakScanner.discover(timeout=5.0)
            addr = next((d.address for d in devices if d.name == name), None)
            
            if not addr:
                raise RuntimeError(f"'{name}' not found")
            
            self._set_status("Connecting...", Theme.WARNING)
            self.client = BleakClient(addr)
            await self.client.connect()
            
            if self.client.is_connected:
                self.connected = True
                self._set_status("● Connected", Theme.SUCCESS)
                self.root.after(0, lambda: self.connect_btn.config(text="Disconnect", state=tk.NORMAL))
                
                await self.client.start_notify(CHAR_UUID, self._on_data)
                
                while self.connected and self.client.is_connected:
                    await asyncio.sleep(0.5)
                
                await self.client.stop_notify(CHAR_UUID)
        except Exception as e:
            self._set_status(f"Error: {e}", Theme.DANGER)
        finally:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
            self.connected = False
            self._set_status("● Disconnected", Theme.DANGER)
            self.root.after(0, lambda: self.connect_btn.config(text="Connect", state=tk.NORMAL))
    
    def _on_data(self, sender, data: bytearray):
        psi, error = decode_ble_data(data)
        self.current_psi = psi
        self.current_error = error
        
        if error is None and psi > 0:
            self.min_psi = min(self.min_psi, psi)
            self.max_psi = max(self.max_psi, psi)
        
        if self.recording:
            self.history.append({"time": datetime.now().isoformat(), "psi": psi, "error": error})
        
        self.graph_data.append(psi)
        self.root.after(0, self._update_ui)
    
    def _scan_devices(self):
        def scan():
            async def do_scan():
                self._set_status("Scanning...", Theme.WARNING)
                devices = await BleakScanner.discover(timeout=5.0)
                names = sorted(set(d.name for d in devices if d.name))
                self._set_status(f"Found {len(names)} devices", Theme.TEXT_DIM)
                if names:
                    msg = "Found devices:\n\n" + "\n".join(f"• {n}" for n in names[:15])
                    self.root.after(0, lambda: messagebox.showinfo("BLE Scan", msg))
            asyncio.run(do_scan())
        threading.Thread(target=scan, daemon=True).start()
    
    def _set_status(self, text: str, color: str):
        self.root.after(0, lambda: (self.status_var.set(text), self.status_label.config(foreground=color)))

    # ═══════════════════════════════════════════════════════════════════════════
    # UI Updates
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _update_ui(self):
        self.gauge.set_value(self.current_psi)
        self.psi_var.set(f"{self.current_psi:.1f}")
        
        self.error_var.set(ERROR_DESC.get(self.current_error, "") if self.current_error else "")
        
        if self.min_psi != float('inf'):
            self.min_var.set(f"{self.min_psi:.1f}")
        if self.max_psi != float('-inf'):
            self.max_var.set(f"{self.max_psi:.1f}")
        
        if self.recording:
            self.info_var.set(f"Samples: {len(self.history)}")
    
    def _start_updates(self):
        if HAS_MATPLOTLIB:
            self._update_graph()
    
    def _update_graph(self):
        if self.graph_data:
            self.ax.clear()
            self._style_graph()
            y = list(self.graph_data)
            self.ax.fill_between(range(len(y)), y, alpha=0.2, color=Theme.GRAPH_LINE)
            self.ax.plot(y, color=Theme.GRAPH_LINE, linewidth=1.5)
            if y:
                ymin, ymax = min(y), max(y)
                margin = max(5, (ymax - ymin) * 0.1)
                self.ax.set_ylim(max(0, ymin - margin), ymax + margin)
            self.canvas.draw_idle()
        self.root.after(500, self._update_graph)

    # ═══════════════════════════════════════════════════════════════════════════
    # Session Management
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.session_start = datetime.now()
            self.history.clear()
            self.record_btn.config(text="■ Stop")
            self.record_var.set("● REC")
        else:
            self.record_btn.config(text="● Record")
            self.record_var.set("")
            self.info_var.set(f"Stopped: {len(self.history)} samples")
    
    def _save_session(self):
        if not self.history:
            messagebox.showwarning("No Data", "No data recorded yet.\n\nClick '● Record' to start recording data.")
            return
        
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"oilgauge_{datetime.now():%Y%m%d_%H%M%S}.json"
        )
        if path:
            data = {
                "app_version": APP_VERSION,
                "device": self.device_var.get(),
                "start_time": self.session_start.isoformat() if self.session_start else None,
                "end_time": datetime.now().isoformat(),
                "samples": len(self.history),
                "min_psi": self.min_psi if self.min_psi != float('inf') else None,
                "max_psi": self.max_psi if self.max_psi != float('-inf') else None,
                "data": list(self.history)
            }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Saved", f"Session saved:\n{path}")
    
    def _open_log(self):
        """Open and view a data log file."""
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            try:
                with open(path) as f:
                    data = json.load(f)
                
                # Open viewer dialog
                DataLogViewer(self.root, data)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file:\n{e}")
    
    def _reset_stats(self):
        self.min_psi = float('inf')
        self.max_psi = float('-inf')
        self.min_var.set("--")
        self.max_var.set("--")
        self.graph_data.clear()
        self.history.clear()
        self.info_var.set("Stats reset")
        self.record_var.set("")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    app = OilGaugeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
