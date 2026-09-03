"""Degrau 1: baseline léxico. Sem treino, serve de piso de comparação."""

import re
from pathlib import Path

from analise.models import NEGATIVO, NEUTRO, POSITIVO

ARQUIVO = Path(__file__).parent / "lexico_pt.txt"
NEGACOES = {"não", "nao", "nunca", "jamais", "nem", "nenhum", "nenhuma"}
JANELA_NEGACAO = 3  # palavras após a negação que têm a polaridade invertida


def _tokenizar(texto):
    return re.findall(r"[a-zà-ÿ]+", texto.lower())


class Lexico:
    nome = "lexico"

    def __init__(self, arquivo=ARQUIVO):
        self.pesos = {}
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            palavra, peso = linha.split()
            self.pesos[palavra] = float(peso)

    def treinar(self, textos, rotulos):
        """Não treina — é o piso. Presente só para manter a interface."""

    def prever(self, textos):
        rotulos, scores = [], []
        for texto in textos:
            soma = 0.0
            negacao_ate = -1
            for i, token in enumerate(_tokenizar(texto)):
                if token in NEGACOES:
                    negacao_ate = i + JANELA_NEGACAO
                    continue
                peso = self.pesos.get(token)
                if peso is not None:
                    soma += -peso if i <= negacao_ate else peso
            rotulos.append(POSITIVO if soma > 0 else NEGATIVO if soma < 0 else NEUTRO)
            scores.append(abs(soma))
        return rotulos, scores
