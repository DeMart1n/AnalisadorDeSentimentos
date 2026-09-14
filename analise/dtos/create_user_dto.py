import re
from dataclasses import dataclass, asdict
from typing import Any, Dict

DEFAULT_ROLE = "USER"

@dataclass(frozen=True)
class CreateUserDTO:
    name: str
    email: str
    password: str
    role: str = DEFAULT_ROLE

    @classmethod
    def from_dict(cls, data: Any) -> "CreateUserDTO":
        if not isinstance(data, dict):
            raise ValueError(["Invalid payload."])

        erros = []

        raw_name = data.get("name")
        if not raw_name:
            erros.append("Name is required.")
        elif not isinstance(raw_name, str) or not raw_name.strip():
            erros.append("Name must be a string.")

        raw_email = data.get("email")
        if not raw_email:
            erros.append("Email is required.")
        elif not isinstance(raw_email, str):
            erros.append("Email must be a string.")
        elif '@' not in raw_email:
            erros.append("Email must be a valid email.")
        elif '.' not in raw_email:
            erros.append("Email must be a valid email.")

        raw_password = data.get("password")
        if not raw_password:
            erros.append("Password is required.")
        elif not isinstance(raw_password, str):
            erros.append("Password must be a string.")
        elif len(raw_password) < 6:
            erros.append("Password must be at least 6 characters.")

        if erros:
            raise ValueError(erros)

        return cls(
            name=raw_name.strip(),
            email=raw_email.strip().lower(),
            password=raw_password,
            role=DEFAULT_ROLE,
        )


@dataclass(frozen=True)
class UserOutputDTO:
    name: str
    email: str
    role: str
    created_at: str

    @classmethod
    def from_model(cls, user: Any) -> "UserOutputDTO":
        return cls(
            name=user.name,
            email=user.email,
            role=user.role,
            created_at=user.created_at.isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
