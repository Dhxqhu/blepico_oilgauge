from machine import SPI, Pin, I2C
from ble_service import BLEPeripheral as BLEService
from mcp3008 import MCP3008
from i2c_lcd import I2cLcd
import time
import error_check

# ------------------------------------
# Timing controls
# ------------------------------------
BLE_INTERVAL_MS = 200      # BLE update interval (ms)
LCD_REFRESH_MS = 1200      # LCD refresh interval (ms)
LOOP_SLEEP_MS = 50         # main loop base sleep (ms)

_last_ble_send = 0
_last_lcd_update_time = 0  # for slower LCD refresh
_last_row_text = ["", ""]  # per-row cache

# connection-change cache for forcing immediate LCD updates
_last_conn_state = None

# ------------------------------------
# Smoothing
# ------------------------------------
ADC_OVERSAMPLE = 4        # Take multiple samples and average
ALPHA = 0.08              # EMA factor (lower = smoother, slower response)
DEADBAND = 1.5            # Only update stable value if change > this many ADC counts
raw_smooth = None         # Smoothed raw ADC value
raw_stable = None         # Stable value with deadband (used for calculations)
psi_smooth = None

# ------------------------------------
# MCP3008 ADC setup
# ------------------------------------
MCP3008_VREF = 3.30
spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs = Pin(17, Pin.OUT)
adc = MCP3008(spi, cs)

DIVIDER_RATIO = 25_000 / 15_000

# ------------------------------------
# BLE setup
# ------------------------------------
ble = BLEService(name="OilGauge")

# ------------------------------------
# LCD setup
# ------------------------------------
i2c = I2C(0, scl=Pin(1), sda=Pin(0))
lcd = I2cLcd(i2c, 0x27, 2, 16)

# ------------------------------------
# Boot sequence
# ------------------------------------
BOOT_DELAY_MS = 3000  # Time for capacitors to stabilize

def boot_screen():
    """Display boot sequence while hardware stabilizes."""
    lcd.clear()
    lcd.move_to(0, 0)
    lcd.putstr("  Oil  Gauge  ")
    lcd.move_to(0, 1)
    lcd.putstr("  Monitor v1.0  ")
    time.sleep_ms(1500)
    
    lcd.move_to(0, 1)
    lcd.putstr("Initializing... ")
    
    # Progress bar while waiting for capacitors
    lcd.move_to(0, 1)
    progress = ""
    steps = 16
    step_time = BOOT_DELAY_MS // steps
    for i in range(steps):
        progress += chr(255)  # Full block character
        lcd.move_to(0, 1)
        lcd.putstr(progress)
        time.sleep_ms(step_time)
    
    lcd.clear()
    print("Boot sequence complete, starting main loop...")

# Run boot sequence
boot_screen()

# ------------------------------------
# Voltage conversion helpers
# ------------------------------------
def raw_to_adc_voltage(raw):
    r = max(0, min(1023, raw))
    return (r / 1023.0) * MCP3008_VREF

def adc_to_sensor_voltage(adc_voltage):
    return adc_voltage * DIVIDER_RATIO

def voltage_to_psi(sensor_voltage):
    if sensor_voltage <= 0.5:
        return 0.0
    if sensor_voltage >= 4.5:
        return 100.0
    return (sensor_voltage - 0.5) * (100.0 / 4.0)

prev_sensor_voltage = None

# ------------------------------------
# LCD helper
# ------------------------------------
def lcd_line(row, text, force=False):
    try:
        s = "" if text is None else str(text)
        if len(s) < 16:
            s = s + (" " * (16 - len(s)))
        else:
            s = s[:16]

        now = time.ticks_ms()

        # If not forced and text unchanged, skip write
        if not force:
            if s == _last_row_text[row]:
                return

        lcd.move_to(0, row)
        lcd.putstr(s)
        _last_row_text[row] = s

    except Exception as e:
        print("LCD write failed:", e)

