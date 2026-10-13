import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .auth import token_generator
from .avaliacao import carregar_dados
from .dtos.analise_dto import AnalisarConversasDTO
from .dtos.importacao_dto import ConversaImportadaDTO, MensagemImportadaDTO, ResultadoImportacaoDTO
from .importacao import ErroDeImportacao, importar
from .modelos import ModeloNaoTreinado
from .models import NEGATIVO, POSITIVO, Conversa, Mensagem, Users

CSV = (
    "conversa_id,ordem,autor,texto,timestamp,rotulo\n"
    "c1,2,usuario,demorou demais,2026-01-02T10:01:00,negativo\n"
    "c1,1,sistema,voce esta na fila,2026-01-02T10:00:00,\n"
    "c2,1,usuario,obrigado resolveu,,positivo\n"
)


class ApiAnaliseTest(TestCase):
    def setUp(self):
        importar(CSV, fonte="teste")
        admin = Users.objects.create(
            name="Admin", email="admin@email.com", password=make_password("senha123"), role="ADMIN"
        )
        user = Users.objects.create(
            name="User", email="user@email.com", password=make_password("senha123"), role="USER"
        )
        self.admin_headers = {"HTTP_AUTHORIZATION": f"Bearer {token_generator(admin)[0]}"}
        self.user_headers = {"HTTP_AUTHORIZATION": f"Bearer {token_generator(user)[0]}"}

    def _upload(self, nome, conteudo, **extra):
        arquivo = SimpleUploadedFile(nome, conteudo)
        return self.client.post("/api/upload", {"arquivo": arquivo, **extra}, **self.admin_headers)

    def _analisar(self, corpo):
        dados = corpo if isinstance(corpo, str) else json.dumps(corpo)
        return self.client.post(
            "/api/conversas/analisar", dados, content_type="application/json", **self.user_headers
        )

    # upload

    def test_upload_recusa_arquivo_fora_de_utf8(self):
        r = self._upload("latin.csv", "conversa_id,texto\nc1,ação\n".encode("latin-1"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("UTF-8", r.json()["erro"])

    def test_upload_recusa_json_malformado(self):
        r = self._upload("quebrado.json", b"[{")
        self.assertEqual(r.status_code, 400)
        self.assertIn("JSON inválido", r.json()["erro"])

    def test_upload_json_sem_fonte_usa_nome_do_arquivo(self):
        dados = [{"conversa_id": "j1", "ordem": 1, "autor": "usuario", "texto": "oi"}]
        r = self._upload("Atendimento.JSON", json.dumps(dados).encode())
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["fonte"], "Atendimento")
        self.assertTrue(Conversa.objects.filter(fonte="Atendimento", origem_id="j1").exists())

    def test_upload_invalido_devolve_no_maximo_20_detalhes(self):
        linhas = "".join(f"c{i},,usuario,\n" for i in range(30))
        r = self._upload("ruim.csv", f"conversa_id,ordem,autor,texto\n{linhas}".encode())
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(r.json()["detalhes"]), 20)

    # conversas

    def test_lista_conversas_filtra_por_fonte(self):
        importar(CSV, fonte="outra")
        r = self.client.get("/api/conversas", {"fonte": "outra"})
        self.assertEqual(r.json()["total"], 2)
        self.assertEqual({c["fonte"] for c in r.json()["conversas"]}, {"outra"})

    def test_lista_conversas_respeita_limite_mas_total_conta_tudo(self):
        r = self.client.get("/api/conversas", {"limite": 1})
        self.assertEqual(r.json()["total"], 2)
        self.assertEqual(len(r.json()["conversas"]), 1)

    def test_lista_conversas_limite_tem_teto_de_500(self):
        Conversa.objects.bulk_create(Conversa(origem_id=f"x{i}", fonte="massa") for i in range(501))
        r = self.client.get("/api/conversas", {"fonte": "massa", "limite": 10000})
        self.assertEqual(r.json()["total"], 501)
        self.assertEqual(len(r.json()["conversas"]), 500)

    def test_lista_conversas_indicadores_usam_so_mensagens_do_usuario(self):
        c1 = Conversa.objects.get(origem_id="c1", fonte="teste")
        c1.mensagens.update(rotulo_pred=NEGATIVO)
        r = self.client.get("/api/conversas", {"fonte": "teste"})
        item = next(c for c in r.json()["conversas"] if c["origem_id"] == "c1")
        self.assertEqual(item["indicadores"]["n_mensagens"], 1)
        self.assertEqual(item["indicadores"]["abertura"], NEGATIVO)

    def test_lista_conversas_so_aceita_get(self):
        self.assertEqual(self.client.post("/api/conversas").status_code, 405)

    # conversa (detalhe)

    def test_detalhe_traz_mensagens_em_ordem_com_rotulos(self):
        c1 = Conversa.objects.get(origem_id="c1", fonte="teste")
        c1.mensagens.filter(autor="usuario").update(rotulo_pred=NEGATIVO, score=0.8)
        corpo = self.client.get(f"/api/conversas/{c1.id}").json()
        self.assertEqual([m["ordem"] for m in corpo["mensagens"]], [1, 2])
        self.assertEqual(corpo["mensagens"][1]["rotulo"], NEGATIVO)
        self.assertEqual(corpo["mensagens"][1]["score"], 0.8)
        self.assertEqual(corpo["mensagens"][1]["rotulo_real"], NEGATIVO)
        self.assertEqual(corpo["indicadores"]["n_mensagens"], 1)

    # metricas

    def test_metricas_sem_arquivo_de_avaliacao_devolve_modelos_none(self):
        with tempfile.TemporaryDirectory() as tmp, patch("analise.views.METRICAS", Path(tmp) / "metricas.json"):
            r = self.client.get("/api/metricas")
        self.assertIsNone(r.json()["modelos"])
        self.assertEqual(r.json()["total_conversas"], 2)

    def test_metricas_le_arquivo_de_avaliacao_e_conta_distribuicao(self):
        Mensagem.objects.filter(texto="demorou demais").update(rotulo_pred=NEGATIVO)
        Mensagem.objects.filter(texto="obrigado resolveu").update(rotulo_pred=POSITIVO)
        # rótulo em mensagem do sistema não entra na distribuição
        Mensagem.objects.filter(autor="sistema").update(rotulo_pred=POSITIVO)
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "metricas.json"
            caminho.write_text(json.dumps({"lexico": {"f1_macro": 0.5}}))
            with patch("analise.views.METRICAS", caminho):
                r = self.client.get("/api/metricas")
        self.assertEqual(r.json()["modelos"], {"lexico": {"f1_macro": 0.5}})
        self.assertEqual(r.json()["distribuicao"], {NEGATIVO: 1, POSITIVO: 1})

    # analisar

    def test_analisar_sem_modelo_treinado_devolve_503(self):
        with patch("analise.views.classificar_conversas", side_effect=ModeloNaoTreinado("sem pesos salvos")):
            r = self._analisar({"fonte": "teste", "modelo": "bertimbau"})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json(), {"erro": "sem pesos salvos"})

    def test_analisar_corpo_vazio(self):
        r = self._analisar("")
        self.assertEqual(r.status_code, 400)
        self.assertIn("vazio", r.json()["erro"])

    def test_analisar_json_invalido(self):
        r = self._analisar("{fonte")
        self.assertEqual(r.status_code, 400)
        self.assertIn("erro", r.json())

    def test_analisar_payload_que_nao_e_objeto(self):
        r = self._analisar([1, 2])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["erro"], ["Payload inválido."])

    def test_analisar_filtra_por_conversa_ids(self):
        c2 = Conversa.objects.get(origem_id="c2", fonte="teste")
        with patch("analise.views.classificar_conversas", return_value=1) as classificar:
            r = self._analisar({"conversa_ids": [c2.id], "modelo": "lexico", "apenas_nao_classificadas": False})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {
            "fonte": None, "total_conversas": 1, "mensagens_classificadas": 1, "modelo_utilizado": "lexico",
        })
        classificar.assert_called_once_with(ids=[c2.id], nome="lexico", apenas_nao_classificadas=False)

    def test_analisar_fonte_e_ids_combinados_sem_intersecao_da_404(self):
        importar(CSV, fonte="outra")
        de_outra = Conversa.objects.get(origem_id="c1", fonte="outra")
        r = self._analisar({"fonte": "teste", "conversa_ids": [de_outra.id], "modelo": "lexico"})
        self.assertEqual(r.status_code, 404)

    def test_analisar_reclassifica_so_o_que_falta_por_padrao(self):
        Mensagem.objects.filter(texto="demorou demais").update(rotulo_pred=NEGATIVO)
        with patch("analise.classificador.modelo") as m:
            m.return_value.prever.side_effect = lambda textos: (["neutro"] * len(textos), [0.5] * len(textos))
            r = self._analisar({"fonte": "teste", "modelo": "lexico"})
        self.assertEqual(r.json()["mensagens_classificadas"], 1)
        self.assertEqual(Mensagem.objects.get(texto="demorou demais").rotulo_pred, NEGATIVO)

    def test_analisar_so_aceita_post(self):
        self.assertEqual(self.client.get("/api/conversas/analisar", **self.user_headers).status_code, 405)

    # openapi

    def test_openapi_usa_caminho_do_container_quando_local_nao_existe(self):
        fallback = MagicMock()
        fallback.exists.return_value = True
        fallback.read_text.return_value = "openapi: 3.1.0\n"
        with patch("analise.views.OPENAPI_PATH", Path("/nao/existe.yaml")), patch("analise.views.Path", return_value=fallback):
            r = self.client.get("/api/openapi.yaml")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "openapi: 3.1.0\n")

    def test_openapi_sem_arquivo_devolve_404(self):
        fallback = MagicMock()
        fallback.exists.return_value = False
        with patch("analise.views.OPENAPI_PATH", Path("/nao/existe.yaml")), patch("analise.views.Path", return_value=fallback):
            r = self.client.get("/api/openapi.yaml")
        self.assertEqual(r.status_code, 404)


