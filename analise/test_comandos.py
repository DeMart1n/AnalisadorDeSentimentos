import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .management.commands import avaliar as cmd_avaliar
from .models import ATENDENTE, NEGATIVO, NEUTRO, POSITIVO, USUARIO, Conversa, Mensagem


def _rodar(*args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    call_command(*args, stdout=out, stderr=err, **kwargs)
    return out.getvalue(), err.getvalue()


def _popular(fonte="teste", n=10):
    # vocabulário repetido: o TF-IDF usa min_df=2
    frases = {POSITIVO: "atendimento excelente adorei", NEGATIVO: "péssimo demora horrível", NEUTRO: "meu pedido número"}
    for c in range(n):
        conversa = Conversa.objects.create(origem_id=f"c{c}", fonte=fonte)
        for ordem, rotulo in enumerate(frases, start=1):
            Mensagem.objects.create(conversa=conversa, ordem=ordem, autor=USUARIO,
                                    texto=frases[rotulo], rotulo_real=rotulo)
        # mensagem do atendente fica de fora do treino
        Mensagem.objects.create(conversa=conversa, ordem=4, autor=ATENDENTE, texto="ok", rotulo_real=NEUTRO)


class TempDirMixin:
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class AvaliarComandoTest(TempDirMixin, TestCase):
    def test_banco_vazio_erro(self):
        with self.assertRaisesMessage(CommandError, "nenhuma mensagem"):
            _rodar("avaliar", "--modelos", "lexico")

    def test_fonte_sem_dados_erro(self):
        _popular()
        with self.assertRaisesMessage(CommandError, "nenhuma mensagem"):
            _rodar("avaliar", "--modelos", "lexico", "--fonte", "outra")

    def test_teste_vazio_erro(self):
        _popular()
        # com proporcao 0.2 o split real nunca devolve teste vazio; forçamos o ramo
        with patch.object(cmd_avaliar, "dividir_por_conversa", lambda dados, seed: (dados, [])):
            with self.assertRaisesMessage(CommandError, "treino ou teste vazio"):
                _rodar("avaliar", "--modelos", "lexico")

    def test_uma_conversa_so_deixa_treino_vazio_e_da_erro_claro(self):
        _popular(n=1)
        with self.assertRaisesMessage(CommandError, "treino ou teste vazio"):
            _rodar("avaliar", "--modelos", "classico")

    def test_avalia_e_compara_modelos(self):
        _popular()
        out, _ = _rodar("avaliar", "--modelos", "lexico", "classico", "--fonte", "teste")
        self.assertIn("=== lexico — F1 macro", out)
        self.assertIn("=== classico — F1 macro", out)
        self.assertIn("(treino 24, teste 6)", out)
        self.assertIn("matriz (ordem positivo/negativo/neutro)", out)
        self.assertIn("McNemar lexico x classico: p=", out)
        self.assertNotIn("métricas salvas", out)

    def test_mcnemar_significativo(self):
        _popular()
        sempre_certo = {"acertos_so_de_a": 30, "acertos_so_de_b": 0, "p": 0.0, "significativo": True}
        with patch.object(cmd_avaliar, "mcnemar", return_value=sempre_certo):
            out, _ = _rodar("avaliar", "--modelos", "lexico", "classico")
        self.assertIn("— diferença significativa", out)

    def test_um_modelo_so_nao_roda_mcnemar(self):
        _popular()
        out, _ = _rodar("avaliar", "--modelos", "lexico")
        self.assertNotIn("McNemar", out)

    def test_salvar_grava_metricas_json(self):
        _popular()
        # destino = parents[3] de __file__ / models / metricas.json -> cai dentro do tempdir
        falso = self.tmp / "analise" / "management" / "commands" / "avaliar.py"
        with patch.object(cmd_avaliar, "__file__", str(falso)):
            out, _ = _rodar("avaliar", "--modelos", "lexico", "classico", "--salvar")
        destino = self.tmp.resolve() / "models" / "metricas.json"
        self.assertIn(f"métricas salvas em {destino}", out)
        dados = json.loads(destino.read_text())
        self.assertEqual(dados["n_teste"], 6)
        self.assertEqual([m["nome"] for m in dados["modelos"]], ["lexico", "classico"])
        self.assertEqual(len(dados["modelos"][0]["matriz"]), 3)
        self.assertEqual(len(dados["mcnemar"]), 1)
        self.assertEqual((dados["mcnemar"][0]["a"], dados["mcnemar"][0]["b"]), ("lexico", "classico"))
        self.assertIn("significativo", dados["mcnemar"][0])

    def test_modelo_invalido_recusado_pelo_parser(self):
        with self.assertRaises(CommandError):
            _rodar("avaliar", "--modelos", "gpt")


class ImportarConversasComandoTest(TempDirMixin, TestCase):
    def test_importa_csv(self):
        arquivo = self.tmp / "conversas.CSV"
        arquivo.write_text("conversa_id,ordem,autor,texto\nc1,1,usuario,oi\nc1,2,atendente,olá\n", encoding="utf-8")
        out, _ = _rodar("importar_conversas", str(arquivo), "--fonte", "csv")
        self.assertIn("1 conversa(s), 2 mensagem(ns)", out)
        self.assertEqual(Mensagem.objects.filter(conversa__fonte="csv").count(), 2)

    def test_importa_json_pela_extensao(self):
        arquivo = self.tmp / "conversas.JSON"
        arquivo.write_text('[{"conversa_id":"j1","ordem":1,"autor":"usuario","texto":"oi"}]', encoding="utf-8")
        out, _ = _rodar("importar_conversas", str(arquivo), "--fonte", "json")
        self.assertIn("1 conversa(s), 1 mensagem(ns)", out)
        self.assertTrue(Conversa.objects.filter(fonte="json", origem_id="j1").exists())

    def test_erros_vao_para_stderr_e_nada_e_gravado(self):
        arquivo = self.tmp / "ruim.csv"
        arquivo.write_text("conversa_id,ordem,autor,texto\nc1,1,robo,oi\n", encoding="utf-8")
        err = io.StringIO()
        with self.assertRaisesMessage(CommandError, "nada foi importado"):
            call_command("importar_conversas", str(arquivo), "--fonte", "x", stdout=io.StringIO(), stderr=err)
        self.assertIn("autor inválido 'robo'", err.getvalue())
        self.assertNotIn("e mais", err.getvalue())
        self.assertEqual(Conversa.objects.count(), 0)

    def test_mais_de_vinte_erros_sao_resumidos(self):
        arquivo = self.tmp / "ruim.csv"
        linhas = "".join(f"c{i},1,robo,oi\n" for i in range(25))
        arquivo.write_text("conversa_id,ordem,autor,texto\n" + linhas, encoding="utf-8")
        err = io.StringIO()
        with self.assertRaises(CommandError):
            call_command("importar_conversas", str(arquivo), "--fonte", "x", stdout=io.StringIO(), stderr=err)
        self.assertEqual(err.getvalue().count("autor inválido"), 20)
        self.assertIn("... e mais 5 erro(s)", err.getvalue())

    def test_arquivo_inexistente_erro(self):
        with self.assertRaisesMessage(CommandError, "arquivo não encontrado"):
            _rodar("importar_conversas", str(self.tmp / "nao_existe.csv"), "--fonte", "x")

    def test_arquivo_fora_de_utf8_erro(self):
        arquivo = self.tmp / "latin.csv"
        arquivo.write_bytes("conversa_id,ordem,autor,texto\nc1,1,usuario,ação\n".encode("latin-1"))
        with self.assertRaisesMessage(CommandError, "UTF-8"):
            _rodar("importar_conversas", str(arquivo), "--fonte", "x")

    def test_json_malformado_erro(self):
        arquivo = self.tmp / "quebrado.json"
        arquivo.write_text("[{", encoding="utf-8")
        with self.assertRaisesMessage(CommandError, "JSON inválido"):
            _rodar("importar_conversas", str(arquivo), "--fonte", "x")
        self.assertEqual(Conversa.objects.count(), 0)

    def test_fonte_obrigatoria(self):
        with self.assertRaises(CommandError):
            _rodar("importar_conversas", str(self.tmp / "a.csv"))


class ImportarKaggleComandoTest(TempDirMixin, TestCase):
    def _csv(self, base, linhas):
        texto = "review_text,rating\n" + "".join(f'"{t}",{r}\n' for t, r in linhas)
        (self.tmp / f"{base}.csv").write_text(texto, encoding="utf-8")

    def test_arquivo_inexistente_erro(self):
        with self.assertRaisesMessage(CommandError, "não encontrei"):
            _rodar("importar_kaggle", "--dir", str(self.tmp))

    def test_mapeia_rating_e_ignora_linhas_vazias(self):
        self._csv("b2w", [("ruim", 1), ("fraco", "2.0"), ("ok", 3), ("bom", 4), ("ótimo", 5), ("  ", 5), ("sem nota", "")])
        out, _ = _rodar("importar_kaggle", "--dir", str(self.tmp), "--bases", "b2w", "--por-classe", "0")
        self.assertIn("b2w: 5 reviews", out)
        rotulos = dict(Mensagem.objects.values_list("texto", "rotulo_real"))
        self.assertEqual(rotulos, {"ruim": NEGATIVO, "fraco": NEGATIVO, "ok": NEUTRO, "bom": POSITIVO, "ótimo": POSITIVO})
        # cada review vira uma conversa de uma mensagem do usuário
        self.assertEqual(Conversa.objects.filter(fonte="b2w").count(), 5)
        self.assertFalse(Mensagem.objects.exclude(ordem=1, autor=USUARIO).exists())

    def test_amostra_por_classe_e_reimportacao_substitui(self):
        self._csv("olist", [(f"bom {i}", 5) for i in range(10)] + [(f"ruim {i}", 1) for i in range(3)])
        self._csv("b2w", [("bom", 5)])
        out, _ = _rodar("importar_kaggle", "--dir", str(self.tmp), "--por-classe", "4")
        self.assertIn("b2w: 1 reviews", out)
        self.assertIn("olist: 7 reviews", out)
        self.assertEqual(Mensagem.objects.filter(conversa__fonte="olist", rotulo_real=POSITIVO).count(), 4)
        self.assertEqual(Mensagem.objects.filter(conversa__fonte="olist", rotulo_real=NEGATIVO).count(), 3)

        _rodar("importar_kaggle", "--dir", str(self.tmp), "--bases", "olist", "--por-classe", "2")
        self.assertEqual(Conversa.objects.filter(fonte="olist").count(), 4)
        self.assertEqual(Conversa.objects.filter(fonte="b2w").count(), 1)

    def test_rating_nao_numerico_e_ignorado(self):
        self._csv("b2w", [("bom", 5), ("estranho", "abc")])
        out, _ = _rodar("importar_kaggle", "--dir", str(self.tmp), "--bases", "b2w", "--por-classe", "0")
        self.assertIn("b2w: 1 reviews", out)

    def test_csv_sem_reviews_validas_preserva_base_atual(self):
        self._csv("b2w", [("bom", 5)])
        _rodar("importar_kaggle", "--dir", str(self.tmp), "--bases", "b2w")
        (self.tmp / "b2w.csv").write_text("texto,nota\nbom,5\n", encoding="utf-8")
        with self.assertRaisesMessage(CommandError, "nada foi alterado"):
            _rodar("importar_kaggle", "--dir", str(self.tmp), "--bases", "b2w")
        self.assertEqual(Conversa.objects.filter(fonte="b2w").count(), 1)

    def test_amostra_e_deterministica_pela_seed(self):
        self._csv("b2w", [(f"bom {i}", 5) for i in range(20)])
        _rodar("importar_kaggle", "--dir", str(self.tmp), "--bases", "b2w", "--por-classe", "5", "--seed", "7")
        primeira = sorted(Mensagem.objects.values_list("texto", flat=True))
        _rodar("importar_kaggle", "--dir", str(self.tmp), "--bases", "b2w", "--por-classe", "5", "--seed", "7")
        self.assertEqual(sorted(Mensagem.objects.values_list("texto", flat=True)), primeira)


class FakeBertimbau:
    instancias = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.destino = Path("/tmp/fake-bertimbau")
        FakeBertimbau.instancias.append(self)

    def treinar(self, textos, rotulos, forcar, progresso):
        self.textos, self.rotulos, self.forcar = textos, rotulos, forcar
        progresso(1, 5, 10, 0.12345)


@patch("analise.management.commands.treinar_bertimbau.dispositivo", return_value="cpu-falso")
@patch("analise.management.commands.treinar_bertimbau.Bertimbau", FakeBertimbau)
class TreinarBertimbauComandoTest(TestCase):
    def setUp(self):
        FakeBertimbau.instancias = []

    def test_banco_vazio_erro(self, _dispositivo):
        with self.assertRaisesMessage(CommandError, "nenhuma mensagem rotulada"):
            _rodar("treinar_bertimbau")
        self.assertEqual(FakeBertimbau.instancias, [])

    def test_treina_so_no_split_de_treino(self, _dispositivo):
        _popular()
        out, _ = _rodar("treinar_bertimbau", "--epocas", "3", "--batch", "8")
        modelo, = FakeBertimbau.instancias
        self.assertEqual(modelo.kwargs, {"epocas": 3, "batch": 8})
        self.assertTrue(modelo.forcar)
        self.assertEqual(len(modelo.textos), 24)
        self.assertEqual(len(modelo.rotulos), 24)
        self.assertIn("dispositivo: cpu-falso | treino: 24 | teste reservado: 6", out)
        self.assertIn("época 1 passo 5/10 perda 0.1235", out)
        self.assertIn("salvo em /tmp/fake-bertimbau", out)

    def test_treino_vazio_erro(self, _dispositivo):
        _popular(n=1)
        with self.assertRaisesMessage(CommandError, "treino vazio"):
            _rodar("treinar_bertimbau")
        self.assertEqual(FakeBertimbau.instancias, [])

    def test_amostra_limita_treino(self, _dispositivo):
        _popular()
        out, _ = _rodar("treinar_bertimbau", "--amostra", "5", "--fonte", "teste")
        self.assertEqual(len(FakeBertimbau.instancias[0].textos), 5)
        self.assertIn("treino: 5 | teste reservado: 6", out)
