# Módulo Backend

**Estado: funcional.** Django 6.1, app único `analise`, 4 endpoints implementados, importação
transacional, indicadores de sessão e a camada de avaliação. 26 testes passando.

Detalhes de design em [docs/ARQUITETURA.md](../ARQUITETURA.md); contratos em
[docs/API.md](../API.md). Este documento é o estado verificado e o que falta.

## Composição

| Arquivo | Linhas | Responsabilidade |
|---|---|---|
| `analise/views.py` | 99 | os 4 endpoints |
| `analise/importacao.py` | 104 | leitura e validação de CSV/JSON |
| `analise/avaliacao.py` | 67 | split por conversa, F1 macro, matriz, McNemar |
| `analise/models.py` | 42 | `Conversa`, `Mensagem`, constantes de rótulo/autor |
| `analise/classificador.py` | 29 | cache do modelo, classificação em lote |
| `analise/indicadores.py` | 28 | trajetória da conversa |
| `analise/urls.py` | 10 | roteamento |
| `analise/tests.py` | 186 | 26 testes |
| `management/commands/` | 196 | `importar_kaggle`, `importar_conversas`, `treinar_bertimbau`, `avaliar` |
| `AnalisadorDeSentimentos/` | 184 | settings, urls raiz, wsgi/asgi |

Total: 1.167 linhas de Python. Sem DRF, sem Celery, sem fila, sem microserviço.

## Modelo de dados

```
Conversa   id, origem_id, fonte, criada_em
           UNIQUE(fonte, origem_id)     → reimportar atualiza, não duplica

Mensagem   conversa(FK), ordem, autor, texto, enviada_em,
           rotulo_pred, score, rotulo_real
           UNIQUE(conversa, ordem)
           ordering = [conversa_id, ordem]
```

`autor ∈ usuario | atendente | sistema`. **Só mensagens de `usuario` são classificadas** —
sistema e atendente não representam o sentimento do cliente.

`rotulo_real` é referência (rating do dataset ou anotação); `rotulo_pred` + `score` são a saída
do modelo. Os dois coexistem: é o que permite avaliar sem reimportar.

Indicadores **não são persistidos** — calculados por consulta.

### Conteúdo real do banco (`db.sqlite3`, 16 MB)

| Fonte | Conversas |
|---|---|
| b2w | 36.000 |
| olist | 27.071 |
| amostra | 1 |
| atendimento-real | 1 |
| **total** | **63.073** |

| Campo | Distribuição |
|---|---|
| `rotulo_real` | positivo 24.001 · negativo 23.408 · neutro 15.664 · nulo 8 |
| `rotulo_pred` | positivo 1 · negativo 2 · **nulo 63.078** |

**O banco está praticamente sem predições.** As 63k mensagens foram importadas com o rótulo de
referência do dataset, mas nunca passaram pelo classificador — só as 3 mensagens das conversas
de teste manual. Consequência direta em `GET /api/metricas` (abaixo). Não é bug: nada no
código classifica em massa fora do `POST /api/upload`, e a avaliação usa `rotulo_real`, não
`rotulo_pred`.

## API

| Método | Rota | Escreve? |
|---|---|---|
| POST | `/api/upload` | sim — única rota que escreve |
| GET | `/api/conversas` | não |
| GET | `/api/conversas/<id>` | não |
| GET | `/api/metricas` | não |

### `POST /api/upload`

Recebe `multipart/form-data` com `arquivo` (CSV ou JSON UTF-8; formato decidido pela extensão)
e `fonte` opcional (padrão: nome do arquivo sem extensão).

Comportamento que importa:

- **Ou entra tudo, ou nada.** `importar()` é `@transaction.atomic`. Qualquer erro de esquema
  aborta o arquivo inteiro. Um CSV meio importado é pior que um erro.
- **Reimportar substitui.** Mesma `(fonte, origem_id)` → mensagens antigas apagadas e regravadas.
- **Classificação síncrona dentro da request**, e ela **reclassifica todas as conversas da
  `fonte`**, não só as do arquivo enviado. Enviar um arquivo com `fonte=b2w` dispararia a
  classificação de 36.000 mensagens dentro de uma request HTTP.
- 400 com `detalhes` (até 20 itens) na validação; 400 em não-UTF-8 e JSON malformado.

### `GET /api/conversas`

`fonte` filtra, `limite` corta em 500 (padrão 100). `total` é a contagem **sem** limite.
`prefetch_related("mensagens")` e indicadores calculados em Python.

### `GET /api/conversas/<id>`

Conversa completa com todas as mensagens em ordem, inclusive sistema e atendente. 404 com
`{"erro": "conversa não encontrada"}`.

### `GET /api/metricas`

Duas coisas distintas na mesma resposta:

