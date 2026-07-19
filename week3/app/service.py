from app.repository import UserRepository

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def add_user(self, name: str, email: str) -> dict:
        # Business logic can go here (e.g., validation)
        if not name or not email:
            raise ValueError("Name and email are required")
        return self.repository.create_user(name, email)

    def list_users(self) -> list:
        return self.repository.get_users()
