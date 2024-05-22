'''
  my_tasmota.py
  Class to turn on or off tasmota plugs using http protocol
 
  Update the smartplugs tuple with your plug ip addresses
  names field only used for debug printing, it does not need to match the actual plug name    
'''
import json
import time

try:
    from micropython import const
    import urequests as requests
    is_upython = True
except ImportError:
    const = lambda x : x
    is_upython = False
    import requests
    
smartplugs = const(( 
            # tuple of plug names and reserved (or static) Ip addresses   
            ('plug 14F0', '192.168.4.11'),
            ('plug EA2D', '192.168.4.12'),
            ('plug E946', '192.168.4.13')))

class my_tasmota():
    def __init__(self):
        pass

    def send_request(self, plug_ip, command):
        url = f"http://{plug_ip}/cm?cmnd={command}"
        try:
            # print(f"sending: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                # print(f"response: {response.json()}")
                return response.json()
            else:
                print(f"Error: {response.status_code}")
                return None
        except Exception as e:
            if is_upython:
                # Handle network-related errors in MicroPython
                if isinstance(e, OSError):
                    if e.args[0] == -2:
                        print("Network is unreachable")
                    elif e.args[0] == -3:
                        print("Temporary failure in name resolution")
                    elif e.args[0] == 110:
                        print("Connection timed out")
                    else:
                        print(f"An error occurred: {e}")
                else:
                    print(f"An error occurred: {e}")
            else:
                # Handle network-related errors in CPython
                if isinstance(e, requests.exceptions.RequestException):
                    print(f"Unable to connect to {plug_ip}")
                else:
                    print(f"An error occurred: {e}")
 
    def set_plug_state(self, index, state):
        plug_name,  plug_ip  = smartplugs[index]
        command = f"Power%20{state}"
        state_str = "On" if state == 1 else "Off" if state == 0 else "?"
        print("Setting {} ({}) {}".format(plug_name, plug_ip, state_str ))

        return self.send_request(plug_ip, command)

    def get_plug_state(self, index):
        plug_name,  plug_ip = smartplugs[index]
        command = "Power"
        print(f"Getting status of {plug_name} ({plug_ip})")
        return self.send_request(plug_ip, command)
 

    def get_name(self, index):
        if index < len(smartplugs):
            return smartplugs[index][0]
        else:
            return None
 

