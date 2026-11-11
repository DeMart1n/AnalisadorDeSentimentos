"""Emoções por LLM (Claude numa sessão na nuvem): mede o teto de um LLM no mesmo teste do BERTimbau.

    uv run manage.py emocoes_llm exportar --conjunto teste_brighter_ptbr
    # sessão na nuvem lê data/llm/lotes/<conjunto>/lote_NN.jsonl e grava lote_NN.rotulado.jsonl
    uv run manage.py emocoes_llm importar --conjunto teste_brighter_ptbr

Os lotes levam só id e texto; o gabarito fica no banco, então quem rotula não vê a resposta.
`importar` calcula as métricas com a mesma `metricas()` do BERTimbau e salva as notas em .npz
(y_true, probs, origem_id) para o ensemble.
"""

import json
import random
from pathlib import Path

import numpy as np
from django.core.management.base import BaseCommand, CommandError

from analise.avaliacao_emocoes import carregar_emocoes, metricas, split_emocoes
from analise.models import EMOCOES

DIR = Path(__file__).resolve().parents[3] / "data" / "llm"

SISTEMA = """Você anota emoções em mensagens curtas em português do Brasil.
Para cada emoção, dê uma nota de 0 a 1: a chance de a pessoa que escreveu estar expressando essa
emoção no texto. Várias emoções podem estar presentes ao mesmo tempo; nenhuma também é possível
(texto neutro, informativo ou só uma pergunta).

- alegria: felicidade, satisfação, gratidão, entusiasmo, alívio.
- raiva: irritação, indignação, frustração com alguém ou algo.
- tristeza: desânimo, decepção, pesar, solidão.
- medo: preocupação, ansiedade, receio, insegurança com o que pode acontecer.
- surpresa: espanto, algo inesperado (positivo ou negativo).
- nojo: repulsa, asco, desprezo moral ou físico.

Avalie a emoção expressa por quem escreve, não a que o texto provocaria no leitor."""

INSTRUCOES = f"""# Rotulagem de emoções

{SISTEMA}

## Como trabalhar

- Leia e julgue **cada mensagem você mesmo**. Não escreva script, regra de palavra-chave nem
  classificador: o objetivo é medir o julgamento do modelo.
- Cada `lote_NN.jsonl` tem uma mensagem por linha: `{{"id", "anterior", "texto"}}`. `anterior`
  é a mensagem que veio antes na conversa (vazia quando não há); use só como contexto.
- Para cada lote, grave `lote_NN.rotulado.jsonl` na mesma pasta, uma linha por mensagem, na
  mesma ordem, sem pular nenhuma:
  `{{"id": "...", {", ".join(f'"{e}": 0.0' for e in EMOCOES)}}}`
- Notas entre 0 e 1. Faça um lote por vez e confira que o número de linhas bate.
"""


def notas(texto):
    """JSON de uma linha rotulada -> lista de notas na ordem de EMOCOES, cortadas em [0, 1]."""
    d = json.loads(texto)
    return [min(1.0, max(0.0, float(d[e]))) for e in EMOCOES]


def notas_llm(conjunto="treino"):
    """{origem_id: notas} de todos os lote_*.rotulado.jsonl em data/llm/lotes/<conjunto>_*/."""
    return {json.loads(linha)["id"]: notas(linha)
            for arquivo in sorted(DIR.glob(f"lotes/{conjunto}_*/lote_*.rotulado.jsonl"))
            for linha in arquivo.read_text().splitlines() if linha.strip()}


def misturar(exemplos, notas_por_id, alfa):
    """Destilação: y = alfa·nota do LLM + (1-alfa)·rótulo original, só onde há nota. Devolve quantos."""
    n = 0
    for e in exemplos:
        if e["origem_id"] in notas_por_id:
            e["y"] = [alfa * p + (1 - alfa) * y for p, y in zip(notas_por_id[e["origem_id"]], e["y"])]
            n += 1
    return n


