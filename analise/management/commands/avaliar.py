import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from analise.avaliacao import avaliar, carregar_dados, dividir_por_conversa, mcnemar
from analise.modelos import REGISTRO, carregar


class Command(BaseCommand):
    help = "Treina e avalia os degraus da escada sobre o mesmo conjunto de teste"

    def add_arguments(self, parser):
        parser.add_argument("--modelos", nargs="+", default=list(REGISTRO), choices=list(REGISTRO))
        parser.add_argument("--fonte", help="limita a uma base específica")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--salvar", action="store_true",
                            help="grava models/metricas.json, consumido por GET /api/metricas")

    def handle(self, *args, **opts):
        dados = carregar_dados(opts["fonte"])
        if not dados:
            raise CommandError("nenhuma mensagem de usuário rotulada no banco — importe uma base antes")
        treino, teste = dividir_por_conversa(dados, seed=opts["seed"])
        if not teste:
            raise CommandError("conjunto de teste vazio — poucas conversas rotuladas")

        resultados = []
        for nome in opts["modelos"]:
            r = avaliar(carregar(nome), treino, teste)
            resultados.append(r)
            self.stdout.write(f"\n=== {nome} — F1 macro {r['f1_macro']:.3f} "
                              f"(treino {r['n_treino']}, teste {r['n_teste']})")
            self.stdout.write(r["relatorio"])
            self.stdout.write(f"matriz (ordem positivo/negativo/neutro): {r['matriz']}")

        if opts["salvar"]:
            destino = Path(__file__).resolve().parents[3] / "models" / "metricas.json"
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(json.dumps({
                "n_teste": resultados[0]["n_teste"],
                "modelos": [{"nome": r["modelo"], "f1_macro": round(r["f1_macro"], 4),
                             "matriz": r["matriz"]} for r in resultados],
                "mcnemar": [
                    {"a": a["modelo"], "b": b["modelo"], **{k: v for k, v in mcnemar(a, b).items()}}
                    for i, a in enumerate(resultados) for b in resultados[i + 1:]
                ],
            }, ensure_ascii=False, indent=2))
            self.stdout.write(self.style.SUCCESS(f"\nmétricas salvas em {destino}"))

        for i, a in enumerate(resultados):
            for b in resultados[i + 1:]:
                m = mcnemar(a, b)
                veredito = "diferença significativa" if m["significativo"] else "sem diferença significativa"
                self.stdout.write(f"\nMcNemar {a['modelo']} x {b['modelo']}: p={m['p']:.4f} — {veredito}")
