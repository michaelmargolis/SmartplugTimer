# SmartplugTimer
Timer for kasa and tasmota smartplugs

Turns smartplugs on and off at various times to simulate presence when away for extended times.
- Up to ten sequences per day can be set.
- Sequence duration can be set between 1 minute and 12 hours.
- The number of sequences per day and start and end times can be randomized.
- Multiple smartplugs can be controlled.
- Can be configured for TP-Link Kasa or Tasmota smartplugs 
- A browser interface provides display of pending events and enables changes to event configuration
- An optional OLED display can be connected to show IP address and next pending event.

## Hardware
- Runs on a Pi Pico W. Should also work on an ESP32 or Raspberry Pi but not tested.
- The optional OLED display should be wired to pins indicated in the display.py module.
-  If no display is connected, see display.py for information on disabling the dispplay

## Software
An easy way to get this going is to use Thonny to upload the repository code to the Pico W.

Edit secrets.py with the SSID and password of you WiFi router.

## Important
I am happy to hear suggestions for improvements or bug fixes, but this is not a professionally supported project.

If you depend on reliable smartplug control then you would be better served by using software that has a warranty, or at least is better tested than this.
