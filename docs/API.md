# API

JSON puro sobre Django views. Sem DRF, autenticação stateless via JWT (`PyJWT`), sem paginação por cursor. Base: `http://localhost:8000/api`.

Todas as respostas de erro têm a forma `{"erro": "..."}` (ou com `"detalhes": [...]` quando há lista de validações de arquivo).

Para endpoints protegidos com `@jwt_required`, envie o cabeçalho:
`Authorization: Bearer <access_token>`

---

## `POST /api/register`

Cria um novo usuário na aplicação com role padrão `USER`. A senha é armazenada com hash seguro (`make_password`). `application/json`. **CSRF desativado** (`@csrf_exempt`).

| Campo | Obrigatório | Tipo | Descrição |
|---|---|---|---|
| `name` | sim | string | Nome do usuário |
| `email` | sim | string | E-mail válido e único |
| `password` | sim | string | Senha com no mínimo 6 caracteres |

### Payload de exemplo

```json
{
  "name": "Luiz Felipe",
  "email": "luiz@email.com",
  "password": "luiz1234"
}
```

### Resposta

| Status | Quando | Formato |
|---|---|---|
| 201 | Usuário criado com sucesso | `{"name": "...", "email": "...", "role": "USER", "created_at": "..."}` |
| 400 | Payload malformado ou campos inválidos/faltando | `{"erro": ["Name is required."]}` ou `{"erro": "JSON inválido: ..."}` |

---

## `POST /api/login`

Autentica um usuário existente por e-mail e senha, gerando um par de tokens JWT (`access_token` e `refresh_token`). `application/json`. **CSRF desativado** (`@csrf_exempt`).

| Campo | Obrigatório | Tipo | Descrição |
|---|---|---|---|
| `email` | sim | string | E-mail cadastrado |
| `password` | sim | string | Senha do usuário |

### Payload de exemplo

```json
{
  "email": "luiz@email.com",
  "password": "luiz1234"
}
```

### Resposta

| Status | Quando | Formato |
|---|---|---|
| 200 | Credenciais válidas | `{"email": "...", "access_token": "eyJhbGci...", "refresh_token": "eyJhbGci..."}` |
| 401 | Credenciais inválidas | `{"erro": "Invalid email or password"}` |
| 400 | Payload malformado ou campos faltando | `{"erro": [...]}` ou `{"erro": "JSON inválido: ..."}` |

- **Access Token:** Validade de 1 hora (`type: "access"`).
- **Refresh Token:** Validade de 7 dias (`type: "refresh"`).

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

- `distribuicao` e `total_conversas` — agregados **ao vivo** do banco. `distribuicao` conta
  `rotulo_pred` (a predição do modelo), **não** `rotulo_real`.
- `modelos` — conteúdo de `models/metricas.json`, gerado pela **última execução** de
  `manage.py avaliar --salvar`. É `null` se o arquivo não existe. Não é recalculado pela API:
  a avaliação é offline por definição.

> **Estado atual do banco local:** as 63k mensagens importadas do dataset público têm
> `rotulo_real` mas nunca passaram pelo classificador — só as 3 mensagens das conversas de
> teste manual. A resposta real hoje é `"distribuicao": {"negativo": 2, "positivo": 1}`. O
> exemplo abaixo é ilustrativo do formato, com o banco totalmente classificado.

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

O `metricas.json` em disco hoje contém apenas **léxico e clássico** — a última execução com
`--salvar` não incluiu o BERTimbau. Reexecutar `avaliar --modelos lexico classico bertimbau
--salvar` para o comparativo ficar completo.

---

## Notas de implementação

- **Sem paginação real.** `limite` corta em 500; se a lista de conversas crescer a ponto de
  incomodar, aí entra cursor.
- **`GET /api/conversas` faz `prefetch_related`** e calcula indicadores em Python. Com milhares
  de conversas por página isso pesa — materializar os indicadores é a saída, e só quando doer.
- **Rotas de escrita:** `/upload` (multipart), `/register` (JSON) e `/login` (JSON).
- **Autenticação Stateless:** JWT (`PyJWT`) com `access_token` (1h) e `refresh_token` (7d). Proteção de rotas com `@jwt_required` checando o cabeçalho `Authorization: Bearer <token>`.
