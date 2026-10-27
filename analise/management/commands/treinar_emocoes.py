import random
import time

from django.core.management.base import BaseCommand, CommandError

from analise.avaliacao_emocoes import PUBLICAS, carregar_emocoes, split_emocoes
from analise.modelos.bertimbau import dispositivo
from analise.management.commands.emocoes_llm import misturar, notas_llm
from analise.modelos.emocoes import Emocoes


class Command(BaseCommand):
    help = "Fine-tune do classificador de emoções no TREINO; limiares ajustados na VALIDAÇÃO"

    def add_arguments(self, parser):
        parser.add_argument("--fontes", nargs="+", help="limita a estas fontes (padrão: todas com rótulo)")
        parser.add_argument("--epocas", type=int, default=2)
        parser.add_argument("--batch", type=int, default=32)
        parser.add_argument("--amostra", type=int, default=0,
                            help="limita treino e validação a N exemplos cada (teste de fumaça)")
        parser.add_argument("--alfa-llm", type=float, default=0.0,
                            help="peso das notas do LLM (data/llm/lotes/treino_*) no alvo do treino; 0 desliga")
        parser.add_argument("--duas-etapas", action="store_true",
                            help="etapa 2: 1 época, lr menor, só com dados de chat (real, LLM, sintético)")

    def handle(self, *args, **opts):
        partes = split_emocoes(carregar_emocoes(opts["fontes"]))
        treino, validacao = partes.get("treino", []), partes.get("validacao", [])
        if not treino or not validacao:
            raise CommandError("faltam exemplos de treino ou validação — importe uma base de emoção antes")
        if opts["amostra"]:
            rng = random.Random(42)
            treino = rng.sample(treino, min(opts["amostra"], len(treino)))
            validacao = rng.sample(validacao, min(opts["amostra"], len(validacao)))
        if opts["alfa_llm"]:
            n = misturar(treino, notas_llm(), opts["alfa_llm"])
            if not n:
                raise CommandError("--alfa-llm sem nenhuma nota de LLM em data/llm/lotes/treino_*/lote_*.rotulado.jsonl")
            self.stdout.write(f"alvo misturado com o LLM (alfa {opts['alfa_llm']}) em {n} de {len(treino)} exemplos")
        chat = None
        if opts["duas_etapas"]:
            chat = [e for e in treino if e["fonte"] not in PUBLICAS]
            if not chat:
                raise CommandError("--duas-etapas sem nenhum exemplo de chat no treino")

        modelo = Emocoes(epocas=opts["epocas"], batch=opts["batch"])
        self.stdout.write(f"dispositivo: {dispositivo()} | treino: {len(treino)} | validação: {len(validacao)}"
                          f" | testes reservados: {', '.join(k for k in partes if k.startswith('teste'))}")
        inicio = time.time()

        def progresso(epoca, passo, total, perda):
            self.stdout.write(f"  época {epoca} passo {passo}/{total} perda {perda:.4f} "
                              f"({(time.time() - inicio) / 60:.1f} min)")

        modelo.treinar(treino, validacao, chat=chat, forcar=True, progresso=progresso)
        self.stdout.write(self.style.SUCCESS(
            f"salvo em {modelo.destino} ({(time.time() - inicio) / 60:.1f} min) | limiares {modelo.limiares}"))
