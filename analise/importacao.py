"""Leitura de conversas em CSV/JSON para o esquema do projeto.

- Esquema corporativo flexível com aliases:
    conversa, seq, origem, autor, mensagem, contato, telefone, data_hora, etc.
- Delimitadores comuns (, e ;).
- UTF-8 com ou sem BOM (\\ufeff).
- Normalização inteligente de papéis (usuario, atendente, sistema).
- Fallback automático de ordenação por timestamp ou ordem física do arquivo.
"""

import csv
import io
import json
from typing import Any, Dict, List, Optional, Set, Tuple
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import get_current_timezone, is_naive, make_aware
from .anonimizador import anonimizar_texto, extrair_nomes_do_dialogo
from .dtos.importacao_dto import ConversaImportadaDTO, MensagemImportadaDTO
from .models import AUTORES, ROTULOS, Conversa, Mensagem

AUTORES_VALIDOS = {a for a, _ in AUTORES}
ROTULOS_VALIDOS = {r for r, _ in ROTULOS}

# ALIASES
PAPEIS_USUARIO = {"usuario", "cliente", "user", "customer", "consumidor", "client"}
PAPEIS_ATENDENTE = {"atendente", "agente", "operador", "atendimento", "support", "analista", "agent"}
PAPEIS_SISTEMA = {"sistema", "bot", "ura", "system", "ia", "virtual", "notificacao"}

MAPA_ALIASES = {
    "conversa_id": ["conversa_id", "conversa", "chat_id", "ticket_id", "protocolo", "id_conversa", "session_id"],
    "ordem": ["ordem", "seq", "sequencia", "index", "order", "mensagem_id"],
    "texto": ["texto", "mensagem", "text", "msg", "conteudo", "message", "body"],
    "autor": ["autor", "remetente", "sender", "from"],
    "origem": ["origem", "tipo", "role"],
    "timestamp": ["timestamp", "mensagem_em", "enviada_em", "data_hora", "created_at", "date"],
    "rotulo": ["rotulo", "sentiment", "sentimento", "label"],
    "contato": ["contato", "nome_contato", "cliente_nome", "nome", "customer_name", "user_name"],
    "telefone": ["telefone", "telefone_contato", "celular", "phone", "contact_phone"],
}


class ErroDeImportacao(Exception):
    def __init__(self, erros: List[str]):
        self.erros = erros
        super().__init__(f"{len(erros)} erro(s) no arquivo")


def _detectar_delimitador(conteudo: str) -> str:
    """Detecta se o CSV é delimitado por vírgula ou ponto e vírgula."""
    linhas = [l for l in conteudo.splitlines() if l.strip()]
    if not linhas:
        return ","
    primeira_linha = linhas[0]
    virgulas = primeira_linha.count(",")
    pontos_e_virgulas = primeira_linha.count(";")
    if pontos_e_virgulas > virgulas:
        return ";"
    try:
        amostra = "\n".join(linhas[:5])
        return csv.Sniffer().sniff(amostra, delimiters=",;").delimiter
    except Exception:
        return ","


def _ler(conteudo: str, formato: str) -> List[Dict[str, Any]]:
    """Lê CSV ou JSON normalizando BOM e decodificação."""
    conteudo_limpo = conteudo.lstrip("\ufeff")
    if formato == "json":
        dados = json.loads(conteudo_limpo)
        if not isinstance(dados, list):
            raise ErroDeImportacao(["JSON deve ser uma lista de objetos"])
        return dados

    delimitador = _detectar_delimitador(conteudo_limpo)
    return list(csv.DictReader(io.StringIO(conteudo_limpo), delimiter=delimitador))


