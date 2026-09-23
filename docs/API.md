# API

JSON puro sobre Django views. Sem DRF, autenticação stateless via JWT (`PyJWT`), sem paginação por cursor. Base: `http://localhost:8000/api`.
A documentação interativa moderna via **Scalar (OpenAPI 3.1)** está disponível em `http://localhost:8000/api/docs` (e a especificação em `http://localhost:8000/api/openapi.yaml`).
Suporte nativo a **CORS** com resolução automática de requisições preflight (`OPTIONS`) em todos os endpoints.

Todas as respostas de erro têm a forma `{"erro": "..."}` (ou com `"detalhes": [...]` quando há lista de validações de arquivo).
A ingestão de conversas conta com **anonimização automática em memória (LGPD / Privacy by Design)** antes de qualquer gravação no banco de dados.

Para endpoints protegidos com `@jwt_required` ou `@admin_required`, envie o cabeçalho:
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
| 400 | Payload malformado ou campos inválidos/faltando | `{"erro": ["O campo 'name' é obrigatório."]}` ou `{"erro": "JSON inválido: ..."}` |

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
| 401 | Credenciais inválidas | `{"erro": "E-mail ou senha inválidos."}` |
| 400 | Payload malformado ou campos faltando | `{"erro": [...]}` ou `{"erro": "JSON inválido: ..."}` |

- **Access Token:** Validade de 1 hora (`type: "access"`).
- **Refresh Token:** Validade de 7 dias (`type: "refresh"`).

---

## `POST /api/refresh`

Renova o par de tokens JWT sem necessidade de informar credenciais novamente (Refresh Token Rotation). `application/json`. **CSRF desativado** (`@csrf_exempt`).

| Campo | Obrigatório | Tipo | Descrição |
|---|---|---|---|
| `refresh_token` | sim | string | Token de renovação emitido no login ou último refresh |

### Payload de exemplo

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Resposta

| Status | Quando | Formato |
|---|---|---|
| 200 | Token válido e renovado com sucesso | `{"access_token": "eyJhbGci...", "refresh_token": "eyJhbGci..."}` |
| 401 | Token expirado, com assinatura inválida ou de tipo incorreto | `{"erro": "Refresh token expirado."}` |
| 404 | Usuário do token não encontrado no banco | `{"erro": "Usuário não encontrado."}` |
| 400 | Payload malformado ou sem campo `refresh_token` | `{"erro": [...]}` ou `{"erro": "JSON inválido: ..."}` |

---

## `POST /api/upload`

Recebe um arquivo CSV ou JSON, valida os dados através de um **Schema Adapter Flexível**, aplica **Anonimização de Dados Sensíveis (LGPD / Privacy by Design)** em memória e grava as conversas e mensagens atomicamente no banco de dados.
`multipart/form-data`. **CSRF desativado** (`@csrf_exempt`). Suporta requisições Preflight `OPTIONS` via CORS.

> 🔒 **Autenticação & Permissão:** Rota protegida via JWT (`@admin_required`). Requer cabeçalho `Authorization: Bearer <access_token>` com role **`ADMIN`**. Usuários com role `USER` recebem `403 Forbidden`.

A classificação por IA foi desacoplada deste endpoint para garantir resposta quase instantânea (~50ms) e evitar timeouts de rede. Para classificar as mensagens importadas, chame o endpoint `POST /api/conversas/analisar`.

| Campo | Obrigatório | Descrição |
|---|---|---|
| `arquivo` | sim | CSV ou JSON em UTF-8 (com ou sem BOM). O formato é decidido pela extensão `.json` |
| `fonte` | não | Identificador da base. Padrão: nome do arquivo sem extensão |

### Recursos do Importador (Schema Adapter Flexível)

O importador adapta exports de diversas plataformas de atendimento (Blip, Zenvia, Salesforce, Zendesk, etc.):

1. **Codificação e Delimitadores:**
   - Suporta arquivos codificados em UTF-8 convencional ou com **BOM (`\ufeff`)**, típico de exportações do Excel no Windows.
   - Detecta automaticamente se o delimitador do CSV é **vírgula (`,`)** ou **ponto e vírgula (`;`)**.
