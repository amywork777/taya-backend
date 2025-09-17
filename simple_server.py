#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"message": "Taya Backend is working on Railway!", "status": "success"}
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "port": os.environ.get("PORT", "8080")}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        # Log to stdout for Railway to capture
        print(f"{self.client_address[0]} - - [{self.log_date_time_string()}] {format % args}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"Starting server on port {port}")
    server.serve_forever()