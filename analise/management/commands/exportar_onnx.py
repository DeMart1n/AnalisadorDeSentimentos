"""Exporta o BERTimbau treinado para ONNX (fp32) e quantiza em int8.

Roda depois de `treinar_bertimbau`: o worker de inferência só lê o .onnx e
não precisa de torch. Retreinou? Exporte de novo.
"""

from django.core.management.base import BaseCommand, CommandError

from analise.modelos.bertimbau import pesos_salvos
from analise.modelos.bertimbau_onnx import ARQUIVO_FP32, ARQUIVO_INT8, DESTINO, MAX_LEN


class Command(BaseCommand):
    help = "Exporta models/bertimbau para model.onnx (fp32) e model.int8.onnx"

    def handle(self, *args, **opts):
        if not pesos_salvos(DESTINO):
            raise CommandError(f"sem pesos em {DESTINO} — rode manage.py treinar_bertimbau")
        # imports tardios: torch/onnx só existem no ambiente de treino
        import torch
        from onnxruntime.quantization import QuantType, quantize_dynamic
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        modelo = AutoModelForSequenceClassification.from_pretrained(DESTINO).eval()
        exemplo = AutoTokenizer.from_pretrained(DESTINO)(
            ["exemplo de mensagem"], truncation=True, padding="max_length",
            max_length=MAX_LEN, return_tensors="pt")
        entradas = ("input_ids", "attention_mask", "token_type_ids")
        eixos = {0: "lote", 1: "seq"}
        torch.onnx.export(
            modelo, tuple(exemplo[k] for k in entradas), DESTINO / ARQUIVO_FP32,
            input_names=list(entradas), output_names=["logits"],
            dynamic_axes={**{k: eixos for k in entradas}, "logits": {0: "lote"}},
            opset_version=17, dynamo=False,
        )
        self.stdout.write(f"fp32: {DESTINO / ARQUIVO_FP32}")
        quantize_dynamic(DESTINO / ARQUIVO_FP32, DESTINO / ARQUIVO_INT8, weight_type=QuantType.QInt8)
        self.stdout.write(self.style.SUCCESS(f"int8: {DESTINO / ARQUIVO_INT8}"))
