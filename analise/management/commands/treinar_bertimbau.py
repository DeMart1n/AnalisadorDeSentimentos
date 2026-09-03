import time

from django.core.management.base import BaseCommand, CommandError

from analise.avaliacao import carregar_dados, dividir_por_conversa
from analise.modelos.bertimbau import Bertimbau, dispositivo


class Command(BaseCommand):
    help = "Faz o fine-tune do BERTimbau no conjunto de TREINO (mesmo split de `avaliar`)"

    def add_arguments(self, parser):
        parser.add_argument("--fonte")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--epocas", type=int, default=2)
        parser.add_argument("--batch", type=int, default=32)
        parser.add_argument("--amostra", type=int, default=0, help="limita o treino a N mensagens (0 = tudo)")

    def handle(self, *args, **opts):
        dados = carregar_dados(opts["fonte"])
        if not dados:
            raise CommandError("nenhuma mensagem rotulada no banco")
        # mesma seed de `avaliar`: o conjunto de teste nunca entra no treino
        treino, teste = dividir_por_conversa(dados, seed=opts["seed"])
        if opts["amostra"]:
            treino = treino[: opts["amostra"]]

        modelo = Bertimbau(epocas=opts["epocas"], batch=opts["batch"])
        self.stdout.write(f"dispositivo: {dispositivo()} | treino: {len(treino)} | teste reservado: {len(teste)}")
        inicio = time.time()

        def progresso(epoca, passo, total, perda):
            decorrido = time.time() - inicio
            self.stdout.write(f"  época {epoca} passo {passo}/{total} perda {perda:.4f} ({decorrido/60:.1f} min)")

        modelo.treinar([t for _, t, _ in treino], [r for _, _, r in treino],
                       forcar=True, progresso=progresso)
        self.stdout.write(self.style.SUCCESS(
            f"salvo em {modelo.destino} ({(time.time()-inicio)/60:.1f} min)"))
