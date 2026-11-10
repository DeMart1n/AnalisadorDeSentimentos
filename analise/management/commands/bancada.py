"""Bancada de testes do pipeline de produção (mapper -> BERTimbau int8 + emoções int8, via ONNX).

    uv run manage.py bancada                         # tudo, amostra de 1000 por conjunto de teste
    uv run manage.py bancada --gravar-referencia     # congela as saídas atuais como referência
    uv run manage.py bancada --partes consistencia   # só "mesma entrada -> mesma saída?"

Quatro partes, sobre os conjuntos de teste congelados (nunca usados no treino):
  precisao      F1 da polaridade e das emoções no modelo que roda em produção (int8), não no torch
  consistencia  a mesma entrada dá a mesma saída: 2 rodadas no mesmo processo e contra a referência
                gravada (rótulo idêntico; probabilidade com diferença <= --tolerancia)
  desempenho    latência por mensagem (p50/p95/p99, os dois modelos) e pico de memória
  escala        vazão com 1, 2, 4... processos dividindo os núcleos, como os workers do Celery

A referência guarda hash do texto, nunca o texto, e o hash dos pesos: se os pesos mudaram, a
diferença é esperada (modelo novo) e não falta de determinismo.
"""

import hashlib
import json
import multiprocessing as mp
import os
import random
import resource
import sys
import time
from pathlib import Path

import numpy as np
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from analise.avaliacao import CLASSES, carregar_dados, split_congelado
from analise.avaliacao_emocoes import carregar_emocoes, metricas, split_emocoes
from analise.mappers.ia_mapper import ConversaIAMapper
from analise.models import EMOCOES
from analise.modelos import bertimbau_onnx, emocoes_onnx

REFERENCIA = Path(__file__).resolve().parents[3] / "models" / "bancada" / "referencia.json"
PARTES = ["precisao", "consistencia", "desempenho", "escala"]


def _hash(*partes):
    return hashlib.sha1("\x1f".join(partes).encode()).hexdigest()[:16]


def _hash_pesos():
    h = hashlib.sha1()
    for destino in (bertimbau_onnx.DESTINO, emocoes_onnx.DESTINO):
        h.update(bertimbau_onnx.caminho_pesos(destino).read_bytes())
    h.update((emocoes_onnx.DESTINO / "limiares.json").read_bytes())
    return h.hexdigest()[:16]


def comparar(referencia, atual, tolerancia):
    """{chave: (rótulo, [probs])} x {chave: ...} -> (comparadas, rótulos diferentes, maior diferença de prob)."""
    comuns = referencia.keys() & atual.keys()
    rotulos = sum(referencia[k][0] != atual[k][0] for k in comuns)
    delta = max((float(np.max(np.abs(np.subtract(referencia[k][1], atual[k][1])))) for k in comuns), default=0.0)
    return len(comuns), rotulos, delta, delta <= tolerancia and rotulos == 0


def _amostra(lista, n, seed=42):
    return lista if not n or n >= len(lista) else random.Random(seed).sample(lista, n)


def _worker(textos, threads, barreira, fila):
    # cada processo carrega os próprios modelos, como um worker do Celery
    os.environ["ONNX_THREADS"] = str(threads)
    pol, emo = bertimbau_onnx.BertimbauOnnx(), emocoes_onnx.EmocoesOnnx()
    pol.prever(textos[:5]), emo.prever([{"anterior": "", "texto": t} for t in textos[:5]])  # aquecimento
    barreira.wait()
    inicio = time.perf_counter()
    pol.prever(textos)
    emo.prever([{"anterior": "", "texto": t} for t in textos])
    fila.put(time.perf_counter() - inicio)


