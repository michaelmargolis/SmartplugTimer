# smartplug_timer.py

import time
from random import randint
import json

from my_kasa import My_Kasa as Smartplug
# from my_tasmota import my_tasmota as Smartplug
from webserver import my_HTTPserver
import timer_utils
from timer_utils import const
from display import Display
from wifi import WiFi

norm = 0
inv = 1
off = 0
on = 1
plugs = ((2,norm),)
DISPLAY_SLEEP_MINS = 1

class plug_event:
    _util = None
    
    # trigger and end are timestamps, index is into plug array, state is 0 if off, 1 if on
    def __init__(self, start, end, index, state, name = None):
        self.start = start
        self.end = end
        self.index = index
        self.state = state
        self.name = name
        
    def set_name(self, name):
        self.name = name
        
    def __repr__(self):
        if plug_event._util:
            rep = '{} {} {}, end {}'.format(
                self.name if self.name else "index ".format(self.index),
                "on" if self.state else "off",
                plug_event._util.str_timestamp(self.start),
                plug_event._util.str_timestamp(self.end)
            )
        else:
            rep = 'Utility method not set'
        return rep
    
    @staticmethod
    def set_util(util):
        plug_event._util = util    

default_cfg = { # these are defaults, actual values are in config.json
    'sunset':True, # start at sunset if True
    'start_hour':19,
    'start_min':0,
    'dur_minutes':60,
    'on_percent':80,
    'max_rand_mins':10, # must be less than 60
    'min_nbr_sequences':1,
    'max_nbr_sequences':3 }

cfg_tags = (  # tuple used to create html cfg tags
    ('C', 1, 'sunset', 'Start sequence at Sunset', None, None),
    ('T', 1, None, 'Or', None, None),
    ('N', 1, 'start_hour', 'Start Hour', 1, 23),
    ('N', 1, 'start_min', 'Start Minute', 0, 59),
    ('N', 2, 'dur_minutes', 'Duration Minutes', 1, 720),
    ('N', 2, 'on_percent', 'Percent On', 1, 99),
    ('N', 2, 'max_rand_mins', 'Max random minutes', 1, 59),
    ('N', 3, 'min_nbr_sequences', 'Min nbr of sequences', 1, 10),
    ('N', 3, 'max_nbr_sequences', 'Max nbr of sequences', 1, 10)
)


