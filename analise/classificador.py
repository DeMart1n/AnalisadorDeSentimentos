"""Classificação das mensagens já gravadas — roda no worker Celery (analise/tasks.py).

O modelo fica em cache de módulo: carregar leva segundos e cada processo do
worker atende muitos lotes. Na produção o BERTimbau roda via ONNX (sem torch).

O pipeline de produção (PADRAO) roda dois modelos por mensagem: polaridade e emoções.
Os outros degraus (lexico, classico) só fazem polaridade: servem para comparação.
"""

from functools import lru_cache

from django.db.models import OuterRef, Q, Subquery

from .models import USUARIO, Mensagem
from .modelos import ModeloNaoTreinado, carregar, emocoes_onnx
from .modelos.bertimbau_onnx import DESTINO, caminho_pesos

PADRAO = "bertimbau"
LOTE_MENSAGENS = 256  # mensagens em memória por vez, por maior que seja a conversa


@lru_cache(maxsize=2)
def modelo(nome=PADRAO):
    if nome == "bertimbau":
        from .modelos.bertimbau_onnx import BertimbauOnnx

        return BertimbauOnnx()
    return carregar(nome)


@lru_cache(maxsize=1)
def modelo_emocoes():
    return emocoes_onnx.EmocoesOnnx()


def verificar(nome):
    """Falha na requisição, e não minutos depois no worker, se não há pesos exportados."""
    if nome != PADRAO:
        return
    for destino in (DESTINO, emocoes_onnx.DESTINO):
        if not caminho_pesos(destino).exists():
            raise ModeloNaoTreinado(f"sem {caminho_pesos(destino)} — rode manage.py exportar_onnx")


def classificar_conversas(ids, nome=PADRAO, apenas_nao_classificadas=False, lote=LOTE_MENSAGENS):
    """Classifica as mensagens do USUÁRIO das conversas dadas. Devolve quantas foram.

    Paginação por pk em vez de list(qs): a memória fica em `lote` mensagens.
    """
    com_emocoes = nome == PADRAO
    qs = Mensagem.objects.filter(conversa_id__in=ids, autor=USUARIO).order_by("pk")
    if apenas_nao_classificadas:
        # base classificada antes das emoções existirem também entra, para ganhar as emoções
        qs = qs.filter(Q(rotulo_pred__isnull=True) | Q(emocoes_pred__isnull=True) if com_emocoes
                       else Q(rotulo_pred__isnull=True))
    if com_emocoes:
        # mensagem imediatamente anterior na conversa, de qualquer autor: o mesmo par do treino
        anterior = (Mensagem.objects.filter(conversa_id=OuterRef("conversa_id"), ordem__lt=OuterRef("ordem"))
                    .order_by("-ordem").values("texto")[:1])
        qs = qs.annotate(anterior=Subquery(anterior))
    total, ultimo = 0, 0
    while mensagens := list(qs.filter(pk__gt=ultimo).only("pk", "texto")[:lote]):
        rotulos, scores = modelo(nome).prever([m.texto for m in mensagens])
        for m, rotulo, score in zip(mensagens, rotulos, scores):
            m.rotulo_pred, m.score = rotulo, score
        atualizados = ["rotulo_pred", "score"]
        if com_emocoes:
            emocoes, probs = modelo_emocoes().prever(
                [{"anterior": m.anterior, "texto": m.texto} for m in mensagens])
            for m, e, p in zip(mensagens, emocoes, probs):
                m.emocoes_pred, m.emocoes_score = e, p
            atualizados += ["emocoes_pred", "emocoes_score"]
        Mensagem.objects.bulk_update(mensagens, atualizados)
        total += len(mensagens)
        ultimo = mensagens[-1].pk
    return total