class Command(BaseCommand):
    help = "Mede precisão, consistência (mesma entrada -> mesma saída), desempenho e escala do pipeline"

    def add_arguments(self, parser):
        parser.add_argument("--partes", nargs="+", choices=PARTES, default=PARTES)
        parser.add_argument("--amostra", type=int, default=1000, help="mensagens por conjunto de teste; 0 = todas")
        parser.add_argument("--processos", type=int, nargs="+", default=[1, 2, 4])
        parser.add_argument("--n-escala", type=int, default=400, help="mensagens no teste de escala")
        parser.add_argument("--tolerancia", type=float, default=1e-3, help="maior diferença aceita numa probabilidade")
        parser.add_argument("--gravar-referencia", action="store_true", help=f"grava {REFERENCIA.relative_to(REFERENCIA.parents[2])}")

    def handle(self, *args, **opts):
        mapper = ConversaIAMapper()
        _, teste_pol = split_congelado(carregar_dados())
        pol = [(mapper.mapear_texto(t), r) for _, t, r in _amostra(teste_pol, opts["amostra"])]
        testes_emo = {k: v for k, v in split_emocoes(carregar_emocoes()).items() if k.startswith("teste")}
        emo = {k: [{"anterior": mapper.mapear_texto(e["anterior"]), "texto": mapper.mapear_texto(e["texto"]),
                    "y": e["y"]} for e in _amostra(v, opts["amostra"])] for k, v in testes_emo.items()}
        if not pol or not emo:
            raise CommandError("sem conjunto de teste de polaridade ou de emoções no banco")
        self.stdout.write(f"amostra: polaridade {len(pol)}; " + "; ".join(f"{k} {len(v)}" for k, v in emo.items()))

        # escala primeiro: o fork tem de acontecer antes de o processo pai criar sessões ONNX
        # (thread pools herdados num fork podem travar)
        if "escala" in opts["partes"]:
            self.escala([t for t, _ in pol][:opts["n_escala"]], opts["processos"])

        modelo_pol, modelo_emo = bertimbau_onnx.BertimbauOnnx(), emocoes_onnx.EmocoesOnnx()
        self.stdout.write(f"pesos: {bertimbau_onnx.caminho_pesos().name} (hash {_hash_pesos()})")

        def rodar():
            rotulos, scores = modelo_pol.prever([t for t, _ in pol])
            saidas = {_hash("pol", t): (r, [s]) for (t, _), r, s in zip(pol, rotulos, scores)}
            preds_emo = {}
            for nome, exemplos in emo.items():
                previstas, probs = modelo_emo.prever(exemplos)
                preds_emo[nome] = previstas
                for e, p, pr in zip(exemplos, previstas, probs):
                    saidas[_hash("emo", e["anterior"], e["texto"])] = (sorted(p), [pr[x] for x in EMOCOES])
            return rotulos, preds_emo, saidas

        inicio = time.perf_counter()
        rotulos, preds_emo, saidas = rodar()
        self.stdout.write(f"rodada completa em {time.perf_counter() - inicio:.1f}s")

        if "precisao" in opts["partes"]:
            self.precisao(pol, rotulos, emo, preds_emo)
        if "consistencia" in opts["partes"]:
            self.consistencia(saidas, rodar()[2], opts)
        if "desempenho" in opts["partes"]:
            self.desempenho(modelo_pol, modelo_emo, [t for t, _ in pol][:300])

    def precisao(self, pol, rotulos, emo, preds_emo):
        from sklearn.metrics import f1_score

        self.stdout.write(self.style.MIGRATE_HEADING("\n== precisão (modelo de produção, int8)"))
        y = [r for _, r in pol]
        por_classe = f1_score(y, rotulos, labels=CLASSES, average=None, zero_division=0)
        self.stdout.write(f"polaridade  F1 macro {por_classe.mean():.3f}  ("
                          + ", ".join(f"{c} {f:.3f}" for c, f in zip(CLASSES, por_classe)) + ")")
        for nome, exemplos in emo.items():
            y_pred = [[e in p for e in EMOCOES] for p in preds_emo[nome]]
            m = metricas([e["y"] for e in exemplos], y_pred, n_boot=200)
            self.stdout.write(f"{nome:28} F1 macro {m['f1_macro']:.3f}  ("
                              + ", ".join(f"{e} {v['f1']:.2f}" for e, v in m["por_emocao"].items()) + ")")
        self.stdout.write("com amostra < conjunto inteiro o número oscila; compare com --amostra 0")

    def consistencia(self, rodada1, rodada2, opts):
        self.stdout.write(self.style.MIGRATE_HEADING("\n== consistência (mesma entrada -> mesma saída)"))
        n, rot, delta, ok = comparar(rodada1, rodada2, opts["tolerancia"])
        self.stdout.write(f"2 rodadas no mesmo processo: {n} entradas, {rot} rótulos diferentes, "
                          f"maior diferença de prob {delta:.2e} -> " + ("OK" if ok else "DIFERENTE"))

        pesos = _hash_pesos()
        if REFERENCIA.exists():
            ref = json.loads(REFERENCIA.read_text())
            n, rot, delta, ok = comparar({k: tuple(v) for k, v in ref["saidas"].items()}, rodada1, opts["tolerancia"])
            aviso = "" if ref["pesos"] == pesos else "  (pesos mudaram desde a referência: diferença esperada)"
            self.stdout.write(f"contra a referência de {ref['gravada_em']}: {n} entradas em comum, {rot} rótulos "
                              f"diferentes, maior diferença {delta:.2e} -> " + ("OK" if ok else "DIFERENTE") + aviso)
        elif not opts["gravar_referencia"]:
            self.stdout.write("sem referência gravada: rode com --gravar-referencia para comparar nas próximas vezes")
        if opts["gravar_referencia"]:
            REFERENCIA.parent.mkdir(parents=True, exist_ok=True)
            REFERENCIA.write_text(json.dumps({"gravada_em": time.strftime("%Y-%m-%d %H:%M"), "pesos": pesos,
                                              "saidas": rodada1}, separators=(",", ":")))
            self.stdout.write(self.style.SUCCESS(f"referência gravada: {len(rodada1)} saídas"))

    def desempenho(self, modelo_pol, modelo_emo, textos):
        self.stdout.write(self.style.MIGRATE_HEADING("\n== desempenho (1 processo, polaridade + emoções por mensagem)"))
        tempos = []
        for t in textos:
            inicio = time.perf_counter()
            modelo_pol.prever([t])
            modelo_emo.prever([{"anterior": "", "texto": t}])
            tempos.append((time.perf_counter() - inicio) * 1000)
        p50, p95, p99 = np.percentile(tempos, [50, 95, 99])
        # ru_maxrss: bytes no macOS, KB no Linux
        pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (2**20 if sys.platform == "darwin" else 2**10)
        self.stdout.write(f"{len(textos)} mensagens: p50 {p50:.1f} ms, p95 {p95:.1f} ms, p99 {p99:.1f} ms, "
                          f"vazão {1000 * len(tempos) / sum(tempos):.0f} msg/s; pico de memória {pico:.0f} MB")

    def escala(self, textos, processos):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n== escala ({len(textos)} mensagens divididas entre processos)"))
        nucleos = os.cpu_count() or 1
        connections.close_all()  # conexão do SQLite não atravessa fork
        ctx = mp.get_context("fork")
        base = None
        for p in processos:
            barreira, fila = ctx.Barrier(p + 1), ctx.Queue()
            partes = [textos[i::p] for i in range(p)]
            filhos = [ctx.Process(target=_worker, args=(parte, max(1, nucleos // p), barreira, fila)) for parte in partes]
            for f in filhos:
                f.start()
            barreira.wait()  # todos carregaram e aqueceram: o relógio começa junto
            inicio = time.perf_counter()
            [fila.get() for _ in filhos]
            parede = time.perf_counter() - inicio
            for f in filhos:
                f.join()
            vazao = len(textos) / parede
            base = base or vazao
            self.stdout.write(f"{p} processo(s) x {max(1, nucleos // p)} threads: {vazao:.0f} msg/s "
                              f"({vazao / base:.2f}x o de {processos[0]} processo(s))")
