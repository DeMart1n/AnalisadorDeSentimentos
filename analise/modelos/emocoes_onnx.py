"""Classificador de emoções só para inferência, via ONNX Runtime: sem torch nem transformers.

Os pesos vêm de `manage.py exportar_onnx` (depois de `treinar_emocoes`). Entrada em par
(anterior, atual), igual ao treino: sem mensagem anterior, o par leva "" e vira
[CLS] [SEP] atual [SEP]. Codificar só o atual muda o resultado sem erro nenhum (F1 macro
0,505 -> 0,512 no BRIGHTER e 0,652 -> 0,640 no GoEmotions-PT, medido em 2026-10-29), por isso
o par é sempre montado.
"""

import json
from pathlib import Path

import numpy as np

from analise.models import EMOCOES

from .bertimbau_onnx import carregar_onnx, entrada

DESTINO = Path(__file__).resolve().parents[2] / "models" / "emocoes"


class EmocoesOnnx:
    nome = "emocoes"

    def __init__(self, destino=DESTINO, arquivo=None):
        self.destino = Path(destino)
        self.tokenizer, self.sessao = carregar_onnx(self.destino, arquivo)
        self.limiares = np.array(json.loads((self.destino / "limiares.json").read_text()))

    # batch=1 pelo mesmo motivo do BertimbauOnnx: sem padding, nenhum token desperdiçado
    def prever(self, exemplos, batch=1):
        """exemplos: [{"anterior", "texto"}]. Devolve ([emoções acima do limiar], [{emoção: prob}])."""
        exemplos = list(exemplos)
        emocoes, probs = [], []
        for i in range(0, len(exemplos), batch):
            pares = [(e["anterior"] or "", e["texto"]) for e in exemplos[i:i + batch]]
            logits = self.sessao.run(["logits"], entrada(self.tokenizer.encode_batch(pares)))[0]
            for p in 1 / (1 + np.exp(-logits)):
                emocoes.append([e for e, sim in zip(EMOCOES, p >= self.limiares) if sim])
                probs.append({e: round(float(v), 4) for e, v in zip(EMOCOES, p)})
        return emocoes, probs
