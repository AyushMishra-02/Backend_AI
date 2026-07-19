import abc
try:
    import psycopg2
    from psycopg2.extras import DictCursor
except ImportError:
    psycopg2 = None
    DictCursor = None

class UserRepository(abc.ABC):
    @abc.abstractmethod
    def create_user(self, name: str, email: str) -> dict:
        pass

    @abc.abstractmethod
    def get_users(self) -> list:
        pass

class InMemoryUserRepository(UserRepository):
    def __init__(self):
        self.users = {}
        self.current_id = 1

    def create_user(self, name: str, email: str) -> dict:
        user = {"id": self.current_id, "name": name, "email": email}
        self.users[self.current_id] = user
        self.current_id += 1
        return user

    def get_users(self) -> list:
        return list(self.users.values())

class PostgresUserRepository(UserRepository):
    def __init__(self, db_url: str):
        self.db_url = db_url

    def get_connection(self):
        return psycopg2.connect(self.db_url, cursor_factory=DictCursor)

    def create_user(self, name: str, email: str) -> dict:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id, name, email;",
                    (name, email)
                )
                row = cursor.fetchone()
                conn.commit()
                return dict(row)

    def get_users(self) -> list:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name, email FROM users ORDER BY id ASC;")
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
