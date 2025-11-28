"""
Build script for Oil Gauge Monitor
Creates a standalone executable using PyInstaller.

Usage:
    python build.py
    
Output:
    dist/OilGaugeMonitor.exe (Windows)
    dist/OilGaugeMonitor (macOS/Linux)
"""

import subprocess
import sys
import shutil
from pathlib import Path

APP_NAME = "OilGaugeMonitor"
MAIN_SCRIPT = "client_gui.py"
ICON_FILE = None  # Set to "icon.ico" if you have one

def build():
    print("=" * 60)
    print(f"Building {APP_NAME}")
    print("=" * 60)
    
    # Check PyInstaller is installed
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("✗ PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Clean previous builds
    for folder in ["build", "dist"]:
        if Path(folder).exists():
            print(f"Cleaning {folder}/...")
            shutil.rmtree(folder)
    
    # PyInstaller arguments
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",           # Single executable
        "--windowed",          # No console window
        "--clean",             # Clean cache
        "--noconfirm",         # Overwrite without asking
        
        # Hidden imports for BLE and matplotlib
        "--hidden-import", "bleak.backends.winrt",
        "--hidden-import", "bleak.backends.winrt.scanner",
        "--hidden-import", "bleak.backends.winrt.client",
        "--hidden-import", "matplotlib.backends.backend_tkagg",
        "--hidden-import", "PIL._tkinter_finder",
        
        # Exclude unnecessary modules to reduce size
        "--exclude-module", "PyQt5",
        "--exclude-module", "PyQt6", 
        "--exclude-module", "PySide2",
        "--exclude-module", "PySide6",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "notebook",
        "--exclude-module", "IPython",
    ]
    
    # Add icon if available
    if ICON_FILE and Path(ICON_FILE).exists():
        args.extend(["--icon", ICON_FILE])
    
    # Main script
    args.append(MAIN_SCRIPT)
    
    print("\nRunning PyInstaller...")
    print(f"Command: {' '.join(args[2:])}\n")
    
    result = subprocess.run(args)
    
    if result.returncode == 0:
        exe_path = Path("dist") / APP_NAME
        if sys.platform == "win32":
            exe_path = exe_path.with_suffix(".exe")
        
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 60)
            print(f"✓ Build successful!")
            print(f"  Output: {exe_path}")
            print(f"  Size: {size_mb:.1f} MB")
            print("=" * 60)
        else:
            print("\n✗ Build completed but executable not found")
    else:
        print("\n✗ Build failed")
        sys.exit(1)


if __name__ == "__main__":
    build()

