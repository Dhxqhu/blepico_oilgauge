# ble_service.py — MicroPython BLE peripheral (notify) with logging and helpers
import ubluetooth as bt
import struct
import sys

class BLEPeripheral:
    def __init__(self, name="OilGauge"):
        self.name = name
        self._ble = bt.BLE()
        self._ble.active(True)
        self.conn_handle = None
        self._connected = False  # reliable flag

        # Service and characteristic UUIDs
        self._SERVICE_UUID = bt.UUID("e7c9c910-7f6f-4b02-bc6d-1d9d3f3b0010")
        self._CHAR_UUID    = bt.UUID("e7c9c911-7f6f-4b02-bc6d-1d9d3f3b0010")

        # Characteristic: readable and notifiable
        CHAR = (self._CHAR_UUID, bt.FLAG_READ | bt.FLAG_NOTIFY)
        SERVICE = (self._SERVICE_UUID, (CHAR,))
        ((self._char_handle,),) = self._ble.gatts_register_services((SERVICE,))

        # Register IRQ and start advertising
        self._ble.irq(self._irq)
        self._advertise(self.name)

        # Debug: print expected IRQ constants
        try:
            print("IRQ constants: CONNECT={} DISCONNECT={}".format(
                bt._IRQ_CENTRAL_CONNECT, bt._IRQ_CENTRAL_DISCONNECT))
        except:
            print("IRQ constants not accessible via bt module")
        
        print("BLEPeripheral initialized, service UUID:", self._SERVICE_UUID)

    def is_connected(self):
        return self._connected

    def _advertise(self, name, interval_us=500_000):
        # Build a minimal advertising payload with flags + name
        try:
            flags = bytes([0x02, 0x01, 0x06])
            name_field = bytes([len(name) + 1, 0x09]) + name.encode()
            payload = flags + name_field
            self._ble.gap_advertise(interval_us, adv_data=payload)
            print("Advertising as:", name)
        except Exception as e:
            print("Advertise failed:", e)

    def _irq(self, event, data):
        # Log ALL events for debugging
        print(">>> IRQ event={} data={}".format(event, data))
        
        try:
            # _IRQ_CENTRAL_CONNECT is typically 1
            if event == 1:
                # data[0] is the connection handle
                self.conn_handle = data[0]
                self._connected = True
                print(">>> CONNECTED! handle=", self.conn_handle)
            # _IRQ_CENTRAL_DISCONNECT is typically 2
            elif event == 2:
                print(">>> DISCONNECTED! handle=", self.conn_handle)
                self.conn_handle = None
                self._connected = False
                # restart advertising with the stored name
                self._advertise(self.name)
        except Exception as e:
            print("IRQ handler error:", e)

    def send(self, s):
        """
        Backwards-compatible send: accepts str or bytes/bytearray.
        Logs what is being written and notifies if connected.
        """
        try:
            if isinstance(s, str):
                b = s.encode("utf-8")
            elif isinstance(s, (bytes, bytearray)):
                b = bytes(s)
            else:
                # Try to coerce other types (e.g., int) to bytes safely
                b = bytes(str(s), "utf-8")

            # Reduced logging - was causing timing issues with fast BLE interval
            # print("BLE send(): writing bytes:", b.hex(), "connected=", self._connected, "handle=", self.conn_handle)
            self._ble.gatts_write(self._char_handle, b)
            if self._connected and self.conn_handle is not None:
                self._ble.gatts_notify(self.conn_handle, self._char_handle)
            return True
        except Exception as e:
            print("BLE send failed:", e)
            return False

    def send_bytes(self, b):
        """
        Send raw bytes/bytearray. Logs and notifies.
        """
        try:
            bb = bytes(b)
            print("BLE send_bytes():", bb.hex(), "connected=", self._connected, "handle=", self.conn_handle)
            self._ble.gatts_write(self._char_handle, bb)
            if self._connected and self.conn_handle is not None:
                self._ble.gatts_notify(self.conn_handle, self._char_handle)
            return True
        except Exception as e:
            print("BLE send_bytes failed:", e)
            return False

    def send_psi_value(self, psi):
        """
        Pack PSI as uint16 little-endian where value = PSI * 10.
        Example: 12.3 PSI -> 123 -> b'\x7b\x00'
        """
        try:
            # clamp and convert
            u16 = int(round(max(0.0, min(6553.5, psi)) * 10))  # max PSI ~6553.5 to fit u16*10
            b = struct.pack("<H", u16)
            print("BLE send_psi_value(): psi=", psi, "u16=", u16, "bytes=", b.hex(),
                  "connected=", self._connected, "handle=", self.conn_handle)
            self._ble.gatts_write(self._char_handle, b)
            if self._connected and self.conn_handle is not None:
                self._ble.gatts_notify(self.conn_handle, self._char_handle)
            return True
        except Exception as e:
            print("BLE send_psi_value failed:", e)
            return False