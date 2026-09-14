from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import os

ALLOWED_MODELS = ("lexico", "classico", "bertimbau")
STANDARD_MODEL = os.environ.get("STANDARD_MODEL")


@dataclass(frozen=True)
class AnalisarConversasDTO:
    fonte: Optional[str] = None
    conversa_ids: Optional[List[int]] = None
    modelo: str = STANDARD_MODEL
    apenas_nao_classificadas: bool = True

    @classmethod
    def from_dict(cls, data: Any) -> "AnalisarConversasDTO":
        if not isinstance(data, dict):
            raise ValueError(["Payload inválido."])

        erros = []

        raw_fonte = data.get("fonte")
        raw_ids = data.get("conversa_ids")

        if not raw_fonte and not raw_ids:
            erros.append("Informe, pelo menos, uma fonte ou uma lista de conversas para analisar.")

        fonte = None
        if raw_fonte is not None:
            if not isinstance(raw_fonte, str) or not raw_fonte.strip():
                erros.append("A fonte deve ser uma string não vazia.")
            else:
                fonte = raw_fonte.strip()

        conversa_ids = None
        if raw_ids is not None:
            if not isinstance(raw_ids, list) or not all(isinstance(i, int) for i in raw_ids):
                erros.append("A lista de conversas deve ser uma lista de ids inteiros.")
            else:
                conversa_ids = raw_ids

        raw_modelo = data.get("modelo")
        if raw_modelo is not None:
            modelo = str(raw_modelo).strip().lower()
            if modelo not in ALLOWED_MODELS:
                erros.append(f"Modelo inválido '{modelo}'. Modelos válidos: {', '.join(ALLOWED_MODELS)}.")
        else:
            modelo = STANDARD_MODEL

        apenas_nao_classificadas = data.get("apenas_nao_classificadas", True)
        if not isinstance(apenas_nao_classificadas, bool):
            erros.append("O campo 'apenas_nao_classificadas' deve ser booleano.")

        if erros:
            raise ValueError(erros)

        return cls(
            fonte=fonte,
            conversa_ids=conversa_ids,
            modelo=modelo,
            apenas_nao_classificadas=apenas_nao_classificadas,
        )


@dataclass(frozen=True)
class AnalisarConversasOutputDTO:
    fonte: Optional[str]
    total_conversas: int
    mensagens_classificadas: int
    modelo_utilizado: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)