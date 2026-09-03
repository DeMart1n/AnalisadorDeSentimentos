from django.test import TestCase

from .importacao import ErroDeImportacao, importar
from .models import Conversa, Mensagem

CSV = (
    "conversa_id,ordem,autor,texto,timestamp,rotulo\n"
    "c1,2,usuario,demorou demais,2026-01-02T10:01:00,negativo\n"
    "c1,1,sistema,voce esta na fila,2026-01-02T10:00:00,\n"
    "c2,1,usuario,obrigado resolveu,,positivo\n"
)


class ImportacaoTest(TestCase):
    def test_importa_e_ordena_por_conversa(self):
        conversas, mensagens = importar(CSV, fonte="teste")
        self.assertEqual((conversas, mensagens), (2, 3))
        textos = list(Conversa.objects.get(origem_id="c1").mensagens.values_list("ordem", "autor"))
        self.assertEqual(textos, [(1, "sistema"), (2, "usuario")])
        self.assertEqual(Mensagem.objects.get(ordem=2, conversa__origem_id="c1").rotulo_real, "negativo")

    def test_reimportar_substitui_sem_duplicar(self):
        importar(CSV, fonte="teste")
        importar(CSV, fonte="teste")
        self.assertEqual(Conversa.objects.count(), 2)
        self.assertEqual(Mensagem.objects.count(), 3)

    def test_arquivo_invalido_nao_grava_nada(self):
        ruim = CSV + "c3,1,robo,oi,,\n"
        with self.assertRaises(ErroDeImportacao):
            importar(ruim, fonte="teste")
        self.assertEqual(Conversa.objects.count(), 0)

    def test_ordem_repetida_na_mesma_conversa(self):
        with self.assertRaises(ErroDeImportacao):
            importar("conversa_id,ordem,autor,texto\nc1,1,usuario,a\nc1,1,usuario,b\n", fonte="teste")

    def test_json(self):
        dados = '[{"conversa_id":"c9","ordem":1,"autor":"usuario","texto":"oi"}]'
        self.assertEqual(importar(dados, fonte="teste", formato="json"), (1, 1))


from .avaliacao import avaliar, dividir_por_conversa, mcnemar
from .modelos import carregar
from .models import NEGATIVO, NEUTRO, POSITIVO


class LexicoTest(TestCase):
    def setUp(self):
        self.modelo = carregar("lexico")

    def test_polaridade(self):
        rotulos, _ = self.modelo.prever(["atendimento excelente", "péssimo, muita demora", "meu pedido é 4512"])
        self.assertEqual(rotulos, [POSITIVO, NEGATIVO, NEUTRO])

    def test_negacao_inverte(self):
        rotulos, _ = self.modelo.prever(["não gostei do atendimento"])
        self.assertEqual(rotulos, [NEGATIVO])


class AvaliacaoTest(TestCase):
    def _dados(self):
        # 10 conversas, 2 mensagens cada
        return [(c, f"texto {c}-{i}", POSITIVO if i == 0 else NEGATIVO) for c in range(10) for i in range(2)]

    def test_split_nao_vaza_conversa_entre_treino_e_teste(self):
        treino, teste = dividir_por_conversa(self._dados())
        self.assertFalse({d[0] for d in treino} & {d[0] for d in teste})
        self.assertEqual(len(treino) + len(teste), 20)

    def test_split_e_deterministico(self):
        self.assertEqual(dividir_por_conversa(self._dados()), dividir_por_conversa(self._dados()))

    def test_avaliar_devolve_f1_e_matriz(self):
        treino, teste = dividir_por_conversa(self._dados())
        r = avaliar(carregar("lexico"), treino, teste)
        self.assertIn("f1_macro", r)
        self.assertEqual(len(r["matriz"]), 3)
        self.assertEqual(len(r["y_pred"]), len(teste))

    def test_mcnemar_exige_mesmo_conjunto_de_teste(self):
        a = {"y_true": [POSITIVO], "y_pred": [POSITIVO]}
        b = {"y_true": [NEGATIVO], "y_pred": [NEGATIVO]}
        with self.assertRaises(ValueError):
            mcnemar(a, b)

    def test_mcnemar_detecta_modelo_melhor(self):
        y = [POSITIVO] * 30
        bom = {"y_true": y, "y_pred": y}
        ruim = {"y_true": y, "y_pred": [NEGATIVO] * 30}
        self.assertTrue(mcnemar(bom, ruim)["significativo"])

    def test_mcnemar_modelos_iguais_nao_e_significativo(self):
        y = [POSITIVO] * 30
        igual = {"y_true": y, "y_pred": y}
        self.assertFalse(mcnemar(igual, dict(igual))["significativo"])


