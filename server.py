import http.server
import socketserver
import json

PORT = 8000

class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Allow CORS for browser testing if needed
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        if self.path == '/api/ping':
            response = {"message": "pong"}
        elif self.path == '/api/info':
            response = {"app": "Minimal Backend", "version": "1.0"}
        else:
            response = {"error": "Not Found. Try /api/ping or /api/info"}
            
        response_bytes = json.dumps(response).encode('utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
        print(f"Server running on http://localhost:{PORT}")
        httpd.serve_forever()
