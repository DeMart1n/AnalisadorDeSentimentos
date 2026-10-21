"""Classificação das mensagens já gravadas — roda no worker Celery (analise/tasks.py).

O modelo fica em cache de módulo: carregar leva segundos e cada processo do
worker atende muitos lotes. Na produção o BERTimbau roda via ONNX (sem torch).
"""

from functools import lru_cache

from .models import USUARIO, Mensagem
from .modelos import ModeloNaoTreinado, carregar
from .modelos.bertimbau_onnx import caminho_pesos

PADRAO = "bertimbau"
LOTE_MENSAGENS = 256  # mensagens em memória por vez, por maior que seja a conversa


@lru_cache(maxsize=2)
def modelo(nome=PADRAO):
    if nome == "bertimbau":
        from .modelos.bertimbau_onnx import BertimbauOnnx

        return BertimbauOnnx()
    return carregar(nome)


def verificar(nome):
    """Falha na requisição, e não minutos depois no worker, se não há pesos exportados."""
    if nome == "bertimbau" and not caminho_pesos().exists():
        raise ModeloNaoTreinado(f"sem {caminho_pesos()} — rode manage.py exportar_onnx")


def classificar_conversas(ids, nome=PADRAO, apenas_nao_classificadas=False, lote=LOTE_MENSAGENS):
    """Classifica as mensagens do USUÁRIO das conversas dadas. Devolve quantas foram.

    Paginação por pk em vez de list(qs): a memória fica em `lote` mensagens.
    """
    qs = Mensagem.objects.filter(conversa_id__in=ids, autor=USUARIO).order_by("pk")
    if apenas_nao_classificadas:
        qs = qs.filter(rotulo_pred__isnull=True)
    total, ultimo = 0, 0
    while mensagens := list(qs.filter(pk__gt=ultimo).only("pk", "texto")[:lote]):
        rotulos, scores = modelo(nome).prever([m.texto for m in mensagens])
        for m, rotulo, score in zip(mensagens, rotulos, scores):
            m.rotulo_pred, m.score = rotulo, score
        Mensagem.objects.bulk_update(mensagens, ["rotulo_pred", "score"])
        total += len(mensagens)
        ultimo = mensagens[-1].pk
    return total
