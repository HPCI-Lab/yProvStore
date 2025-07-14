from dataclasses import dataclass


@dataclass
class User:
    """
    Represents a user in the system.
    """
    email: str
    password_hash: str
    id: str | None = None

    def __post_init__(self):
        if not self.email:
            raise ValueError("Email cannot be empty.")
        if not self.password_hash:
            raise ValueError("Password hash cannot be empty.")
