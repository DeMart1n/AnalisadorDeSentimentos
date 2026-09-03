"""Classificação das mensagens já gravadas.

O modelo fica em cache de módulo: carregar o BERTimbau leva segundos e o
processo do Django atende várias requisições.
"""

from functools import lru_cache

from .models import USUARIO, Mensagem
from .modelos import carregar

PADRAO = "bertimbau"


@lru_cache(maxsize=2)
def modelo(nome=PADRAO):
    return carregar(nome)


def classificar_conversas(ids, nome=PADRAO):
    """Classifica as mensagens do USUÁRIO das conversas dadas. Devolve quantas foram."""
    mensagens = list(Mensagem.objects.filter(conversa_id__in=ids, autor=USUARIO))
    if not mensagens:
        return 0
    rotulos, scores = modelo(nome).prever([m.texto for m in mensagens])
    for m, rotulo, score in zip(mensagens, rotulos, scores):
        m.rotulo_pred, m.score = rotulo, score
    Mensagem.objects.bulk_update(mensagens, ["rotulo_pred", "score"], batch_size=1000)
    return len(mensagens)
