# error_check.py

# ------------------------------
# Voltage thresholds
# ------------------------------

# MCP3008 ADC safety limits
ADC_HIGH_THRESHOLD = 3.4     # Short to 5V / over-voltage
ADC_LOW_THRESHOLD = 0.10     # Short to ground

# Sensor spec (0.5–4.5V usable range)
SENSOR_MIN = 0.5
SENSOR_MAX = 4.5

# Floating detection
FLOAT_THRESHOLD = 2.0          # Must jump more than 2V
FLOAT_CONSECUTIVE_REQUIRED = 2 # Must happen twice in a row (prevents false triggers)
SMOOTH_WINDOW = 3              # Moving average samples


# ------------------------------
# Helper state (auto-created)
# ------------------------------

# Keep last few voltages for smoothing
_last_voltages = []

# Count consecutive large jumps
_float_jump_count = 0


# ------------------------------
# Error check function
# ------------------------------
def check_errors(adc_voltage, sensor_voltage, prev_voltage=None):
    global _float_jump_count, _last_voltages

    # ---------------------------------------
    # 1. Apply simple smoothing (moving avg)
    # ---------------------------------------
    _last_voltages.append(sensor_voltage)
    if len(_last_voltages) > SMOOTH_WINDOW:
        _last_voltages.pop(0)

    avg_voltage = sum(_last_voltages) / len(_last_voltages)

    # ---------------------------------------
    # 2. Highest priority errors (don’t change)
    # ---------------------------------------

    # Over-voltage / short to +5V
    if adc_voltage > ADC_HIGH_THRESHOLD:
        _float_jump_count = 0
        return "VHIGH"

    # Under-voltage / short to GND
    if adc_voltage < ADC_LOW_THRESHOLD:
        _float_jump_count = 0
        return "VLOW"

    # Out-of-range sensor values
    if avg_voltage < SENSOR_MIN or avg_voltage > SENSOR_MAX:
        _float_jump_count = 0
        return "SENSOR_OOR"

    # ---------------------------------------
    # 3. Floating detection (low priority)
    # - Requires consecutive large jumps
    # ---------------------------------------
    if prev_voltage is not None:
        if abs(avg_voltage - prev_voltage) > FLOAT_THRESHOLD:
            _float_jump_count += 1
        else:
            _float_jump_count = 0

        if _float_jump_count >= FLOAT_CONSECUTIVE_REQUIRED:
            return "FLOATING"

    # ---------------------------------------
    # 4. No error
    # ---------------------------------------
    return None
