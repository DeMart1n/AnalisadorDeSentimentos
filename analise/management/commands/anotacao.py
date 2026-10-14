"""Ciclo de anotação humana de emoções: exportar CSV -> anotar -> importar -> kappa.

Regras em docs/emocoes/guia-anotacao.md. A coluna `neutro` existe para separar
"anotei como neutro" de "pulei a linha": linha sem nenhum 1 é ignorada na importação.
"""

import csv
import random
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from sklearn.metrics import cohen_kappa_score

from analise.models import EMOCOES, HUMANO, USUARIO, Mensagem, RotuloEmocao

COLUNAS = ["mensagem_id", "anterior", "texto", *EMOCOES, "neutro"]


def _bit(valor, linha):
    valor = (valor or "").strip()
    if valor not in ("", "0", "1"):
        raise CommandError(f"mensagem {linha['mensagem_id']}: valor inválido {valor!r} (use 0, 1 ou vazio)")
    return valor == "1"


class Command(BaseCommand):
    help = "Exporta amostra para anotação humana, importa de volta e calcula o Kappa por emoção"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="acao", required=True)
        exp = sub.add_parser("exportar")
        exp.add_argument("arquivo")
        exp.add_argument("--fontes", nargs="+", required=True, help="fontes de chat real (Conversa.fonte)")
        exp.add_argument("--n", type=int, default=1000)
        exp.add_argument("--seed", type=int, default=42)
        imp = sub.add_parser("importar")
        imp.add_argument("arquivo")
        imp.add_argument("--anotador", required=True)
        kap = sub.add_parser("kappa")
        kap.add_argument("anotador_a")
        kap.add_argument("anotador_b")

    def handle(self, *args, **opts):
        getattr(self, opts["acao"])(opts)

    def exportar(self, opts):
        # ponytail: unidade = mensagem; agrupar turnos do mesmo autor quando o chat real mostrar picotes
        todas = list(Mensagem.objects.filter(conversa__fonte__in=opts["fontes"])
                     .order_by("conversa_id", "ordem").values("id", "conversa_id", "autor", "texto"))
        ja_anotadas = set(RotuloEmocao.objects.filter(origem=HUMANO).values_list("mensagem_id", flat=True))
        anterior, por_conversa = {}, defaultdict(list)
        for i, m in enumerate(todas):
            mesma = i > 0 and todas[i - 1]["conversa_id"] == m["conversa_id"]
            anterior[m["id"]] = todas[i - 1]["texto"] if mesma else ""
            if m["autor"] == USUARIO and m["id"] not in ja_anotadas:
                por_conversa[m["conversa_id"]].append(m)
        if not por_conversa:
            raise CommandError("nenhuma mensagem de cliente não anotada nessas fontes")

        # estratifica por conversa: uma mensagem de cada conversa por rodada,
        # para conversa longa não dominar a amostra
        rng = random.Random(opts["seed"])
        filas = list(por_conversa.values())
        rng.shuffle(filas)
        for f in filas:
            rng.shuffle(f)
        amostra = []
        while len(amostra) < opts["n"] and any(filas):
            amostra += [f.pop() for f in filas if f][: opts["n"] - len(amostra)]

        with open(opts["arquivo"], "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(COLUNAS)
            for m in amostra:
                w.writerow([m["id"], anterior[m["id"]], m["texto"], *[""] * (len(EMOCOES) + 1)])
        self.stdout.write(self.style.SUCCESS(
            f"{len(amostra)} mensagens de {len({m['conversa_id'] for m in amostra})} conversas em {opts['arquivo']}"))

    def importar(self, opts):
        with open(opts["arquivo"], encoding="utf-8") as f:
            linhas = list(csv.DictReader(f))
        faltando = set(COLUNAS) - set(linhas[0] if linhas else {})
        if faltando:
            raise CommandError(f"colunas ausentes: {sorted(faltando)}")
        gravadas = puladas = 0
        with transaction.atomic():
            for l in linhas:
                marcas = {e: _bit(l[e], l) for e in EMOCOES}
                neutro = _bit(l["neutro"], l)
                if neutro and any(marcas.values()):
                    raise CommandError(f"mensagem {l['mensagem_id']}: neutro junto com emoção")
                if not neutro and not any(marcas.values()):
                    puladas += 1
                    continue
                RotuloEmocao.objects.update_or_create(
                    mensagem_id=int(l["mensagem_id"]), origem=HUMANO, anotador=opts["anotador"],
                    defaults=marcas)
                gravadas += 1
        self.stdout.write(self.style.SUCCESS(f"{gravadas} rótulos de {opts['anotador']}; {puladas} linhas em branco puladas"))

    def kappa(self, opts):
        rotulos = {}
        for a in (opts["anotador_a"], opts["anotador_b"]):
            rotulos[a] = {r.mensagem_id: r for r in RotuloEmocao.objects.filter(origem=HUMANO, anotador=a)}
        comuns = sorted(set(rotulos[opts["anotador_a"]]) & set(rotulos[opts["anotador_b"]]))
        if not comuns:
            raise CommandError("nenhuma mensagem anotada pelos dois")
        self.stdout.write(f"{len(comuns)} mensagens em comum")
        for e in [*EMOCOES, "neutro"]:
            a, b = ([getattr(rotulos[x][i], e) if e != "neutro" else not rotulos[x][i].emocoes for i in comuns]
                    for x in (opts["anotador_a"], opts["anotador_b"]))
            # kappa é indefinido se os dois nunca (ou sempre) marcam: vira nan
            self.stdout.write(f"  {e:9} kappa {cohen_kappa_score(a, b):.3f}  (a marcou {sum(a)}, b marcou {sum(b)})")