# ------------------------------------
# BLE helper
# ------------------------------------
def ble_send_safe(payload):
    try:
        if not getattr(ble, "conn_handle", None):
            return False
        s = str(payload)[:20]
        ble.send(s)
        return True
    except Exception as e:
        print("BLE send failed:", e)
        return False

# ------------------------------------
# Main loop
# ------------------------------------
while True:
    try:
        now = time.ticks_ms()

        # Read raw ADC value with oversampling
        total = 0
        for _ in range(ADC_OVERSAMPLE):
            total += adc.read(0)
        raw = total // ADC_OVERSAMPLE
        
        # Apply EMA smoothing to raw value
        if raw_smooth is None:
            raw_smooth = float(raw)
            raw_stable = float(raw)
        else:
            raw_smooth = ALPHA * raw + (1.0 - ALPHA) * raw_smooth
            # Only update stable value if smoothed moves beyond deadband
            if abs(raw_smooth - raw_stable) > DEADBAND:
                raw_stable = raw_smooth

        # Use stable value for calculations (eliminates small oscillations)
        adc_voltage = raw_to_adc_voltage(raw_stable)
        sensor_voltage = adc_to_sensor_voltage(adc_voltage)
        psi = voltage_to_psi(sensor_voltage)

        # Error checking
        try:
            error_code = error_check.check_errors(
                adc_voltage,
                sensor_voltage,
                prev_voltage=prev_sensor_voltage
            )
        except Exception as e:
            print("error_check failed:", e)
            error_code = "CHK"

        prev_sensor_voltage = sensor_voltage

        # ---------- Fast BLE updates ----------
        if time.ticks_diff(now, _last_ble_send) >= BLE_INTERVAL_MS:
            if error_code:
                ble_send_safe("ERR:" + str(error_code))
            else:
                ble_send_safe("{:.2f}".format(psi))
            _last_ble_send = now

        # ---------- Smoothing for LCD ----------
        if psi_smooth is None:
            psi_smooth = psi
        else:
            psi_smooth = ALPHA * psi + (1.0 - ALPHA) * psi_smooth

        # ---------- LCD updates (slower than main loop) ----------
        # Build the strings first (use rounded smoothed value for display)
        conn_current = ble.is_connected()
        row0_text = f"BLE:{'Connected' if conn_current else 'Waiting'}"

        if error_code:
            row1_text = f"ERROR:{error_code}"
        else:
            psi_disp = round(psi_smooth, 1)
            v_disp = round(sensor_voltage, 2)
            row1_text = "PSI:{:>5} V:{:>4}".format(psi_disp, v_disp)

        # If connection state changed, force immediate update of row0
        if conn_current != _last_conn_state:
            print(">>> STATE CHANGE: {} -> {}".format(_last_conn_state, conn_current))
            lcd_line(0, row0_text, force=True)
            _last_conn_state = conn_current
            # Also update row1 immediately so display is consistent
            lcd_line(1, row1_text, force=True)
            _last_lcd_update_time = now
        else:
            # Otherwise only update when refresh interval passed (and only write if text changed)
            if time.ticks_diff(now, _last_lcd_update_time) >= LCD_REFRESH_MS:
                lcd_line(0, row0_text)  # will skip if unchanged
                lcd_line(1, row1_text)
                _last_lcd_update_time = now

        # ---------- Console output (prints with LCD updates, not every loop) ----------
        # Only print when LCD was just updated to reduce serial traffic
        if time.ticks_diff(now, _last_lcd_update_time) <= LOOP_SLEEP_MS:
            print("Raw:{:<4} Smooth:{:<6.1f} Stable:{:<6.1f} PSI:{:>5.2f}  Err:{}"
                  .format(raw, raw_smooth, raw_stable, psi, error_code))

    except Exception as exc:
        print("Main loop exception:", exc)

    time.sleep_ms(LOOP_SLEEP_MS)
