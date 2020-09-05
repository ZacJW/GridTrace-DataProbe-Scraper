import bs4, requests, re, time, ssdpy, cherrypy, threading, json
from . config import *
connected = re.compile('^[0-9]*-[AB]$')

class Service_Thread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()
        self.ssdpy_server = ssdpy.SSDPServer('urn:gridtrace:service:data-probe:1', location='data')

    def run(self):
        self.ssdpy_server.serve_forever()
            
class App():
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def data(self):
        data = self.get_inverter_data()
        if data is None:
            raise cherrypy.HTTPError(502, 'Unexpected html format from inverters')
        return {
            "panel" : {
                "columns" : [
                    {"name" : "id", "type" : "text"},
                    {"name" : "power", "type" : "integer"},
                    {"name" : "frequency", "type" : "integer"},
                    {"name" : "voltage", "type" : "integer"},
                    {"name" : "temperature", "type" : "integer"}
                ],
                "values" : [
                    [[row['id'], row['power'], row['frequency'], row['voltage'], row['temperature']] for row in data]
                ]
            }
        }
    def get_inverter_data(self):
        for tries in range (5):
            response = requests.get(DATA_SOURCE_URL)
            if response.status_code != 200:
                time.sleep(RETRY_PERIOD)
                continue
            html = bs4.BeautifulSoup(response.text, features="html.parser")
            rows = html.table.find_all('tr')

            data = []
            for row in rows:
                data_line = []
                for cell in row.find_all('td'):
                    data_line.append(cell.text.replace('\xa0', '').strip())
                if len(data_line) == 6 and connected.match(data_line[0]):
                    data.append({'id' : data_line[0], 
                                'power' : data_line[1][:-1], 
                                'frequency' : data_line[2][:-2], 
                                'voltage' : data_line[3][:-1], 
                                'temperature' : data_line[4][:-2]})
            return data
        return None

class SSDP_Feature(cherrypy.process.plugins.SimplePlugin):
    def start(self):
        self.bus.log("Starting SSDPy")
        self.thread = Service_Thread()
        self.thread.start()

    def stop(self):
        self.bus.log("Stopping SSDPy")
        self.thread.ssdpy_server.stopped = True
        self.thread.join()

ssdp_feature = SSDP_Feature(cherrypy.engine)
ssdp_feature.subscribe()
cherrypy.quickstart(App(), '/')
