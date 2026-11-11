"""Exporta os BERTimbau treinados para ONNX (fp32) e quantiza em int8 por canal.

Roda depois de `treinar_bertimbau` / `treinar_emocoes`: o worker de inferência só lê o .onnx e
não precisa de torch. Retreinou? Exporte de novo.
"""

from django.core.management.base import BaseCommand, CommandError

from analise.modelos import bertimbau_onnx, emocoes_onnx
from analise.modelos.bertimbau import pesos_salvos
from analise.modelos.bertimbau_onnx import ARQUIVO_FP32, ARQUIVO_INT8, MAX_LEN

# exemplo de entrada do traçado: a polaridade lê uma mensagem, as emoções leem o par (anterior, atual)
MODELOS = {
    "bertimbau": (bertimbau_onnx, (["exemplo de mensagem"],), "treinar_bertimbau"),
    "emocoes": (emocoes_onnx, (["mensagem anterior"], ["mensagem atual"]), "treinar_emocoes"),
}


class Command(BaseCommand):
    help = "Exporta models/bertimbau e models/emocoes para model.onnx (fp32) e model.int8.onnx"

    def add_arguments(self, parser):
        parser.add_argument("--modelos", nargs="+", default=list(MODELOS), choices=list(MODELOS))

    def handle(self, *args, **opts):
        # confere todos antes de exportar: falhar no segundo deixaria o primeiro já reescrito
        for nome in opts["modelos"]:
            modulo, _, treino = MODELOS[nome]
            if not pesos_salvos(modulo.DESTINO):
                raise CommandError(f"sem pesos em {modulo.DESTINO} — rode manage.py {treino}")
        for nome in opts["modelos"]:
            modulo, exemplo, _ = MODELOS[nome]
            self.exportar(modulo.DESTINO, exemplo)

    def exportar(self, destino, exemplo):
        # imports tardios: torch/onnx só existem no ambiente de treino
        import torch
        from onnxruntime.quantization import QuantType, quantize_dynamic
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        modelo = AutoModelForSequenceClassification.from_pretrained(destino).eval()
        enc = AutoTokenizer.from_pretrained(destino)(
            *exemplo, truncation=True, padding="max_length", max_length=MAX_LEN, return_tensors="pt")
        entradas = ("input_ids", "attention_mask", "token_type_ids")
        eixos = {0: "lote", 1: "seq"}
        torch.onnx.export(
            modelo, tuple(enc[k] for k in entradas), destino / ARQUIVO_FP32,
            input_names=list(entradas), output_names=["logits"],
            dynamic_axes={**{k: eixos for k in entradas}, "logits": {0: "lote"}},
            opset_version=17, dynamo=False,
        )
        self.stdout.write(f"fp32: {destino / ARQUIVO_FP32}")
        # por canal: um fator de escala por coluna de peso; o por tensor derrubava as emoções raras
        quantize_dynamic(destino / ARQUIVO_FP32, destino / ARQUIVO_INT8, weight_type=QuantType.QInt8,
                         per_channel=True)
        self.stdout.write(self.style.SUCCESS(f"int8: {destino / ARQUIVO_INT8}"))
