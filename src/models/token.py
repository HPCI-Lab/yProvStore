from dataclasses import dataclass


@dataclass
class TokenData:
    email: str

    @classmethod
    def from_dict(cls, data: dict) -> "TokenData":
        return cls(email=data.get("email"))

    def to_dict(self) -> dict:
        return {"email": self.email}
