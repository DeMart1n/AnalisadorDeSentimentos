"""Ciclo de anotação humana de emoções: exportar CSV -> anotar -> importar -> kappa.

Ou, sem CSV, direto no terminal (grava a cada mensagem; rodar de novo continua de onde parou):
    uv run manage.py anotacao anotar --fontes atendimento-real --anotador caua --n 200

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


def sortear(fontes, n, seed, excluir=()):
    """Amostra de mensagens de cliente com a anterior da conversa (qualquer autor) como contexto."""
    # ponytail: unidade = mensagem; agrupar turnos do mesmo autor quando o chat real mostrar picotes
    todas = list(Mensagem.objects.filter(conversa__fonte__in=fontes)
                 .order_by("conversa_id", "ordem").values("id", "conversa_id", "autor", "texto"))
    por_conversa = defaultdict(list)
    for i, m in enumerate(todas):
        mesma = i > 0 and todas[i - 1]["conversa_id"] == m["conversa_id"]
        m["anterior"] = todas[i - 1]["texto"] if mesma else ""
        if m["autor"] == USUARIO and m["id"] not in excluir:
            por_conversa[m["conversa_id"]].append(m)
    if not por_conversa:
        raise CommandError("nenhuma mensagem de cliente não anotada nessas fontes")

    # estratifica por conversa: uma mensagem de cada conversa por rodada,
    # para conversa longa não dominar a amostra
    rng = random.Random(seed)
    filas = list(por_conversa.values())
    rng.shuffle(filas)
    for f in filas:
        rng.shuffle(f)
    amostra = []
    while len(amostra) < n and any(filas):
        amostra += [f.pop() for f in filas if f][: n - len(amostra)]
    return amostra


TECLAS = {"a": "alegria", "r": "raiva", "t": "tristeza", "m": "medo", "s": "surpresa", "n": "nojo"}
AJUDA = "(a)legria (r)aiva (t)risteza (m)edo (s)urpresa (n)ojo | 0 neutro | p pular | v voltar | q sair"


def ler_resposta(entrada):
    """'ar' -> {"alegria", "raiva"}; '0' -> set() (neutro); p/v/q -> a própria letra; inválido -> None."""
    entrada = entrada.strip().lower().replace(" ", "")
    if entrada in ("p", "v", "q"):
        return entrada
    if entrada == "0":
        return set()
    if entrada and all(c in TECLAS for c in entrada):
        return {TECLAS[c] for c in entrada}
    return None


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
        ano = sub.add_parser("anotar", help="anota no terminal, uma mensagem por vez, às cegas")
        ano.add_argument("--fontes", nargs="+", required=True)
        ano.add_argument("--anotador", required=True)
        ano.add_argument("--n", type=int, default=200, help="tamanho total da amostra deste anotador")
        ano.add_argument("--seed", type=int, default=42, help="mesma seed = mesma ordem para todos (dá o kappa)")
        kap = sub.add_parser("kappa")
        kap.add_argument("anotador_a")
        kap.add_argument("anotador_b")

    def handle(self, *args, **opts):
        getattr(self, opts["acao"])(opts)

    def exportar(self, opts):
        ja_anotadas = set(RotuloEmocao.objects.filter(origem=HUMANO).values_list("mensagem_id", flat=True))
        amostra = sortear(opts["fontes"], opts["n"], opts["seed"], excluir=ja_anotadas)
        with open(opts["arquivo"], "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(COLUNAS)
            for m in amostra:
                w.writerow([m["id"], m["anterior"], m["texto"], *[""] * (len(EMOCOES) + 1)])
        self.stdout.write(self.style.SUCCESS(
            f"{len(amostra)} mensagens de {len({m['conversa_id'] for m in amostra})} conversas em {opts['arquivo']}"))

    def anotar(self, opts):
        # sorteia sem excluir nada e só depois pula o que este anotador já fez: a ordem fica
        # igual entre sessões e entre anotadores, então as primeiras N de dois anotadores coincidem
        amostra = sortear(opts["fontes"], opts["n"], opts["seed"])
        feitas = set(RotuloEmocao.objects.filter(origem=HUMANO, anotador=opts["anotador"])
                     .values_list("mensagem_id", flat=True))
        pendentes = [m for m in amostra if m["id"] not in feitas]
        self.stdout.write(f"{len(amostra) - len(pendentes)}/{len(amostra)} já anotadas. {AJUDA}\n")
        i, historico = 0, []
        while i < len(pendentes):
            m = pendentes[i]
            self.stdout.write(f"[{len(amostra) - len(pendentes) + i + 1}/{len(amostra)}]")
            if m["anterior"]:
                self.stdout.write(f"  anterior: {m['anterior']}")
            self.stdout.write(self.style.MIGRATE_HEADING(f"  cliente:  {m['texto']}"))
            try:
                resposta = ler_resposta(input("> "))
            except EOFError:
                resposta = "q"
            if resposta is None:
                self.stdout.write(f"  não entendi. {AJUDA}")
                continue
            if resposta == "q":
                break
            if resposta == "v":
                if historico:
                    i = historico.pop()
                    RotuloEmocao.objects.filter(mensagem_id=pendentes[i]["id"], origem=HUMANO,
                                                anotador=opts["anotador"]).delete()
                continue
            if resposta != "p":
                RotuloEmocao.objects.update_or_create(
                    mensagem_id=m["id"], origem=HUMANO, anotador=opts["anotador"],
                    defaults={e: e in resposta for e in EMOCOES})
                self.stdout.write(f"  ok: {', '.join(sorted(resposta)) or 'neutro'}\n")
            historico.append(i)
            i += 1
        total = RotuloEmocao.objects.filter(origem=HUMANO, anotador=opts["anotador"],
                                            mensagem_id__in=[m["id"] for m in amostra]).count()
        self.stdout.write(self.style.SUCCESS(f"{total}/{len(amostra)} anotadas por {opts['anotador']}"))

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