2. **Mapeamento Dinâmico de Colunas (Aliases):**
   - `conversa_id`: `["conversa_id", "conversa", "chat_id", "ticket_id", "protocolo", "id_conversa", "session_id"]`
   - `ordem`: `["ordem", "seq", "sequencia", "index", "order", "mensagem_id"]` *(opcional; ver fallback abaixo)*
   - `texto`: `["texto", "mensagem", "text", "msg", "conteudo", "message", "body"]`
   - `autor`: `["autor", "origem", "remetente", "sender", "from"]`
   - `origem`: `["origem", "tipo", "role"]`
   - `timestamp`: `["timestamp", "mensagem_em", "enviada_em", "data_hora", "created_at", "date"]`
   - `rotulo`: `["rotulo", "sentiment", "sentimento", "label"]`
   - `contato`: `["contato", "nome_contato", "cliente_nome", "nome", "customer_name", "user_name"]`
   - `telefone`: `["telefone", "telefone_contato", "celular", "phone", "contact_phone"]`
3. **Normalização Inteligente de Papéis (Roles):**
   - `usuario`: `usuario`, `cliente`, `user`, `customer`, `consumidor`, `client`
   - `atendente`: `atendente`, `agente`, `operador`, `atendimento`, `support`, `analista`, `agent`
   - `sistema`: `sistema`, `bot`, `ura`, `system`, `ia`, `virtual`, `notificacao`
   - Resolve automaticamente casos onde a coluna `origem` indica o papel (ex: `"atendimento"`) e `autor` traz o nome do agente (ex: `"Lucas Mendes Cod 1234"`).
4. **Fallback Automático de Ordenação:**
   - Se o arquivo não contiver coluna de ordem (`ordem` / `seq`), o sistema ordena automaticamente as mensagens da conversa pelo `timestamp` ou pela ordem física de leitura das linhas.

### Anonimização de Dados Sensíveis (LGPD / Privacy by Design)

Antes de gravar qualquer registro no banco de dados, o texto das mensagens passa por um pipeline estrito e irreversível de anonimização:

- `[EMAIL]`: Endereços de e-mail válidos.
- `[CARTAO]`: Números de cartão de crédito de 13 a 16 dígitos validados via algoritmo de Luhn.
- `[CNPJ]`: CNPJs formatados ou sequências numéricas de 14 dígitos com checksum de Módulo 11 válido.
- `[CPF]`: CPFs formatados ou sequências numéricas de 11 dígitos com checksum de Módulo 11 válido (evita corromper números de pedidos ou protocolos de 11 dígitos).
- `[TELEFONE]`: Telefones fixos e celulares, formatos com/sem DDD e código de país (+55).
- `[NOME]`: Nomes próprios de clientes e atendentes identificados via:
  - Metadados do arquivo (colunas `contato` e `autor`, com limpeza de sufixos como `"Cod 1234"`).
  - Respostas do usuário a perguntas do bot (ex: *"Informe seu nome por favor:"* ➔ *"vinicius"*).
  - Ecos de confirmação do bot (ex: *"Obrigado \*vinicius\*"*).
  - Apresentações explícitas no chat (ex: *"Sou João Augusto"*).
  - Cartões de contato compartilhados do WhatsApp (ex: `**Contact:** *Name:* Flavinha *Number (1):* ...`).

### Exemplo de CSV Aceito (Corporativo com Aliases)

```csv
conversa,seq,origem,autor,mensagem,contato,telefone,data_hora
chat_100,1,cliente,Mariana Souza,Gostaria de saber meu saldo,Mariana Souza,11999998888,2026-03-01T10:00:00
chat_100,2,atendimento,Carlos Suporte,Ola Mariana seu saldo e de 100 reais,Mariana Souza,11999998888,2026-03-01T10:01:00
chat_100,3,sistema,URA Bot,Protocolo finalizado: 2026100,Mariana Souza,11999998888,2026-03-01T10:02:00
```

### Comportamento

- **Ou entra tudo, ou nada.** A importação é uma transação atômica (`transaction.atomic`): qualquer erro de validação aborta o arquivo inteiro.
- **Reimportar substitui.** Mesma `(fonte, conversa_id)` → as mensagens antigas são apagadas e regravadas sem duplicidade.
- **As mensagens são salvas já anonimizadas e inicialmente com `rotulo_pred = null`**, aguardando análise pelo endpoint de classificação.

### Resposta

```json
{"fonte": "piloto", "conversas": 2, "mensagens": 3, "status": "importado"}
```

