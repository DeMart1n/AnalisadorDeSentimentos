# Modelo IA: relatório técnico (06/10 a 14/10/2026)

Documentos-fonte conferidos: `docs/relatorio/03-MODELO-IA.md` (polaridade) e
`docs/relatorio/04-MODELO-EMOCOES.md` (emoções), contra o código da branch
`feat/emocoes-e-correcoes` (`b987f52`), `models/metricas.json`, `models/metricas_emocoes.json`, o
disco e o `db.sqlite3`.

## 1. Estado atual

- **Polaridade: os três degraus estão treinados e medidos de novo.** O BERTimbau foi retreinado em
  13/10 (1 época, 71,1 min em MPS) e teve F1 macro **0,768**. O `metricas.json` agora traz os três
  degraus, as matrizes e os três pares do McNemar.
- **O bug "a IA dá um resultado diferente a cada vez" foi resolvido no código.** Faltavam os pesos
  do BERTimbau. Sem eles, o `origin/main` classificava com a cabeça aleatória do modelo base.
  Agora o modelo levanta `ModeloNaoTreinado`, e `/conversas/analisar` responde 503.
- **Emoções:** não houve treino novo na semana. As métricas são as da configuração A (05/10): F1
  macro 0,448 no BRIGHTER e 0,643 no GoEmotions-PT. O código dos gráficos e o histórico, que
  estavam soltos, foram commitados.
- **Testes:** 160, todos passando. A cobertura do app foi de 73% para 95%, e a parte de IA ficou
  praticamente toda em 100%.
- **Não andou:** o PR para a `main` não foi aberto (o `gh` está sem login). Não há chat real
  anotado. Os pesos continuam só na máquina do Cauã.

## 2. O que foi feito na semana

