from machine import Pin, I2C
import ssd1306

# Constants for the OLED dimensions
OLED_WIDTH = 128
OLED_HEIGHT = 32

# Setup I2C
# Use GPIO16 for SDA and GPIO17 for SCL
i2c = I2C(1, scl=Pin(27), sda=Pin(26), freq=400000)

# Initialize the OLED display
oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# Clear the display
oled.fill(0)
oled.show()

# Display some text
oled.text('SSID -> mem4', 0, 0)  # Display at position x=0, y=0
oled.text('192.168.1.163', 0, 10)  # Display at position x=0, y=10
oled.text('next evt: 12:53', 0, 20)      # Display at position x=0, y=20
oled.show()

