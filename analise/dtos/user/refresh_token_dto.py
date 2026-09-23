from dataclasses import dataclass, asdict
from typing import Any, Dict

@dataclass(frozen=True)
class RefreshTokenDTO:
    refresh_token: str

    @classmethod
    def from_dict(cls, data: Any) -> "RefreshTokenDTO":
        if not isinstance(data, dict):
            raise ValueError(["Payload inválido."])

        raw_token = data.get("refresh_token")
        if not raw_token:
            raise ValueError(["O campo 'refresh_token' é obrigatório."])
        if not isinstance(raw_token, str) or not raw_token.strip():
            raise ValueError(["O campo 'refresh_token' deve ser uma string não vazia."])

        return cls(refresh_token=raw_token.strip())


@dataclass(frozen=True)
class RefreshTokenOutputDTO:
    access_token: str
    refresh_token: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)