"""Gráficos do classificador de emoções, a partir do que treinar/avaliar_emocoes salvam.

    uv run --with matplotlib python scripts/graficos_emocoes.py

Lê models/emocoes/historico.json, models/metricas_emocoes.json e models/emocoes/predicoes_*.npz.
Grava PNGs em docs/relatorio/img/emocoes/.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import precision_recall_curve  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "models" / "emocoes"
SAIDA = RAIZ / "docs" / "relatorio" / "img" / "emocoes"
EMOCOES = ["alegria", "raiva", "tristeza", "medo", "surpresa", "nojo"]


def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(SAIDA / nome, dpi=130)
    plt.close(fig)
    print("  ", SAIDA / nome)


def perda(hist):
    pontos = hist["perda"]
    x = np.arange(len(pontos)) * 10  # registrado a cada 10 passos
    y = np.array([p["perda"] for p in pontos])
    janela = max(1, len(y) // 30)
    media = np.convolve(y, np.ones(janela) / janela, mode="valid")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x, y, alpha=0.3, label="perda (a cada 10 passos)")
    ax.plot(x[janela - 1:], media, label=f"média móvel ({janela})")
    # marca o início de cada época
    for i, p in enumerate(pontos):
        if p["passo"] == 0 and i > 0:
            ax.axvline(x[i], color="gray", ls="--", lw=0.8)
    ax.set(xlabel="passo de treino", ylabel="BCE ponderada", title="Perda de treino")
    ax.legend()
    salvar(fig, "perda.png")


def validacao(hist):
    v = hist["validacao"]
    rot = [f"et{p['etapa']} ép{p['epoca']}" for p in v]
    fig, ax = plt.subplots(figsize=(8, 4))
    for e in EMOCOES:
        ax.plot(rot, [p["f1_por_emocao"][e] for p in v], marker="o", label=e)
    ax.plot(rot, [p["f1_macro"] for p in v], marker="s", color="black", lw=2.5, label="macro")
    ax.set(ylim=(0, 1), ylabel="F1 (limiar 0,5)", title="F1 na validação ao fim de cada época")
    ax.legend(ncol=4, fontsize=8)
    salvar(fig, "validacao_por_epoca.png")


def f1_por_emocao(metricas):
    testes = metricas["testes"]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    largura = 0.8 / len(testes)
    for k, (nome, m) in enumerate(testes.items()):
        f1 = [m["por_emocao"][e]["f1"] for e in EMOCOES]
        ic = np.array([m["por_emocao"][e]["ic95"] for e in EMOCOES])
        erro = [np.array(f1) - ic[:, 0], ic[:, 1] - np.array(f1)]
        x = np.arange(len(EMOCOES)) + k * largura
        ax.bar(x, f1, largura, yerr=erro, capsize=3, label=f"{nome} (macro {m['f1_macro']:.3f})")
    ax.set_xticks(np.arange(len(EMOCOES)) + largura * (len(testes) - 1) / 2, EMOCOES)
    ax.set(ylim=(0, 1), ylabel="F1", title="F1 por emoção no teste (barras = IC 95% bootstrap)")
    ax.legend(fontsize=8)
    salvar(fig, "f1_por_emocao.png")


def matrizes(nome, m):
    fig, eixos = plt.subplots(2, 3, figsize=(9, 6))
    for ax, e in zip(eixos.flat, EMOCOES):
        mat = np.array(m["matriz_por_emocao"][e])  # [[tn, fp], [fn, tp]]
        ax.imshow(mat, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, mat[i, j], ha="center", va="center",
                        color="white" if mat[i, j] > mat.max() / 2 else "black")
        ax.set_xticks([0, 1], ["prev. não", "prev. sim"])
        ax.set_yticks([0, 1], ["real não", "real sim"])
        ax.set_title(f"{e} (F1 {m['por_emocao'][e]['f1']:.2f})")
    fig.suptitle(f"Matriz de confusão por emoção — {nome}")
    salvar(fig, f"matrizes_{nome}.png")


def coocorrencia(nome, m):
    rot = EMOCOES + ["neutro"]
    mat = np.array(m["coocorrencia"], dtype=float)
    norm = mat / np.maximum(mat.sum(1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    for i in range(len(rot)):
        for j in range(len(rot)):
            ax.text(j, i, f"{norm[i, j]:.2f}\n({int(mat[i, j])})", ha="center", va="center", fontsize=7,
                    color="white" if norm[i, j] > 0.5 else "black")
    ax.set_xticks(range(len(rot)), rot, rotation=45)
    ax.set_yticks(range(len(rot)), rot)
    ax.set(xlabel="previsto", ylabel="verdadeiro",
           title=f"Real x previsto (fração da linha) — {nome}")
    salvar(fig, f"coocorrencia_{nome}.png")


def curvas_pr(nome, limiares):
    arq = MODELO / f"predicoes_{nome}.npz"
    if not arq.exists():
        return
    d = np.load(arq)
    fig, eixos = plt.subplots(2, 3, figsize=(10, 6.5))
    for i, (ax, e) in enumerate(zip(eixos.flat, EMOCOES)):
        y, p = d["y_true"][:, i], d["probs"][:, i]
        if y.sum() == 0:
            continue
        prec, rev, lim = precision_recall_curve(y, p)
        ax.plot(rev, prec)
        # ponto do limiar escolhido na validação
        k = min(np.searchsorted(lim, limiares[e]), len(lim) - 1)
        ax.plot(rev[k], prec[k], "ro", label=f"limiar {limiares[e]}")
        ax.axhline(y.mean(), color="gray", ls="--", lw=0.8, label="acaso")
        ax.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="revocação", ylabel="precisão", title=e)
        ax.legend(fontsize=7)
    fig.suptitle(f"Curvas precisão-revocação — {nome}")
    salvar(fig, f"pr_{nome}.png")


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    hist_arq = MODELO / "historico.json"
    if hist_arq.exists():
        hist = json.loads(hist_arq.read_text())
        perda(hist)
        validacao(hist)
    met_arq = RAIZ / "models" / "metricas_emocoes.json"
    if met_arq.exists():
        met = json.loads(met_arq.read_text())
        f1_por_emocao(met)
        for nome, m in met["testes"].items():
            matrizes(nome, m)
            coocorrencia(nome, m)
            curvas_pr(nome, met["limiares"])
