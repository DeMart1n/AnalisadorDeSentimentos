import re
from typing import Any, Dict, Iterable, Optional, Set

RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

RE_CNPJ_FORMATADO = re.compile(
    r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"
)
RE_CNPJ_NUMERICO = re.compile(
    r"\b\d{14}\b"
)

RE_CPF_FORMATADO = re.compile(
    r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"
)
RE_CPF_NUMERICO = re.compile(
    r"\b\d{11}\b"
)

# Cartão de crédito (13 a 16 dígitos com separadores de espaço ou traço, ou contínuo)
RE_CARTAO = re.compile(
    r"\b(?:\d{4}[ -]?){3}\d{1,4}\b"
)

# Telefones:
# Formato com DDD: (XX) 9XXXX-XXXX, (XX) XXXX-XXXX, XX 9XXXXXXXX, XX 9XXXX-XXXX
# Prefixo +55 opcional
# Telefones locais de 8 ou 9 dígitos com hífen: 9XXXX-XXXX ou XXXX-XXXX
RE_TELEFONE_COMPLETO = re.compile(
    r"(?:\+55\s*|0055\s*)?(?:\(?([1-9][0-9])\)?\s*)?(?:(9\s*\d{4})|([2-8]\d{3}))[-\s]?(\d{4})\b"
)

STOPWORDS_NOMES = {
    "de", "da", "do", "das", "dos", "e", "em", "para", "com", "por",
    "ola", "olá", "oi", "bom", "boa", "dia", "tarde", "noite",
    "sr", "sra", "senhor", "senhora", "atendente", "suporte",
    "cliente", "usuario", "usuário", "sistema", "bot", "ura",
    "central", "ajuda", "sac", "protocolo", "empresa", "loja",
    "aqui", "novo", "nova", "humano", "pessoa", "farmacia", "farmácia",
    "comercial", "varejo", "fiscal", "financeiro", "gerente", "vendedor",
    "operador", "sair", "cancelar", "finalizar", "atendimento", "sim", "nao", "não",
}

RE_SOLICITACAO_NOME = re.compile(
    r"(?i)\b(?:informe|digite|qual|diga)\s+(?:o\s+)?seu\s+nome\b|\bseu\s+nome\s+(?:por\s+favor)?\b"
)
RE_ECO_BOT = re.compile(
    r"(?i)(?:obrigado|olá|ola|bem-vindo|bem vindo)\s+\*([A-Za-zÀ-ÿ]{3,}(?:\s+[A-Za-zÀ-ÿ]{3,})?)\*"
)
RE_APRESENTACAO = re.compile(
    r"(?i)\b(?:me\s+chamo|meu\s+nome\s+[eé]|sou(?:\s+[oa])?)\s+([A-Za-zÀ-ÿ]{3,}(?:\s+[A-Za-zÀ-ÿ]{3,})?)\b"
)
RE_CARD_CONTATO = re.compile(
    r"(?i)\*(?:Name|Nome):\*\s*([A-Za-zÀ-ÿ]{3,}(?:\s+[A-Za-zÀ-ÿ]{3,})?)"
)

DDDS_VALIDOS = {
    "11", "12", "13", "14", "15", "16", "17", "18", "19",
    "21", "22", "24", "27", "28",
    "31", "32", "33", "34", "35", "37", "38",
    "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "51", "53", "54", "55",
    "61", "62", "63", "64", "65", "66", "67", "68", "69",
    "71", "73", "74", "75", "77", "79",
    "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "91", "92", "93", "94", "95", "96", "97", "98", "99",
}


def validar_luhn(numero: str) -> bool:
    """Valida se o número possui dígito verificador de cartão de crédito válido via Luhn."""
    digitos = [int(d) for d in numero if d.isdigit()]
    if not (13 <= len(digitos) <= 19):
        return False
    soma = 0
    inverso = digitos[::-1]
    for i, d in enumerate(inverso):
        if i % 2 == 1:
            d = d * 2
            if d > 9:
                d -= 9
        soma += d
    return soma % 10 == 0


def validar_cpf_checksum(cpf: str) -> bool:
    """Valida se uma sequência numérica de 11 dígitos possui checksum de CPF válido (Módulo 11)."""
    numeros = [int(d) for d in cpf if d.isdigit()]
    if len(numeros) != 11:
        return False
    if len(set(numeros)) == 1:
        return False
    soma = sum(numeros[i] * (10 - i) for i in range(9))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    if numeros[9] != d1:
        return False
    soma = sum(numeros[i] * (11 - i) for i in range(10))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    return numeros[10] == d2


def validar_cnpj_checksum(cnpj: str) -> bool:
    numeros = [int(d) for d in cnpj if d.isdigit()]
    if len(numeros) != 14 or len(set(numeros)) == 1:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(n * p for n, p in zip(numeros[:12], pesos1))
    resto1 = soma1 % 11
    d1 = 0 if resto1 < 2 else 11 - resto1
    if numeros[12] != d1:
        return False
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(n * p for n, p in zip(numeros[:13], pesos2))
    resto2 = soma2 % 11
    d2 = 0 if resto2 < 2 else 11 - resto2
    return numeros[13] == d2


def anonimizar_email(texto: str) -> str:
    return RE_EMAIL.sub("[EMAIL]", texto)


def anonimizar_cartao(texto: str) -> str:
    def _substituir(m: re.Match) -> str:
        candidato = m.group(0)
        if validar_luhn(candidato):
            return "[CARTAO]"
        return candidato

    return RE_CARTAO.sub(_substituir, texto)


def anonimizar_cnpj(texto: str) -> str:
    texto = RE_CNPJ_FORMATADO.sub("[CNPJ]", texto)

    def _substituir_num(m: re.Match) -> str:
        candidato = m.group(0)
        if validar_cnpj_checksum(candidato):
            return "[CNPJ]"
        return candidato

    return RE_CNPJ_NUMERICO.sub(_substituir_num, texto)


