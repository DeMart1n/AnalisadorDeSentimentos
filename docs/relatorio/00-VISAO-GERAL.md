# Relatório do Sistema — Visão Geral

Data do levantamento: 2026-09-09. Base: código em `main` (`a1ac1ae`), `db.sqlite3` local e
`models/metricas.json`.

Projeto: classificação de sentimento (`positivo | negativo | neutro`) por mensagem em conversas
de atendimento, com indicadores de trajetória da conversa. Entregável duplo: um web app
(Django + Next) e um artigo científico sobre o custo/benefício de cada degrau de modelo.

## Módulos

| Módulo | Documento | Estado |
|---|---|---|
| Frontend | [01-FRONTEND.md](01-FRONTEND.md) | **não iniciado** (0 arquivos) |
| Backend | [02-BACKEND.md](02-BACKEND.md) | **funcional** — 4 endpoints, importação, indicadores, 26 testes |
| Modelo IA | [03-MODELO-IA.md](03-MODELO-IA.md) | **concluído para v1** — 3 degraus treinados e comparados por McNemar |

## Mapa em uma tela

```
[ Next.js — NÃO EXISTE ]
        ↓ HTTP/JSON
Django (app único `analise`)
  views.py ──> importacao.py    CSV/JSON → banco, transação atômica
           ──> classificador.py cache lru do modelo, inferência síncrona
           ──> indicadores.py   trajetória da conversa, calculada por consulta
           ──> avaliacao.py     split por conversa, F1 macro, McNemar
                    ↓
              modelos/  lexico → classico → bertimbau
                    ↓
      SQLite (db.sqlite3, 16 MB)  +  models/bertimbau/ (436 MB)
```

## Números do projeto

| | |
|---|---|
| Linhas de Python (app + projeto) | 1.167 |
| Arquivos de frontend | 0 |
| Endpoints | 4 |
| Testes | 26, todos em `analise/tests.py` |
| Conversas no banco | 63.073 |
| Modelos comparados | 3 |
| F1 macro do melhor degrau | 0,764 (BERTimbau, 1 época) |

## Progresso contra a spec

A ordem de execução da [SPEC.md](../../SPEC.md) §9:

| # | Passo | Estado |
|---|---|---|
| 1 | Importação + models + carga da base pública | ✅ |
| 2 | Baselines léxico e TF-IDF com avaliação | ✅ |
| 3 | Fine-tune BERTimbau + McNemar | ✅ |
| 4 | API dos 4 endpoints | ✅ |
| 5 | Frontend Next, 4 telas | ❌ não iniciado |
| 6 | Indicadores de sessão na UI | ⚠️ calculados no backend, sem UI |
| 7 | Artigo | ❌ não iniciado |

## Pendências transversais (ordenadas por custo/benefício)

1. **Reexecutar `avaliar --modelos lexico classico bertimbau --salvar`.** O `metricas.json` em
   disco tem só léxico e clássico; a API serve um comparativo incompleto e a matriz de confusão
   do BERTimbau não existe em lugar nenhum de forma reprodutível. Custo: uma execução.
2. **Reclassificar o banco.** Das 63.078 mensagens gravadas, apenas **3** têm `rotulo_pred`.
   `GET /api/metricas` devolve hoje `{"negativo": 2, "positivo": 1}` — detalhe em
   [02-BACKEND.md](02-BACKEND.md).
3. **Frontend.** É o bloqueio inteiro do passo 5–6.
4. **Conjunto de teste anotado pelo grupo.** Único item que ataca a limitação central do dado
   (ver [03-MODELO-IA.md](03-MODELO-IA.md) §Limitações). O mais caro.

## Divergências entre documentação e código encontradas neste levantamento

| Onde | Documentado | Real |
|---|---|---|
| `docs/ARQUITETURA.md` | "31 testes" | 26 (`grep -c "def test_"`) |
| `docs/API.md`, exemplo de `/api/metricas` | distribuição com 63k mensagens | 3 mensagens classificadas; o número documentado é o de `rotulo_real`, não de `rotulo_pred` |
| `SPEC.md` §3 | treino em `scripts/train.py` | é comando de gerenciamento `treinar_bertimbau` |
