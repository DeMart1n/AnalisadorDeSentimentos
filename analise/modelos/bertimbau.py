"""Degrau 3: fine-tune do BERTimbau. Alvo do projeto.

Loop de treino manual em PyTorch — evita trazer accelerate/datasets só para
usar o Trainer, e deixa explícito o que acontece a cada passo.
"""

from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from analise.models import NEGATIVO, NEUTRO, POSITIVO

BASE = "neuralmind/bert-base-portuguese-cased"
DESTINO = Path(__file__).resolve().parents[2] / "models" / "bertimbau"
CLASSES = [POSITIVO, NEGATIVO, NEUTRO]
MAX_LEN = 128  # ponytail: cobre a maioria dos reviews; subir se o truncamento doer


def dispositivo():
    return "mps" if torch.backends.mps.is_available() else "cpu"


class _Dados(Dataset):
    def __init__(self, textos, rotulos, tokenizer):
        self.enc = tokenizer(textos, truncation=True, padding="max_length",
                             max_length=MAX_LEN, return_tensors="pt")
        self.y = torch.tensor([CLASSES.index(r) for r in rotulos]) if rotulos else None

    def __len__(self):
        return self.enc["input_ids"].size(0)

    def __getitem__(self, i):
        item = {k: v[i] for k, v in self.enc.items()}
        if self.y is not None:
            item["labels"] = self.y[i]
        return item


class Bertimbau:
    nome = "bertimbau"

    def __init__(self, destino=DESTINO, epocas=2, batch=32, lr=2e-5):
        self.destino, self.epocas, self.batch, self.lr = Path(destino), epocas, batch, lr
        self.device = dispositivo()
        self.treinado = (self.destino / "config.json").exists()
        origem = self.destino if self.treinado else BASE
        self.tokenizer = AutoTokenizer.from_pretrained(origem)
        self.modelo = AutoModelForSequenceClassification.from_pretrained(
            origem, num_labels=len(CLASSES),
            id2label=dict(enumerate(CLASSES)),
            label2id={c: i for i, c in enumerate(CLASSES)},
        ).to(self.device)

    def treinar(self, textos, rotulos, forcar=False, progresso=None):
        """No-op se já existe modelo salvo — evita retreino acidental na avaliação."""
        if self.treinado and not forcar:
            return
        loader = DataLoader(_Dados(textos, rotulos, self.tokenizer), batch_size=self.batch, shuffle=True)
        otimizador = torch.optim.AdamW(self.modelo.parameters(), lr=self.lr)
        escalonador = torch.optim.lr_scheduler.OneCycleLR(
            otimizador, max_lr=self.lr, total_steps=self.epocas * len(loader), pct_start=0.1
        )
        # neutro é minoritário; sem peso o modelo o abandona
        contagem = torch.bincount(torch.tensor([CLASSES.index(r) for r in rotulos]), minlength=len(CLASSES))
        pesos = (contagem.sum() / (len(CLASSES) * contagem.clamp(min=1))).float().to(self.device)
        perda_fn = torch.nn.CrossEntropyLoss(weight=pesos)

        self.modelo.train()
        for epoca in range(self.epocas):
            for passo, lote in enumerate(loader):
                lote = {k: v.to(self.device) for k, v in lote.items()}
                y = lote.pop("labels")
                perda = perda_fn(self.modelo(**lote).logits, y)
                perda.backward()
                otimizador.step()
                escalonador.step()
                otimizador.zero_grad()
                if progresso and passo % 100 == 0:
                    progresso(epoca + 1, passo, len(loader), perda.item())
        self.salvar()

    def salvar(self):
        self.destino.mkdir(parents=True, exist_ok=True)
        self.modelo.save_pretrained(self.destino)
        self.tokenizer.save_pretrained(self.destino)
        self.treinado = True

    @torch.no_grad()
    def prever(self, textos, batch=64):
        self.modelo.eval()
        loader = DataLoader(_Dados(list(textos), None, self.tokenizer), batch_size=batch)
        rotulos, scores = [], []
        for lote in loader:
            lote = {k: v.to(self.device) for k, v in lote.items()}
            probs = self.modelo(**lote).logits.softmax(-1).cpu()
            for p in probs:
                i = int(p.argmax())
                rotulos.append(CLASSES[i])
                scores.append(round(float(p[i]), 4))
        return rotulos, scores