class AnalisarConversasDTOTest(TestCase):
    def _erros(self, dados):
        with self.assertRaises(ValueError) as ctx:
            AnalisarConversasDTO.from_dict(dados)
        return ctx.exception.args[0]

    def test_exige_fonte_ou_conversa_ids(self):
        self.assertIn("Informe, pelo menos, uma fonte ou uma lista de conversas para analisar.", self._erros({}))

    def test_sem_modelo_usa_um_modelo_valido(self):
        # sem STANDARD_MODEL no ambiente o padrão era None e o carregar quebrava com 400
        from .dtos.analise_dto import ALLOWED_MODELS

        self.assertIn(AnalisarConversasDTO.from_dict({"fonte": "x"}).modelo, ALLOWED_MODELS)

    def test_fonte_em_branco_ou_nao_string(self):
        self.assertIn("A fonte deve ser uma string não vazia.", self._erros({"fonte": "   "}))
        self.assertIn("A fonte deve ser uma string não vazia.", self._erros({"fonte": 123}))

    def test_conversa_ids_precisa_ser_lista_de_inteiros(self):
        msg = "A lista de conversas deve ser uma lista de ids inteiros."
        self.assertIn(msg, self._erros({"conversa_ids": "1,2"}))
        self.assertIn(msg, self._erros({"conversa_ids": [1, "2"]}))

    def test_apenas_nao_classificadas_precisa_ser_booleano(self):
        erros = self._erros({"fonte": "x", "modelo": "lexico", "apenas_nao_classificadas": "sim"})
        self.assertEqual(erros, ["O campo 'apenas_nao_classificadas' deve ser booleano."])

    def test_acumula_todos_os_erros(self):
        erros = self._erros({"fonte": "", "conversa_ids": "x", "modelo": "gpt", "apenas_nao_classificadas": 1})
        self.assertEqual(len(erros), 4)

    def test_normaliza_fonte_e_modelo(self):
        dto = AnalisarConversasDTO.from_dict({"fonte": "  zendesk ", "conversa_ids": [3], "modelo": " LEXICO "})
        self.assertEqual((dto.fonte, dto.conversa_ids, dto.modelo, dto.apenas_nao_classificadas),
                         ("zendesk", [3], "lexico", True))


