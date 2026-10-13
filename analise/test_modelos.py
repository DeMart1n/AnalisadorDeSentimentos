import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import torch
from django.test import SimpleTestCase, TestCase
from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast
from transformers.utils.logging import disable_progress_bar

from .classificador import classificar_conversas, modelo
from .modelos import REGISTRO, ModeloNaoTreinado, carregar
from .modelos.bertimbau import CLASSES, Bertimbau, _Dados, dispositivo, pesos_salvos
from .modelos.classico import Classico
from .modelos.lexico import Lexico
from .models import ATENDENTE, NEGATIVO, NEUTRO, POSITIVO, USUARIO, Conversa, Mensagem

disable_progress_bar()

PALAVRAS = ["bom", "ótimo", "ruim", "péssimo", "pedido", "atendimento", "não", "gostei"]


def _base_minuscula(pasta):
    """BERT de 1 camada salvo em disco: substitui o BERTimbau real (436 MB) sem rede."""
    vocab = Path(pasta) / "vocab.txt"
    vocab.write_text("\n".join(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *PALAVRAS]), encoding="utf-8")
    tokenizer = BertTokenizerFast(vocab_file=str(vocab), do_lower_case=False)
    config = BertConfig(
        vocab_size=len(PALAVRAS) + 5, hidden_size=8, num_hidden_layers=1, num_attention_heads=1,
        intermediate_size=16, max_position_embeddings=256, num_labels=len(CLASSES),
        id2label=dict(enumerate(CLASSES)), label2id={c: i for i, c in enumerate(CLASSES)},
    )
    torch.manual_seed(0)
    BertForSequenceClassification(config).save_pretrained(pasta)
    tokenizer.save_pretrained(pasta)


