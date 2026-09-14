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
            raise ValueError(["Payload inválido."])

        erros = []

        raw_name = data.get("name")
        if not raw_name:
            erros.append("O campo 'name' é obrigatório.")
        elif not isinstance(raw_name, str) or not raw_name.strip():
            erros.append("O campo 'name' deve ser uma string.")

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
