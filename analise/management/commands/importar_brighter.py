"""Importa o BRIGHTER PT-BR (SemEval-2025 Task 11, track B) como conversas de uma mensagem.

Licença CC BY 4.0 — ver docs/emocoes/fontes.md. Os CSVs ficam em data/ (fora do git).
Track B traz intensidade 0-3 por emoção; presença = intensidade > 0 (idêntico à track A).
O split original (train/dev/test) fica no origem_id: "ptbr_train_track_b_00001".
"""

import csv
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from analise.anonimizador import anonimizar_texto
from analise.models import ORIGINAL_DATASET, USUARIO, Conversa, Mensagem, RotuloEmocao

FONTE = "brighter_ptbr"
URL = ("https://raw.githubusercontent.com/emotion-analysis-project/SemEval2025-Task11/main/"
       "task-dataset/semeval-2025-task11-dataset/track_b/{split}/ptbr.csv")
SPLITS = ["train", "dev", "test"]
# coluna do CSV -> campo do RotuloEmocao
EMOCOES = {"joy": "alegria", "anger": "raiva", "sadness": "tristeza",
           "fear": "medo", "surprise": "surpresa", "disgust": "nojo"}
PADRAO_DIR = Path(__file__).resolve().parents[3] / "data" / "brighter"


class Command(BaseCommand):
    help = "Baixa (se preciso) e importa o BRIGHTER PT-BR com rótulos de emoção"

    def add_arguments(self, parser):
        parser.add_argument("--dir", type=Path, default=PADRAO_DIR)

    def handle(self, *args, **opts):
        linhas = []
        for split in SPLITS:
            arquivo = opts["dir"] / f"{split}.csv"
            if not arquivo.exists():
                arquivo.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(URL.format(split=split), arquivo)
            with arquivo.open(encoding="utf-8") as f:
                linhas += list(csv.DictReader(f))

        with transaction.atomic():
            # rótulos do dataset são reconstruíveis; humanos/LLM sobre essas mensagens
            # bloqueiam o delete (PROTECT) — melhor falhar do que perder anotação
            RotuloEmocao.objects.filter(mensagem__conversa__fonte=FONTE, origem=ORIGINAL_DATASET).delete()
            Conversa.objects.filter(fonte=FONTE).delete()
            conversas = Conversa.objects.bulk_create(
                [Conversa(fonte=FONTE, origem_id=l["id"]) for l in linhas], batch_size=2000)
            mensagens = Mensagem.objects.bulk_create(
                [Mensagem(conversa=c, ordem=1, autor=USUARIO, texto=anonimizar_texto(l["text"]))
                 for c, l in zip(conversas, linhas)], batch_size=2000)
            RotuloEmocao.objects.bulk_create([
                RotuloEmocao(
                    mensagem=m, origem=ORIGINAL_DATASET, anotador=FONTE,
                    intensidades={campo: int(l[col]) for col, campo in EMOCOES.items()},
                    **{campo: int(l[col]) > 0 for col, campo in EMOCOES.items()},
                )
                for m, l in zip(mensagens, linhas)
            ], batch_size=2000)

        por_split = {s: sum(f"_{s}_" in l["id"] for l in linhas) for s in SPLITS}
        self.stdout.write(self.style.SUCCESS(f"{FONTE}: {len(linhas)} mensagens {por_split}"))
