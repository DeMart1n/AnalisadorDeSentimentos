"""Avaliação compartilhada por todos os degraus da escada.

Regras da spec, valem igualmente para léxico, TF-IDF e BERTimbau:
  - split POR CONVERSA (mensagens da mesma sessão vazam informação entre treino e teste)
  - métrica principal F1 macro (a base é desbalanceada em neutro; acurácia engana)
  - comparação entre modelos por McNemar, não por diferença de número
"""

import json
import random
from pathlib import Path

from scipy.stats import binomtest
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from .models import ROTULOS, USUARIO, Conversa, Mensagem

CLASSES = [r for r, _ in ROTULOS]
SPLIT_POLARIDADE = Path(__file__).resolve().parents[1] / "models" / "splits" / "polaridade.json"


def carregar_dados(fontes=None):
    """Mensagens do usuário que têm rótulo real. Devolve [(conversa_id, texto, rotulo)]."""
    qs = Mensagem.objects.filter(autor=USUARIO, rotulo_real__isnull=False)
    if fontes:
        qs = qs.filter(conversa__fonte__in=fontes)
    return list(qs.values_list("conversa_id", "texto", "rotulo_real"))


def dividir_por_conversa(dados, proporcao_teste=0.2, seed=42):
    conversas = sorted({d[0] for d in dados})
    random.Random(seed).shuffle(conversas)
    corte = int(len(conversas) * (1 - proporcao_teste))
    treino_ids = set(conversas[:corte])
    treino = [d for d in dados if d[0] in treino_ids]
    teste = [d for d in dados if d[0] not in treino_ids]
    return treino, teste


def split_congelado(dados, destino=SPLIT_POLARIDADE):
    """Treino/teste lidos de um arquivo versionado, gerado uma única vez sobre TODA a base.

    Chave "fonte:origem_id", não o id do banco: sobrevive a reimportação.
    Conversa que não está no arquivo (rotulada depois) vai para o treino, nunca para o teste.
    Para regerar, apague o arquivo — e aceite que as métricas antigas deixam de ser comparáveis.
    """
    chave = {i: f"{f}:{o}" for i, f, o in Conversa.objects.values_list("id", "fonte", "origem_id")}
    if not destino.exists():
        treino, teste = dividir_por_conversa(carregar_dados())
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps({
            "treino": sorted({chave[d[0]] for d in treino}),
            "teste": sorted({chave[d[0]] for d in teste}),
        }, indent=0))
    teste_ids = set(json.loads(destino.read_text())["teste"])
    treino = [d for d in dados if chave[d[0]] not in teste_ids]
    teste = [d for d in dados if chave[d[0]] in teste_ids]
    return treino, teste


def avaliar(modelo, treino, teste):
    modelo.treinar([t for _, t, _ in treino], [r for _, _, r in treino])
    y_true = [r for _, _, r in teste]
    y_pred, _ = modelo.prever([t for _, t, _ in teste])
    return {
        "modelo": modelo.nome,
        "n_treino": len(treino),
        "n_teste": len(teste),
        "f1_macro": f1_score(y_true, y_pred, average="macro", labels=CLASSES, zero_division=0),
        "matriz": confusion_matrix(y_true, y_pred, labels=CLASSES).tolist(),
        "relatorio": classification_report(y_true, y_pred, labels=CLASSES, zero_division=0),
        "y_true": y_true,
        "y_pred": y_pred,
    }


def mcnemar(resultado_a, resultado_b):
    """McNemar exato entre dois modelos avaliados no MESMO conjunto de teste.

    Conta só onde discordam: b = A acertou e B errou, c = o inverso.
    p < 0.05 permite afirmar que um supera o outro; acima disso, a diferença
    de F1 observada não sustenta a afirmação.
    """
    y_true = resultado_a["y_true"]
    if y_true != resultado_b["y_true"]:
        raise ValueError("McNemar exige o mesmo conjunto de teste nos dois modelos")
    b = sum(a == v and c != v for v, a, c in zip(y_true, resultado_a["y_pred"], resultado_b["y_pred"]))
    c = sum(a != v and c == v for v, a, c in zip(y_true, resultado_a["y_pred"], resultado_b["y_pred"]))
    # float() e bool() nativos: binomtest devolve numpy, que não serializa em JSON
    p = 1.0 if b + c == 0 else float(binomtest(b, b + c, 0.5).pvalue)
    return {"acertos_so_de_a": b, "acertos_so_de_b": c, "p": p, "significativo": bool(p < 0.05)}
