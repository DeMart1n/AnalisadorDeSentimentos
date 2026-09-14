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
            raise ValueError(["Payload inválido."])

        erros = []

        raw_email = data.get("email")
        if not raw_email:
            erros.append("O campo 'email' é obrigatório.")
        elif not isinstance(raw_email, str):
            erros.append("O campo 'email' deve ser uma string.")
        elif '@' not in raw_email or '.' not in raw_email:
            erros.append("O campo 'email' deve ser um e-mail válido.")

        raw_password = data.get("password")
        if not raw_password:
            erros.append("O campo 'password' é obrigatório.")
        elif not isinstance(raw_password, str):
            erros.append("O campo 'password' deve ser uma string.")
        elif len(raw_password) < 6:
            erros.append("A senha deve ter no mínimo 6 caracteres.")

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