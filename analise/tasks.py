from celery import shared_task

from .classificador import classificar_conversas


@shared_task
def classificar_lote(ids, nome, apenas_nao_classificadas):
    """Um lote de conversas por tarefa: lotes se espalham entre os workers."""
    return classificar_conversas(ids, nome=nome, apenas_nao_classificadas=apenas_nao_classificadas)
