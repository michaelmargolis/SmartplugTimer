'''
  wifi.py
  connects to WLAN if Pico-W or ESP32 
  uses existing network if Raspberry Pi or Windows
'''

import os
import sys
import socket

class WiFi(object):
    def __init__(self, timeout=0.5):
        self.timeout = timeout
        self.this_ip = None
        self.ssid = None
        self.password = None
        self.is_micropython = False

    def init_hardware(self):
        # print(os.uname())
        self.environ = 'UNKNOWN'
        try:
            # print(os.name)
            hostname = socket.gethostname()
            self.this_ip  = socket.gethostbyname(hostname)
            if os.name == 'posix':
                self.environ = 'POSIX'
                print("Env is Posix', this ip address is {}".format(self.this_ip))
            elif os.name == 'nt':
                self.environ = 'WINDOWS'
                print("Env is Windows, this ip address is {}".format(self.this_ip))
        except (ImportError, AttributeError):
            # here if micropython ?
            print("Environment is micropython")
            self.is_micropython = True
            try:
                import secrets
                self.ssid = secrets.SSID # store ssid for oled display
                self.password = secrets.PASSWORD
                machine = os.uname().machine
                if 'Pico W' in machine:
                    print('Pico W')
                    self.environ = 'PICO_W'
                elif 'ESP32' in machine:
                    print('ESP32')
                    self.environ = 'ESP32'
            except Exception as e:
                print(e, "hardware not identified")
                sys.print_exception(e)
            
    def connect(self):
        max_wait = 8
        try:
            if self.is_micropython:
                import network
                import time
                import gc                
                import urequests as requests
                
                wlan = network.WLAN(network.STA_IF)
                wlan.active(True)
                wlan.connect(self.ssid, self.password)
                print("Connecting to", self.ssid)
                # Wait for connect or fail

                while max_wait > 0:
                    if wlan.status() < 0 or wlan.status() >= 3:
                        break
                    max_wait -= 1
                    print('waiting for connection...')
                    time.sleep(1)

                # Handle connection error
                if wlan.status() != 3:
                    print(self._get_error_message(wlan.status()))
                    return False
                else:
                    print('connected')
                    status = wlan.ifconfig()
                    self.this_ip = status[0]
                    print('Pico ip = ' + self.this_ip )
                    gc.collect()
                    return True
                
            else:
                 if self.this_ip != None:
                     print("Using existing network, IP Address is {}".format(self.this_ip))
                     return True
                 else:
                     print("unable to get IP address")
                     return False
         
        except Exception as e:
            print(e)
            return False
        
        return True # assume using ethernet     

    def _get_error_message(self, status):
        error_messages = {
            network.STAT_IDLE: "Idle status.",
            network.STAT_CONNECTING: "Connecting...",
            network.STAT_WRONG_PASSWORD: "Wrong WiFi password.",
            network.STAT_NO_AP_FOUND: "Access point not found.",
            network.STAT_CONNECT_FAIL: "Connection failed.",
            network.STAT_GOT_IP: "Connected successfully and obtained an IP address."
        }    
        return error_messages.get(status, f"Unknown error with status code {status}.")
   
 