class ImportacaoDTOTest(TestCase):
    def test_to_dict_das_mensagens_conversas_e_resultado(self):
        enviada = datetime(2026, 1, 2, tzinfo=timezone.utc)
        msg = MensagemImportadaDTO(ordem=1, autor="usuario", texto="oi", enviada_em=enviada)
        conversa = ConversaImportadaDTO(
            origem_id="c1", fonte="f", mensagens=[msg], nomes_contexto={"Ana"}, telefones_contexto={"1199"}
        )
        self.assertEqual(msg.to_dict()["enviada_em"], enviada)
        d = conversa.to_dict()
        self.assertEqual(d["nomes_contexto"], ["Ana"])
        self.assertEqual(d["telefones_contexto"], ["1199"])
        self.assertEqual(d["mensagens"][0]["texto"], "oi")
        self.assertEqual(
            ResultadoImportacaoDTO(fonte="f", total_conversas=1, total_mensagens=2).to_dict(),
            {"fonte": "f", "total_conversas": 1, "total_mensagens": 2, "status": "importado"},
        )


class ImportacaoRamosTest(TestCase):
    def _erros(self, conteudo, formato="csv"):
        with self.assertRaises(ErroDeImportacao) as ctx:
            importar(conteudo, fonte="t", formato=formato)
        return ctx.exception.erros

    def _autores(self, origem_id="c1"):
        return list(Mensagem.objects.filter(conversa__origem_id=origem_id).values_list("autor", flat=True))

    def test_csv_vazio_nao_importa_nada(self):
        self.assertEqual(importar("", fonte="t"), (0, 0))

    def test_csv_de_uma_coluna_cai_no_delimitador_virgula(self):
        # sem nenhum delimitador o Sniffer falha; o importador assume vírgula
        self.assertEqual(self._erros("texto\noi\n"), ["linha 1: campos faltando: autor, conversa_id"])

    def test_json_que_nao_e_lista(self):
        self.assertEqual(self._erros('{"a": 1}', formato="json"), ["JSON deve ser uma lista de objetos"])

    def test_origem_de_bot_vira_sistema(self):
        importar("conversa_id,ordem,autor,origem,texto\nc1,1,Maria,chatbot,ola\n", fonte="t")
        self.assertEqual(self._autores(), ["sistema"])

    def test_papel_deduzido_de_origem_composta(self):
        csv = (
            "conversa_id,ordem,autor,origem,texto\n"
            "c1,1,Ana,cliente_vip,quero cancelar\n"
            "c1,2,Bruno,agente_n2,vou verificar\n"
        )
        importar(csv, fonte="t")
        self.assertEqual(self._autores(), ["usuario", "atendente"])

    def test_autor_desconhecido_sem_pista_na_origem(self):
        self.assertEqual(
            self._erros("conversa_id,ordem,autor,origem,texto\nc1,1,Ana,diretoria,oi\n"),
            ["linha 1: autor inválido 'Ana'"],
        )

    def test_timestamp_com_fuso_e_preservado(self):
        importar("conversa_id,autor,texto,timestamp\nc1,usuario,oi,2026-01-02T10:00:00+00:00\n", fonte="t")
        enviada = Mensagem.objects.get().enviada_em
        self.assertEqual(enviada, datetime(2026, 1, 2, 10, tzinfo=timezone.utc))

    def test_erros_de_linha_sao_todos_reportados(self):
        csv = (
            "conversa_id,ordem,autor,texto,rotulo\n"
            ",1,usuario,sem conversa,\n"
            "c1,1,usuario,rotulo ruim,feliz\n"
            "c2,um,usuario,ordem ruim,\n"
        )
        self.assertEqual(self._erros(csv), [
            "linha 1: campos faltando: conversa_id",
            "linha 2: rotulo inválido 'feliz'",
            "linha 3: ordem não é inteiro: 'um'",
        ])
        self.assertFalse(Conversa.objects.exists())

    def test_ordem_parcial_na_mesma_conversa(self):
        csv = "conversa_id,ordem,autor,texto\nc1,1,usuario,a\nc1,,usuario,b\n"
        self.assertEqual(self._erros(csv), ["linha 2: ordem ausente na conversa c1"])


class CarregarDadosTest(TestCase):
    def test_so_mensagens_do_usuario_com_rotulo_real_filtrando_por_fonte(self):
        importar(CSV, fonte="teste")
        importar("conversa_id,ordem,autor,texto,rotulo\nz1,1,usuario,tanto faz,neutro\n", fonte="outra")
        textos = sorted(t for _, t, _ in carregar_dados())
        self.assertEqual(textos, ["demorou demais", "obrigado resolveu", "tanto faz"])
        self.assertEqual([r for _, _, r in carregar_dados(fonte="outra")], ["neutro"])
