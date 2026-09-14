# 🚀 Coleção Bruno — API Analisador de Sentimentos

Coleção completa e detalhada de requisições para teste e exploração de todas as rotas do backend **Analisador de Sentimentos** utilizando o [Bruno](https://www.usebruno.com/).

---

## 📂 Estrutura da Coleção

```text
bruno/
├── bruno.json                               # Manifesto da coleção Bruno
├── README.md                                # Documentação e guia de uso
├── environments/
│   ├── Local.bru                            # Ambiente local (http://localhost:8000/api)
│   └── Docker.bru                           # Ambiente em contêiner Docker
├── samples/
│   ├── conversas_exemplo.csv                # Amostra CSV pronta para teste de upload
│   └── conversas_exemplo.json               # Amostra JSON pronta para teste de upload
├── 01-Autenticacao/
│   ├── 1. Registrar Usuario.bru             # POST /api/register
│   └── 2. Login (Obter Tokens JWT).bru      # POST /api/login (script de extração de token)
├── 02-Ingestao/
│   ├── 1. Upload de Conversas (CSV).bru     # POST /api/upload (arquivo CSV, admin required)
│   └── 2. Upload de Conversas (JSON).bru    # POST /api/upload (arquivo JSON, admin required)
├── 03-Analise/
│   ├── 1. Analisar por Fonte (Modelo Lexico).bru     # POST /api/conversas/analisar
│   ├── 2. Analisar por Fonte (Modelo Classico).bru   # POST /api/conversas/analisar
│   ├── 3. Analisar por Fonte (Modelo BERTimbau).bru  # POST /api/conversas/analisar
│   └── 4. Analisar por Lista de IDs.bru              # POST /api/conversas/analisar
├── 04-Conversas/
│   ├── 1. Listar Conversas (Todas).bru               # GET /api/conversas (script salva conversaId)
│   ├── 2. Listar Conversas (Filtradas por Fonte).bru # GET /api/conversas?fonte=...&limite=...
│   └── 3. Obter Detalhes da Conversa por ID.bru      # GET /api/conversas/:id
└── 05-Metricas/
    └── 1. Obter Metricas do Sistema.bru              # GET /api/metricas
```

---

## ⚙️ Configuração & Ambientes

A coleção já vem configurada com dois ambientes principais:
- **`Local`**: Aponta para `http://localhost:8000/api`
- **`Docker`**: Aponta para o backend rodando via contêiner

### Variáveis de Ambiente

| Variável | Descrição | Preenchimento |
|---|---|---|
| `baseUrl` | URL base da API (`http://localhost:8000/api`) | Pré-configurado |
| `fonte` | Nome padrão da base de conversas (`piloto`) | Pré-configurado |
| `conversaId` | ID numérico da conversa consultada | Automático / Editável |
| `accessToken` | Token JWT de acesso (Bearer) | **Capturado automaticamente via login** |
| `refreshToken` | Token JWT de renovação | **Capturado automaticamente via login** |

---

## ⚡ Automações & Scripts Embutidos

1. **Captura Automática de Tokens JWT:**
   - Ao executar a requisição `01-Autenticacao/2. Login (Obter Tokens JWT)`, um script de pós-resposta armazena o `access_token` diretamente na variável de ambiente `accessToken`.
   - Todas as requisições autenticadas (`Upload`, `Análise`) utilizam `{{accessToken}}` automaticamente.

2. **Chaining de Conversas:**
   - Ao executar `04-Conversas/1. Listar Conversas (Todas)`, o script armazena o ID da primeira conversa encontrada em `conversaId`.
   - Você pode imediatamente executar `3. Obter Detalhes da Conversa por ID` sem copiar e colar IDs manualmente.

3. **Asserções e Testes Automáticos:**
   - Cada requisição possui testes de integridade verificando status code (200, 201, etc.) e a estrutura dos campos retornados.

---

## 🔄 Fluxo de Teste Recomendado

1. **Selecione o ambiente `Local`** no canto superior direito do Bruno.
2. Execute **`01-Autenticacao / 1. Registrar Usuário`** (ou use um usuário existente).
3. Execute **`01-Autenticacao / 2. Login (Obter Tokens JWT)`** para autenticar e preencher `accessToken`.
   > 💡 *Nota sobre o Upload:* O endpoint `/api/upload` requer que o usuário tenha a role `ADMIN`. Se necessário, ajuste a role do usuário no banco (`python manage.py shell` -> `Users.objects.filter(email="...").update(role="ADMIN")`).
4. Execute **`02-Ingestao / 1. Upload de Conversas (CSV)`** para carregar os atendimentos de teste (`samples/conversas_exemplo.csv`).
5. Execute **`03-Analise / 1. Analisar por Fonte (Modelo Léxico)`** para rodar a inferência de sentimentos nas mensagens importadas.
6. Execute **`04-Conversas / 1. Listar Conversas (Todas)`** para visualizar os indicadores calculados (abertura, encerramento, delta).
7. Execute **`04-Conversas / 3. Obter Detalhes da Conversa por ID`** para ver o chat completo com predições por mensagem.
8. Execute **`05-Metricas / 1. Obter Métricas do Sistema`** para visualizar a distribuição dos sentimentos classificados no banco e as métricas do modelo.

---

## 🖥️ Executando via Linha de Comando (Bruno CLI)

Se você utiliza o `bru CLI` (`npm install -g @usebruno/cli`), você pode rodar a suíte inteira de testes diretamente no terminal:

```bash
# Rodar todos os testes com o ambiente Local
bru run ./bruno --env Local

# Rodar apenas a pasta de autenticação
bru run ./bruno/01-Autenticacao --env Local
```
