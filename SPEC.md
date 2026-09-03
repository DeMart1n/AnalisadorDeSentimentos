# Análise de Sentimentos em Atendimentos via Chat — Spec e Escopo

Status: v1 (2026-08-27). Baseado na Proposta Inicial v2.

## 1. Decisões travadas

| Tema | Decisão |
|---|---|
| Entregável | Web app: backend Django (API) + frontend Next.js. Artigo científico depois, sobre os resultados. |
| Dados | `fredericods/ptbr-sentiment-analysis-datasets` (Kaggle), bases **b2w + olist**. Dados reais de empresa ficam como evolução futura. |
| Classe neutra | A base é binária (rating 3 descartado pelo autor). Recuperamos rating 3 como neutro. |
| Modelo principal | Fine-tune do BERTimbau. |
| Baselines | Léxico e TF-IDF+regressão logística — obrigatórios como piso de comparação (custo baixo, exigidos pelo artigo). |
| LLM zero-shot | Fora do escopo v1. |

## 2. Escopo

### Dentro
- Ingestão de conversas em CSV/JSON com esquema fixo (ver §4).
- Limpeza: separar mensagens automáticas/sistema das do usuário; só as do usuário entram na classificação.
- Classificação por mensagem em `positivo | negativo | neutro`.
- Indicadores por conversa: sentimento de abertura, de encerramento, delta, nº de trocas de polaridade, ponto mais negativo.
- Avaliação: F1 macro + matriz de confusão, split por conversa, McNemar entre modelos.
- Web app: upload de arquivo, lista de conversas, timeline de sentimento de uma conversa, dashboard agregado.

### Fora (v1)
- Criar chatbot.
- Negociação com empresa, script de anonimização, verificação de PII — só entra se e quando houver dado real.
- LLM zero-shot/few-shot.
- Multiusuário, autenticação, multi-tenant. App roda local/single-user.
- Retreino pela interface. Treino é offline, por script.
- Rótulo indireto via CSAT/NPS (depende de dado real).

### Fora agora, previsto depois
- Rota de dados reais: anonimização na empresa → verificação de PII na entrega → validação da trajetória contra CSAT.
- Anotação manual do grupo com guia de anotação e Kappa, para o conjunto de teste de domínio.

## 3. Arquitetura

```
next (frontend)  →  django REST (api)  →  sqlite
                          ↓
                   modelo salvo em disco (transformers)
```

- Um app Django: `analise`. Sem microserviço, sem Celery, sem fila. Inferência síncrona na request; se um upload grande travar, aí sim vira job.
- Modelo carregado uma vez no processo, em cache de módulo.
- SQLite. Migrar para Postgres só se houver dado real em volume.
- Treino fora do Django: `scripts/train.py`, salva em `models/bertimbau/`.

## 4. Modelo de dados

```
Conversa   id, origem_id, fonte, criada_em
Mensagem   conversa_fk, ordem, autor(usuario|atendente|sistema), texto, enviada_em,
           rotulo_pred, score, rotulo_real (nullable)
```

Indicadores de sessão são calculados por consulta, não persistidos. Se ficar lento, materializa depois.

Formato de importação aceito (CSV ou JSON):
`conversa_id, ordem, autor, texto, timestamp[, rotulo]`

## 5. API

| Método | Rota | O quê |
|---|---|---|
| POST | `/api/upload` | Recebe CSV/JSON, cria conversas, classifica, devolve resumo |
| GET | `/api/conversas` | Lista com indicadores da sessão |
| GET | `/api/conversas/<id>` | Mensagens com rótulo e score |
| GET | `/api/metricas` | Distribuição geral + comparação entre modelos |

## 6. Telas (Next)

1. **Upload** — dropzone, resultado da importação e erros de esquema.
2. **Conversas** — tabela com abertura, encerramento, delta, trocas de polaridade; filtro por rótulo.
3. **Conversa** — timeline das mensagens coloridas por sentimento, ponto mais negativo marcado.
4. **Dashboard** — distribuição de sentimentos, comparação dos modelos (F1 macro, matriz de confusão).

## 7. Modelos e avaliação

Escada implementada, do piso ao alvo:

1. **Léxico** — dicionário de polaridade em PT. Sem treino. Piso: modelo treinado que não supera isso indica erro no processo.
2. **TF-IDF + regressão logística** — rápido, inspecionável, referência para o transformer.
3. **BERTimbau fine-tuned** — `neuralmind/bert-base-portuguese-cased`, alvo do projeto.

Regras de avaliação, valem para os três:
- Split **por conversa**, nunca por mensagem — mensagens da mesma sessão vazam informação.
- Métrica principal: **F1 macro**. Acurácia não conta: a base é desbalanceada em neutro.
- Comparação entre modelos por **McNemar**, não por diferença de número.
- Mesmo conjunto de teste para todos.

## 8. Riscos assumidos

- **Domínio.** b2w e olist são review de e-commerce pós-compra, não diálogo de atendimento. A queda ao aplicar em conversa é esperada — vira resultado do artigo, não bug.
- **O neutro treinado não é o neutro do caso de uso.** Rating 3 é avaliação morna (tem sentimento, é ambivalente); o neutro que precisamos detectar em atendimento é ausência de sentimento ("meu pedido é o 4512"). Limitação a declarar no artigo e a principal razão para o conjunto de teste anotado pelo grupo.
- **Sem conjunto de teste de domínio.** Enquanto não houver conversa real anotada pelo grupo, os números medem a base pública, não o caso de uso. Registrar isso em todo relatório.
- **Neutro domina.** Provável colapso do modelo na classe majoritária; tratar com class weights antes de partir para técnicas mais caras.

## 8.1 Resultados da escada (b2w + olist, 63k reviews, teste 12.615)

| degrau | F1 macro | F1 neutro | acurácia |
|---|---|---|---|
| 1. léxico | 0.488 | 0.32 | 0.50 |
| 2. TF-IDF + LR | 0.735 | 0.56 | 0.76 |
| 3. BERTimbau (1 época) | **0.764** | 0.60 | 0.79 |

McNemar: todos os pares com p < 0.0001 — as três diferenças se sustentam estatisticamente.

Treino do BERTimbau: 1 época, batch 32, max_len 128, lr 2e-5, MPS em M4 Air 16GB, 46 min.

Leitura: o transformer supera o TF-IDF, mas por 2,9 pontos de F1 macro — muito menos que os
24,7 pontos entre léxico e TF-IDF. O ganho concentra-se no neutro (0.56 → 0.60), que segue
sendo a classe difícil nos três degraus. Antes de buscar arquitetura maior, testar 2 épocas
e max_len maior; o custo/benefício do degrau 3 é o resultado mais interessante para o artigo.

## 9. Ordem de execução

1. Esquema de importação + models + comando de carga da base pública.
2. Baseline léxico e TF-IDF, com a avaliação já pronta (split por conversa, F1 macro).
3. Fine-tune BERTimbau, comparação por McNemar.
4. API dos 4 endpoints.
5. Frontend Next, as 4 telas.
6. Indicadores de sessão.
7. Artigo.

Passos 1–3 entregam o resultado científico sozinhos. O web app é a camada de apresentação em cima disso.
