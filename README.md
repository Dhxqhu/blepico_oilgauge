# Oil Pressure Gauge — Raspberry Pi Pico WH + BLE

A MicroPython project that reads oil pressure from an analog sensor via MCP3008 ADC, displays readings on an LCD, and transmits data over Bluetooth Low Energy to a Windows PC client.

## Features

**Pico WH (Peripheral)**
- MCP3008 ADC for precise analog-to-digital conversion
- Voltage divider support for 0-5V sensors
- Real-time BLE transmission with error detection
- 1602 LCD display with connection status

**PC Client**
- Modern GUI with radial pressure gauge
- Real-time graph with history
- Session recording, save & load (JSON)
- Export to CSV and print reports
- Standalone `.exe` - no installation required

---

## Quick Start

### Step 1: Set Up the Pico WH (Using Thonny)

1. **Install Thonny** from [thonny.org](https://thonny.org/)

2. **Connect your Pico WH** via USB

3. **Open Thonny** and select:
   - **Run → Configure interpreter**
   - Choose **"MicroPython (Raspberry Pi Pico)"**
   - Select your COM port

4. **Copy all files from the `pico/` folder to your Pico:**
   - In Thonny, go to **View → Files** to show the file browser
   - On the left (your computer), navigate to the `pico/` folder
   - Select each file, right-click → **"Upload to /"**
   
   Files to upload:
   ```
   pico/
   ├── boot.py          # Startup script
   ├── main.py          # Main program
   ├── ble_service.py   # BLE service
   ├── mcp3008.py       # ADC driver
   └── error_check.py   # Error detection
   ```

5. **Install the LCD library** (if using 1602 LCD):
   - In Thonny: **Tools → Manage packages**
   - Search for `lcd_i2c` or `i2c_lcd` and install

6. **Unplug and replug the Pico** - it will start automatically!

### Step 2: Install the PC Client

**Option A: Download the Release (Recommended)**
1. Go to the [Releases](../../releases) page
2. Download `OilGaugeMonitor.exe`
3. Run it - no installation needed!

**Option B: Run from Source**
```bash
cd client
pip install -r requirements.txt
python client_gui.py
```

### Step 3: Connect!

1. Power on your Pico WH (LCD should show "BLE: Waiting")
2. Open `OilGaugeMonitor.exe` on your PC
3. Click **Connect**
4. Watch your pressure readings in real-time!

---

## Project Structure

```
blepico_oilgauge/
├── pico/                    # Pico WH firmware (upload to device)
│   ├── boot.py              # Startup script
│   ├── main.py              # Main program loop
│   ├── ble_service.py       # BLE peripheral service
│   ├── mcp3008.py           # MCP3008 ADC driver
│   └── error_check.py       # Sensor fault detection
│
├── client/                  # Windows PC client
│   ├── client_gui.py        # GUI application
│   ├── client.py            # CLI client
│   ├── build.py             # Build script for .exe
│   └── requirements.txt     # Python dependencies
│
└── README.md
```

---

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
| MCP3008 | Pico | Pico SPI Name |
|---------|------|---------------|
| VDD, VREF | 3.3V | Power |
| AGND, DGND | GND | Ground |
| CLK | GP18 | SCK |
| DOUT | GP16 | MISO (data from MCP3008) |
| DIN | GP19 | MOSI (data to MCP3008) |
| CS/SHDN | GP17 | Chip Select |

### LCD → Pico (I2C0)
| LCD | Pico |
|-----|------|
| SDA | GP0 |
| SCL | GP1 |
| VCC | 5V |
| GND | GND |

### Pressure Sensor (with voltage divider)
```
Sensor 0.5-4.5V output
        │
        ├──[10kΩ]──┬── MCP3008 CH0
        │          │
        └──[15kΩ]──┴── GND
```

---

## Building the Windows Client

To build your own `.exe`:

```bash
cd client
pip install pyinstaller
python build.py
```

Output: `dist/OilGaugeMonitor.exe`

---

## BLE Protocol

**Service UUID:** `e7c9c910-7f6f-4b02-bc6d-1d9d3f3b0010`  
**Characteristic UUID:** `e7c9c911-7f6f-4b02-bc6d-1d9d3f3b0010`

**Data Format:** String-based PSI values
- Normal: `"42.50"` (PSI as string)
- Error: `"ERR:VHIGH"` (error code)

---

## Calibration

Edit `pico/main.py`:
```python
MCP3008_VREF = 3.30         # ADC reference voltage
DIVIDER_RATIO = 25000/15000 # Voltage divider ratio
```

Edit `pico/error_check.py`:
```python
ADC_HIGH_THRESHOLD = 3.4    # Over-voltage limit
ADC_LOW_THRESHOLD = 0.10    # Under-voltage limit
SENSOR_MIN = 0.5            # Sensor minimum output
SENSOR_MAX = 4.5            # Sensor maximum output
```

---

## ADC Smoothing Configuration

### Why Smoothing is Needed

The analog signal path introduces noise that causes ADC readings to fluctuate:

1. **Voltage divider resistors** - Resistor tolerance and thermal noise add small voltage variations
2. **Voltage amplifier** - Op-amp circuits amplify both signal and noise
3. **ADC quantization** - When the actual voltage sits right at the boundary between two digital levels (e.g., between 417 and 418), even tiny noise causes the reading to bounce back and forth between those values

Even with hardware filtering capacitors (10µF + 100nF on signal and VREF), there's often residual 1-count oscillation. The software smoothing eliminates this jitter to provide stable, usable readings.

### Smoothing Parameters

Edit these values at the top of `pico/main.py`:

```python
ADC_OVERSAMPLE = 4    # Number of rapid samples to average
ALPHA = 0.08          # EMA filter factor (0.0-1.0)
DEADBAND = 1.5        # Minimum change to update stable value (ADC counts)
```

### How Each Parameter Works

| Parameter | Default | Effect |
|-----------|---------|--------|
| `ADC_OVERSAMPLE` | 4 | Takes N rapid readings and averages them. Higher = less noise but slower reads. Try 4-16. |
| `ALPHA` | 0.08 | Exponential Moving Average factor. **Lower = smoother but slower response**. **Higher = faster but more jitter**. Range: 0.05 (very smooth) to 0.3 (responsive). |
| `DEADBAND` | 1.5 | Only updates the output when the smoothed value changes by more than this many ADC counts. Eliminates single-count oscillation. Try 1.0-3.0. |

### Tuning Guide

**If readings still jitter:**
- Decrease `ALPHA` (try 0.05)
- Increase `DEADBAND` (try 2.0 or 2.5)
- Increase `ADC_OVERSAMPLE` (try 8)

**If readings respond too slowly to real changes:**
- Increase `ALPHA` (try 0.15)
- Decrease `DEADBAND` (try 1.0)
- Decrease `ADC_OVERSAMPLE` (try 2)

### Smoothing Flow

```
Raw ADC → Oversample (average N reads) → EMA Filter → Deadband → Stable Output
                                                                      ↓
                                                            Used for PSI calculation
```

### Hardware Filtering (Recommended)

For best results, add filtering capacitors to your circuit:
- **10µF electrolytic + 100nF ceramic** in parallel on the sensor signal line
- **10µF electrolytic + 100nF ceramic** in parallel on MCP3008 VREF

This reduces noise at the hardware level before it reaches the ADC.

---

## Roadmap / Future Improvements

- [x] **Signal filtering** - hardware capacitors + software smoothing documented
- [ ] **Full wiring diagram** with filtering capacitors and optimized voltage divider
- [ ] **Orderable PCB** design (KiCad/EasyEDA files for custom board)
- [ ] **Step-by-step video guide** for assembly and setup
- [ ] **GUI improvements** - additional features and UI polish

---

## License

MIT License — feel free to fork, modify, and build upon it.