class Smartplug_Timer(object):

    def __init__(self):
        self.plug_events = [] # sorted queue of pending smartplug events
        self.cfg = self.load_config()
        self.wifi = WiFi()
        self.wifi.init_hardware()
        self.smartplug = Smartplug()
        self.display = Display(DISPLAY_SLEEP_MINS) # display goes to sleep after this interval
        self.display.update('','   Starting','')
        self.display.wake(2716060823) # way in the future
        self.scheduled_time_str = "Not yet Scheduled"
         
        self.utils = timer_utils.Time_utils(0) # arg is offset from utc
        plug_event.set_util(self.utils)
        self.utils.set_clock(self.utils.pico_rtc_setter)
        self.display.wake(self.utils.timestamp_now()) # reset wake timer
        print("\nScript started at {} on {}".format (self.utils.str_timestamp(self.utils.timestamp_now()),
            self.wifi.environ))

        # only connects to wifi AP if micropython, posix and windows use pre-existing network
        self.display.show_connecting(self.wifi.ssid) 
        while self.wifi.connect() == False:
            print("Unable to connect to WiFi, Retrying ...")


        self.display.update(self.wifi.this_ip,'','Scheduling ...',)
        self.webserver = my_HTTPserver(self.cfg, cfg_tags, self)

        for plug in plugs:
            self.smartplug.set_plug_state(plug[0], 1)
            time.sleep(.5)
            self.smartplug.set_plug_state(plug[0], 0)  
        
        self.schedule_events(plugs)
        self.display_status()



    def display_status(self):
        if len(self.plug_events):
            for event in self.plug_events:
                if event.state:                    
                    on =  'ON  {}'.format( self.utils.str_timestamp(event.start))
                    off = 'Off {}'.format(self.utils.str_timestamp(event.end))
                    self.display.update(self.wifi.this_ip, on, off)
                    break;
        else:
            self.display.update(self.wifi.this_ip, self.utils.str_day_month, 'No events', '')
    
    def save_config(self, data):
        with open("config.json","w") as fp:
            json.dump(data, fp)
        
    def load_config(self):   
        try:
            with open('config.json', 'r') as fp:
                data = json.load(fp)
            return data
        except: # FileNotFoundError:
            return default_cfg # default values
            
    def update_config(self, updated_dict):
        is_changed = False
        if not 'sunset' in updated_dict:
            updated_dict.update({'sunset':0})  
        for k, v in updated_dict.items():
            # print(k,v)
            if type(v) == str:
                v = int(v)
            if self.cfg[k] != v:
                is_changed = True
                self.cfg[k] = int(v)
        if is_changed:
            self.save_config(self.cfg)
            print("saving changed cfg", self.cfg)
            self.schedule_events(plugs)

    def get_eventQ(self):
        for event in self.plug_events:
            yield event 

    def ms_to_next_event(self):
        if len(self.plug_events) > 0:
            remaining = self.plug_events[0].start - self.utils.timestamp_now()
            return remaining * 1000  # time in ms
        else:
            print('todo ms to next event - no events!')
            return 1000

    def get_ticks_ms(self):
        return self.utils.ticks_ms()

    def get_time_scheduled(self):
        return  self.scheduled_time_str
        
    def get_next_start(self, dur_secs,  hour, minute):
        t_now = list(time.localtime())
        t_now[3] = hour
        t_now[4] = minute
        next_start = time.mktime(tuple(t_now)) + self.utils.utc_offset
        if next_start + dur_secs < self.utils.timestamp_now():
            next_start += 3600*24 # seconds per day
        return next_start
        
    def rand_secs(self):
        r = randint(0, self.cfg['max_rand_mins'])
        r = r-(r/2)
        if r ==0:
            r = 1
        # print('rand secs returning', int(r*30))
        return  int(r*30)
        
    def schedule_events(self, plugs):
        # plug event tuple: (event trigger time, event end time, plug index, on/off)  (0 is off, 1 is on))
        self.display.wake(self.utils.timestamp_now())
        new_events = []
        now = self.utils.timestamp_now()
        date_str = self.utils.str_day_month(now)
        if self.cfg['sunset']:
            sunset_hr,sunset_min = self.utils.get_sunset_time(now)
            print("next sunset at:", sunset_hr,sunset_min)
            self.cfg['start_hour'] = sunset_hr
            self.cfg['start_min'] = sunset_min
        start_hour =  self.cfg['start_hour'] 
        start_minute =  self.cfg['start_min']      
        dur_secs = self.cfg['dur_minutes'] *60
        on_dur = int(dur_secs * self.cfg['on_percent']*.01)
        min_nbr_sequences = self.cfg['min_nbr_sequences']
        max_nbr_sequences = self.cfg['max_nbr_sequences']
        start_timestamp = self.get_next_start(dur_secs, start_hour, start_minute)
        self.scheduled_time_str = self.utils.str_timestamp(now)
        print("\nrecalculating at {}, next start: {}".format (self.utils.str_timestamp(now),
            self.utils.str_timestamp(start_timestamp))) 
        self.plug_events = []   # clear old events
        for plug in plugs:
            plug_index, inversion = plug 
            # print("plug index=", plug_index)
            nxt_event_time = int(start_timestamp + self.rand_secs())
            # print("next event time for {} is {}".format(plug, time.gmtime(nxt_event_time)))
            off_dur = int(dur_secs - on_dur)
            nbr_sequences = randint(min_nbr_sequences, max_nbr_sequences)
            # print("totals: on={}, off={}, total dur={}, nbr sequences={}".format(on_dur, off_dur, dur_secs, nbr_sequences))
       
            if nbr_sequences > 1:
                 off_dur = int(off_dur/(nbr_sequences-1))   
            state_duration = []
            cume_dur = [0]

            for i in range(nbr_sequences):           
               state_duration.append(int((on_dur / nbr_sequences)) + self.rand_secs())
               state_duration.append(off_dur + self.rand_secs())
            cume =0
            for i in range (len(state_duration)):
                cume += state_duration[i]
                cume_dur.append(cume)
            cume_index = 0
            for i in range(nbr_sequences):
                self.plug_events.append(plug_event(nxt_event_time + cume_dur[cume_index],
                  nxt_event_time + cume_dur[cume_index+1], plug_index, on^inversion,
                  self.smartplug.get_name(plug_index)))
                cume_index += 1
                self.plug_events.append(plug_event(nxt_event_time + cume_dur[cume_index], 
                  nxt_event_time + cume_dur[cume_index+1], plug_index, off^inversion, 
                  self.smartplug.get_name(plug_index)))
                cume_index += 1
            if inversion:
                    ne = nxt_event_time + cume_dur[cume_index]
                    self.plug_events.append( plug_event(ne, ne+off_dur, plug_index, 0,
                    self.smartplug.get_name(plug_index))) # off if inv    
            
            self.plug_events = sorted(self.plug_events, key=lambda e: e.start)  # sort by start time
            # print( '\n'.join(str(y) for y in self.plug_events) )
            now = self.utils.timestamp_now()
            # print("removing events ending prior to", self.utils.str_timestamp(now))
            expired = 0
            for i in range(len(self.plug_events)):
                # print(i, self.utils.str_timestamp(self.plug_events[i].end), self.plug_events[i].end < now, self.utils.str_timestamp(now))
                if self.plug_events[i].end < now:
                  expired += 1
            if expired > 0:
               print("removed {} expired event(s)".format(expired))
            self.plug_events = self.plug_events[expired:] # remove events that ended before now       
            # print( '\n'.join(str(y) for y in self.plug_events) )
            
        '''    
        for plug_event in self.plug_events:
            print(str(plug_event))
        '''
   
    def check_display_trigger(self, timestamp):
        # if gpio low then self.wake() else:
        self.display.check_timeout(timestamp)
        
        
    def check_next_event(self, timestamp):
        # returns the first unexpired event or None if no events matured
        # the returned event is removed
        self.check_display_trigger(timestamp)
        if len(self.plug_events) > 0:
            remaining = self.plug_events[0].start - timestamp
            # print("remaining", remaining)
            if remaining <= 0: # true if next event has matured
                event = self.plug_events[0]
                print("Event Ready on", self.utils.str_timestamp(timestamp), event, "finishes at", self.utils.str_timestamp(event.end))
                self.plug_events.pop(0)
                if len(self.plug_events) > 0:
                    next_event = self.utils.str_timestamp(self.plug_events[0].start)
                    print("Processing event on {}, next event at {}".format (self.utils.str_timestamp(timestamp), next_event)) 
                else:
                    print("Processing last event on {}\n".format(self.utils.str_timestamp(timestamp))) 
                return event   
        return None


    
if __name__ == "__main__":
    timer = Smartplug_Timer()
    while(True):
        while len(timer.plug_events) > 0:
            event = timer.check_next_event(timer.utils.timestamp_now())
            if event:
                # print("process", event)
                timer.smartplug.set_plug_state(event.index, event.state)
                timer.display_status()
            timer.webserver.listen()
        timer.schedule_events(plugs)
        
    