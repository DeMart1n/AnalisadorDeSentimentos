import json
from pathlib import Path

import numpy as np
from django.core.management.base import BaseCommand, CommandError

from analise.avaliacao_emocoes import carregar_emocoes, metricas, split_emocoes
from analise.models import EMOCOES
from analise.modelos.emocoes import Emocoes

DESTINO = Path(__file__).resolve().parents[3] / "models" / "metricas_emocoes.json"


class Command(BaseCommand):
    help = "Avalia o classificador de emoções em cada conjunto de teste, separadamente"

    def add_arguments(self, parser):
        parser.add_argument("--fontes", nargs="+")
        parser.add_argument("--salvar", action="store_true", help=f"grava {DESTINO.name}")

    def handle(self, *args, **opts):
        modelo = Emocoes()
        if not modelo.treinado:
            raise CommandError("modelo de emoções não treinado — rode treinar_emocoes")
        partes = split_emocoes(carregar_emocoes(opts["fontes"]))
        testes = {k: v for k, v in sorted(partes.items()) if k.startswith("teste")}
        if not testes:
            raise CommandError("nenhum conjunto de teste")

        resultado = {"limiares": dict(zip(EMOCOES, modelo.limiares)), "testes": {}}
        for nome, exemplos in testes.items():
            y_pred, probs = modelo.prever(exemplos)
            y_true = [e["y"] for e in exemplos]
            m = metricas(y_true, y_pred)
            # probabilidades brutas para curvas precisão-revocação (scripts/graficos_emocoes.py)
            np.savez(modelo.destino / f"predicoes_{nome}.npz", y_true=y_true, probs=probs)
            resultado["testes"][nome] = m
            self.stdout.write(f"\n=== {nome} (n={m['n']}) — F1 macro {m['f1_macro']:.3f} | micro {m['f1_micro']:.3f}")
            for e, v in m["por_emocao"].items():
                self.stdout.write(f"  {e:9} F1 {v['f1']:.3f}  IC95 [{v['ic95'][0]:.3f}, {v['ic95'][1]:.3f}]"
                                  f"  suporte {v['suporte']}")
        if opts["salvar"]:
            DESTINO.write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
            self.stdout.write(self.style.SUCCESS(f"\nmétricas salvas em {DESTINO}"))