| Status | Quando |
|---|---|
| 201 | Arquivo validado, anonimizado e conversas importadas com sucesso |
| 400 | Sem campo `arquivo`; arquivo não é UTF-8; JSON malformado; erro de esquema (com `detalhes`, até 20 mensagens) |
| 401 | Token JWT ausente, expirado ou inválido |
| 403 | Usuário autenticado, mas não possui a role `ADMIN` |

```json
{"erro": "Acesso negado: privilégios de administrador necessários."}
```

---

## `POST /api/conversas/analisar`

Dispara a inferência da IA para classificar o sentimento das mensagens de usuário (`positivo | negativo | neutro`) das conversas previamente importadas. `application/json`. **CSRF desativado** (`@csrf_exempt`).

> 🔒 **Autenticação:** Rota protegida via JWT (`@jwt_required`). Requer cabeçalho `Authorization: Bearer <access_token>` de qualquer usuário autenticado (`ADMIN` ou `USER`).

| Campo | Obrigatório | Tipo | Padrão | Descrição |
|---|---|---|---|---|
| `fonte` | condicional | string | `null` | Identificador da base a ser analisada (obrigatório se não informar `conversa_ids`) |
| `conversa_ids` | condicional | array[int] | `null` | Lista específica de IDs das conversas (obrigatório se não informar `fonte`) |
| `modelo` | não | string | `"lexico"` | Modelo a utilizar: `"lexico"`, `"classico"` ou `"bertimbau"` |
| `apenas_nao_classificadas` | não | boolean | `true` | Se `true`, classifica apenas mensagens pendentes (`rotulo_pred is null`). Se `false`, reclassifica tudo |

### Payload de exemplo

```json
{
  "fonte": "piloto",
  "modelo": "lexico",
  "apenas_nao_classificadas": true
}
```

### Resposta

```json
{
  "fonte": "piloto",
  "total_conversas": 2,
  "mensagens_classificadas": 2,
  "modelo_utilizado": "lexico"
}
```

| Status | Quando |
|---|---|
| 200 | Mensagens analisadas e classificadas com sucesso |
| 400 | Payload malformado, modelo inválido ou ausência de `fonte`/`conversa_ids` |
| 404 | Nenhuma conversa encontrada para a fonte ou IDs informados |

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

## `GET /api/openapi.yaml`

Retorna a especificação estática da API no padrão **OpenAPI 3.1** em formato YAML, contendo todos os esquemas de dados, exemplos, códigos de retorno e autenticação.

---

## `GET /api/docs`

Interface web moderna e interativa gerada pelo **Scalar** (`@scalar/api-reference`), com cliente HTTP integrado para testes, suporte a temas (dark mode) e documentação de todos os endpoints.

---

## Notas de implementação

- **Sem paginação real.** `limite` corta em 500; se a lista de conversas crescer a ponto de
  incomodar, aí entra cursor.
- **`GET /api/conversas` faz `prefetch_related`** e calcula indicadores em Python. Com milhares
  de conversas por página isso pesa — materializar os indicadores é a saída, e só quando doer.
- **Rotas de escrita:** `/upload` (multipart), `/register` (JSON), `/login` (JSON), `/refresh` (JSON) e `/conversas/analisar` (JSON).
- **Autenticação Stateless:** JWT (`PyJWT`) com `access_token` (1h) e `refresh_token` (7d). Proteção de rotas com `@jwt_required` ou `@admin_required` checando o cabeçalho `Authorization: Bearer <token>`.
- **Suporte a CORS Preflight:** Middleware próprio que responde a requisições `OPTIONS` com status 200 e cabeçalhos permissivos (`Access-Control-Allow-Origin: *`), viabilizando chamadas via Scalar e frontends SPA.
- **Privacy by Design (LGPD):** O processamento de remoção de dados pessoais sensíveis (`[NOME]`, `[CPF]`, `[CNPJ]`, `[TELEFONE]`, `[EMAIL]`, `[CARTAO]`) é estritamente *in-flight* — dados confidenciais nunca são gravados em disco no SQLite.
- **Schema Adapter e Resiliência:** Mapeador dinâmico de aliases para cabeçalhos de arquivos, detecção de delimitador (`,` e `;`) e suporte a UTF-8 com ou sem BOM (`\ufeff`).
