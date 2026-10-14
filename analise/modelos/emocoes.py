"""Classificador de emoções: BERTimbau multi-rótulo (6 sigmoides), entrada em par (anterior, atual).

Mesmo esqueleto de bertimbau.py (loop manual em PyTorch). Diferenças:
  - BCE com pos_weight por emoção em vez de CE com peso por classe;
  - um limiar por emoção, ajustado na validação e salvo em limiares.json junto dos pesos;
  - amostragem ponderada por fonte, para o GoEmotions-PT não dominar a mistura.
Textos já chegam anonimizados: os importadores aplicam anonimizar_texto.
"""

import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from analise.models import EMOCOES

from .bertimbau import BASE, MAX_LEN, dispositivo, pesos_salvos

DESTINO = Path(__file__).resolve().parents[2] / "models" / "emocoes"
# peso relativo de cada exemplo da fonte no sorteio; fonte ausente = 1
# ponytail: valores a olho (GoEmotions tem ~7x o BRIGHTER); ajustar na ablação da Fase 7
PESO_FONTE = {"goemotions_pt": 0.3, "brighter_ptbr": 1.0}
GRADE_LIMIARES = np.arange(0.05, 0.96, 0.05)


def ajustar_limiares(probs, y):
    """Por emoção, o limiar da grade que maximiza o F1 na validação. Sem positivos, fica 0.5."""
    probs, y = np.asarray(probs), np.asarray(y, dtype=bool)
    limiares = []
    for i in range(y.shape[1]):
        if not y[:, i].any():
            limiares.append(0.5)
            continue
        p = probs[:, i][None, :] >= GRADE_LIMIARES[:, None]  # grade x N
        tp = (p & y[:, i]).sum(1)
        f1 = 2 * tp / (p.sum(1) + y[:, i].sum())
        limiares.append(round(float(GRADE_LIMIARES[f1.argmax()]), 2))
    return limiares


class _Dados(Dataset):
    def __init__(self, exemplos, tokenizer, com_rotulo=True):
        self.enc = tokenizer([e["anterior"] for e in exemplos], [e["texto"] for e in exemplos],
                             truncation=True, padding="max_length", max_length=MAX_LEN, return_tensors="pt")
        self.y = torch.tensor([e["y"] for e in exemplos], dtype=torch.float) if com_rotulo else None

    def __len__(self):
        return self.enc["input_ids"].size(0)

    def __getitem__(self, i):
        item = {k: v[i] for k, v in self.enc.items()}
        if self.y is not None:
            item["labels"] = self.y[i]
        return item


