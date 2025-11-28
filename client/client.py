"""
Oil Gauge BLE Client (CLI)
Connects to the OilGauge peripheral and displays pressure readings.
"""

import asyncio
from bleak import BleakScanner, BleakClient
import struct

# BLE Configuration - must match ble_service.py
DEVICE_NAME = "OilGauge"
SERVICE_UUID = "e7c9c910-7f6f-4b02-bc6d-1d9d3f3b0010"
CHAR_UUID = "e7c9c911-7f6f-4b02-bc6d-1d9d3f3b0010"

# Error code mapping (matches ble_service.py)
ERROR_CODES = {
    0: None,
    1: "VHIGH",
    2: "VLOW",
    3: "SENSOR_OOR",
    4: "FLOATING",
}


def decode_pressure_data(data: bytearray) -> tuple[float, str | None]:
    """
    Decode pressure data from the peripheral.
    Supports both formats:
    - Legacy string format: "42.50" or "ERR:VHIGH"
    - Binary format: [u16 psi_x10, u8 error_code]
    Returns: (psi, error_code_string or None)
    """
    # Try to decode as string first (legacy format)
    try:
        text = data.decode('utf-8').strip()
        
        # Check for error string format: "ERR:XXXX"
        if text.startswith("ERR:"):
            error_code = text[4:]
            return 0.0, error_code
        
        # Try to parse as float PSI value
        psi = float(text)
        return psi, None
    except (UnicodeDecodeError, ValueError):
        pass
    
    # Fall back to binary format
    if len(data) >= 3:
        psi_u16, err_byte = struct.unpack("<HB", data[:3])
        psi = psi_u16 / 10.0
        error = ERROR_CODES.get(err_byte)
        return psi, error
    elif len(data) >= 2:
        psi_u16 = struct.unpack("<H", data[:2])[0]
        return psi_u16 / 10.0, None
    
    return 0.0, "INVALID_DATA"


async def find_device(name: str = DEVICE_NAME) -> str:
    """Scan for the OilGauge device and return its address."""
    print(f"Scanning for '{name}'...")
    devices = await BleakScanner.discover(timeout=5.0)
    
    for d in devices:
        if d.name == name:
            print(f"Found: {d.name} [{d.address}]")
            return d.address
    
    raise RuntimeError(f"Device '{name}' not found. Is it advertising?")


def handle_notification(sender, data: bytearray):
    """Handle incoming BLE notifications."""
    psi, error = decode_pressure_data(data)
    
    if error:
        print(f"⚠️  ERROR: {error} | Last PSI: {psi:.1f}")
    else:
        print(f"🛢️  Pressure: {psi:.1f} PSI")


async def main():
    """Main entry point - connect and subscribe to notifications."""
    address = await find_device()
    
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        
        # Subscribe to notifications
        await client.start_notify(CHAR_UUID, handle_notification)
        print("Subscribed to pressure updates. Press Ctrl+C to quit.\n")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nDisconnecting...")
        finally:
            await client.stop_notify(CHAR_UUID)
    
    print("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
