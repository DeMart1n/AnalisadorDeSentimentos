"""Importa o GoEmotions traduzido (data/goemotions/traduzido.jsonl) como conversas de uma mensagem.

O arquivo vem de scripts/goemotions_lotes.py + tradução por LLM (ver docs/emocoes/fontes.md).
Rótulos já mapeados para Ekman no script; aqui só viram campos do RotuloEmocao.
Split original no origem_id: "train_eeabc123".
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from analise.anonimizador import anonimizar_texto
from analise.management.commands.importar_brighter import EMOCOES
from analise.models import ORIGINAL_DATASET, USUARIO, Conversa, Mensagem, RotuloEmocao

FONTE = "goemotions_pt"
PADRAO = Path(__file__).resolve().parents[3] / "data" / "goemotions" / "traduzido.jsonl"
# raiva mais estreita que o mapa oficial: sem `disapproval`, que puxava neutro para raiva
# (34% -> 23% das mensagens; relatório de 2026-10-05). Linha sem "original" fica com o "ekman".
RAIVA = {"anger", "annoyance"}


def ekman(linha):
    if not linha.get("original"):
        return set(linha["ekman"])
    return set(linha["ekman"]) - {"anger"} | ({"anger"} if RAIVA & set(linha["original"]) else set())


class Command(BaseCommand):
    help = "Importa o GoEmotions traduzido para PT-BR com rótulos de Ekman"

    def add_arguments(self, parser):
        parser.add_argument("--arquivo", type=Path, default=PADRAO)

    def handle(self, *args, **opts):
        if not opts["arquivo"].exists():
            raise CommandError(f"não encontrei {opts['arquivo']} — ver docs/emocoes/fontes.md")
        linhas = [json.loads(l) for l in opts["arquivo"].open(encoding="utf-8")]

        with transaction.atomic():
            RotuloEmocao.objects.filter(mensagem__conversa__fonte=FONTE, origem=ORIGINAL_DATASET).delete()
            Conversa.objects.filter(fonte=FONTE).delete()
            conversas = Conversa.objects.bulk_create(
                [Conversa(fonte=FONTE, origem_id=f"{l['split']}_{l['id']}") for l in linhas], batch_size=2000)
            mensagens = Mensagem.objects.bulk_create([
                # [NAME] do Reddit vira o marcador do nosso anonimizador, igual ao da produção
                Mensagem(conversa=c, ordem=1, autor=USUARIO,
                         texto=anonimizar_texto(l["texto_pt"].replace("[NAME]", "[NOME]")))
                for c, l in zip(conversas, linhas)], batch_size=2000)
            RotuloEmocao.objects.bulk_create([
                RotuloEmocao(mensagem=m, origem=ORIGINAL_DATASET, anotador=FONTE,
                             **{campo: col in ekman(l) for col, campo in EMOCOES.items()})
                for m, l in zip(mensagens, linhas)], batch_size=2000)

        por_split = {s: sum(l["split"] == s for l in linhas) for s in ("train", "dev", "test")}
        self.stdout.write(self.style.SUCCESS(f"{FONTE}: {len(linhas)} mensagens {por_split}"))
