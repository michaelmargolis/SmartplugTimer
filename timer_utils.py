# timer_utils

import time
from usunset import  SolarTime
# import datetime  #from: https://github.com/micropython/micropython-lib/blob/master/python-stdlib/datetime/datetime.py


try:
    from micropython import const
    import machine
    import ntptime
    DAY_OFFSET = 6
    upython = True
except ImportError:
    # here if running in full python 
    upython = False
    const = lambda x : x
    DAY_OFFSET = 4 
     
days = ('Mon','Tue','Wed','Thr','Fri','Sat','Sun')
months = ('', 'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec') 

UTC_OFFSET = 0 # hours UTC_OFFSEToffset to local time, ignore DST
    
class Time_utils(object):
    def __init__(self, utc_offset, tz_region= 'EU'):
       self.utc_offset = utc_offset
       print("utc offset =", self.utc_offset)
       self.tz_region = tz_region
       self.tz_offset = utc_offset*3600
       self.dst_offset_hrs = 0 
       print("TZ region set to", self.tz_region)
       self.time_synced = None
       self.time_sync_interval = 3660 * 1000 # ms between ntp sync (1 hr)
       self.sun = SolarTime()
  
    def ticks_ms(self):
        if upython:
            return time.ticks_ms()
        else:    
            return round(time.time()*1000)

    def zfl(self, s, width):
        # Pads given string with leading 0's to suit the specified width
        return '{:0>{w}}'.format(s, w=width)
        
    def get_sunset_time(self, ts):
        lat, lon = 51.5, -0.126
        tt = time.localtime(ts) #fixme use actual local time
        jd = self.sun._julianday(tt[2], tt[1], tt[0])
        offset = tt[3] - time.gmtime(ts)[3]
        h,m = self.sun.my_calc_sunset(jd, lat, lon)  
        return h+offset, m

    def strhms(self, dt):
        return str(dt)[11:19]
     
    def str_timestamp(self, ts):
        dt = time.localtime(ts)
        return '{} {}:{}.{}'.format(days[dt[6]], self.zfl(dt[3],2), \
                                self.zfl(dt[4],2), self.zfl(dt[5],2))

    def str_day_month(self, ts):
        tt = time.localtime(ts)
        ret = self.zfl(str(tt[2]),2) + ' ' + months[tt[1]-1]
        return ret
        
    def timestamp_now(self):
        lt = time.localtime() 
        now = time.mktime(time.localtime())
        '''
        if not upython:
            self._utc_offset = -time.altzone
            now +=  self._utc_offset
        '''    
        # print(now, time.localtime(now))   
        return int(now)
        
    def utc_offset(self):
        self.timestamp_now()
        return self.utc_offset
    
    def get_ntp_ts(self):
        ts = 0
        remaining_attempts = 2
        while ts == 0:
            try:
                ts = ntptime.time()
                return ts
            except:    
            # except Exception as e:
                print('ts=', ts, "attempting ntp time")
                time.sleep(2)
                ts=0
                remaining_attempts -= 1
                if remaining_attempts <=0:
                    return 0
                
        
    def set_clock(self, rtc_setter = None ):
        """
        calls the given rtc_setter method to sync localtime
        returns True iff synced on this call
        """
        ts = self.get_ntp_ts()
        if ts == 0:
            return False  
        if self.is_dst(ts, self.tz_region):
            self.dst_offset_hrs  = 1
        else:
            self.dst_offset = 0
        self.tz_offset =  UTC_OFFSET *3600 + self.dst_offset_hrs*3600   
        
        local_ts = ts + self.tz_offset
        tm = time.localtime(local_ts)
        if rtc_setter:
            rtc_setter(tm)
        self.time_synced = self.ticks_ms()
        print("NTP time sync: {}".format(tm[:6]))
        return True
    
    def pico_rtc_setter(self, tm):
        if upython:
            machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
        else:
            print("Not running on Micropyton, RTC not set")
    
    def is_synced(self):
        if self.time_synced == None:
            return False # time has not yet been synced
        # return true if previous sync was within the time_sync interval
        return time.ticks_diff(self.ticks_ms(),self.time_synced) < self.time_sync_interval
    
    def check_sync(self, rtc_setter):
        if not self.is_synced():
            if self.set_clock(rtc_setter):
                self.time_synced = self.ticks_ms()
                return True
        return False # time was not synced on this call   
    
    """
    DST utils
    see: https://en.wikipedia.org/wiki/Daylight_saving_time_by_country
    'EU' -> EU and UK:  +1 1am last sunday March, end 2am (local time) last sunday Oct 
    'NA' -> North America: +1 2am second sunday March, end 2am first sunday Nov
            (North America code has not been tested)
    """
    def nth_sunday(self, n, year, month, hour):
        # return timestamp for nth sunday in given month and year
        # -1 returns date of last sunday in previous month
        secs_per_day = 24*3600 
        if n == -1:
            month += 1 
        ts = time.mktime((year, month, 1, 0, 0,0,0,0,-1))
        dt = time.localtime(ts)
        ts +=(6-dt[6]) * secs_per_day # first sunday
        if n > 1: 
            ts += (n-1) * 7 * secs_per_day
        else:
            ts -= 7*secs_per_day # last sunday of previous month
        return ts + hour*3600
            
        
    def dst_transition_dates(self, year, location):
        # returns dst start, end (clocks go forward, back)
        if location == 'EU':
            start_dst = self.nth_sunday(-1, year, 3, 1)
            end_dst = self.nth_sunday(-1, year, 10, 2)
            return start_dst, end_dst
        elif location == 'NA':
            start_dst = self.nth_sunday(2, year, 3, 2)
            end_dst = self.nth_sunday(1, year, 11, 2)
            print("North America DST is untested!")
            return start_dst, end_dst
        else:
            raise ValueError('Unknown location for dst_transiton')

    def is_dst(self, ts, location):
        # returns true if given UTC time is dst in the UK
        struct_time = time.gmtime(ts)
        year = struct_time[0]
        transition_dates = self.dst_transition_dates(year, location)
        # print('start dst', time.localtime(transition_dates[0]))
        # print('end dst', time.localtime(transition_dates[1]))
        return ts >= transition_dates[0] and ts < transition_dates[1]

"""
if __name__ == "__main__":
    import MemNet, secrets
    net = MemNet.MemNet()
    if net.init_network():
        # utc_ts = ntptime.time()
        t = Time_utils(0)
        t.set_clock(t.pico_rtc_setter)
        print("epoch starts at", time.gmtime(0)[0])
        print("timestamp now is", t.timestamp_now(), time.time())
        if t.is_dst(utc_ts, t.tz_region):        
            print("time now is {} {}".format(t.str_timestamp(time.time())), 'DST' )
        else:
            print("time now is {}".format(t.str_timestamp(time.time())))     
    else:
        print("wifi not connected")
"""