- `distribuicao` + `total_conversas`: agregados **ao vivo** do banco sobre `rotulo_pred`.
- `modelos`: conteúdo bruto de `models/metricas.json`, da última execução de
  `avaliar --salvar`. `null` se o arquivo não existe. Não recalcula — avaliação é offline.

**Estado real da resposta hoje:**

```json
{"distribuicao": {"negativo": 2, "positivo": 1}, "total_conversas": 63073,
 "modelos": {"n_teste": 12615, "modelos": ["lexico", "classico"], "mcnemar": ["lexico×classico"]}}
```

O exemplo em [docs/API.md](../API.md) mostra `{"positivo": 24001, ...}` — esses são os números
de `rotulo_real`, não de `rotulo_pred`. A documentação está adiantada em relação ao banco.

## Indicadores de sessão

Calculados sobre a sequência de `rotulo_pred` das mensagens de usuário, em ordem:

| Indicador | Definição |
|---|---|
| `abertura` | rótulo da primeira mensagem do usuário |
| `encerramento` | rótulo da última |
| `delta` | valor(encerramento) − valor(abertura), com positivo=1, neutro=0, negativo=−1 |
| `trocas_de_polaridade` | inversões de sinal, **ignorando neutros** |
| `pior_momento` | posição (1-based) da mensagem mais negativa |
| `n_mensagens` | mensagens de usuário com rótulo |

Neutros são descartados na contagem de trocas de propósito: `negativo → neutro → negativo` é a
mesma insatisfação continuando, não duas viradas. Sem nenhum rótulo, devolve `None`.

**Nunca foram avaliados.** Não existe referência anotada contra a qual medir — precisa de
conversa real com CSAT ou anotação manual.

## Cache do modelo

`classificador.modelo()` é `@lru_cache(maxsize=2)`, padrão `bertimbau`. Carregar o BERTimbau
custa segundos e o processo atende várias requisições; `maxsize=2` permite alternar entre dois
degraus sem recarregar nem segurar três modelos em RAM.

## Comandos de gerenciamento

| Comando | O quê |
|---|---|
| `importar_kaggle --dir <pasta> --bases b2w olist --por-classe 12000 --seed 42` | dataset público → esquema do projeto; idempotente por fonte |
| `importar_conversas <arquivo> --fonte <nome>` | CSV/JSON do usuário → banco |
| `treinar_bertimbau --epocas 1 --batch 32` | fine-tune offline, salva em `models/bertimbau/` |
| `avaliar --modelos lexico classico bertimbau --salvar` | avalia os degraus no mesmo teste e grava `models/metricas.json` |

## Testes

`uv run manage.py test analise` — **26 testes** em `analise/tests.py`, cobrindo:

| Área | Testes |
|---|---|
| Importação | 5 — ordenação, reimportar sem duplicar, arquivo inválido não grava nada, ordem repetida, JSON |
| Léxico | 2 — polaridade, negação inverte |
| Avaliação | 6 — split não vaza conversa, split determinístico, F1 e matriz, McNemar (3 casos) |
| Registro de modelos | 3 — três degraus presentes, modelo desconhecido, interface comum |
| Indicadores | 3 — trajetória, neutro no meio não conta, sem rótulo devolve `None` |
| Endpoints | 7 |

O BERTimbau **não é instanciado** nos testes (baixaria 436 MB de pesos); a checagem de
interface é estática. `docs/ARQUITETURA.md` diz "31 testes" — está desatualizado.

## Decisões deliberadas (não são dívida acidental)

- **`@csrf_exempt` no upload.** App local, single-user, sem autenticação. Religar quando entrar
  auth ou dado real de empresa.
- **`DEBUG = True` e `SECRET_KEY` de desenvolvimento.** Não é deploy.
- **SQLite.** Postgres só quando houver dado real em volume.
- **Sem paginação por cursor.** Corte em 500; cursor entra quando doer.
- **Inferência síncrona na request.** Vira job se um upload grande travar — não antes.

## Riscos e pendências do backend

| # | Item | Gravidade |
|---|---|---|
| 1 | Upload reclassifica a `fonte` inteira dentro da request — `fonte=b2w` classificaria 36.000 mensagens sincronamente. É onde a decisão "vira job se travar" será cobrada. | alta |
| 2 | Banco sem predições: `/api/metricas` serve dado vazio e a tela de dashboard não tem o que mostrar | alta |
| 3 | `metricas.json` sem o BERTimbau — o comparativo servido pela API é incompleto | alta |
| 4 | Sem CORS configurado; bloqueia o frontend Next | alta (quando o front começar) |
| 5 | `GET /api/conversas` calcula indicadores em Python sobre até 500 conversas com prefetch — pesa; materializar só quando doer | média |
| 6 | Sem filtro por rótulo na listagem, embora a spec peça na tela 2 | média |
| 7 | Docs divergentes do código (contagem de testes, exemplo de `/api/metricas`, caminho do script de treino) | baixa |
