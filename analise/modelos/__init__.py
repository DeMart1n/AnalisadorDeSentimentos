"""Escada de abordagens.

Todo modelo implementa a mesma interface, para que a avaliação seja idêntica
entre os degraus:

    treinar(textos, rotulos) -> None
    prever(textos) -> (rotulos, scores)

Degraus: lexico (piso) -> classico (TF-IDF) -> bertimbau (alvo do projeto).
"""

from .lexico import Lexico

class ModeloNaoTreinado(RuntimeError):
    """Modelo sem pesos salvos: prever com ele daria resultado aleatório."""


# None = import tardio: torch e sklearn pesam centenas de MB e o processo web não usa nenhum
REGISTRO = {"lexico": Lexico, "classico": None, "bertimbau": None}


def _bertimbau():
    from .bertimbau import Bertimbau

    return Bertimbau


def _classico():
    from .classico import Classico

    return Classico


def carregar(nome):
    if nome not in REGISTRO:
        raise ValueError(f"modelo desconhecido: {nome}. Disponíveis: {', '.join(REGISTRO)}")
    if nome == "bertimbau":
        return _bertimbau()()
    if nome == "classico":
        return _classico()()
    return REGISTRO[nome]()
