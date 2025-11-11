from machine import Pin, I2C
import ssd1306

# Initialize OLED display
i2c = I2C(0, scl=Pin(1), sda=Pin(0))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

def show_pressure(raw, psi):
    oled.fill(0)
    oled.text("Oil Pressure", 0, 0)
    oled.text("Raw: {}".format(raw), 0, 16)
    oled.text("PSI: {:.2f}".format(psi), 0, 32)
    oled.show()