#!/usr/bin/env python3
import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import sys
from urllib.error import HTTPError, URLError

class CORSProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/api/'):
            self.handle_api_request()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            self.handle_api_request()
        else:
            super().do_POST()

    def handle_api_request(self):
        try:
            # Remove /api prefix and construct TempMail API URL
            api_path = self.path[4:]  # Remove '/api'
            api_url = f"https://api.tempmail.co/v1{api_path}"
            
            # Get request body for POST requests
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = None
            if content_length > 0:
                post_data = self.rfile.read(content_length)

            # Create request
            request = urllib.request.Request(api_url, data=post_data, method=self.command)
            
            # Copy authorization header
            auth_header = self.headers.get('Authorization')
            if auth_header:
                request.add_header('Authorization', auth_header)
            
            if post_data:
                request.add_header('Content-Type', 'application/json')
            
            request.add_header('Accept', 'application/json')
            request.add_header('User-Agent', 'TempMail-Proxy/1.0')

            print(f"Proxying {self.command} request to: {api_url}")
            if auth_header:
                print(f"Using auth: {auth_header[:20]}...")

            # Make the request
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    response_data = response.read()
                    
                    # Send successful response
                    self.send_response(response.status)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(response_data)
                    
                    print(f"Success: {response.status}")
                    
            except HTTPError as e:
                # Send error response
                error_data = e.read() if hasattr(e, 'read') else b'{"message": "API Error"}'
                
                self.send_response(e.code)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(error_data)
                
                print(f"API Error: {e.code}")
                
            except URLError as e:
                # Network error
                error_response = json.dumps({"message": f"Network error: {str(e)}"}).encode()
                
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(error_response)
                
                print(f"Network Error: {e}")

        except Exception as e:
            # General error
            error_response = json.dumps({"message": f"Proxy error: {str(e)}"}).encode()
            
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error_response)
            
            print(f"Proxy Error: {e}")

if __name__ == "__main__":
    PORT = 5000
    
    print(f"Starting CORS Proxy Server on port {PORT}")
    print("API endpoints will be available at /api/*")
    print("Static files served from current directory")
    
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("0.0.0.0", PORT), CORSProxyHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()
