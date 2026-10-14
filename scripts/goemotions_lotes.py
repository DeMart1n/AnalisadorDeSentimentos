"""GoEmotions -> subconjunto Ekman -> lotes para tradução -> arquivo único traduzido.

Só stdlib: roda na sessão da nuvem sem `uv sync` (torch é pesado). Dados em data/ (fora do git).

    python3 scripts/goemotions_lotes.py lotes    # baixa, monta o subconjunto e divide em lotes
    python3 scripts/goemotions_lotes.py juntar   # valida os lotes traduzidos e gera traduzido.jsonl

Mapeamento: o oficial do GoEmotions para Ekman, EXCETO surpresa, que fica só com `surprise`.
Texto só com curiosity/confusion/realization é descartado: senão toda pergunta do chat vira surpresa.
Subconjunto: tudo que tem raiva/medo/surpresa/nojo/tristeza + 4.000 só alegria + 3.000 neutros (seed 42).
"""

import csv
import json
import random
import sys
import urllib.request
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "data" / "goemotions"
URL = "https://raw.githubusercontent.com/google-research/google-research/master/goemotions/data/"
ARQUIVOS = ["train.tsv", "dev.tsv", "test.tsv", "emotions.txt", "ekman_mapping.json"]
DESCARTAR = {"curiosity", "confusion", "realization"}
TAMANHO_LOTE = 800


def lotes():
    DIR.mkdir(parents=True, exist_ok=True)
    for a in ARQUIVOS:
        if not (DIR / a).exists():
            urllib.request.urlretrieve(URL + a, DIR / a)
    nomes = (DIR / "emotions.txt").read_text().split()
    mapa = json.loads((DIR / "ekman_mapping.json").read_text())
    mapa["surprise"] = ["surprise"]
    inv = {g: e for e, gs in mapa.items() for g in gs}

    raras, alegria, neutro = [], [], []
    for split in ["train", "dev", "test"]:
        with (DIR / f"{split}.tsv").open(encoding="utf-8") as f:
            for texto, labs, id_ in csv.reader(f, delimiter="\t"):
                gs = [nomes[int(i)] for i in labs.split(",")]
                ek = sorted({inv[g] for g in gs if g in inv})
                if not ek and DESCARTAR & set(gs):
                    continue
                r = {"id": id_, "split": split, "texto": texto, "ekman": ek, "original": gs}
                (raras if set(ek) - {"joy"} else alegria if ek else neutro).append(r)
    rng = random.Random(42)
    sub = raras + rng.sample(alegria, 4000) + rng.sample(neutro, 3000)
    rng.shuffle(sub)

    with (DIR / "subconjunto.jsonl").open("w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in sub)
    (DIR / "lotes").mkdir(exist_ok=True)
    for n, i in enumerate(range(0, len(sub), TAMANHO_LOTE)):
        with (DIR / "lotes" / f"lote_{n:03d}.jsonl").open("w", encoding="utf-8") as f:
            f.writelines(json.dumps({"id": r["id"], "texto": r["texto"]}, ensure_ascii=False) + "\n"
                         for r in sub[i:i + TAMANHO_LOTE])
    print(f"{len(sub)} textos em {n + 1} lotes de até {TAMANHO_LOTE} em {DIR / 'lotes'}")


def juntar():
    """Falha alto se algum lote faltar, tiver id trocado ou tradução vazia/idêntica ao original."""
    sub = {r["id"]: r for r in map(json.loads, (DIR / "subconjunto.jsonl").open(encoding="utf-8"))}
    erros, saida = [], []
    for entrada in sorted((DIR / "lotes").glob("lote_[0-9][0-9][0-9].jsonl")):
        pt = entrada.with_suffix(".pt.jsonl")
        if not pt.exists():
            erros.append(f"{pt.name}: não existe")
            continue
        ids = [json.loads(l)["id"] for l in entrada.open(encoding="utf-8")]
        try:
            trad = [json.loads(l) for l in pt.open(encoding="utf-8") if l.strip()]
        except json.JSONDecodeError as e:
            erros.append(f"{pt.name}: JSON inválido ({e})")
            continue
        if [t["id"] for t in trad] != ids:
            erros.append(f"{pt.name}: ids diferentes da entrada ({len(trad)} de {len(ids)})")
            continue
        for t in trad:
            r = sub[t["id"]]
            if not t.get("texto_pt", "").strip() or t["texto_pt"].strip() == r["texto"].strip():
                erros.append(f"{pt.name}: {t['id']} sem tradução")
            saida.append({**r, "texto_pt": t["texto_pt"]})
    if erros:
        sys.exit("\n".join(erros))
    with (DIR / "traduzido.jsonl").open("w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in saida)
    print(f"ok: {len(saida)} textos em {DIR / 'traduzido.jsonl'}")


if __name__ == "__main__":
    {"lotes": lotes, "juntar": juntar}[sys.argv[1]]()
