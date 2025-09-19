from dataclasses import dataclass


@dataclass
class TokenData:
    email: str

    @classmethod
    def from_dict(cls, data: dict) -> "TokenData":
        if not data.get("email"):
            raise ValueError("Email is required in token data")
        return cls(email=str(data.get("email")))

    def to_dict(self) -> dict:
        return {"email": self.email}