class EscadaTest(TestCase):
    def test_registro_tem_os_tres_degraus(self):
        from .modelos import REGISTRO

        self.assertEqual(set(REGISTRO), {"lexico", "classico", "bertimbau"})

    def test_carregar_modelo_desconhecido(self):
        with self.assertRaises(ValueError):
            carregar("gpt")

    def test_todos_expoem_a_mesma_interface(self):
        # bertimbau fica de fora: instanciar baixaria pesos. A checagem é estática.
        from .modelos.bertimbau import Bertimbau

        for classe in (type(carregar("lexico")), type(carregar("classico")), Bertimbau):
            self.assertTrue(callable(getattr(classe, "treinar")))
            self.assertTrue(callable(getattr(classe, "prever")))
            self.assertTrue(hasattr(classe, "nome"))


from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

from .indicadores import indicadores


class IndicadoresTest(TestCase):
    def test_trajetoria_negativa_para_positiva(self):
        i = indicadores([NEUTRO, NEGATIVO, NEGATIVO, POSITIVO])
        self.assertEqual(i["abertura"], NEUTRO)
        self.assertEqual(i["encerramento"], POSITIVO)
        self.assertEqual(i["delta"], 1)
        self.assertEqual(i["pior_momento"], 2)
        self.assertEqual(i["n_mensagens"], 4)

    def test_neutro_no_meio_nao_conta_como_troca(self):
        self.assertEqual(indicadores([NEGATIVO, NEUTRO, NEGATIVO])["trocas_de_polaridade"], 0)
        self.assertEqual(indicadores([NEGATIVO, NEUTRO, POSITIVO])["trocas_de_polaridade"], 1)

    def test_sem_rotulo_devolve_none(self):
        self.assertIsNone(indicadores([]))
        self.assertIsNone(indicadores([None, None]))


class ApiTest(TestCase):
    def setUp(self):
        importar(CSV, fonte="teste")

    def _falso_modelo(self, textos):
        return [NEUTRO] * len(textos), [0.9] * len(textos)

    def test_upload_classifica_e_responde(self):
        arquivo = SimpleUploadedFile("novo.csv", CSV.encode(), content_type="text/csv")
        with patch("analise.classificador.modelo") as m:
            m.return_value.prever.side_effect = self._falso_modelo
            r = self.client.post("/api/upload", {"arquivo": arquivo, "fonte": "via-api"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["conversas"], 2)
        self.assertEqual(r.json()["mensagens_classificadas"], 2)  # só mensagens de usuário

    def test_upload_recusa_arquivo_invalido_sem_gravar(self):
        ruim = SimpleUploadedFile("ruim.csv", b"conversa_id,ordem\nc1,x\n", content_type="text/csv")
        r = self.client.post("/api/upload", {"arquivo": ruim, "fonte": "ruim"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Conversa.objects.filter(fonte="ruim").exists())

    def test_upload_sem_arquivo(self):
        self.assertEqual(self.client.post("/api/upload").status_code, 400)

    def test_lista_conversas(self):
        r = self.client.get("/api/conversas")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total"], 2)

    def test_detalhe_da_conversa(self):
        conversa = Conversa.objects.get(origem_id="c1")
        r = self.client.get(f"/api/conversas/{conversa.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["mensagens"]), 2)

    def test_conversa_inexistente(self):
        self.assertEqual(self.client.get("/api/conversas/99999").status_code, 404)

    def test_metricas(self):
        r = self.client.get("/api/metricas")
        self.assertEqual(r.status_code, 200)
        self.assertIn("distribuicao", r.json())