def _resolver_papel(autor: Optional[str], origem: Optional[str]) -> Optional[str]:
    """Mapeia os valores de autor/origem para as roles canônicas do modelo."""
    autor_limpo = autor.strip().lower() if autor else ""
    origem_limpo = origem.strip().lower() if origem else ""

    # Se autor ou origem contiverem indicadores claros de bot ou sistema
    if autor_limpo in PAPEIS_SISTEMA or "bot" in autor_limpo or "ura" in autor_limpo:
        return "sistema"
    if origem_limpo in PAPEIS_SISTEMA or "bot" in origem_limpo or "ura" in origem_limpo:
        return "sistema"

    # Verificar correspondência direta de papéis conhecidos
    if origem_limpo in PAPEIS_USUARIO:
        return "usuario"
    if origem_limpo in PAPEIS_ATENDENTE:
        return "atendente"

    if autor_limpo in PAPEIS_USUARIO:
        return "usuario"
    if autor_limpo in PAPEIS_ATENDENTE:
        return "atendente"

    if autor_limpo in AUTORES_VALIDOS:
        return autor_limpo
    if origem_limpo in AUTORES_VALIDOS:
        return origem_limpo

    # Se autor é o nome de um atendente/cliente e a origem dá a pista do papel
    if origem_limpo:
        for p in PAPEIS_USUARIO:
            if p in origem_limpo:
                return "usuario"
        for p in PAPEIS_ATENDENTE:
            if p in origem_limpo:
                return "atendente"

    return None


def _normalizar_linha(linha_bruta: Dict[str, Any]) -> Dict[str, Any]:
    """Mapeia colunas brutas para o esquema canônico usando aliases."""
    mapa_chaves = {}
    for k, v in linha_bruta.items():
        if k is not None:
            chave_limpa = str(k).strip().lower().replace(" ", "_").lstrip("\ufeff")
            mapa_chaves[chave_limpa] = v

    linha_norm = {}
    for campo_canonico, aliases in MAPA_ALIASES.items():
        for alias in aliases:
            if alias in mapa_chaves:
                linha_norm[campo_canonico] = mapa_chaves[alias]
                break

    # Fallback se autor não foi encontrado mas origem sim (ou vice-versa)
    if "autor" not in linha_norm and "origem" in linha_norm:
        linha_norm["autor"] = linha_norm["origem"]

    return linha_norm


def _data(valor: Any) -> Optional[Any]:
    """Converte string ISO/data para datetime ciente de timezone."""
    if not valor:
        return None
    dt = parse_datetime(str(valor))
    if dt and is_naive(dt):
        return make_aware(dt, get_current_timezone())
    return dt


