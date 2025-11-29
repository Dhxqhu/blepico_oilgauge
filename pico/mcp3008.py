class MCP3008:
    def __init__(self, spi, cs):
        self.spi = spi
        self.cs = cs
        self._buf = bytearray(3)

    def read(self, channel):
        # MCP3008 protocol: send start bit, single-ended mode, channel select
        cmd = bytearray([0x01, (0x80 | (channel << 4)), 0x00])
        self.cs.value(0)
        self.spi.write_readinto(cmd, self._buf)
        self.cs.value(1)
        # 10-bit result: bits [1:0] of byte 1, all 8 bits of byte 2
        return ((self._buf[1] & 0x03) << 8) | self._buf[2]
