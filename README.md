# Oil Pressure Gauge — Raspberry Pi Pico WH + BLE

A MicroPython project that reads oil pressure from an analog sensor via MCP3008 ADC, displays readings on an LCD, and transmits data over Bluetooth Low Energy to PC/mobile clients.

## Features

**Pico WH (Peripheral)**
- MCP3008 ADC for precise analog-to-digital conversion
- Voltage divider support for 0-5V sensors
- Real-time BLE transmission with error detection
- 1602 LCD display with connection status
- Comprehensive error checking (over/under voltage, floating signal, out-of-range)

**PC Client**
- Modern GUI with radial pressure gauge
- Real-time graph with history
- Session recording, save & load (JSON)
- BLE device scanning and connection management
- CLI client for headless operation

## Hardware

| Component | Description |
|-----------|-------------|
| Raspberry Pi Pico WH | Microcontroller with BLE |
| MCP3008 | 8-channel 10-bit SPI ADC |
| Oil Pressure Sensor | 0.5-4.5V output (0-100 PSI) |
| 10kΩ + 15kΩ Resistors | Voltage divider for 5V→3.3V |
| 1602 LCD (I2C) | Status display |

## Wiring

### MCP3008 → Pico (SPI0)
| MCP3008 | Pico |
|---------|------|
| VDD, VREF | 3.3V |
| AGND, DGND | GND |
| CLK | GP18 |
| DOUT | GP16 |
| DIN | GP19 |
| CS | GP17 |

### LCD → Pico (I2C0)
| LCD | Pico |
|-----|------|
| SDA | GP0 |
| SCL | GP1 |
| VCC | 5V |
| GND | GND |

### Pressure Sensor
```
Sensor 0.5-4.5V output
        │
        ├──[10kΩ]──┬── MCP3008 CH0
        │          │
        └──[15kΩ]──┴── GND
```

## Project Structure

```
blepico_oilgauge/
├── main.py           # Main loop: ADC read, BLE send, LCD display
├── ble_service.py    # BLE peripheral service (advertising, notifications)
├── mcp3008.py        # MCP3008 SPI driver
├── error_check.py    # Sensor fault detection
├── display.py        # OLED display driver (optional SSD1306)
├── client.py         # CLI BLE client
├── client_gui.py     # GUI BLE client with gauge & graph
└── README.md
```

## Installation

### Pico WH Setup

1. Flash MicroPython to your Pico WH
2. Install required libraries via Thonny:
   - `i2c_lcd` (for 1602 LCD)
3. Upload all `.py` files to the Pico
4. Run `main.py`

### PC Client Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run CLI client
python client.py

# Run GUI client
python client_gui.py
```

### Build Standalone Executable

```bash
# Install build dependencies
pip install pyinstaller

# Build executable
python build.py

# Output: dist/OilGaugeMonitor.exe
```

## BLE Protocol

**Service UUID:** `e7c9c910-7f6f-4b02-bc6d-1d9d3f3b0010`  
**Characteristic UUID:** `e7c9c911-7f6f-4b02-bc6d-1d9d3f3b0010`

**Data Format (3 bytes):**
| Byte | Type | Description |
|------|------|-------------|
| 0-1 | u16 LE | PSI × 10 (0.1 PSI resolution) |
| 2 | u8 | Error code |

**Error Codes:**
| Code | Meaning |
|------|---------|
| 0 | OK |
| 1 | VHIGH - Over-voltage |
| 2 | VLOW - Under-voltage |
| 3 | SENSOR_OOR - Out of range |
| 4 | FLOATING - Unstable signal |

## GUI Features

- **Gauge:** Radial dial with color-coded zones (green/yellow/red)
- **Graph:** Rolling 100-sample history chart
- **Recording:** Capture sessions with timestamps
- **Save/Load:** Export to JSON for analysis
- **Scan:** Discover nearby BLE devices

## Calibration

Adjust these values in `main.py` for your setup:

```python
MCP3008_VREF = 3.30        # ADC reference voltage
DIVIDER_RATIO = 25000/15000 # Voltage divider ratio (R1+R2)/R2
```

In `error_check.py`:
```python
ADC_HIGH_THRESHOLD = 3.4   # Over-voltage limit
ADC_LOW_THRESHOLD = 0.10   # Under-voltage limit
SENSOR_MIN = 0.5           # Sensor minimum output
SENSOR_MAX = 4.5           # Sensor maximum output
```

## License

MIT License — feel free to fork, modify, and build upon it.
