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
| [docs/API.md](docs/API.md) | Os 4 endpoints, formatos de request/response |

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
uv run manage.py runserver
```

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
| `manage.py avaliar --modelos lexico classico bertimbau --salvar` | Avalia os degraus no mesmo teste e grava `models/metricas.json` |

## Testes

```bash
uv run manage.py test analise
```

26 testes cobrindo importação, léxico, split/McNemar, indicadores e os 4 endpoints. O BERTimbau
não é instanciado nos testes (baixaria pesos); a checagem de interface é estática.

## Stack

Python 3.12, Django 6.1, scikit-learn 1.9, PyTorch 2.13 (backend MPS no Apple Silicon),
transformers 5.16, SQLite. Dependência de dev: `kagglehub` para baixar o dataset.
