# Modelo IA: relatório técnico (24/09 a 30/09/2026)

Documento-fonte conferido: `docs/relatorio/03-MODELO-IA.md` (commit `2effafd`, 09/09), idêntico à cópia em `Downloads/relatorio/`.

## 1. Estado atual

- **Resultado científico: íntegro.** Código dos três degraus, protocolo de avaliação, conjunto de teste e métricas de léxico/TF-IDF conferem com o documento.
- **BERTimbau: não roda hoje.** `models/bertimbau/` tem `config.json` e tokenizer, mas **não tem `model.safetensors`**. `carregar("bertimbau")` levanta `OSError: Error no file named model.safetensors`. Como `classificador.PADRAO = "bertimbau"`, a classificação de conversas pela API também falha.
- Os números do BERTimbau (F1 0,764) seguem valendo como registro do treino de 28/08, mas **não dá para reproduzi-los** sem retreinar (~46 min).

## 2. O que foi feito na semana

- **No módulo, nenhum commit.** O último commit que mexeu em `analise/modelos/` ou `analise/avaliacao.py` é o `a1ac1ae`, de 03/09.
- **Hoje (30/09):** conferência completa do documento contra código, banco e artefatos (seção 3). Criei a skill `relatorio-semanal`.
- **Commits de outros módulos que afetam este:**
  - `7b1b901` (23/09, anonimizador): o texto de upload/importação passa a chegar ao modelo com `[EMAIL]`, `[CPF]`, `[CNPJ]`, `[CARTAO]` e nomes substituídos. O modelo foi treinado em reviews sem esses marcadores.
  - `204ebfa` (28/09, telas do front): consome `/api/metricas`, que só traz léxico e clássico (ver P1).

## 3. Conferência do documento-fonte

| Afirmação no doc | Status | Realidade | Fonte |
|---|---|---|---|
| "Estado: concluído para a v1" | **diverge** | Os resultados estão concluídos, mas o artefato do degrau 3 sumiu do disco e o modelo não carrega | `ls models/bertimbau/`; `carregar("bertimbau")` → `OSError` |
| Pesos "não estão no repositório, são artefato reconstrutível" | **diverge (incompleto)** | Também não estão na máquina local. A pasta foi modificada em 18/09 09:11 e os arquivos restantes são de 28/08 13:36 | `stat models/bertimbau` |
| 436 MB de pesos | não verificável | Não há arquivo para medir | — |
| 46 min de treino em MPS | não verificável | Consta só na SPEC, sem log salvo | `SPEC.md:112` |
| Split 50.456 treino / 12.615 teste | **diverge (treino)** | 50.458 / 12.615. A conversa `fonte='amostra'` (id 1, 2 mensagens rotuladas, de 27/08) entra em `carregar_dados` e caiu no treino | `dividir_por_conversa(carregar_dados())` |
| Suporte do teste: 4.689 / 4.785 / 3.141 | confere | Idem | mesmo comando |
| Amostragem b2w 12k×3; olist 12.000 / 11.407 / 3.664; total 63.071 | confere | 63.071 de Kaggle, mais 2 de `amostra` = 63.073 rotuladas | `sqlite3 db.sqlite3` agrupado por fonte/rótulo |
| Texto: b2w 151,5 (máx. 4.134); olist 78,0 (máx. 208) | confere | Idem | consulta no banco |
| Léxico com 118 linhas, negação em janela de 3, regex `[a-zà-ÿ]+` | confere | Idem | `analise/modelos/lexico.py`, `wc -l lexico_pt.txt` |
| TF-IDF `(1,2)`, `min_df=2`, `sublinear_tf`; LR `balanced`, `max_iter=1000` | confere | Idem | `analise/modelos/classico.py:15-17` |
| BERTimbau: max_len 128, batch 32, lr 2e-5, AdamW, OneCycle 10%, CE com peso, 2 épocas padrão | confere | Idem | `analise/modelos/bertimbau.py` |
| `id2label` positivo/negativo/neutro, vocab 29.794, 12 camadas, hidden 768 | confere | Idem | `models/bertimbau/config.json` |
| Guarda contra retreino (`treinar()` no-op se já treinado) | confere, com efeito novo | A guarda olha só `config.json`, então com pesos ausentes o modelo se declara treinado e quebra no load em vez de retreinar | `bertimbau.py:47-48` |
| F1 léxico 0,489, clássico 0,735, matrizes e McNemar 1.343 × 4.584 | confere | `metricas.json`: 0,4885 / 0,7346, mesmas matrizes | `models/metricas.json` (28/08 14:35) |
| Matriz do BERTimbau ausente de `metricas.json` | confere | Continua ausente | idem |
| Anonimização dos textos | **ausente no doc** | Entrou em 23/09 e muda a entrada do modelo em produção | `7b1b901`, `analise/importacao.py` |

## 4. Riscos e pendências (por custo/benefício)

1. **P0: restaurar ou retreinar os pesos.** Se houver backup do `model.safetensors`, copiar para `models/bertimbau/`. Se não houver: `uv run manage.py treinar_bertimbau --epocas 1 --batch 32` (~46 min). Isso desbloqueia a API e o item 2.
2. **P1: regravar `metricas.json` com os três degraus.** Comando: `uv run manage.py avaliar --modelos lexico classico bertimbau --salvar`. Fecha a matriz do BERTimbau e o McNemar completo, e o front passa a mostrar o degrau 3.
3. **P1: congelar o split.** Qualquer conversa rotulada nova (a `amostra` já é uma; um upload com `rotulo` também seria) reembaralha o teste, porque o split é `shuffle` sobre todos os IDs. Hoje o teste bateu por sorte. Opções: filtrar por `fonte in (b2w, olist)` em `avaliar` e em `treinar_bertimbau` (a flag `--fonte` já existe, mas aceita uma base só) ou apagar a conversa `amostra`.
4. **P2: medir o efeito do anonimizador.** Classificar uma amostra do teste com e sem `anonimizar_texto` e comparar o F1. Reviews quase não têm CPF ou e-mail, então o efeito esperado é pequeno. Mesmo assim, é mais uma diferença entre treino e uso.
5. **P2: testes não rodam.** `uv run manage.py test analise` falha com `ModuleNotFoundError: jwt`. O `pyjwt` está só em `requirements-docker.txt`, não no `pyproject.toml`. Correção: `uv add pyjwt`. Não é do módulo, mas bloqueia a verificação.
6. Seguem abertos os experimentos do doc: 2 épocas, `max_len` 256 e conjunto anotado pelo grupo com Kappa.
