# Minimal Backend

A demonstration of the smallest possible backend server written in Python, created to understand the request-response loop.

## Features
- **Dependency-free**: Uses only Python's built-in `http.server` (no Flask or Django required).
- **Lightweight**: Just ~25 lines of code.
- **JSON Responses**: Serves data correctly formatted as JSON.

## Endpoints

### 1. Ping
- **URL**: `/api/ping`
- **Response**: 
  ```json
  {"message": "pong"}
  ```

### 2. Info
- **URL**: `/api/info`
- **Response**: 
  ```json
  {"app": "Minimal Backend", "version": "1.0"}
  ```

## How to Run

1. Clone the repository to your local machine.
2. Start the server by running:
   ```bash
   python server.py
   ```
3. The server will start on port `8000`. You can test it by opening a browser and navigating to `http://localhost:8000/api/ping` or by running the following command in your terminal:
   ```bash
   curl http://localhost:8000/api/ping
   ```
