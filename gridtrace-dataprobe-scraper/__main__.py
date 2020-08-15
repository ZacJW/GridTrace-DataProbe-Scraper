import bs4, requests, re, time, ssdpy, http.server, threading, json

connected = re.compile('^[0-9]*-[AB]$')
def get_inverter_data():
    for tries in range (5):
        response = requests.get('http://192.168.0.22/cgi-bin/parameters')
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
                data.append({'name' : data_line[0], 
                            'power' : data_line[1][:-1], 
                            'frequency' : data_line[2][:-2], 
                            'voltage' : data_line[3][:-1], 
                            'temperature' : data_line[4][:-2]})
        return data
    return None

ssdpy_server = ssdpy.SSDPServer('urn:gridtrace:service:data-probe:1')

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def do_GET(self):
        data = get_inverter_data()
        if data is None:
            return self.send_error(502, 'Unexpected html format from inverters')
        json_data = json.dumps(data)
        
