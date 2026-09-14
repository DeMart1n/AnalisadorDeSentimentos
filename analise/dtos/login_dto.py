import re
from dataclasses import dataclass, asdict
from typing import Any, Dict

@dataclass(frozen=True)
class LoginUserDTO:
    email: str
    password: str

    @classmethod
    def from_dict(cls, data: Any) -> "LoginUserDTO":
        if not isinstance(data, dict):
            raise ValueError(["Invalid payload."])

        erros = []

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
            erros.append(f"Password must be at least 6 characters.")

        if erros:
            raise ValueError(erros)

        return cls(
            email=raw_email.strip().lower(),
            password=raw_password,
        )


@dataclass(frozen=True)
class LoginOutputDTO:
    email: str
    access_token: str
    refresh_token: str

    @classmethod
    def from_user(cls, user: Any, access_token: str, refresh_token: str) -> "LoginOutputDTO":
        return cls(
            email=user.email,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)