def anonimizar_cpf(texto: str) -> str:
    texto = RE_CPF_FORMATADO.sub("[CPF]", texto)

    def _substituir_num(m: re.Match) -> str:
        candidato = m.group(0)
        if validar_cpf_checksum(candidato):
            return "[CPF]"
        return candidato

    return RE_CPF_NUMERICO.sub(_substituir_num, texto)


def anonimizar_telefone(texto: str, telefones_conhecidos: Optional[Iterable[str]] = None) -> str:
    if telefones_conhecidos:
        for tel in telefones_conhecidos:
            tel_limpo = str(tel).strip()
            if len(tel_limpo) >= 8:
                texto = re.sub(rf"\b{re.escape(tel_limpo)}\b", "[TELEFONE]", texto)

    def _substituir_tel(m: re.Match) -> str:
        ddd = m.group(1)
        if ddd and ddd not in DDDS_VALIDOS:
            return m.group(0)
        return "[TELEFONE]"

    return RE_TELEFONE_COMPLETO.sub(_substituir_tel, texto)


def extrair_nomes_limpos(candidatos: Iterable[str]) -> Set[str]:
    nomes_limpos = set()
    for item in candidatos:
        if not item or not isinstance(item, str):
            continue
        limpo = re.sub(r"(?i)\b(cod|código|id|suporte|atendente|agente)\s*:?\s*\d+\b", "", item)
        limpo = re.sub(r"(?i)\s*\((suporte|atendente|agente|cliente|operador)\)\s*", "", limpo)
        limpo = re.sub(r"(?i)\b(atendimento|suporte|agente|atendente|ura|bot)\s*-\s*", "", limpo)
        limpo = limpo.strip()
        if not limpo:
            continue

        if len(limpo) >= 3 and limpo.lower() not in STOPWORDS_NOMES:
            nomes_limpos.add(limpo)

        for parte in limpo.split():
            parte = parte.strip()
            if len(parte) >= 3 and parte.lower() not in STOPWORDS_NOMES:
                nomes_limpos.add(parte)

    return nomes_limpos


def extrair_nomes_do_dialogo(mensagens: Iterable[Dict[str, Any]]) -> Set[str]:
    """Extrai nomes próprios mencionados ou informados durante o diálogo do chat."""
    lista_msgs = list(mensagens)
    nomes_extraidos: Set[str] = set()

    for i, msg in enumerate(lista_msgs):
        texto = str(msg.get("texto") or "").strip()
        autor = str(msg.get("autor_canonico") or msg.get("autor") or "").lower()

        if autor == "usuario" and i > 0:
            msg_anterior = lista_msgs[i - 1]
            autor_ant = str(msg_anterior.get("autor_canonico") or msg_anterior.get("autor") or "").lower()
            texto_ant = str(msg_anterior.get("texto") or "")
            if autor_ant == "sistema" and RE_SOLICITACAO_NOME.search(texto_ant):
                candidato = re.sub(r"^[^\w]+|[^\w]+$", "", texto)
                palavras = candidato.split()
                if 1 <= len(palavras) <= 4:
                    if not any(char.isdigit() for char in candidato) and candidato.lower() not in STOPWORDS_NOMES:
                        nomes_extraidos.add(candidato)

        for match in RE_ECO_BOT.finditer(texto):
            nome_eco = match.group(1).strip()
            if nome_eco.lower() not in STOPWORDS_NOMES:
                nomes_extraidos.add(nome_eco)

        for match in RE_APRESENTACAO.finditer(texto):
            nome_apres = match.group(1).strip()
            primeira_palavra = nome_apres.split()[0].lower()
            if primeira_palavra not in STOPWORDS_NOMES and len(nome_apres) >= 3:
                nomes_extraidos.add(nome_apres)

        for match in RE_CARD_CONTATO.finditer(texto):
            nome_card = match.group(1).strip()
            if nome_card.lower() not in STOPWORDS_NOMES:
                nomes_extraidos.add(nome_card)

    return nomes_extraidos


def anonimizar_nomes(texto: str, nomes_conhecidos: Optional[Iterable[str]] = None) -> str:
    if not nomes_conhecidos:
        return texto

    nomes_higienizados = extrair_nomes_limpos(nomes_conhecidos)
    nomes_ordenados = sorted(nomes_higienizados, key=len, reverse=True)

    for nome in nomes_ordenados:
        padrao = rf"\b{re.escape(nome)}\b"
        texto = re.sub(padrao, "[NOME]", texto, flags=re.IGNORECASE)

    return texto


def _compactar_marcadores(texto: str) -> str:
    for tag in ["[NOME]", "[TELEFONE]", "[CPF]", "[CNPJ]", "[EMAIL]", "[CARTAO]"]:
        escaped = re.escape(tag)
        texto = re.sub(rf"(?:{escaped}\s*){{2,}}", f"{tag} ", texto)
        texto = re.sub(rf"{escaped}\s+{escaped}", tag, texto)
    return texto.strip()


def anonimizar_texto(
    texto: str,
    nomes_conhecidos: Optional[Iterable[str]] = None,
    telefones_conhecidos: Optional[Iterable[str]] = None,
) -> str:
    if not texto or not isinstance(texto, str):
        return texto

    resultado = anonimizar_email(texto)

    resultado = anonimizar_cartao(resultado)

    resultado = anonimizar_cnpj(resultado)

    resultado = anonimizar_cpf(resultado)

    resultado = anonimizar_telefone(resultado, telefones_conhecidos)

    resultado = anonimizar_nomes(resultado, nomes_conhecidos)

    return _compactar_marcadores(resultado)