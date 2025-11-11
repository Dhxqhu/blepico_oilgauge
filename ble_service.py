from bluetooth import BLE, UUID, FLAG_READ, FLAG_WRITE, FLAG_NOTIFY

class BLEPeripheral:
    def __init__(self, name="PicoBLE"):
        self.ble = BLE()
        self.ble.active(True)
        self.name = name
        self.conn_handle = None
        self._setup()

    def _setup(self):
        SERVICE_UUID = UUID('12345678-1234-5678-1234-56789abcdef0')
        CHAR_UUID = UUID('12345678-1234-5678-1234-56789abcdef1')

        self.service = (
            SERVICE_UUID,
            [(CHAR_UUID, FLAG_READ | FLAG_WRITE | FLAG_NOTIFY)],
        )

        ((self.service_handle, self.char_handle),) = self.ble.gatts_register_services([self.service])
        self.ble.irq(self._irq)

        adv_data = bytes([0x02, 0x01, 0x06]) + bytes([len(self.name) + 1, 0x09]) + self.name.encode()
        self.ble.gap_advertise(100, adv_data)

    def _irq(self, event, data):
        if event == 1:  # connected
            self.conn_handle, _, _ = data
            print("Connected:", self.conn_handle)
        elif event == 2:  # disconnected
            self.conn_handle = None
            print("Disconnected")
            adv_data = bytes([0x02, 0x01, 0x06]) + bytes([len(self.name) + 1, 0x09]) + self.name.encode()
            self.ble.gap_advertise(100, adv_data)

    def send(self, data):
        if not self.conn_handle:
            return
        self.ble.gatts_write(self.char_handle, data)
        self.ble.gatts_notify(self.conn_handle, self.char_handle, data)
