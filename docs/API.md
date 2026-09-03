# API

JSON puro sobre Django views. Sem DRF, sem autenticação, sem paginação por cursor — app local
single-user. Base: `http://localhost:8000/api`.

Todas as respostas de erro têm a forma `{"erro": "...", "detalhes": [...]}`, com `detalhes`
apenas quando há uma lista de problemas (validação de arquivo).

---

## `POST /api/upload`

Recebe um arquivo, importa, classifica as mensagens de usuário e devolve o resumo.
`multipart/form-data`. **CSRF desativado** (`@csrf_exempt`) — ver ARQUITETURA.md.

| Campo | Obrigatório | Descrição |
|---|---|---|
| `arquivo` | sim | CSV ou JSON em UTF-8. O formato é decidido pela extensão `.json` |
| `fonte` | não | Identificador da base. Padrão: nome do arquivo sem extensão |

### Esquema do arquivo

Colunas do CSV / chaves do objeto JSON (o JSON deve ser uma **lista** de objetos):

| Campo | Obrigatório | Formato |
|---|---|---|
| `conversa_id` | sim | qualquer string |
| `ordem` | sim | inteiro, único dentro da conversa |
| `autor` | sim | `usuario` \| `atendente` \| `sistema` |
| `texto` | sim | |
| `timestamp` | não | ISO 8601. Sem fuso, é lido em `America/Sao_Paulo` |
| `rotulo` | não | `positivo` \| `negativo` \| `neutro` — o rótulo de referência |

```csv
conversa_id,ordem,autor,texto,timestamp,rotulo
c1,1,sistema,voce esta na fila,2026-01-02T10:00:00,
c1,2,usuario,demorou demais,2026-01-02T10:01:00,negativo
c2,1,usuario,obrigado resolveu,,positivo
```

### Comportamento

- **Ou entra tudo, ou nada.** A importação é uma transação: qualquer erro de esquema aborta o
  arquivo inteiro. Um CSV meio importado é pior que um erro.
- **Reimportar substitui.** Mesma `(fonte, conversa_id)` → as mensagens antigas são apagadas e
  regravadas. Corrigir e reenviar não duplica.
- **Só mensagens de `usuario` são classificadas.** As de `sistema` e `atendente` são gravadas
  com `rotulo_pred = null`.
- **A classificação é síncrona**, dentro da request, e reclassifica todas as conversas da
  `fonte` — não apenas as do arquivo enviado.

### Resposta

```json
{"fonte": "piloto", "conversas": 2, "mensagens": 3, "mensagens_classificadas": 2}
```

| Status | Quando |
|---|---|
| 200 | importado e classificado |
| 400 | sem campo `arquivo`; arquivo não é UTF-8; JSON malformado; erro de esquema (com `detalhes`, até 20 mensagens) |

```json
{"erro": "arquivo inválido", "detalhes": ["linha 4: autor inválido 'robo'", "linha 7: ordem não é inteiro: 'x'"]}
```

---

## `GET /api/conversas`

Lista de conversas com os indicadores de sessão.

| Query param | Padrão | Descrição |
|---|---|---|
| `fonte` | — | filtra por base |
| `limite` | 100 | máximo 500 |

```json
{
  "total": 2,
  "conversas": [
    {
      "id": 1,
      "origem_id": "c1",
      "fonte": "piloto",
      "indicadores": {
        "abertura": "negativo",
        "encerramento": "positivo",
        "delta": 2,
        "trocas_de_polaridade": 1,
        "pior_momento": 1,
        "n_mensagens": 3
      }
    }
  ]
}
```

`total` é a contagem **sem** o limite. `indicadores` é `null` quando a conversa não tem
nenhuma mensagem de usuário classificada. Definição de cada indicador em ARQUITETURA.md.

---

## `GET /api/conversas/<id>`

Conversa completa: todas as mensagens (inclusive sistema e atendente), em ordem.

```json
{
  "id": 1,
  "origem_id": "c1",
  "fonte": "piloto",
  "indicadores": {"abertura": "negativo", "...": "..."},
  "mensagens": [
    {"ordem": 1, "autor": "sistema", "texto": "voce esta na fila",
     "rotulo": null, "score": null, "rotulo_real": null},
    {"ordem": 2, "autor": "usuario", "texto": "demorou demais",
     "rotulo": "negativo", "score": 0.9731, "rotulo_real": "negativo"}
  ]
}
```

`rotulo` é a predição do modelo, `score` a probabilidade da classe escolhida, `rotulo_real` o
rótulo de referência quando existe. É a rota que alimenta a timeline da tela de conversa.

404 com `{"erro": "conversa não encontrada"}` se o id não existir.

---

## `GET /api/metricas`

Duas coisas diferentes na mesma resposta:

- `distribuicao` e `total_conversas` — agregados **ao vivo** do banco, sobre o que foi
  classificado.
- `modelos` — conteúdo de `models/metricas.json`, gerado pela **última execução** de
  `manage.py avaliar --salvar`. É `null` se o arquivo não existe. Não é recalculado pela API:
  a avaliação é offline por definição.

```json
{
  "distribuicao": {"positivo": 24001, "negativo": 23408, "neutro": 15664},
  "total_conversas": 63073,
  "modelos": {
    "n_teste": 12615,
    "modelos": [
      {"nome": "lexico", "f1_macro": 0.4885, "matriz": [[3303,114,1272],[414,1626,2745],[1430,345,1366]]},
      {"nome": "classico", "f1_macro": 0.7346, "matriz": [[3645,163,881],[87,4097,601],[674,673,1794]]}
    ],
    "mcnemar": [
      {"a": "lexico", "b": "classico", "acertos_so_de_a": 1343, "acertos_so_de_b": 4584,
       "p": 0.0, "significativo": true}
    ]
  }
}
```

A matriz vem sempre na ordem **positivo, negativo, neutro**, linhas = verdadeiro,
colunas = predito.

---

## Notas de implementação

- **Sem paginação real.** `limite` corta em 500; se a lista de conversas crescer a ponto de
  incomodar, aí entra cursor.
- **`GET /api/conversas` faz `prefetch_related`** e calcula indicadores em Python. Com milhares
  de conversas por página isso pesa — materializar os indicadores é a saída, e só quando doer.
- **Nenhuma rota escreve exceto `/upload`.**
