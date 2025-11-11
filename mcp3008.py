class MCP3008:
    def __init__(self, spi, cs):
        self.spi = spi
        self.cs = cs

    def read(self, channel):
        self.cs.value(0)
        cmd = 0b11 << 6 | (channel & 0x07) << 3
        result = self.spi.read(3, cmd.to_bytes(1, 'big'))
        self.cs.value(1)
        return ((result[1] & 0x0F) << 8) | result[2]