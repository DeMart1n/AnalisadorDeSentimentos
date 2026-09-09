# Módulo Frontend

**Estado: não iniciado.** Não existe nenhum arquivo de frontend no repositório — nem projeto
Next, nem `package.json`, nem template Django. `TEMPLATES.DIRS` está vazio e `APP_DIRS=True`
sem nenhum diretório `templates/`. A única interface hoje é `curl` contra a API e o admin do
Django (registrado vazio em `analise/admin.py`).

Este documento registra o que está **especificado** e o que precisa ser decidido antes de
começar, não o que existe.

## O que a spec define

Stack: **Next.js**, consumindo a API JSON do Django ([SPEC.md](../../SPEC.md) §3 e §6).

### As 4 telas

| # | Tela | Consome | Conteúdo |
|---|---|---|---|
| 1 | Upload | `POST /api/upload` | dropzone; resultado da importação; lista de erros de esquema |
| 2 | Conversas | `GET /api/conversas` | tabela com abertura, encerramento, delta, trocas de polaridade; filtro por rótulo |
| 3 | Conversa | `GET /api/conversas/<id>` | timeline das mensagens coloridas por sentimento, pior momento marcado |
| 4 | Dashboard | `GET /api/metricas` | distribuição de sentimentos; comparação dos modelos (F1 macro, matriz de confusão) |

Contratos completos de request/response em [docs/API.md](../API.md).

### Fora de escopo v1

Autenticação, multiusuário, multi-tenant, retreino pela interface. O app roda local e
single-user — é a premissa que justifica o `@csrf_exempt` no upload.

## Bloqueios reais antes da primeira linha de código

1. **CORS.** O backend não tem `django-cors-headers` nem `CORS_ALLOWED_ORIGINS`. Next em
   `:3000` chamando Django em `:8000` é cross-origin e vai falhar. Duas saídas: instalar o
   pacote, ou usar o proxy de rewrites do Next (`next.config.js`) e evitar a dependência.
2. **CSRF no upload.** Hoje está desligado, então o upload funciona sem token. Se a decisão for
   religar CSRF, o frontend precisa buscar e enviar o cookie — decidir antes, não depois.
3. **O dashboard não tem dado para mostrar.** `GET /api/metricas` devolve hoje
   `distribuicao: {"negativo": 2, "positivo": 1}` e um comparativo de modelos sem o BERTimbau.
   Construir a tela 4 contra isso é construir contra um mock. Reclassificar o banco e regravar
   `metricas.json` são pré-requisitos da tela 4, não polimento posterior.
4. **Paginação.** `GET /api/conversas` corta em 500 sem cursor, sobre 63.073 conversas. A tela 2
   precisa de filtro por `fonte` desde o início ou lista as primeiras 500 de `b2w` e nada mais.
5. **Filtro por rótulo é da spec mas não existe na API.** A tela 2 pede "filtro por rótulo"; a
   API só aceita `fonte` e `limite`. Ou filtra no cliente (sobre no máximo 500 itens, aceitável)
   ou entra um query param novo no backend.

## Formato de resposta a considerar ao desenhar as telas

- `indicadores` vem `null` quando a conversa não tem mensagem de usuário classificada — hoje é
  o caso de praticamente todas. A tabela precisa de estado vazio, não de `undefined`.
- `score` é a probabilidade da classe escolhida, entre 0 e 1 para clássico e BERTimbau, mas no
  léxico é `abs(soma)` dos pesos — **não é probabilidade e não é comparável entre modelos**.
  Não renderizar como percentual sem saber qual modelo produziu.
- A matriz de confusão vem sempre na ordem `positivo, negativo, neutro`, linhas = verdadeiro.
- Erros da API têm a forma `{"erro": "...", "detalhes": [...]}`, com `detalhes` só na validação
  de arquivo e cortado em 20 itens.

## Recomendação de sequência

Telas 1 → 3 → 2 → 4. Upload e conversa individual funcionam com o dado que existe hoje; a
tabela precisa de filtro; o dashboard precisa dos dois pré-requisitos do item 3 acima.
