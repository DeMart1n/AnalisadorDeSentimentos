"""Dados, split e métricas do classificador de emoções (multi-rótulo, Ekman).

Separado de avaliacao.py: polaridade é classe única com softmax; aqui são 6 saídas
independentes, F1 por emoção e intervalo de confiança por bootstrap.
"""

from collections import defaultdict

import numpy as np
from sklearn.metrics import f1_score

from .models import EMOCOES, HUMANO, LLM, ORIGINAL_DATASET, USUARIO, Mensagem, RotuloEmocao

# split original de cada dataset público, lido do origem_id gravado na importação
PUBLICAS = {
    "brighter_ptbr": lambda origem: origem.split("_")[1],  # ptbr_train_track_b_00001
    "goemotions_pt": lambda origem: origem.split("_")[0],  # train_eeabc12
}
NOME_SPLIT = {"train": "treino", "dev": "validacao"}  # "test" vira "teste_<fonte>"
PRIORIDADE = {HUMANO: 0, ORIGINAL_DATASET: 1, LLM: 2}


def carregar_emocoes(fontes=None):
    """Um rótulo por mensagem de cliente. Devolve [dict(fonte, origem_id, anterior, texto, y)].

    `anterior` é a mensagem imediatamente anterior na conversa, de qualquer autor (contexto do par).
    """
    qs = RotuloEmocao.objects.filter(mensagem__autor=USUARIO).select_related("mensagem__conversa")
    if fontes:
        qs = qs.filter(mensagem__conversa__fonte__in=fontes)
    escolhido = {}
    for r in qs:
        # ponytail: com dois humanos na mesma mensagem fica o primeiro; adjudicar quando houver anotação real
        atual = escolhido.get(r.mensagem_id)
        if atual is None or PRIORIDADE[r.origem] < PRIORIDADE[atual.origem]:
            escolhido[r.mensagem_id] = r

    # filtra por fonte, não por id: lista de ids estoura o limite de variáveis do SQLite
    fontes_usadas = {r.mensagem.conversa.fonte for r in escolhido.values()}
    ordem = defaultdict(list)
    for cid, o, texto in (Mensagem.objects.filter(conversa__fonte__in=fontes_usadas)
                          .order_by("conversa_id", "ordem").values_list("conversa_id", "ordem", "texto")
                          .iterator(chunk_size=5000)):
        ordem[cid].append((o, texto))

    dados = []
    for r in escolhido.values():
        m = r.mensagem
        anteriores = [t for o, t in ordem[m.conversa_id] if o < m.ordem]
        dados.append({
            "fonte": m.conversa.fonte, "origem_id": m.conversa.origem_id,
            "anterior": anteriores[-1] if anteriores else "", "texto": m.texto,
            "y": [int(getattr(r, e)) for e in EMOCOES],
        })
    return dados


def split_emocoes(dados):
    """{"treino": [...], "validacao": [...], "teste_<fonte>": [...]} pelo split original de cada fonte.

    Chat real e sintético ainda não têm split congelado (Fases 3 e 5): falha alto em vez de
    deixá-los cair no treino e, depois, no teste.
    """
    partes = defaultdict(list)
    for d in dados:
        if d["fonte"] not in PUBLICAS:
            raise ValueError(f"fonte {d['fonte']!r} sem split congelado — gerar models/splits/emocoes.json antes")
        s = PUBLICAS[d["fonte"]](d["origem_id"])
        partes[NOME_SPLIT.get(s, f"teste_{d['fonte']}")].append(d)
    return dict(partes)


def metricas(y_true, y_pred, n_boot=1000, seed=42):
    """F1 por emoção (com IC 95% por bootstrap), macro, micro e suporte."""
    y_true, y_pred = np.asarray(y_true, dtype=bool), np.asarray(y_pred, dtype=bool)
    idx = np.random.default_rng(seed).integers(0, len(y_true), (n_boot, len(y_true)))
    t, p = y_true[idx], y_pred[idx]  # n_boot x N x 6
    tp, fp, fn = (t & p).sum(1), (~t & p).sum(1), (t & ~p).sum(1)
    f1_boot = np.where(2 * tp + fp + fn > 0, 2 * tp / np.maximum(2 * tp + fp + fn, 1), 0.0)
    por_emocao = {}
    for i, e in enumerate(EMOCOES):
        lo, hi = np.percentile(f1_boot[:, i], [2.5, 97.5])
        por_emocao[e] = {
            "f1": round(float(f1_score(y_true[:, i], y_pred[:, i], zero_division=0)), 4),
            "ic95": [round(float(lo), 4), round(float(hi), 4)],
            "suporte": int(y_true[:, i].sum()),
        }
    return {
        "n": len(y_true),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1_micro": round(float(f1_score(y_true, y_pred, average="micro", zero_division=0)), 4),
        "neutro_suporte": int((~y_true.any(1)).sum()),
        "por_emocao": por_emocao,
    }
