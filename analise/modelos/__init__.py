"""Escada de abordagens.

Todo modelo implementa a mesma interface, para que a avaliação seja idêntica
entre os degraus:

    treinar(textos, rotulos) -> None
    prever(textos) -> (rotulos, scores)

Degraus: lexico (piso) -> classico (TF-IDF) -> bertimbau (alvo do projeto).
"""

from .classico import Classico
from .lexico import Lexico

REGISTRO = {"lexico": Lexico, "classico": Classico, "bertimbau": None}


def _bertimbau():
    # import tardio: torch demora a carregar e nem todo comando precisa dele
    from .bertimbau import Bertimbau

    return Bertimbau


def carregar(nome):
    if nome not in REGISTRO:
        raise ValueError(f"modelo desconhecido: {nome}. Disponíveis: {', '.join(REGISTRO)}")
    if nome == "bertimbau":
        return _bertimbau()()
    return REGISTRO[nome]()
