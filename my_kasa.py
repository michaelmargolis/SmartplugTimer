#  Class to turn on or off kasa plugs using prediscovered ids 
import json
import socket
from time import sleep
import struct
from builtins import bytes

try:
    from micropython import const
    upython = True
except ImportError:
    const = lambda x : x
    upython = False
    
smartplugs = const(( 
            ('8006B196B161301BAAB04C385B337B3D1FB8CA0000', 'plug 1', 'KP303(UK)', '192.168.1.186'),
            ('8006B196B161301BAAB04C385B337B3D1FB8CA0001', 'plug 2', 'KP303(UK)', '192.168.1.186'),
            ('8006B196B161301BAAB04C385B337B3D1FB8CA0002', 'plug 3', 'KP303(UK)', '192.168.1.186'),
            ('800680793892C6E47BE40118213A40421C79F9DA', 'ender 5', 'HS100(UK)', '192.168.1.198'),
            ('8006E091F6F579E27A1E9B7E3C5CA5BE1FA21112', 'security lamp1', 'KP105(UK)', '192.168.1.185')))

class My_Kasa():
    def __init__(self):
        self.kasa_port = 9999
        self.timeout = 2.0
        self.show_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def show(self, text, addr=('192.168.1.117',9998)):
        # print(text)
        print('call to show with text:', text)
                
    def show_discovered_plugs(self):
        for i in range(len(smartplugs)):
            print(smartplugs[i][1:])

    def get_system_info(self):    
        self.sys_info = self.send_udp_command('{"system":{"get_sysinfo":{}}}', protocol='udp')
        if self.sys_info != None:
            # print("full info=", self.sys_info)
            self.sys_info =  self.sys_info['system']['get_sysinfo']
            print("in get_system_info", self.sys_info)
            if not self.device_id:
                self.device_id = self.sys_info['deviceId']
                print("device id =", self.device_id)
        else:
            print("failed to get sys_info")
        # return self._udp_send_command('{"system":{"get_sysinfo":{}}}')

    def get_plug_info(self, plug_num):
        if self.sys_info != None:
            target_plug = [plug for plug in self.sys_info['children'] if plug['id'] == zfl(str(int(plug_num)-1), 2)]
            return target_plug
        else:
            print("Plug info not available")
            return None

    def get_name(self, index):
        if index < len(smartplugs):
            return smartplugs[index][1]
        else:
            return None
        
    def set_plug_state(self, plug_index, state):
        # state 0 is off, 1 is on, index into smartplugs tuple for ip and plug id
        print("Setting plug index {} ({}) {}".format( plug_index, self.get_name(plug_index), 'on' if state else 'off'))
        plug_id = smartplugs[plug_index][0]
        addr = (smartplugs[plug_index][3], self.kasa_port)
        if smartplugs[plug_index][2][2] == '1': # single plug (no children)
            relay_command = '{"system":{"set_relay_state":{"state":' + str(state) + '}}}'
        else:
            relay_command = '{"context":{"child_ids":["' + plug_id + '"]},' + \
                    '"system":{"set_relay_state":{"state":' + str(state) + '}}}'
        # print(relay_command)
        return self.tcp_send_and_recv(self._encrypt_command(relay_command), addr)
        
    def tcp_send_and_recv(self, command, addr=None):

        if addr: 
            # here if allocating sock on each call
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(self.timeout)
            try:
                sock.connect(addr) # (self.ip, self.port))
            except Exception as e:
                print(e, addr)
            
        else:
            if sock == None:
                print("sock not connected")
                return None
        
        if sock != None:
            try:
                sock.send(command) # self._encrypt_command(command))
                # print("sent", command)
                data = sock.recv(2048)       
                sock.close()
                # the first 4 chars are the length of the command so can be excluded
                return data[4:]
            except:
                pass
        return None

    def _encrypt_command(self, string):
        key = 171
        result = b''
        
        result = struct.pack(">I", len(string)) # prepend length for tcp msgs
        for i in bytes(string.encode('latin-1')):
            a = key ^ i
            key = a
            result += bytes([a])
        return result

    def _decrypt_command(self, string):
        key = 171
        result = b''
        for i in bytes(string):
            a = key ^ i
            key = i
            result += bytes([a])
        return result.decode('latin-1')

