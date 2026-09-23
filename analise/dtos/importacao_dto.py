from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


@dataclass(frozen=True)
class MensagemImportadaDTO:
    ordem: int
    autor: str
    texto: str
    enviada_em: Optional[datetime] = None
    rotulo_real: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConversaImportadaDTO:
    origem_id: str
    fonte: str
    mensagens: List[MensagemImportadaDTO]
    nomes_contexto: Set[str]
    telefones_contexto: Set[str]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["nomes_contexto"] = list(self.nomes_contexto)
        d["telefones_contexto"] = list(self.telefones_contexto)
        return d


@dataclass(frozen=True)
class ResultadoImportacaoDTO:
    fonte: str
    total_conversas: int
    total_mensagens: int
    status: str = "importado"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)