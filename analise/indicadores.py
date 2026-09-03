"""Indicadores da conversa inteira — a sessão, não a mensagem isolada.

Uma conversa pode abrir neutra, passar por momentos negativos e terminar
positiva depois que o problema é resolvido; é isso que estes números capturam.
"""

from .models import NEGATIVO, NEUTRO, POSITIVO

VALOR = {POSITIVO: 1, NEUTRO: 0, NEGATIVO: -1}


def indicadores(rotulos):
    """rotulos: sequência de rótulos das mensagens do usuário, em ordem."""
    rotulos = [r for r in rotulos if r]
    if not rotulos:
        return None
    valores = [VALOR[r] for r in rotulos]
    # trocas de polaridade ignoram o neutro: neg -> neutro -> neg não é uma virada
    polarizados = [v for v in valores if v != 0]
    trocas = sum(a * b < 0 for a, b in zip(polarizados, polarizados[1:]))
    return {
        "abertura": rotulos[0],
        "encerramento": rotulos[-1],
        "delta": valores[-1] - valores[0],
        "trocas_de_polaridade": trocas,
        "pior_momento": min(range(len(valores)), key=lambda i: valores[i]) + 1,
        "n_mensagens": len(rotulos),
    }
