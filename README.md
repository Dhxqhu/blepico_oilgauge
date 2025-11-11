# 🛠️ Oil Pressure Gauge Simulator — Raspberry Pi Pico WH

A modular MicroPython project that simulates an oil pressure gauge using a potentiometer, MCP3008 ADC, and Raspberry Pi Pico WH. It transmits readings via BLE to a mobile app and displays live data on an LCD screen.

## 📦 Features

- Simulated analog input using a potentiometer  
- MCP3008 ADC for precise voltage-to-digital conversion  
- BLE transmission to mobile devices (e.g., nRF Connect)  
- Real-time display on 1602 LCD via I²C  
- Modular MicroPython codebase for easy debugging and upgrades  

## 🧰 Hardware Used

| Component            | Description                                      |
|---------------------|--------------------------------------------------|
| Raspberry Pi Pico WH| Microcontroller with onboard wireless (BLE)      |
| MCP3008             | 8-channel 10-bit ADC for analog input            |
| Potentiometer       | Simulates oil pressure sensor                    |
| 1602 LCD Display     | I²C interface for live data visualization        |
| Breadboard & Wires  | For prototyping and connections                  |

## 🔌 Wiring Overview

### MCP3008 to Pico WH (SPI)
- **VDD/VREF** → 3.3V  
- **AGND/DGND** → GND  
- **CLK** → GP10  
- **DOUT** → GP12  
- **DIN** → GP11  
- **CS/SHDN** → GP13  

### LCD (I²C)
- **SDA** → GP0  
- **SCL** → GP1  
- **VCC/GND** → 5V/GND  

### Potentiometer
- **VCC** → 3.3V  
- **GND** → GND  
- **Signal** → MCP3008 CH0  

## 📁 Project Structure

```
blepico_oilgauge/
├── main.py            # Entry point: initializes modules and runs main loop
├── ble_service.py     # BLE advertising and data transmission logic
├── cpuoilpressure.py  # Reads and processes oil pressure data from MCP3008
├── display.py         # LCD display logic via I²C
├── mcp3008.py         # SPI interface for MCP3008 ADC
├── README.md          # Project documentation
├── .gitattributes     # Git settings (optional)
```

## 🚀 Getting Started

1. Flash MicroPython to your Pico WH  
2. Use Thonny or VS Code with the Pico SDK to upload files  
3. Connect hardware as per wiring diagram  
4. Run `main.py` to start the simulation  
5. Use a BLE app (e.g., nRF Connect) to view transmitted data  

## 📊 Output Example

- LCD: `Oil Pressure: 42.3 PSI`  
- BLE: `{"pressure": 42.3}`  

## 🧠 Concepts Covered

- SPI communication with MCP3008  
- I²C display control  
- BLE advertising and data packets  
- Modular MicroPython architecture  
- Real-world sensor simulation  

## 🛠️ Future Improvements

- Replace potentiometer with actual pressure sensor  
- Add OLED display support  
- Implement mobile app for BLE data visualization  
- Add logging and calibration features  

## 📜 License

MIT License — feel free to fork, modify, and build upon it.