| Commit / artefato | O quê |
|---|---|
| diagnóstico (13/10) | O `origin/main` não tinha a guarda `a65100e`. Como `models/bertimbau/` está no `.gitignore`, quem clonava o repositório classificava com a cabeça aleatória do BERT base, e o resultado mudava a cada reinício do processo. O frontend sempre envia `modelo: 'bertimbau'`, então não havia troca de modelo. |
| `models/bertimbau/model.safetensors` (13/10 14:29) | Retreino com `treinar_bertimbau --fonte b2w olist --epocas 1`: 50.456 de treino, 1.577 passos, 71,1 min |
| `models/metricas.json` (13/10 14:36), `dfd892a` | `avaliar --fonte b2w olist --salvar` com os 3 degraus no split congelado |
| `e924365`, `af3cb7e` | Cherry-pick da guarda de pesos e do `pyjwt` sobre o `origin/main` |
| `979c312` | Exceção `ModeloNaoTreinado`; `analisar` → 503; `STANDARD_MODEL` passa a ter `bertimbau` como padrão (antes era `None`, e a requisição dava 400); `openapi.yaml` documentado |
| `558a8e5` | 86 testes novos em `test_modelos.py`, `test_comandos.py` e `test_api_analise.py`. Rodam sem rede, com um BERT minúsculo gerado num diretório temporário |
| `4fcede7` | 6 bugs que os testes encontraram, cada um com um teste de regressão (os 11 falham no código antigo) |
| `48039c4` | Emoções: histórico de perda e F1 por época, matrizes, `.npz` de probabilidades, `scripts/graficos_emocoes.py` e 9 PNGs |
| `82f0f6f` | Relatório semanal de 05/10 commitado |
| `fa18163`, `b987f52` | Merge do `origin/main` (front-end #4) e da `fix/bugs-ia`. Os testes de comandos passaram a usar um split temporário |

### Polaridade (`models/metricas.json`, teste 12.615)

| Degrau | F1 macro | F1 neutro | Acurácia |
|---|---|---|---|
| Léxico | 0,489 | 0,321 | 0,499 |
| TF-IDF + LR | 0,735 | 0,559 | 0,756 |
| BERTimbau (1 época) | **0,768** | **0,605** | **0,789** |

| Classe | Precisão | Recall | F1 |
|---|---|---|---|
| positivo | 0,85 | 0,81 | 0,83 |
| negativo | 0,85 | 0,89 | 0,87 |
| neutro | 0,60 | 0,61 | 0,60 |

Discordâncias no McNemar entre clássico e BERTimbau: 603 mensagens só o clássico acerta, 1.024 só
o BERTimbau acerta, p = 1,2e-25.

### Bugs corrigidos (`4fcede7`)

| Onde | Antes | Depois |
|---|---|---|
| `importar_kaggle` | Um CSV sem `review_text`/`rating` válidos apagava a base e gravava 0 reviews | `CommandError`, sem alterar nada |
| `importar_kaggle` | `rating` não numérico derrubava o comando | A linha é ignorada |
| `importar_conversas` | Traceback cru para arquivo inexistente, fora de UTF-8 ou com JSON malformado | `CommandError` |
| `avaliar`, `treinar_bertimbau` | Treino vazio quebrava dentro do sklearn/torch | `CommandError` |
| `views.py` (4 views) | O `except JSONDecodeError` vinha depois de `ValueError` e era inalcançável | Ordem invertida |
| `GET /conversas?limite=` | `abc` ou `-1` davam 500 | 400 |
| `Classico.termos_por_classe` | Com 2 classes, atribuía os termos à classe errada | Corrigido |

## 3. Conferência dos documentos-fonte

### `03-MODELO-IA.md`

| Afirmação | Status | Realidade | Fonte |
|---|---|---|---|
| Léxico com 118 linhas | confere | 118 | `analise/modelos/lexico_pt.txt` |
| max_len 128, batch 32, lr 2e-5, OneCycle com pct_start 0,1 | confere | Idem | `bertimbau.py:20,51,70` |
| "Épocas: 2 no código / 1 no resultado atual" | confere | Default 2; o retreino de 13/10 usou `--epocas 1` | `treinar_bertimbau.py:14` |
| b2w 36.000 / olist 27.071 | confere | Idem | `db.sqlite3`, consulta por fonte |
| Split 50.456 / 12.615, suporte 4.689 / 4.785 / 3.141 | confere | Idem | saída de `avaliar` (13/10) |
| Léxico 0,489 / 0,321 / 0,499 | confere | 0,4885 / 0,321 / 0,499 | `metricas.json` |
| TF-IDF 0,735 / 0,559 / 0,756 | confere | 0,7345 / 0,559 / 0,756 | `metricas.json` |
| BERTimbau 0,764 / 0,600 / 0,790, "46 min" | **diverge** | Retreino: **0,768 / 0,605 / 0,789**, **71,1 min** (com a máquina dividida com outras tarefas) | `metricas.json`; log do treino |
| "+2,9 pontos" do TF-IDF para o BERTimbau | **diverge** | +3,4 pontos (0,7345 → 0,7683) | idem |
| 436 MB de pesos | confere | 435.725.300 bytes | `models/bertimbau/model.safetensors` |
| McNemar léxico × clássico: 1.343 / 4.584 | **diverge (pouco)** | 1.343 / **4.582** (split congelado) | `metricas.json` |
| "A matriz do BERTimbau não está no `metricas.json`" e "contagens com o BERTimbau voltam quando reexecutar" | **resolvida** | A matriz e os três pares estão no arquivo | `metricas.json` |
| Sem pesos, `prever` levanta `RuntimeError` | **diverge** | Agora levanta `ModeloNaoTreinado` (subclasse de `RuntimeError`), e a API responde 503 | `modelos/__init__.py`, `views.py` |
| Pendência 1: "Reavaliar e regravar `metricas.json`" | **resolvida** | Feito em 13/10 | `dfd892a` |

### `04-MODELO-EMOCOES.md`

| Afirmação | Status | Realidade | Fonte |
|---|---|---|---|
| Cabeçalho: "o modelo ainda não foi treinado de verdade" | **diverge** (já apontado em 05/10, segue sem correção) | Treinado em 05/10 | `models/emocoes/model.safetensors` (05/10 20:54) |
| Métricas da seção 5 | confere | Idem ao relatório de 05/10; sem treino novo | `metricas_emocoes.json` (05/10 20:55) |
| Percentuais de neutro → raiva/alegria | **diverge (pouco)** (já apontado em 05/10) | Por mensagem: sem emoção 24,7%; raiva 38,6% / 43,9% | `coocorrencia` ÷ `neutro_suporte` |
| Gráficos e histórico | **agora commitados** | — | `48039c4` |
| Rótulos de emoção no banco | não verificável no doc | 25.248 linhas em `RotuloEmocao` | `db.sqlite3` |

### Pendências do relatório de 05/10

| Pendência | Status |
|---|---|
| 1. Commitar o código e os resultados das emoções | **resolvida** (`48039c4`) |
| 2. Corrigir o cabeçalho e os percentuais do `04-MODELO-EMOCOES.md` | aberta |
| 3. Neutro e raiva: remapear raiva e atenuar o `pos_weight` | aberta |
| 4. Limiares só no dev do BRIGHTER | aberta |
| 5. P0 da polaridade: retreinar o BERTimbau | **resolvida** (13/10) |
| 6. Chat real | aberta |

## 4. Riscos e pendências (por custo/benefício)

1. **Abrir o PR para a `main`.** O código está pronto e enviado; falta o login.
   `gh auth login`, depois `gh pr create --base main --head feat/emocoes-e-correcoes`.
2. **Distribuir os pesos para a equipe.** Sem eles, a API agora responde 503 em vez de devolver
   um resultado aleatório, mas continua sem classificar. É preciso compartilhar `models/bertimbau/`
   (415 MiB) e `models/emocoes/` por Drive ou release, ou cada pessoa roda
   `uv run manage.py treinar_bertimbau --fonte b2w olist --epocas 1` (~70 min).
3. **Fechar as branches `fix/pesos-bertimbau` e `fix/bugs-ia`** sem merge. O conteúdo delas já
   está na `feat/emocoes-e-correcoes`, e elas carregam um `.gitignore` quebrado (`.env.coverage*`).
4. **Atualizar os docs** (edição de texto): os números do BERTimbau no `03` e o cabeçalho e os
   percentuais no `04`.
5. **Ligar as emoções à API.** O modelo existe, mas nenhuma rota o usa.
6. **Neutro e raiva nas emoções** (retreino, ~33 min): pendência 3 de 05/10.
7. **Chat real anotado.** Todos os números vêm de reviews e de texto traduzido. Sem conversa de
   atendimento anotada, não existe medida do caso de uso. Precisa de um export de conversas;
   depois, `importar_conversas` e `anotacao exportar`.