class Command(BaseCommand):
    help = "Exporta lotes sem rótulo para um LLM rotular (exportar) e mede as notas dele no teste (importar)"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="acao", required=True)
        for nome in ("exportar", "importar"):
            p = sub.add_parser(nome)
            p.add_argument("--conjunto", default="teste_brighter_ptbr")
            p.add_argument("--fonte", default="brighter_ptbr", help="a validação mistura fontes; filtra por esta")
        sub.choices["exportar"].add_argument("--tamanho", type=int, default=250, help="mensagens por lote")
        sub.choices["exportar"].add_argument("--amostra", type=int, default=0, help="sorteia N (seed 42)")

    def handle(self, *args, **opts):
        exemplos = split_emocoes(carregar_emocoes([opts["fonte"]])).get(opts["conjunto"])
        if not exemplos:
            raise CommandError(f"conjunto {opts['conjunto']!r} vazio ou inexistente para {opts['fonte']}")
        exemplos.sort(key=lambda e: e["origem_id"])  # a ordem do banco não é garantida
        if opts.get("amostra"):
            exemplos = sorted(random.Random(42).sample(exemplos, min(opts["amostra"], len(exemplos))),
                              key=lambda e: e["origem_id"])
        # "teste_<fonte>" já leva a fonte no nome; treino e validação misturam fontes
        self.nome = opts["conjunto"] if opts["conjunto"].startswith("teste") else f"{opts['conjunto']}_{opts['fonte']}"
        self.pasta = DIR / "lotes" / self.nome
        getattr(self, opts["acao"])(exemplos, opts)

    def exportar(self, exemplos, opts):
        self.pasta.mkdir(parents=True, exist_ok=True)
        n = opts["tamanho"]
        for k in range(0, len(exemplos), n):
            linhas = [json.dumps({"id": e["origem_id"], "anterior": e["anterior"], "texto": e["texto"]},
                                 ensure_ascii=False) for e in exemplos[k:k + n]]
            (self.pasta / f"lote_{k // n + 1:02d}.jsonl").write_text("\n".join(linhas) + "\n")
        (self.pasta / "INSTRUCOES.md").write_text(INSTRUCOES)
        self.stdout.write(self.style.SUCCESS(
            f"{len(exemplos)} mensagens em {-(-len(exemplos) // n)} lotes: {self.pasta}"))

    def importar(self, exemplos, opts):
        # com --amostra na exportação, mede só o que foi exportado
        ids = {json.loads(l)["id"] for a in self.pasta.glob("lote_??.jsonl") for l in a.read_text().splitlines() if l.strip()}
        exemplos = [e for e in exemplos if e["origem_id"] in ids]
        rotulado = {}
        for arquivo in sorted(self.pasta.glob("lote_*.rotulado.jsonl")):
            for linha in arquivo.read_text().splitlines():
                if linha.strip():
                    rotulado[json.loads(linha)["id"]] = notas(linha)
        if not rotulado:
            raise CommandError(f"nenhum lote_*.rotulado.jsonl em {self.pasta}")

        # ponytail: mensagem sem rótulo fica com nota 0, que conta como erro no F1
        faltando = [e["origem_id"] for e in exemplos if e["origem_id"] not in rotulado]
        probs = np.array([rotulado.get(e["origem_id"], [0.0] * len(EMOCOES)) for e in exemplos])
        y = [e["y"] for e in exemplos]
        m = metricas(y, (probs >= 0.5).astype(int).tolist())
        self.stdout.write(f"\n=== {self.nome} (n={m['n']}) — F1 macro {m['f1_macro']:.3f} | "
                          f"micro {m['f1_micro']:.3f} | limiar 0,5")
        for e, v in m["por_emocao"].items():
            self.stdout.write(f"  {e:9} F1 {v['f1']:.3f}  IC95 [{v['ic95'][0]:.3f}, {v['ic95'][1]:.3f}]"
                              f"  suporte {v['suporte']}")
        self.stdout.write(f"\nsem rótulo: {len(faltando)}" + (f" (ex.: {faltando[:3]})" if faltando else ""))
        np.savez(DIR / f"predicoes_{self.nome}.npz", y_true=y, probs=probs,
                 origem_id=[e["origem_id"] for e in exemplos])
