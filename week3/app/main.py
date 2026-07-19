import http.server
import socketserver
import json
import os
import sys
from urllib.parse import parse_qs, urlparse
import redis

# Ensure the app module can be found when running this script directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repository import InMemoryUserRepository, PostgresUserRepository
from app.service import UserService

PORT = 8000

# =========================================================================
# THE ARCHITECTURE PROOF:
# Switch between InMemoryUserRepository and PostgresUserRepository here, 
# and literally nothing else in the service or routes needs to change!
# =========================================================================
db_url = os.getenv("DATABASE_URL")
if db_url:
    # Use Postgres if DATABASE_URL is provided (e.g., in Docker)
    print("Using PostgresUserRepository")
    repo = PostgresUserRepository(db_url)
else:
    # Fallback to InMemory for local development without Docker
    print("Using InMemoryUserRepository")
    repo = InMemoryUserRepository()

user_service = UserService(repo)

redis_url = os.getenv("REDIS_URL")
redis_client = redis.Redis.from_url(redis_url) if redis_url else None

class AppRequestHandler(http.server.BaseHTTPRequestHandler):
    def _send_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _send_error(self, message, status=400):
        self._send_response({"error": message}, status)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/users':
            try:
                users = user_service.list_users()
                self._send_response({"users": users})
            except Exception as e:
                self._send_error(str(e), 500)
        elif parsed_url.path == '/api/ping':
            response = {"message": "pong"}
            if redis_client:
                try:
                    redis_client.ping()
                    response["redis"] = "connected"
                except Exception as e:
                    response["redis"] = f"error: {str(e)}"
            self._send_response(response)
        else:
            self._send_error("Not Found", 404)

    def do_POST(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/users':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return self._send_error("Empty payload")

            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                name = payload.get('name')
                email = payload.get('email')
                
                new_user = user_service.add_user(name, email)
                self._send_response(new_user, 201)
            except ValueError as ve:
                self._send_error(str(ve))
            except Exception as e:
                self._send_error(f"Internal error: {str(e)}", 500)
        else:
            self._send_error("Not Found", 404)

if __name__ == "__main__":
    # Ensure the app module can be found
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    with socketserver.TCPServer(("", PORT), AppRequestHandler) as httpd:
        print(f"Server starting on port {PORT}")
        httpd.serve_forever()
