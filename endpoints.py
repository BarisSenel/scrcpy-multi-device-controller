from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import subprocess
import time
import os
from urllib.parse import urlparse, parse_qs

class RequestHandler(BaseHTTPRequestHandler):
    request_count = 0
    lock = threading.Lock()

    def execute_adb_command(self, command):
        try:
            subprocess.run(command, check=True, shell=True)
            return True
        except subprocess.CalledProcessError:
            return False
    def do_GET(self):
        parsed_url = urlparse(self.path)
       
        # Extract query parameters
        query_params = parse_qs(parsed_url.query)

        # Get the value of the 'serial' parameter
        

        if parsed_url.path == "/ipreset":
            serial = query_params.get('serial', [None])[0]
            if serial == None:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(bytes(f"Missing serial parameter", "utf-8"))
            else:
                result = self.handle_request(serial)
                if result:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(bytes(f"Phone data toggled successfully.", "utf-8"))
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(bytes(f"Failed to disable phone data.", "utf-8"))
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(f"404 not found", "utf-8"))
        

    def handle_request(self,serial):
        if self.execute_adb_command(f"adb -s {serial} shell cmd connectivity airplane-mode enable"):
            time.sleep(5)
            if self.execute_adb_command(f"adb -s {serial} shell cmd connectivity airplane-mode disable"):
                time.sleep(1)
                return True
            else:
                return False
        else:
            return False
        



class ThreadedHTTPServer(HTTPServer):
    running_servers = {}

    def __init__(self, server_address, RequestHandlerClass, serial):
        self.serial = serial
        super().__init__(server_address, RequestHandlerClass)
        self.pid = os.getpid()  # Store the PID of the server process
        self.running_servers[(server_address[1], serial)] = self


    def process_request(self, request, client_address):
        """Override process_request to handle each request in a new thread."""
        t = threading.Thread(target=self.__new_request_handler, args=(request, client_address))
        t.start()

    def __new_request_handler(self, request, client_address):
        """Create a new instance of the request handler."""
        self.RequestHandlerClass(request, client_address, self)

    @classmethod
    def get_running_servers(cls):
        return list(cls.running_servers.keys())

def run_server(port=8000, serial='52033df0fa539313'):
    server_address = ('127.0.0.1', port)
    try:
        httpd = ThreadedHTTPServer(server_address, RequestHandler, serial)
        print(f'Starting server on port {port} with serial {serial}...')
        httpd.serve_forever()
    except Exception as e:
        print(f"Error starting server: {e}")
