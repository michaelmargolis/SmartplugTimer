from smartplug_timer import Smartplug_Timer
import timer_utils as utils
from timer_utils import const

offset_from_utc = 0 
utils = utils.Time_utils(offset_from_utc) 

print(__name__)


timer = Smartplug_Timer()
while(True):
    while len(timer.plug_events) > 0:
        event = timer.check_next_event(utils.timestamp_now())
        if event:
            # print("process", event)
            timer.smartplug.set_plug_state(event.index, event.state)
            timer.display_status()
        timer.webserver.listen()
    timer.schedule_events(plugs)