class Emocoes:
    nome = "emocoes"

    def __init__(self, destino=DESTINO, epocas=2, batch=32, lr=2e-5):
        self.destino, self.epocas, self.batch, self.lr = Path(destino), epocas, batch, lr
        self.device = dispositivo()
        self.treinado = pesos_salvos(self.destino) and (self.destino / "limiares.json").exists()
        origem = self.destino if self.treinado else BASE
        self.tokenizer = AutoTokenizer.from_pretrained(origem)
        self.modelo = AutoModelForSequenceClassification.from_pretrained(
            origem, num_labels=len(EMOCOES), problem_type="multi_label_classification",
            id2label=dict(enumerate(EMOCOES)), label2id={e: i for i, e in enumerate(EMOCOES)},
        ).to(self.device)
        self.limiares = (json.loads((self.destino / "limiares.json").read_text())
                         if self.treinado else [0.5] * len(EMOCOES))

    def treinar(self, treino, validacao, chat=None, forcar=False, progresso=None):
        """`chat`: exemplos só de chat para a etapa 2 (1 época, lr 1e-5). None = uma etapa só."""
        if self.treinado and not forcar:
            return
        self.historico = {"perda": [], "validacao": []}
        self._loop(treino, self.epocas, self.lr, progresso, validacao, etapa=1)
        if chat:
            self._loop(chat, 1, self.lr / 2, progresso, validacao, etapa=2)
        self.limiares = ajustar_limiares(self.probabilidades(validacao), [e["y"] for e in validacao])
        self.salvar()

    def _loop(self, exemplos, epocas, lr, progresso, validacao, etapa):
        peso = torch.tensor([PESO_FONTE.get(e["fonte"], 1.0) for e in exemplos], dtype=torch.double)
        amostrador = WeightedRandomSampler(peso, num_samples=len(exemplos), replacement=True)
        loader = DataLoader(_Dados(exemplos, self.tokenizer), batch_size=self.batch, sampler=amostrador)
        otimizador = torch.optim.AdamW(self.modelo.parameters(), lr=lr)
        escalonador = torch.optim.lr_scheduler.OneCycleLR(
            otimizador, max_lr=lr, total_steps=epocas * len(loader), pct_start=0.1)
        # pos_weight sobre a distribuição SORTEADA (ponderada), não a bruta
        y = torch.tensor([e["y"] for e in exemplos], dtype=torch.double)
        pos = (peso[:, None] * y).sum(0)
        neg = (peso[:, None] * (1 - y)).sum(0)
        pos_weight = (neg / pos.clamp(min=1e-6)).clamp(max=50).float().to(self.device)
        perda_fn = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

        self.modelo.train()
        for epoca in range(epocas):
            for passo, lote in enumerate(loader):
                lote = {k: v.to(self.device) for k, v in lote.items()}
                rotulos = lote.pop("labels")
                perda = perda_fn(self.modelo(**lote).logits, rotulos)
                perda.backward()
                otimizador.step()
                escalonador.step()
                otimizador.zero_grad()
                if passo % 10 == 0:
                    self.historico["perda"].append(
                        {"etapa": etapa, "epoca": epoca + 1, "passo": passo, "total": len(loader),
                         "perda": round(perda.item(), 4)})
                if progresso and passo % 100 == 0:
                    progresso(epoca + 1, passo, len(loader), perda.item())
            # F1 na validação ao fim de cada época, com limiar 0.5 (os ajustados só existem no fim)
            y_val = np.array([e["y"] for e in validacao])
            pred = self.probabilidades(validacao) >= 0.5
            self.modelo.train()
            self.historico["validacao"].append({
                "etapa": etapa, "epoca": epoca + 1,
                "f1_macro": round(float(f1_score(y_val, pred, average="macro", zero_division=0)), 4),
                "f1_por_emocao": dict(zip(EMOCOES, f1_score(y_val, pred, average=None, zero_division=0)
                                          .round(4).tolist())),
            })

    def salvar(self):
        self.destino.mkdir(parents=True, exist_ok=True)
        self.modelo.save_pretrained(self.destino)
        self.tokenizer.save_pretrained(self.destino)
        (self.destino / "limiares.json").write_text(json.dumps(self.limiares))
        if getattr(self, "historico", None):
            (self.destino / "historico.json").write_text(json.dumps(self.historico, indent=1))
        self.treinado = True

    @torch.no_grad()
    def probabilidades(self, exemplos, batch=64):
        self.modelo.eval()
        loader = DataLoader(_Dados(exemplos, self.tokenizer, com_rotulo=False), batch_size=batch)
        saida = [self.modelo(**{k: v.to(self.device) for k, v in lote.items()}).logits.sigmoid().cpu()
                 for lote in loader]
        return torch.cat(saida).numpy()

    def prever(self, exemplos):
        """exemplos: [{"anterior", "texto"}]. Devolve (rótulos 0/1 por emoção, probabilidades)."""
        if not self.treinado:
            raise RuntimeError(f"sem pesos em {self.destino} — rode manage.py treinar_emocoes")
        probs = self.probabilidades(exemplos)
        return (probs >= np.array(self.limiares)).astype(int).tolist(), probs.round(4).tolist()
