# Frontend PRD - Analisador de Sentimentos

Este documento serve como fonte de verdade para o desenvolvimento do frontend do Analisador de Sentimentos. Ele consolida o escopo, stack tecnológica, contratos de API e inventário de telas.

## 1. Visão Geral

O frontend é uma aplicação de analytics (dashboard) para explorar resultados de classificação de sentimentos de conversas de atendimento. Não é uma interface de chatbot, mas sim uma ferramenta para visualizar as trajetórias e métricas calculadas pelo backend.

## 2. Decisões Técnicas & Stack

- **Framework:** Next.js (App Router).
- **Linguagem:** TypeScript, tipando estritamente os contratos da API.
- **Estilização:** Tailwind CSS (alinhado com as especificações do Stitch).
- **Data Fetching & State:** TanStack Query (React Query) para chamadas à API, cache e revalidação.
- **Gráficos:** Recharts para visualizações no Dashboard.
- **Estado Global:** Context API (ou Zustand) estritamente para dados globais (ex: sessão do usuário autenticado).
- **Autenticação:** O backend usa JWT (access de 1h, refresh de 7d).
  - **Decisão de armazenamento:** Guardaremos o `access_token` e `refresh_token` no `localStorage` por simplicidade na v1 (dado que é um projeto local/acadêmico) ou, caso desejado, gerenciar via Context + `localStorage`.
  - O header `Authorization: Bearer <token>` será anexado em todas as chamadas autenticadas.
  - O refresh automático será feito via interceptador no cliente HTTP (ex: wrapper do `fetch` ou axios).

## 3. Inventário de Telas (Stitch)

As telas foram desenhadas no Stitch (Projeto: *SentimentIQ Analytics Dashboard* - ID `projects/18398547391647593690`).

| Tela | Stitch ID / Ref | Endpoints Consumidos | Observações |
|---|---|---|---|
| **Login** | `f407377a4e1d460ca123d4d751871b2d` | `POST /api/login`, `POST /api/register`, `POST /api/refresh` | Redireciona o usuário e armazena os tokens de acesso e refresh. |
| **Dashboard Principal** | `976e6a8354474f69a9a0dbe4780a5ffa` | `GET /api/metricas` | Precisa lidar graciosamente com ausência de dados (distribuição vazia). |
| **Inserir Conversas** | `28aa1c5bcf4f4b9282621e0a7ca0c04d` | `POST /api/upload`, `POST /api/conversas/analisar` | Exige permissão `ADMIN`. Usuários com role `USER` não devem ver ou ter acesso funcional a esta tela. |
| **Listagem de Conversas** | `b96b713aff674d65a45bcce0271ecd3f` | `GET /api/conversas` | O filtro de sentimento e texto será feito **client-side** em cima do limite de 500 retornados pela API. |
| **Detalhe da Conversa** | `d2b736aa96ab46afb2a1bee44b539d82` | `GET /api/conversas/<id>` | Renderiza a timeline de mensagens com as cores baseadas no sentimento. |

*Ordem de Implementação:*
1. Upload (Inserir Conversas)
2. Detalhe da Conversa
3. Listagem de Conversas
4. Dashboard

## 4. Contratos de API (Tipagem Base)

```typescript
type Role = "ADMIN" | "USER";
type Sentimento = "positivo" | "negativo" | "neutro";
type Modelo = "lexico" | "classico" | "bertimbau";

interface LoginResponse {
  email: string;
  access_token: string;
  refresh_token: string;
}

interface RegisterResponse {
  name: string;
  email: string;
  role: Role;
  created_at: string;
}

interface UploadResponse {
  fonte: string;
  conversas: number;
  mensagens: number;
  status: "importado";
}

interface AnalisarResponse {
  fonte: string;
  total_conversas: number;
  mensagens_classificadas: number;
  modelo_utilizado: Modelo;
}

interface Indicadores {
  abertura: Sentimento;
  encerramento: Sentimento;
  delta: number;
  trocas_de_polaridade: number;
  pior_momento: number;
  n_mensagens: number;
}

interface ConversaListItem {
  id: number;
  origem_id: string;
  fonte: string;
  indicadores: Indicadores | null;
}

interface Mensagem {
  ordem: number;
  autor: string;
  texto: string;
  rotulo: Sentimento | null;
  score: number | null;
  rotulo_real: Sentimento | null;
}

interface ConversaDetalhe extends ConversaListItem {
  mensagens: Mensagem[];
}

interface MatrizModelo {
  nome: Modelo;
  f1_macro: number;
  matriz: number[][]; // [positivo, negativo, neutro]
}

interface McNemarComparacao {
  a: Modelo;
  b: Modelo;
  acertos_so_de_a: number;
  acertos_so_de_b: number;
  p: number;
  significativo: boolean;
}

interface MetricasResponse {
  distribuicao: Record<Sentimento, number>;
  total_conversas: number;
  modelos: {
    n_teste: number;
    modelos: MatrizModelo[];
    mcnemar: McNemarComparacao[];
  } | null;
}

interface ApiErro {
  erro: string | string[];
  detalhes?: string[];
}
```

## 5. Pontos de Atenção & Riscos Assumidos

1. **CORS:** O documento mais recente de API menciona que o middleware preflight resolve o CORS. Confirmaremos testando. Caso falhe, a mitigação será configurar `rewrites` no `next.config.js`.
2. **Sem dados no Dashboard:** O banco atualmente contém mensagens, mas a maioria delas não foi classificada. A UI do dashboard assumirá dados em zero/incompletos como caso normal (empty states amigáveis).
3. **Score Relativo:** O `score` retornado pode ser probabilidade ou soma de pesos (caso do Léxico). A UI não apresentará esse dado como "porcentagem de certeza" de forma ingênua, já que sua semântica muda por modelo.
4. **Filtro Client-Side:** Como a rota de listagem suporta apenas `fonte` e `limite`, toda filtragem por sentimento na tela 2 será executada via JavaScript no frontend, operando na coleção recebida.
5. **Indicadores Null:** Sempre considerar `indicadores: null` na listagem (exibir "Não Classificado" e não quebrar o layout).
6. **CSRF Desligado:** Nenhuma submissão do front vai buscar cookie `csrftoken` (as rotas do backend usam `@csrf_exempt`).
