import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from analise.models import NEGATIVO, NEUTRO, POSITIVO, Mensagem


@dataclass(frozen=True)
class MensagemOtimizada:
    mensagem: Mensagem
    texto_original: str
    texto_otimizado: str
    classificacao_direta: Optional[Tuple[str, float]] = None  # (rotulo, score) se resolvido por atalho heurístico

    @property
    def requer_inferencia(self) -> bool:
        return self.classificacao_direta is None


@dataclass
class MapeamentoIAResult:
    itens: List[MensagemOtimizada] = field(default_factory=list)
    total_original_caracteres: int = 0
    total_otimizado_caracteres: int = 0
    atalhos_heuristicos: int = 0
    enviadas_para_ia: int = 0

    @property
    def caracteres_economizados(self) -> int:
        return max(0, self.total_original_caracteres - self.total_otimizado_caracteres)

    @property
    def taxa_reducao_percentual(self) -> float:
        if self.total_original_caracteres == 0:
            return 0.0
        return round((self.caracteres_economizados / self.total_original_caracteres) * 100, 2)


class ConversaIAMapper:
    """Mapper responsável por preparar, sanitizar e otimizar os textos das conversas antes do envio à IA.
    
    Objetivos:
    1. Economia de tokens e processamento: normaliza repetições desnecessárias, pontuações redundantes
       e atalha mensagens triviais (ex: vazias, 'ok', 'olá').
    2. Segurança e privacidade: remove caracteres de controle invisíveis, tags HTML e potenciais injeções de prompt.
    3. Redução de ruído cognitivo: comprime alongamentos artificiais de palavras que geram fragmentação em subwords.
    """

    # Caracteres de controle invisíveis ou maliciosos (zero-width, bidi override, etc.)
    _RE_CONTROLE_E_INVISIVEIS = re.compile(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u202a-\u202e\ufeff]"
    )

    # Tags HTML ou scripts
    _RE_HTML = re.compile(r"<[^>]+>")

    # URLs completas (com parâmetros longos de tracking que gastam dezenas de tokens sem carregar sentimento)
    _RE_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

    # Sequências de pontuação repetidas (ex: '???????' -> '?', '!!!!!!!' -> '!')
    _RE_PONTUACAO_REPETIDA = re.compile(r"([!?.,;:])\1{2,}")

    # Alongamento exagerado de caracteres (ex: 'nããããããããão' -> 'nãão', 'muitooooo' -> 'muitoo')
    # Limita a repetição a no máximo 2 ocorrências consecutivas para preservar ênfase sem explodir tokens.
    _RE_CARACTERES_REPETIDOS = re.compile(r"(.)\1{2,}", re.IGNORECASE)

    # Múltiplos espaços em branco e quebras de linha
    _RE_ESPACOS = re.compile(r"\s+")

    # Padrões comuns de prompt injection / quebra de contexto em LLMs
    _RE_PROMPT_INJECTION = re.compile(
        r"(?i)(?:\b(?:ignore(?:\s+all)?\s+(?:previous|above)\s+instructions|"
        r"desconsidere\s+(?:todas\s+as\s+)?instruções\s+anteriores)\b|"
        r"\b(?:system\s*prompt|human|assistant|system):|<\|im_start\|>|<\|im_end\|>)"
    )

    # Atalhos rápidos de mensagens triviais que dispensam passar pelo modelo
    _ATALHOS_TRIVIAIS_NEUTROS = {
        "ok", "blz", "beleza", "certo", "entendi", "sim", "não", "nao", "ola", "olá",
        "oi", "bom dia", "boa tarde", "boa noite", "ola bom dia", "ola boa tarde",
        "aguardando", "estou aguardando", "continua", "seguinte", "alo", "alô"
    }

    _ATALHOS_TRIVIAIS_POSITIVOS = {
        "obrigado", "obrigada", "muito obrigado", "muito obrigada", "valeu", "show", "perfeito", "excelente"
    }

    def __init__(self, limite_caracteres: int = 512, permitir_atalhos_heuristicos: bool = False):
        self.limite_caracteres = limite_caracteres
        self.permitir_atalhos_heuristicos = permitir_atalhos_heuristicos

    def sanitizar_texto(self, texto: Optional[str]) -> str:
        """Limpa caracteres de controle, tags HTML, URLs e mitiga prompt injections."""
        if not texto:
            return ""

        # 1. Remove caracteres de controle invisíveis e perigosos
        limpo = self._RE_CONTROLE_E_INVISIVEIS.sub("", texto)

        # 2. Neutraliza tentativas de injeção de prompt
        limpo = self._RE_PROMPT_INJECTION.sub(" [REMOVIDO] ", limpo)

        # 3. Remove tags HTML
        limpo = self._RE_HTML.sub(" ", limpo)

        # 4. Neutraliza URLs
        limpo = self._RE_URL.sub(" [URL] ", limpo)

        return limpo

    def reduzir_ruido(self, texto: str) -> str:
        """Diminui o ruído cognitivo e redundâncias que inflam custos de tokenização."""
        if not texto:
            return ""

        # 1. Comprime pontuação exagerada mantendo reticências no máximo de 3 pontos
        texto = self._RE_PONTUACAO_REPETIDA.sub(r"\1", texto)

        # 2. Comprime alongamento artificial de letras (ex: 'socorrooooo' -> 'socorroo')
        texto = self._RE_CARACTERES_REPETIDOS.sub(r"\1\1", texto)

        # 3. Normaliza espaços múltiplos e quebras de linha para espaço simples
        texto = self._RE_ESPACOS.sub(" ", texto).strip()

        # 4. Truncamento defensivo para evitar payload abusivo
        if len(texto) > self.limite_caracteres:
            texto = texto[:self.limite_caracteres].rstrip()

        return texto

    def mapear_texto(self, texto: Optional[str]) -> str:
        """Pipeline completo de transformação do texto para o modelo."""
        sanitizado = self.sanitizar_texto(texto)
        return self.reduzir_ruido(sanitizado)

    def obter_atalho_heuristico(self, texto_otimizado: str) -> Optional[Tuple[str, float]]:
        """Verifica se a mensagem pode ser resolvida instantaneamente sem custo de inferência."""
        if not self.permitir_atalhos_heuristicos:
            return None

        normalizado = texto_otimizado.lower().strip()
        # Se ficou vazia ou só com pontuação residual sem letras/números
        if not normalizado or not any(c.isalnum() for c in normalizado):
            return (NEUTRO, 1.0)

        if normalizado in self._ATALHOS_TRIVIAIS_NEUTROS:
            return (NEUTRO, 0.95)

        if normalizado in self._ATALHOS_TRIVIAIS_POSITIVOS:
            return (POSITIVO, 0.95)

        return None

    def mapear_mensagens(self, mensagens: Sequence[Mensagem]) -> MapeamentoIAResult:
        """Mapeia uma lista de mensagens Django, aplicando redução de ruído e separando atalhos."""
        resultado = MapeamentoIAResult()

        for m in mensagens:
            original = m.texto or ""
            otimizado = self.mapear_texto(original)

            atalho = self.obter_atalho_heuristico(otimizado)

            item = MensagemOtimizada(
                mensagem=m,
                texto_original=original,
                texto_otimizado=otimizado,
                classificacao_direta=atalho,
            )

            resultado.itens.append(item)
            resultado.total_original_caracteres += len(original)
            resultado.total_otimizado_caracteres += len(otimizado)

            if atalho:
                resultado.atalhos_heuristicos += 1
            else:
                resultado.enviadas_para_ia += 1

        return resultado
