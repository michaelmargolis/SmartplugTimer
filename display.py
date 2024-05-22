'''
display.py - simple interface to ssd1306 OLED_HEIGHT

this functionality requires ssd1306 module
if module cannot be imported the funcionality is disabled 
'''


try:
    from machine import Pin, I2C
    import ssd1306
    has_display = True # set this False to disable display
except ImportError:    
    has_display = False
    print("OLED display disabled (ssd1306 module not found)")

class Display():  
    def __init__(self, timeout_minutes = 0, trigger_pin = None):
        if has_display:
            i2c = I2C(1, scl=Pin(27), sda=Pin(26), freq=400000)
            OLED_WIDTH = 128
            OLED_HEIGHT = 32
            self.oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
            self.oled.fill(0)
            self.oled.show()
            self.timeout_seconds = timeout_minutes * 60
            self.start_timestamp = 0
            self.is_on = True # on by default
            if trigger_pin:
                self.trigger = machine.Pin(trigger_pin, Pin.IN, Pin.PULL_UP)
            else:
                self.trigger = None
        
    def show_connecting(self, ssid):
        if has_display:
            self.oled.fill(0)
            self.oled.text('Connecting ...', 0, 5)  # Display at position x=0, y=5
            self.oled.text('SSID: {}'.format(ssid), 0, 25)
            self.oled.show()

       
    def update(self, ip, evt_on_time, evt_off_time):
        if has_display:
            self.oled.fill(0)
            self.oled.text(ip, 0, 2)  # Display at position x=0, y=2
            self.oled.text(evt_on_time, 0, 12)
            self.oled.text(evt_off_time, 0, 22)
            self.oled.show()
        
    def check_timeout(self, current_timestamp):
        if has_display and self.timeout_seconds > 0:
            # print(current_timestamp,  self.start_timestamp + self.timeout_seconds)
            if self.is_on:
                if (current_timestamp >= self.start_timestamp + self.timeout_seconds):
                    self.is_on = False
                    self.oled.poweroff()
            else:
                if self.trigger and self.trigger.value() == 0:
                    self.wake(current_timestamp)  

    def wake(self, current_timestamp):
        if has_display:
            self.oled.poweron()
            self.is_on = True
            self.start_timestamp = current_timestamp
