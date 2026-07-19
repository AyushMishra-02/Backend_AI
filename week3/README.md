# Week 3: Dockerized Postgres & Repository Layer

This project demonstrates how to run a Python HTTP server connected to a persistent PostgreSQL database using Docker Compose.

## 🏗️ The Architecture Proof

The most important part of this assignment was proving that **"switch storage really does change only one file."**

Our business logic (`app/service.py`) and our routing logic (`app/main.py`) only know about the `UserRepository` interface. 
In `main.py`, the code looks like this:

```python
db_url = os.getenv("DATABASE_URL")
if db_url:
    repo = PostgresUserRepository(db_url)
else:
    repo = InMemoryUserRepository()

user_service = UserService(repo)
```

By simply swapping `InMemoryUserRepository` for `PostgresUserRepository`, the entire application switches from memory to a real database, and **zero routes or business logic had to be touched**.

## 🚀 How to Run

1. Make sure Docker is installed and running.
2. Build and start the stack:
   ```bash
   docker compose up -d
   ```
3. The server will be available at `http://localhost:8000`.

## 💾 Proving Persistence (The Survival Kit)

To prove the database volume works and survives restarts, follow these steps:

1. **Create a row:**
   ```bash
   curl -X POST http://localhost:8000/api/users \
        -H "Content-Type: application/json" \
        -d '{"name": "Alice", "email": "alice@example.com"}'
   ```
   *(Expected response: `{"id": 1, "name": "Alice", "email": "alice@example.com"}`)*

2. **Verify the row exists:**
   ```bash
   curl http://localhost:8000/api/users
   ```

3. **Restart the container:**
   ```bash
   docker compose down
   docker compose up -d
   ```

4. **Verify the row is still there:**
   ```bash
   curl http://localhost:8000/api/users
   ```
   *Because we used a Docker volume (`postgres_data`), the database file is saved on your host machine, and the data survives the container destruction!*

## 🌟 Stretch Goals Completed

### 1. Redis Integration
A Redis container has been added to `docker-compose.yml`. The application checks for `REDIS_URL` on startup.
You can ping the application to see it actively connect and ping Redis:
```bash
curl http://localhost:8000/api/ping
```
*(Expected response: `{"message": "pong", "redis": "connected"}`)*

### 2. Seeding & EXPLAIN ANALYZE
To demonstrate the performance impact of indexes on a large dataset, a script has been added: `seed_and_explain.py`.

Run it (make sure you have installed the requirements locally, e.g., `pip install -r requirements.txt`):
```bash
python seed_and_explain.py
```
**What it does:**
1. Drops the email index if it exists.
2. Seeds the database with 10,000 user rows.
3. Runs `EXPLAIN ANALYZE` on a search by email (Seq Scan, high execution time).
4. Creates the `idx_users_email` index.
5. Runs `EXPLAIN ANALYZE` again (Index Scan, extremely fast execution time).

