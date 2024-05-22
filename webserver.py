import socket
import os
import errno
import sys
import time

try:
    from micropython import const
    upython = True
except ImportError:
    const = lambda x: x
    upython = False

TITLE = 'Smartplug Timer' # Only Bears in the Building
IMAGE = 'image.jpg' # 'bears.jpg'

SOCK_TIMEOUT = const(1)
READ_BUF_LEN = 512

content_types = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'json': 'application/json',
    'jpg': 'image/jpeg',
    'ico': 'image/x-icon',
    'default': 'text/plain',
}

class my_HTTPserver(object):
    def __init__(self, cfg, cfg_tags, timer):
        self.cfg = cfg
        self.cfg_tags = cfg_tags
        self.get_eventQ = timer.get_eventQ
        self.update_func = timer.update_config
        self.get_time_scheduled = timer.get_time_scheduled
        self.ms_to_next_event = timer.ms_to_next_event
        self.timer = timer

        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(SOCK_TIMEOUT)
        self.sock.bind(addr)
        self.send_array = bytearray(READ_BUF_LEN)
        self.sock.listen(5)
        print('Ready to listen on', addr)

    def listen(self):
        client = None
        try:
            client, addr = self.sock.accept()
            client.setblocking(False)
            print(f"Connection from {addr}")
            self.handle_client(client)
        except OSError as e:
            if e.args[0] == errno.EAGAIN:
                pass
            elif e.args[0] == errno.ETIMEDOUT:
                pass
            elif 'timed out' in str(e):
                pass
            else:
                print('Error in listen:', e)
        finally:
            if client:
                client.close()

    def handle_client(self, client):
        request = b""
        start_time = self.timer.get_ticks_ms()
        timeout = 2000

        while True:
            try:
                part = client.recv(2048)
                if part:
                    request += part
                    start_time = self.timer.get_ticks_ms()
                elif self.timer.get_ticks_ms() - start_time > timeout:
                    break
            except OSError as e:
                if e.args[0] == errno.EAGAIN or e.args[0] == errno.EWOULDBLOCK:
                    if self.timer.get_ticks_ms() - start_time > timeout:
                        break
                    time.sleep(0.1)
              
                    
                else:
                    print('Error in listen recv:', e)
                    break

        if request:
            self.process_request(request.decode('utf-8'), client)


    def process_request(self, request, client):
        if request.startswith('GET'):
            self.process_get(request, client)
        elif request.startswith('POST'):
            self.process_post(request, client)
        else:
            print("Unhandled request method:", request.split(' ', 1)[0])

    def process_get(self, response, cl):
        r = response[:32].split(' ', 3)
        if r[1][1:7] == 'images':
            fname = r[1][1:]
            self.send_file(cl, fname)
        elif r[2][:4] == 'HTTP':
            ms_to_next_event = str(self.ms_to_next_event())
            response = self.generate_html(ms_to_next_event, self.get_input_tags())
            cl.send(b'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n' + response.encode('utf-8'))
        elif len(r) > 0:
            print('unhandled:', r)

    def process_post(self, request, cl):
        try:
            start = request.find('\r\n\r\n') + 4
            fields = request[start:].split('&')
            
            if len(fields) >= len(self.cfg_tags) - 2:
                d = {}
                for item in fields:
                    key, value = item.split("=")
                    if value:
                        d[key] = int(value)  # Add validation here
                    else:
                        raise ValueError(f"Missing value for {key}")

                self.update_func(d)  # update config
            
            # After processing the form data, redirect to the GET method
            cl.send(b'HTTP/1.0 303 See Other\r\nLocation: /\r\n\r\n')
        except ValueError as e:
            print(f'Error processing POST request: {e}')
            cl.send(b'HTTP/1.0 400 Bad Request\r\nContent-type: text/plain\r\n\r\nInvalid input value')
        except Exception as e:
            print(f'Error processing POST request: {e}')
            cl.send(b'HTTP/1.0 400 Bad Request\r\nContent-type: text/plain\r\n\r\nBad Request')

    def send_file(self, cl, filename, binary=True):
        content_type = content_types.get(filename.split('.')[-1], content_types['default'])
        file_size = os.stat(filename)[6]

        cl.send(b"HTTP/1.1 200 OK\r\n")
        cl.send(f"Content-Type: {content_type}\r\n".encode())
        cl.send(f"Content-Length: {file_size}\r\n\r\n".encode())

        buf = self.send_array
        try:
            with open(filename, 'rb' if binary else 'r') as f:
                while True:
                    data = f.read(READ_BUF_LEN)
                    if not data:
                        break
                    while data:
                        try:
                            sent = cl.send(data)
                            data = data[sent:]
                        except OSError as e:
                            if e.args[0] == errno.EAGAIN:
                                time.sleep(0.1)  # Wait before retrying
                            else:
                                raise
        except OSError as e:
            if e.args[0] == errno.ETIMEDOUT:
                pass
            elif e.args[0] == errno.ENOENT:
                raise HttpError(cl, 404, "File Not Found")
            else:
                raise
            
    def generate_html(self, refresh_time, content):
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
        table {{ width: auto; margin: 0 auto; border-collapse: separate; border-spacing: 0; }}
        form  {{ display: table; margin: 0 auto; }}
        p     {{ display: table-row;  }}
        label {{ display: table-cell; padding: 0.2em; }}
        input {{ display: table-cell; width: 3em; padding: 0.2em; appearance: textfield; }}
        th    {{ text-align: center; font-weight: bold; background-color: #D3D3D3; padding: 0.2em; }}
        td    {{ padding: 0.2em; text-align: center; }}
        .group0 {{ background-color: #D3D3D3; }}
        .group1 {{ background-color: #FFFFCC; }}
        .group2 {{ background-color: #CCFFCC; }}
        .group3 {{ background-color: #CCFFFF; }}
        .group {{ padding: 0.5em; }}
        input[type="submit"] {{ display: block; margin: auto; padding: 0.5em 2em; width: auto; }}
        .content-wrapper {{ max-width: 600px; margin: 0 auto; text-align: center; }}
        img   {{ max-width: 100%; height: auto; margin-bottom: 0; }}
        .section-title {{ font-size: 1.5em; font-weight: bold; text-align: center; background-color: #D3D3D3; }}
        </style>
        </head>
        <body onLoad="timeRefresh({refresh_time});">
            <script>
              function timeRefresh(time) {{
                setTimeout("location.reload(true);", time);
              }}
            </script>
        <div class="content-wrapper">
            <h1>{TITLE}</h1>
            <img src="images/{IMAGE}"/>
            <table>
                <tr><td colspan="2" class="section-title">Pending Events</td></tr>
                {self.get_pending_events()}
                <tr><td colspan="2" style="text-align: center;">Events were scheduled on {self.get_time_scheduled()}</td></tr>
                <tr><td colspan="2"><br><br><hr></td></tr>
            </table>
            <form action="/" method="POST">
                <div class="group group0"><table><tbody>
                <tr><td colspan="2" class="section-title">Configuration</td></tr>
                </tbody></table></div>
                {content}
                <br>
                <input type="submit" value="Submit">
            </form>
        </div>
        </body>
        </html>
        """
        return html_template

    def get_pending_events(self):
        pending_events_html = []
        for event in self.get_eventQ():
            if event.state:  # Check the state attribute of the event
                pending_events_html.append(f'<tr><td colspan="2">{str(event)}</td></tr>')
        return '\n'.join(pending_events_html)

    def get_input_tags(self):
        fields = []

        current_group = None

        for tag in self.cfg_tags:
            type, group, key, text, min, max = tag
            if group != current_group:
                if current_group is not None:
                    fields.append('</tbody></table></div>')
                current_group = group
                fields.append(f'<div class="group group{group}"><table><tbody>')

            if type == 'C':
                checked = 'checked' if self.cfg[key] else ''
                fields.append(f'<tr><td colspan="2" style="text-align: center;">{text}<input type="checkbox" name="{key}" value="1" {checked} style="background-color: silver"/>&nbsp;</td></tr>')
            elif type == 'T':
                fields.append(f'<tr><td colspan="2" style="text-align: center;">{text}</td></tr>')
            elif type == 'N':
                fields.append(self.form_input(key, text, min, max, self.cfg[key]))

        fields.append('</tbody></table></div>')

        return '\n'.join(fields)

    def form_input(self, id, text, min, max, value):
        line = '<tr><td style="text-align: center;"><label for="{}">{} (between {} and {}):</label></td>' \
               '<td style="text-align: center;"><input type="number" id="{}" name="{}" min="{}" max="{}" value="{}" style="width: 3em; appearance: textfield;"></td></tr>' \
               .format(id, text, min, max, id, id, min, max, value)
        return line

if __name__ == "__main__":
    import time

    cfg = {  # these are defaults, actual values are in config.json
        'sunset': True,  # start at sunset if True
        'start_hour': 19,
        'start_min': 0,
        'dur_minutes': 60,
        'on_percent': 80,
        'max_rand_mins': 10,  # must be less than 60
        'min_nbr_sequences': 1,
        'max_nbr_sequences': 3
    }

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

    class Timer():
        def get_eventQ(self):
            plug_events = [str(time.time()), "EVENT2"]
            for event in plug_events:
                yield event

        def update_config(self, updated_dict):
            print(updated_dict)

        def ms_to_next_event(self):
            return 10000  # time in ms

    timer = Timer()

    webserver = my_HTTPserver(cfg, cfg_tags, timer)
    while True:
        webserver.listen()
