"""Converte o dataset ptbr-sentiment-analysis-datasets (Kaggle) para o esquema do projeto.

Cada review vira uma conversa de uma mensagem só. Isso mantém o split por conversa
válido e deixa explícito, pela fonte, que esses dados são review e não atendimento.

Mapeamento de rótulo (a base descarta rating 3; nós o usamos como neutro):
    rating 1-2 -> negativo    rating 3 -> neutro    rating 4-5 -> positivo
"""

import csv
import random
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from analise.models import NEGATIVO, NEUTRO, POSITIVO, USUARIO, Conversa, Mensagem

BASES = ["b2w", "olist", "buscape", "utlc_apps", "utlc_movies"]
csv.field_size_limit(10**7)


def _rotulo(rating):
    nota = float(rating)
    return NEGATIVO if nota <= 2 else NEUTRO if nota == 3 else POSITIVO


class Command(BaseCommand):
    help = "Importa reviews do dataset Kaggle como conversas de uma mensagem"

    def add_arguments(self, parser):
        parser.add_argument("--dir", type=Path, required=True, help="pasta com os CSVs do dataset")
        parser.add_argument("--bases", nargs="+", default=["b2w", "olist"], choices=BASES)
        parser.add_argument("--por-classe", type=int, default=15000,
                            help="amostra por classe em cada base (0 = tudo). Equilibra o treino.")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **opts):
        for base in opts["bases"]:
            arquivo = opts["dir"] / f"{base}.csv"
            if not arquivo.exists():
                raise CommandError(f"não encontrei {arquivo}")
            self._importar_base(arquivo, base, opts["por_classe"], opts["seed"])

    def _importar_base(self, arquivo, fonte, por_classe, seed):
        por_rotulo = {POSITIVO: [], NEGATIVO: [], NEUTRO: []}
        with arquivo.open(encoding="utf-8") as f:
            for i, linha in enumerate(csv.DictReader(f)):
                texto = (linha.get("review_text") or "").strip()
                if not texto or not linha.get("rating"):
                    continue
                por_rotulo[_rotulo(linha["rating"])].append((f"{fonte}-{i}", texto))

        rng = random.Random(seed)
        amostra = []
        for rotulo, itens in por_rotulo.items():
            if por_classe and len(itens) > por_classe:
                itens = rng.sample(itens, por_classe)
            amostra += [(oid, texto, rotulo) for oid, texto in itens]
        rng.shuffle(amostra)

        with transaction.atomic():
            Conversa.objects.filter(fonte=fonte).delete()
            conversas = Conversa.objects.bulk_create(
                [Conversa(origem_id=oid, fonte=fonte) for oid, _, _ in amostra], batch_size=2000
            )
            Mensagem.objects.bulk_create(
                [
                    Mensagem(conversa=c, ordem=1, autor=USUARIO, texto=texto, rotulo_real=rotulo)
                    for c, (_, texto, rotulo) in zip(conversas, amostra)
                ],
                batch_size=2000,
            )

        contagem = {r: sum(1 for _, _, x in amostra if x == r) for r in por_rotulo}
        self.stdout.write(self.style.SUCCESS(f"{fonte}: {len(amostra)} reviews {contagem}"))
