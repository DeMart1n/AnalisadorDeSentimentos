"""BERTimbau só para inferência, via ONNX Runtime: sem torch nem transformers.

Os pesos vêm de `manage.py exportar_onnx`. As constantes do BERTimbau moram
aqui (e não em bertimbau.py) porque aquele módulo importa torch no topo.
"""

import os
from pathlib import Path

import numpy as np

from analise.models import NEGATIVO, NEUTRO, POSITIVO

from . import ModeloNaoTreinado

DESTINO = Path(__file__).resolve().parents[2] / "models" / "bertimbau"
CLASSES = [POSITIVO, NEGATIVO, NEUTRO]
MAX_LEN = 128  # ponytail: cobre a maioria dos reviews; subir se o truncamento doer
ARQUIVO_FP32 = "model.onnx"
ARQUIVO_INT8 = "model.int8.onnx"


def caminho_pesos(destino=DESTINO, arquivo=None):
    """int8 por canal por padrão: F1 0,7675 x 0,7683 do fp32 com ~1/4 dos pesos (o int8 por tensor
    dava 0,7638 e derrubava nojo de 0,215 para 0,147 nas emoções; medido em 2026-10-29).
    BERTIMBAU_ONNX=model.onnx volta ao fp32, idêntico ao torch — vale para polaridade e emoções."""
    return Path(destino) / (arquivo or os.environ.get("BERTIMBAU_ONNX", ARQUIVO_INT8))


def carregar_onnx(destino, arquivo=None):
    """(tokenizer, sessão) de um BERTimbau exportado. Usado pela polaridade e pelas emoções."""
    import onnxruntime as ort
    from tokenizers import Tokenizer

    caminho = caminho_pesos(destino, arquivo)
    if not caminho.exists():
        raise ModeloNaoTreinado(f"sem {caminho} — rode manage.py exportar_onnx")
    tokenizer = Tokenizer.from_file(str(Path(destino) / "tokenizer.json"))
    tokenizer.enable_truncation(MAX_LEN)
    # padding até a maior do lote, não até MAX_LEN: mensagem curta custa menos
    tokenizer.enable_padding(pad_id=tokenizer.token_to_id("[PAD]"), pad_token="[PAD]")
    opcoes = ort.SessionOptions()
    # vários workers na mesma máquina disputam os núcleos: ONNX_THREADS=núcleos/workers
    opcoes.intra_op_num_threads = int(os.environ.get("ONNX_THREADS", 0))
    return tokenizer, ort.InferenceSession(str(caminho), opcoes, providers=["CPUExecutionProvider"])


def entrada(encodings):
    return {
        "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
        "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
        "token_type_ids": np.array([e.type_ids for e in encodings], dtype=np.int64),
    }


class BertimbauOnnx:
    nome = "bertimbau"

    def __init__(self, destino=DESTINO, arquivo=None):
        self.destino = Path(destino)
        self.tokenizer, self.sessao = carregar_onnx(self.destino, arquivo)

    def treinar(self, textos, rotulos, forcar=False, progresso=None):
        """Só inferência: o treino é do Bertimbau (torch) e depois `exportar_onnx`."""

    # batch=1 mediu melhor que 64 em RAM (365 MB x 1,1 GB de pico) e vazão (115 x 53 msg/s):
    # sem padding não há token desperdiçado, e o ONNX Runtime já paraleliza dentro de cada operação
    def prever(self, textos, batch=1):
        textos = list(textos)
        rotulos, scores = [], []
        for i in range(0, len(textos), batch):
            logits = self.sessao.run(["logits"], entrada(self.tokenizer.encode_batch(textos[i:i + batch])))[0]
            probs = np.exp(logits - logits.max(-1, keepdims=True))
            probs /= probs.sum(-1, keepdims=True)
            for p in probs:
                j = int(p.argmax())
                rotulos.append(CLASSES[j])
                scores.append(round(float(p[j]), 4))
        return rotulos, scores
