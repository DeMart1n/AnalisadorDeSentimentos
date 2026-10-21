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
    """int8 por padrão: F1 0,763 x 0,768 do fp32 (McNemar p=0,06) com ~1/4 dos pesos.
    BERTIMBAU_ONNX=model.onnx volta ao fp32, idêntico ao torch."""
    return Path(destino) / (arquivo or os.environ.get("BERTIMBAU_ONNX", ARQUIVO_INT8))


class BertimbauOnnx:
    nome = "bertimbau"

    def __init__(self, destino=DESTINO, arquivo=None):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.destino = Path(destino)
        caminho = caminho_pesos(self.destino, arquivo)
        if not caminho.exists():
            raise ModeloNaoTreinado(f"sem {caminho} — rode manage.py exportar_onnx")
        self.tokenizer = Tokenizer.from_file(str(self.destino / "tokenizer.json"))
        self.tokenizer.enable_truncation(MAX_LEN)
        # padding até a maior do lote, não até MAX_LEN: mensagem curta custa menos
        self.tokenizer.enable_padding(pad_id=self.tokenizer.token_to_id("[PAD]"), pad_token="[PAD]")
        opcoes = ort.SessionOptions()
        # vários workers na mesma máquina disputam os núcleos: ONNX_THREADS=núcleos/workers
        opcoes.intra_op_num_threads = int(os.environ.get("ONNX_THREADS", 0))
        self.sessao = ort.InferenceSession(str(caminho), opcoes, providers=["CPUExecutionProvider"])

    def treinar(self, textos, rotulos, forcar=False, progresso=None):
        """Só inferência: o treino é do Bertimbau (torch) e depois `exportar_onnx`."""

    # batch=1 mediu melhor que 64 em RAM (365 MB x 1,1 GB de pico) e vazão (115 x 53 msg/s):
    # sem padding não há token desperdiçado, e o ONNX Runtime já paraleliza dentro de cada operação
    def prever(self, textos, batch=1):
        textos = list(textos)
        rotulos, scores = [], []
        for i in range(0, len(textos), batch):
            enc = self.tokenizer.encode_batch(textos[i:i + batch])
            entrada = {
                "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64),
            }
            logits = self.sessao.run(["logits"], entrada)[0]
            probs = np.exp(logits - logits.max(-1, keepdims=True))
            probs /= probs.sum(-1, keepdims=True)
            for p in probs:
                j = int(p.argmax())
                rotulos.append(CLASSES[j])
                scores.append(round(float(p[j]), 4))
        return rotulos, scores