class BertimbauTest(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._base = tempfile.TemporaryDirectory()
        _base_minuscula(cls._base.name)

    @classmethod
    def tearDownClass(cls):
        cls._base.cleanup()
        super().tearDownClass()

    def setUp(self):
        destino = tempfile.TemporaryDirectory()
        self.addCleanup(destino.cleanup)
        self.destino = Path(destino.name) / "bertimbau"
        for alvo in (patch("analise.modelos.bertimbau.BASE", self._base.name),
                     patch("analise.modelos.bertimbau.dispositivo", return_value="cpu")):
            alvo.start()
            self.addCleanup(alvo.stop)
        torch.manual_seed(0)

    def _novo(self, **kw):
        return Bertimbau(destino=self.destino, epocas=1, batch=2, **kw)

    def _treinar(self, b, **kw):
        b.treinar(["bom ótimo", "ruim péssimo", "pedido", "não gostei"],
                  [POSITIVO, NEGATIVO, NEUTRO, NEGATIVO], **kw)

    def test_sem_pesos_parte_da_base_e_nao_esta_treinado(self):
        b = self._novo()
        self.assertFalse(b.treinado)
        self.assertEqual(b.device, "cpu")
        self.assertEqual(b.modelo.config.id2label, dict(enumerate(CLASSES)))

    def test_sem_pesos_prever_levanta_erro(self):
        with self.assertRaises(ModeloNaoTreinado):
            self._novo().prever(["bom"])

    def test_treinar_salva_pesos_e_permite_prever(self):
        b = self._novo()
        self._treinar(b)
        self.assertTrue(b.treinado)
        self.assertTrue(pesos_salvos(self.destino))
        self.assertTrue((self.destino / "tokenizer.json").exists())

        rotulos, scores = b.prever(["bom", "ruim", "pedido"], batch=2)
        self.assertEqual(len(rotulos), 3)
        self.assertTrue(set(rotulos) <= set(CLASSES))
        self.assertTrue(all(0 <= s <= 1 for s in scores))

    def test_com_pesos_carrega_do_destino_e_nao_da_base(self):
        self._treinar(self._novo())
        # base inexistente: se o __init__ tentasse usá-la, o load quebraria
        with patch("analise.modelos.bertimbau.BASE", "/nao/existe"):
            b = self._novo()
        self.assertTrue(b.treinado)
        rotulos, _ = b.prever(["bom"])
        self.assertIn(rotulos[0], CLASSES)

    def test_treinar_ja_treinado_e_no_op(self):
        self._treinar(self._novo())
        b = self._novo()
        with patch.object(b, "salvar") as salvar:
            self._treinar(b)
        salvar.assert_not_called()

    def test_forcar_retreina_mesmo_ja_treinado(self):
        self._treinar(self._novo())
        b = self._novo()
        antes = [p.clone() for p in b.modelo.parameters()]
        with patch.object(b, "salvar") as salvar:
            self._treinar(b, forcar=True)
        salvar.assert_called_once()
        self.assertTrue(any(not torch.equal(a, p) for a, p in zip(antes, b.modelo.parameters())))

    def test_progresso_recebe_epoca_passo_total_e_perda(self):
        b = Bertimbau(destino=self.destino, epocas=2, batch=2)
        chamadas = []
        self._treinar(b, progresso=lambda *a: chamadas.append(a))
        # 4 textos / batch 2 = 2 passos por época; só o passo 0 é múltiplo de 100
        self.assertEqual([c[:3] for c in chamadas], [(1, 0, 2), (2, 0, 2)])
        self.assertTrue(all(isinstance(c[3], float) for c in chamadas))

    def test_salvar_cria_pasta_e_marca_treinado(self):
        b = self._novo()
        b.salvar()
        self.assertTrue(b.treinado)
        self.assertTrue(pesos_salvos(self.destino))

    def test_dados_com_e_sem_rotulos(self):
        tokenizer = BertTokenizerFast.from_pretrained(self._base.name)
        com = _Dados(["bom", "ruim"], [POSITIVO, NEGATIVO], tokenizer)
        self.assertEqual(len(com), 2)
        self.assertEqual(int(com[1]["labels"]), CLASSES.index(NEGATIVO))
        self.assertEqual(com[0]["input_ids"].shape[0], 128)

        sem = _Dados(["bom"], None, tokenizer)
        self.assertNotIn("labels", sem[0])


class DispositivoTest(SimpleTestCase):
    def test_usa_mps_quando_disponivel(self):
        with patch("torch.backends.mps.is_available", return_value=True):
            self.assertEqual(dispositivo(), "mps")

    def test_cai_para_cpu_sem_mps(self):
        with patch("torch.backends.mps.is_available", return_value=False):
            self.assertEqual(dispositivo(), "cpu")


class CarregarTest(SimpleTestCase):
    def test_bertimbau_e_importado_tarde(self):
        self.assertIsNone(REGISTRO["bertimbau"])

    def test_carregar_bertimbau_instancia_a_classe(self):
        with patch("analise.modelos.bertimbau.Bertimbau") as classe:
            self.assertIs(carregar("bertimbau"), classe.return_value)

    def test_carregar_devolve_instancias_novas(self):
        self.assertIsInstance(carregar("classico"), Classico)
        self.assertIsNot(carregar("lexico"), carregar("lexico"))

    def test_erro_lista_os_disponiveis(self):
        with self.assertRaisesRegex(ValueError, "lexico, classico, bertimbau"):
            carregar("gpt")


class ClassicoTest(SimpleTestCase):
    def setUp(self):
        textos = ["adorei o atendimento", "adorei muito", "odiei o atendimento", "odiei muito",
                  "meu pedido chegou", "meu pedido saiu"] * 2
        rotulos = [POSITIVO, POSITIVO, NEGATIVO, NEGATIVO, NEUTRO, NEUTRO] * 2
        self.modelo = Classico()
        self.modelo.treinar(textos, rotulos)

    def test_prever_devolve_rotulo_e_probabilidade(self):
        rotulos, scores = self.modelo.prever(["adorei", "odiei", "meu pedido"])
        self.assertEqual(rotulos, [POSITIVO, NEGATIVO, NEUTRO])
        self.assertTrue(all(1 / 3 < s <= 1 for s in scores))

    def test_termos_por_classe(self):
        termos = self.modelo.termos_por_classe(n=2)
        self.assertEqual(set(termos), set(CLASSES))
        self.assertIn("adorei", termos[POSITIVO])
        self.assertIn("odiei", termos[NEGATIVO])
        self.assertTrue(all(len(t) == 2 for t in termos.values()))


class ClassicoBinarioTest(SimpleTestCase):
    def test_termos_por_classe_com_duas_classes(self):
        # binário: o sklearn guarda uma linha de coeficientes só, a da segunda classe
        modelo = Classico()
        modelo.treinar(["adorei muito", "adorei demais", "odiei muito", "odiei demais"] * 2,
                       [POSITIVO, POSITIVO, NEGATIVO, NEGATIVO] * 2)
        termos = modelo.termos_por_classe(n=1)
        self.assertEqual(termos, {POSITIVO: ["adorei"], NEGATIVO: ["odiei"]})


class LexicoArquivoTest(SimpleTestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.arquivo = Path(pasta.name) / "lexico.txt"
        self.arquivo.write_text("# comentário\n\nbom 1\nruim -2\n  \n", encoding="utf-8")

    def test_ignora_comentarios_e_linhas_vazias(self):
        self.assertEqual(Lexico(self.arquivo).pesos, {"bom": 1.0, "ruim": -2.0})

    def test_score_e_modulo_da_soma(self):
        _, scores = Lexico(self.arquivo).prever(["bom ruim ruim"])
        self.assertEqual(scores, [3.0])

    def test_negacao_vale_so_na_janela(self):
        # "bom" a 4 palavras da negação já está fora da janela de 3
        rotulos, _ = Lexico(self.arquivo).prever(["não a b c bom", "não bom"])
        self.assertEqual(rotulos, [POSITIVO, NEGATIVO])

    def test_treinar_nao_altera_pesos(self):
        lexico = Lexico(self.arquivo)
        lexico.treinar(["ruim"], [POSITIVO])
        self.assertEqual(lexico.pesos["ruim"], -2.0)


class ClassificadorTest(TestCase):
    def setUp(self):
        modelo.cache_clear()
        self.addCleanup(modelo.cache_clear)
        self.conversa = Conversa.objects.create(origem_id="1", fonte="t")
        self.outra = Conversa.objects.create(origem_id="2", fonte="t")
        self.u1 = Mensagem.objects.create(conversa=self.conversa, ordem=1, autor=USUARIO, texto="bom")
        self.at = Mensagem.objects.create(conversa=self.conversa, ordem=2, autor=ATENDENTE, texto="ruim")
        self.u2 = Mensagem.objects.create(conversa=self.conversa, ordem=3, autor=USUARIO, texto="ok",
                                          rotulo_pred=NEUTRO, score=0.5)
        self.fora = Mensagem.objects.create(conversa=self.outra, ordem=1, autor=USUARIO, texto="x")
        self.falso = MagicMock()
        self.falso.prever.side_effect = lambda textos: ([POSITIVO] * len(textos), [0.9] * len(textos))
        alvo = patch("analise.classificador.carregar", return_value=self.falso)
        self.carregar = alvo.start()
        self.addCleanup(alvo.stop)

    def test_classifica_so_mensagens_do_usuario_das_conversas_dadas(self):
        self.assertEqual(classificar_conversas([self.conversa.id], nome="lexico"), 2)
        self.falso.prever.assert_called_once_with(["bom", "ok"])
        for m, rotulo in [(self.u1, POSITIVO), (self.u2, POSITIVO), (self.at, None), (self.fora, None)]:
            m.refresh_from_db()
            self.assertEqual(m.rotulo_pred, rotulo)
        self.assertEqual(self.u1.score, 0.9)

    def test_apenas_nao_classificadas_preserva_as_ja_rotuladas(self):
        self.assertEqual(classificar_conversas([self.conversa.id], nome="lexico", apenas_nao_classificadas=True), 1)
        self.falso.prever.assert_called_once_with(["bom"])
        self.u2.refresh_from_db()
        self.assertEqual((self.u2.rotulo_pred, self.u2.score), (NEUTRO, 0.5))

    def test_sem_mensagens_nao_carrega_modelo(self):
        self.assertEqual(classificar_conversas([999]), 0)
        self.carregar.assert_not_called()

    def test_modelo_fica_em_cache_por_nome(self):
        classificar_conversas([self.conversa.id], nome="lexico")
        classificar_conversas([self.outra.id], nome="lexico")
        self.carregar.assert_called_once_with("lexico")
        modelo("classico")
        self.assertEqual(self.carregar.call_count, 2)

    def test_padrao_e_bertimbau(self):
        classificar_conversas([self.conversa.id])
        self.carregar.assert_called_once_with("bertimbau")
