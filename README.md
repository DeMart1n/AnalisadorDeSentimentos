# Análise de Sentimentos em Atendimentos via Chat

Classificação de sentimento (`positivo | negativo | neutro`) por mensagem em conversas de
atendimento, com indicadores de trajetória da conversa inteira. Backend Django + API JSON,
três modelos comparados estatisticamente (léxico → TF-IDF → BERTimbau fine-tuned).

O objetivo final é um artigo científico sobre o custo/benefício de cada degrau. O web app é a
camada de apresentação em cima do resultado.

## Documentação

| Documento | Conteúdo |
|---|---|
| [SPEC.md](SPEC.md) | Escopo travado, decisões, riscos assumidos |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Estrutura do código, modelo de dados, fluxo |
| [docs/TREINAMENTO.md](docs/TREINAMENTO.md) | Dados, pré-processamento, hiperparâmetros, reprodução |
| [docs/RESULTADOS.md](docs/RESULTADOS.md) | Métricas, matrizes de confusão, McNemar, análise de erro |
| [docs/API.md](docs/API.md) | Os endpoints REST, formatos de request/response e autenticação |
| [docs/openapi.yaml](docs/openapi.yaml) | Especificação OpenAPI 3.1 servida com interface interativa **Scalar** em `/api/docs` |
| [docs/relatorio/](docs/relatorio/00-VISAO-GERAL.md) | Relatório do sistema por módulo: [frontend](docs/relatorio/01-FRONTEND.md), [backend](docs/relatorio/02-BACKEND.md), [modelo IA](docs/relatorio/03-MODELO-IA.md) |

## Estado atual

Passos 1–3 da spec (dados, escada de modelos, avaliação) estão concluídos. Passo 4 (API) está
implementado. Passos 5–7 (frontend Next, indicadores na UI, artigo) ainda não.

| Degrau | F1 macro | F1 neutro | Acurácia |
|---|---|---|---|
| 1. Léxico | 0,488 | 0,32 | 0,50 |
| 2. TF-IDF + LR | 0,735 | 0,56 | 0,76 |
| 3. BERTimbau (1 época) | **0,764** | 0,60 | 0,79 |

Base: b2w + olist, 63.071 reviews, conjunto de teste com 12.615 exemplos. Detalhes em
[docs/RESULTADOS.md](docs/RESULTADOS.md).

## Setup

```bash
uv sync
uv run manage.py migrate
```

O banco (`db.sqlite3`, 16 MB) e os pesos do modelo (`models/bertimbau/`, 436 MB) **não estão
no repositório** — são artefatos reconstrutíveis e o segundo passa do limite do GitHub. Para
gerar os dois do zero, veja [docs/TREINAMENTO.md](docs/TREINAMENTO.md).

## Uso rápido

```bash
uv run manage.py exportar_onnx   # uma vez por treino: gera models/bertimbau/model.int8.onnx
redis-server &
uv run manage.py runserver
uv run celery -A AnalisadorDeSentimentos worker --pool=solo -l info   # 1 terminal por worker
```

A classificação (`POST /api/conversas/analisar`) roda nos workers Celery, não no processo web.
Cada worker é um processo com o BERTimbau int8 via ONNX Runtime (~330 MB, sem torch). Para ter
mais vazão, suba mais workers (`docker compose up --scale worker=N`) e ajuste
`ONNX_THREADS` ≈ núcleos ÷ workers. Com vários workers, use Postgres/RDS (`DATABASE_HOST`): o
SQLite trava o arquivo inteiro a cada escrita.

Acesse a documentação interativa em: **http://localhost:8000/api/docs** (Scalar) ou a especificação em **http://localhost:8000/api/openapi.yaml**.

```bash
curl -F arquivo=@conversas.csv -F fonte=piloto http://localhost:8000/api/upload
curl http://localhost:8000/api/conversas
curl http://localhost:8000/api/conversas/1
curl http://localhost:8000/api/metricas
```

## Comandos de gerenciamento

| Comando | O quê |
|---|---|
| `manage.py importar_kaggle --dir <pasta> --bases b2w olist` | Converte o dataset público para o esquema do projeto |
| `manage.py importar_conversas <arquivo> --fonte <nome>` | Importa CSV/JSON de conversas no esquema do projeto |
| `manage.py treinar_bertimbau --epocas 2 --batch 32` | Fine-tune no conjunto de treino, salva em `models/bertimbau/` |
| `manage.py exportar_onnx` | Exporta o BERTimbau treinado para `model.onnx` (fp32) e `model.int8.onnx` (usado pelos workers) |
| `manage.py avaliar --modelos lexico classico bertimbau --salvar` | Avalia os degraus no mesmo teste e grava `models/metricas.json` |

## Testes

```bash
uv run manage.py test analise
```

26 testes cobrindo importação, léxico, split/McNemar, indicadores e os 4 endpoints. O BERTimbau
não é instanciado nos testes (baixaria pesos); a checagem de interface é estática.

## Stack

Python 3.12, Django 6.1, scikit-learn 1.9, PyTorch 2.13 (backend MPS no Apple Silicon),
transformers 5.16 (só treino), ONNX Runtime 1.31 (inferência), Celery 5.6 + Redis,
SQLite local ou Postgres (RDS). Dependência de dev: `kagglehub` para baixar o dataset.
