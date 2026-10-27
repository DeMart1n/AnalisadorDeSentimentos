"""Classificação das mensagens já gravadas.

O modelo fica em cache de módulo: carregar o BERTimbau leva segundos e o
processo do Django atende várias requisições.
"""

from functools import lru_cache

from .mappers.ia_mapper import ConversaIAMapper
from .models import USUARIO, Mensagem
from .modelos import carregar

PADRAO = "bertimbau"


@lru_cache(maxsize=2)
def modelo(nome=PADRAO):
    return carregar(nome)


def classificar_conversas(ids, nome=PADRAO, apenas_nao_classificadas=False, mapper=None):
    """Classifica as mensagens do USUÁRIO das conversas dadas.
    
    Aplica o ConversaIAMapper para sanitizar o texto, remover ruído cognitivo,
    mitigar riscos de segurança e economizar tokens/tempo de inferência.
    """
    qs = Mensagem.objects.filter(conversa_id__in=ids, autor=USUARIO)
    if apenas_nao_classificadas:
        qs = qs.filter(rotulo_pred__isnull=True)
    mensagens = list(qs)
    if not mensagens:
        return 0

    ia_mapper = mapper or ConversaIAMapper()
    mapeamento = ia_mapper.mapear_mensagens(mensagens)

    itens_para_inferencia = [item for item in mapeamento.itens if item.requer_inferencia]

    if itens_para_inferencia:
        textos_otimizados = [item.texto_otimizado for item in itens_para_inferencia]
        rotulos, scores = modelo(nome).prever(textos_otimizados)
        for item, rotulo, score in zip(itens_para_inferencia, rotulos, scores):
            item.mensagem.rotulo_pred = rotulo
            item.mensagem.score = score

    for item in mapeamento.itens:
        if not item.requer_inferencia and item.classificacao_direta:
            rotulo, score = item.classificacao_direta
            item.mensagem.rotulo_pred = rotulo
            item.mensagem.score = score

    Mensagem.objects.bulk_update(mensagens, ["rotulo_pred", "score"], batch_size=1000)
    return len(mensagens)
