"""Leitura de conversas em CSV/JSON para o esquema do projeto.

Esquema esperado por linha/objeto:
    conversa_id, ordem, autor, texto, timestamp (opcional), rotulo (opcional)
"""

import csv
import io
import json

from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import get_current_timezone, is_naive, make_aware

from .models import AUTORES, ROTULOS, Conversa, Mensagem

OBRIGATORIOS = {"conversa_id", "ordem", "autor", "texto"}
AUTORES_VALIDOS = {a for a, _ in AUTORES}
ROTULOS_VALIDOS = {r for r, _ in ROTULOS}


class ErroDeImportacao(Exception):
    def __init__(self, erros):
        self.erros = erros
        super().__init__(f"{len(erros)} erro(s) no arquivo")


def _ler(conteudo, formato):
    if formato == "json":
        dados = json.loads(conteudo)
        if not isinstance(dados, list):
            raise ErroDeImportacao(["JSON deve ser uma lista de objetos"])
        return dados
    return list(csv.DictReader(io.StringIO(conteudo)))


def _validar(linhas):
    erros = []
    vistos = set()
    for i, linha in enumerate(linhas, start=1):
        faltando = OBRIGATORIOS - {k for k, v in linha.items() if v not in (None, "")}
        if faltando:
            erros.append(f"linha {i}: campos faltando: {', '.join(sorted(faltando))}")
            continue
        if linha["autor"] not in AUTORES_VALIDOS:
            erros.append(f"linha {i}: autor inválido '{linha['autor']}'")
        rotulo = linha.get("rotulo") or None
        if rotulo and rotulo not in ROTULOS_VALIDOS:
            erros.append(f"linha {i}: rotulo inválido '{rotulo}'")
        try:
            ordem = int(linha["ordem"])
        except (TypeError, ValueError):
            erros.append(f"linha {i}: ordem não é inteiro: '{linha['ordem']}'")
            continue
        chave = (str(linha["conversa_id"]), ordem)
        if chave in vistos:
            erros.append(f"linha {i}: ordem {ordem} repetida na conversa {chave[0]}")
        vistos.add(chave)
    if erros:
        raise ErroDeImportacao(erros)


@transaction.atomic
def importar(conteudo, fonte, formato="csv"):
    """Grava as conversas do arquivo. Ou entra tudo, ou nada.

    Reimportar a mesma conversa da mesma fonte substitui as mensagens dela.
    Devolve (conversas, mensagens) gravadas.
    """
    linhas = _ler(conteudo, formato)
    _validar(linhas)

    por_conversa = {}
    for linha in linhas:
        por_conversa.setdefault(str(linha["conversa_id"]), []).append(linha)

    total_msgs = 0
    for origem_id, linhas_da_conversa in por_conversa.items():
        conversa, _ = Conversa.objects.get_or_create(origem_id=origem_id, fonte=fonte)
        conversa.mensagens.all().delete()
        Mensagem.objects.bulk_create(
            Mensagem(
                conversa=conversa,
                ordem=int(l["ordem"]),
                autor=l["autor"],
                texto=l["texto"],
                enviada_em=_data(l.get("timestamp")),
                rotulo_real=l.get("rotulo") or None,
            )
            for l in sorted(linhas_da_conversa, key=lambda l: int(l["ordem"]))
        )
        total_msgs += len(linhas_da_conversa)

    return len(por_conversa), total_msgs


def _data(valor):
    """Timestamp sem fuso é lido no fuso local — export de atendimento costuma vir assim."""
    if not valor:
        return None
    dt = parse_datetime(valor)
    if dt and is_naive(dt):
        return make_aware(dt, get_current_timezone())
    return dt
