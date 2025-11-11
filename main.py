from machine import SPI, Pin, I2C
from ble_service import BLEPeripheral
from mcp3008 import MCP3008
from i2c_lcd import I2cLcd
import time

# -------------------------------
# SPI setup for MCP3008 ADC
# -------------------------------
spi = SPI(0, baudrate=1000000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs = Pin(17, Pin.OUT)
adc = MCP3008(spi, cs)

# -------------------------------
# BLE setup
# -------------------------------
ble = BLEPeripheral(name="OilGauge")

# -------------------------------
# I2C setup for LCD (16x2)
# -------------------------------
i2c = I2C(0, scl=Pin(1), sda=Pin(0))
lcd = I2cLcd(i2c, 0x27, 2, 16)  # 2 rows, 16 columns

# -------------------------------
# Convert voltage to PSI
# -------------------------------
def voltage_to_psi(voltage, v_ref=3.3, max_psi=100):
    return (voltage / v_ref) * max_psi

# -------------------------------
# Main loop
# -------------------------------
while True:
    # Read ADC
    raw = adc.read(0)
    voltage = raw * 3.3 / 1023
    psi = voltage_to_psi(voltage)

    # ---------------------------
    # Send BLE notification (ASCII string)
    # ---------------------------
    ble.send("{:.2f}".format(psi))  # float as string

    # ---------------------------
    # Update LCD display
    # ---------------------------
    # First row: BLE connection status
    conn_status = "Connected" if ble.conn_handle else "Waiting"
    lcd.move_to(0, 0)
    lcd.putstr("BLE:{:<10}".format(conn_status))  # padded, max 16 chars

    # Second row: PSI numeric + bar graph (fits in 16 chars)
    bar_length = int((psi / 100) * 10)  # 10-character bar
    bar = "#" * bar_length + "-" * (10 - bar_length)
    lcd.move_to(0, 1)
    lcd.putstr("PSI:{:>5.1f} {}".format(psi, bar))  # total 16 chars

    # ---------------------------
    # Console output for debugging
    # ---------------------------
    print(f"Raw: {raw}, Voltage: {voltage:.2f}V, PSI: {psi:.2f}")

    time.sleep(1)
