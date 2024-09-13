from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import subprocess
import time
import os

class RequestHandler(BaseHTTPRequestHandler):
    request_count = 0
    lock = threading.Lock()
    last_executed_time = 0
    cooldown_period = 10  # seconds

    def execute_adb_command(self, command):
        try:
            subprocess.run(command, check=True, shell=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        self.handle_request()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        self.handle_request()

    def handle_request(self):
        with self.lock:
            self.request_count += 1
            count = self.request_count

        if count >= 1:
            current_time = time.time()
            if current_time - self.last_executed_time >= self.cooldown_period:
                if self.execute_adb_command(f"adb -s {self.server.serial} shell svc data disable"):
                    time.sleep(5)
                    if self.execute_adb_command(f"adb -s {self.server.serial} shell svc data enable"):
                        self.wfile.write(b'Phone data toggled successfully.')
                    else:
                        self.wfile.write(b'Failed to enable phone data.')
                else:
                    self.wfile.write(b'Failed to disable phone data.')
                with self.lock:
                    self.request_count = 0
                    self.last_executed_time = time.time()
            else:
                remaining_time = int(self.cooldown_period - (current_time - self.last_executed_time))
                response = f'Request ignored due to cooldown period. {remaining_time} seconds left.'
                self.wfile.write(response.encode())
                with self.lock:
                    self.request_count -= 1
        else:
            while True:
                with self.lock:
                    if self.request_count >= 1:
                        break
                time.sleep(1)

            self.wfile.write(b'')


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
