# boot.py - Runs on Pico WH power-on before main.py
# Oil Gauge BLE Monitor

import gc

# Free up memory before main.py runs
gc.collect()

# Print startup message (shows in Thonny serial monitor)
print("="*40)
print("Oil Gauge BLE Monitor")
print("Boot complete. Starting main.py...")
print("="*40)

# main.py runs automatically after this file completes