def _validar_e_estruturar(
    linhas_brutas: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Valida as linhas, normaliza papéis e agrupa mensagens por conversa."""
    erros = []
    por_conversa: Dict[str, List[Dict[str, Any]]] = {}

    for i, linha_bruta in enumerate(linhas_brutas, start=1):
        linha = _normalizar_linha(linha_bruta)

        faltando = []
        if not linha.get("conversa_id"):
            faltando.append("conversa_id")
        if not linha.get("texto"):
            faltando.append("texto")
        if not linha.get("autor") and not linha.get("origem"):
            faltando.append("autor")

        if faltando:
            erros.append(f"linha {i}: campos faltando: {', '.join(sorted(faltando))}")
            continue

        autor_resolvido = _resolver_papel(linha.get("autor"), linha.get("origem"))
        if not autor_resolvido:
            autor_invalido = linha.get("autor") or linha.get("origem")
            erros.append(f"linha {i}: autor inválido '{autor_invalido}'")
            continue
        linha["autor_canonico"] = autor_resolvido

        rotulo = linha.get("rotulo") or None
        if rotulo and rotulo not in ROTULOS_VALIDOS:
            erros.append(f"linha {i}: rotulo inválido '{rotulo}'")

        raw_ordem = linha.get("ordem")
        if raw_ordem not in (None, ""):
            try:
                linha["ordem_int"] = int(raw_ordem)
            except (TypeError, ValueError):
                erros.append(f"linha {i}: ordem não é inteiro: '{raw_ordem}'")
                continue
        else:
            linha["ordem_int"] = None

        linha["linha_numero"] = i
        linha["dt_enviada"] = _data(linha.get("timestamp"))

        cid = str(linha["conversa_id"])
        por_conversa.setdefault(cid, []).append(linha)

    # Validar ordens repetidas ou inconsistências por conversa
    for cid, msgs in por_conversa.items():
        ordens_vistas: Set[int] = set()
        tem_ordem = any(m["ordem_int"] is not None for m in msgs)
        falta_ordem = any(m["ordem_int"] is None for m in msgs)

        if tem_ordem and falta_ordem:
            for m in msgs:
                if m["ordem_int"] is None:
                    erros.append(f"linha {m['linha_numero']}: ordem ausente na conversa {cid}")

        if tem_ordem and not falta_ordem:
            for m in msgs:
                ordem = m["ordem_int"]
                if ordem in ordens_vistas:
                    erros.append(f"linha {m['linha_numero']}: ordem {ordem} repetida na conversa {cid}")
                ordens_vistas.add(ordem)

    if erros:
        raise ErroDeImportacao(erros)

    return por_conversa


def _construir_dtos_conversa(
    por_conversa: Dict[str, List[Dict[str, Any]]],
    fonte: str
) -> Dict[str, ConversaImportadaDTO]:
    """Ordena mensagens e cria instâncias imutáveis de DTO por conversa."""
    conversas_dto = {}

    for cid, msgs in por_conversa.items():
        # Fallback de ordenação: se não tiver ordem explícita, ordenar por timestamp ou ordem física
        tem_ordem = msgs[0]["ordem_int"] is not None
        if tem_ordem:
            msgs_ordenadas = sorted(msgs, key=lambda m: m["ordem_int"])
        else:
            tem_timestamp = all(m["dt_enviada"] is not None for m in msgs)
            if tem_timestamp:
                msgs_ordenadas = sorted(msgs, key=lambda m: m["dt_enviada"])
            else:
                msgs_ordenadas = sorted(msgs, key=lambda m: m["linha_numero"])

        nomes_contexto: Set[str] = set()
        telefones_contexto: Set[str] = set()
        for m in msgs:
            contato = m.get("contato")
            if contato and str(contato).strip():
                nomes_contexto.add(str(contato).strip())

            autor_raw = m.get("autor")
            if autor_raw and str(autor_raw).strip():
                autor_str = str(autor_raw).strip()
                if autor_str.lower() not in AUTORES_VALIDOS and autor_str.lower() not in PAPEIS_SISTEMA:
                    nomes_contexto.add(autor_str)

            telefone = m.get("telefone")
            if telefone and str(telefone).strip():
                telefones_contexto.add(str(telefone).strip())

        nomes_dialogo = extrair_nomes_do_dialogo(msgs_ordenadas)
        nomes_contexto.update(nomes_dialogo)

        mensagens_dto: List[MensagemImportadaDTO] = []
        for seq, m in enumerate(msgs_ordenadas, start=1):
            ordem_final = m["ordem_int"] if tem_ordem else seq
            texto_anonimizado = anonimizar_texto(
                m["texto"],
                nomes_conhecidos=nomes_contexto,
                telefones_conhecidos=telefones_contexto,
            )

            mensagens_dto.append(
                MensagemImportadaDTO(
                    ordem=ordem_final,
                    autor=m["autor_canonico"],
                    texto=texto_anonimizado,
                    enviada_em=m["dt_enviada"],
                    rotulo_real=m.get("rotulo") or None,
                )
            )

        conversas_dto[cid] = ConversaImportadaDTO(
            origem_id=cid,
            fonte=fonte,
            mensagens=mensagens_dto,
            nomes_contexto=nomes_contexto,
            telefones_contexto=telefones_contexto,
        )

    return conversas_dto


@transaction.atomic
def importar(conteudo: str, fonte: str, formato: str = "csv") -> Tuple[int, int]:
    """Importa conversas atomicamente para o banco de dados.

    Reimportar a mesma conversa da mesma fonte substitui as mensagens dela.
    Devolve (total_conversas, total_mensagens) gravadas.
    """
    linhas_brutas = _ler(conteudo, formato)
    por_conversa = _validar_e_estruturar(linhas_brutas)
    conversas_dto = _construir_dtos_conversa(por_conversa, fonte)

    total_msgs = 0
    for origem_id, conv_dto in conversas_dto.items():
        conversa, _ = Conversa.objects.get_or_create(origem_id=origem_id, fonte=fonte)
        conversa.mensagens.all().delete()
        Mensagem.objects.bulk_create(
            Mensagem(
                conversa=conversa,
                ordem=m.ordem,
                autor=m.autor,
                texto=m.texto,
                enviada_em=m.enviada_em,
                rotulo_real=m.rotulo_real,
            )
            for m in conv_dto.mensagens
        )
        total_msgs += len(conv_dto.mensagens)

    return len(conversas_dto), total_msgs