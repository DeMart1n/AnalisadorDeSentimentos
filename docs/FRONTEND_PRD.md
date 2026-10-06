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

| Tela | Stitch ID / Ref | Endpoints Consumidos | Status | Observações |
|---|---|---|---|---|
| **Login** | `f407377a4e1d460ca123d4d751871b2d` | `POST /api/login`, `POST /api/register`, `POST /api/refresh` | Concluída | Layout split 50/50 com cards demonstrativos, persistência de JWT e redirecionamento. |
| **Dashboard Principal** | `976e6a8354474f69a9a0dbe4780a5ffa` | `GET /api/metricas`, `GET /api/conversas?limite=500` | Concluída | KPIs de topo, Donut Chart (Recharts) de distribuição, Bar Chart de F1-Macro e tabela de casos críticos com queda de delta. |
| **Inserir Conversas** | `28aa1c5bcf4f4b9282621e0a7ca0c04d` | `POST /api/upload`, `POST /api/conversas/analisar` | Concluída | Drag & drop para CSV/JSON, histórico de importações e gatilho de classificação com IA (BERTimbau). |
| **Listagem de Conversas** | `b96b713aff674d65a45bcce0271ecd3f` | `GET /api/conversas?limite=500` | Concluída | Filtros client-side instantâneos (Todas, Críticas, Positivas, Com Queda, Pendentes) e badges de status. |
| **Detalhe da Conversa** | `d2b736aa96ab46afb2a1bee44b539d82` | `GET /api/conversas/<id>` | Concluída | Cards analíticos, gráfico de evolução temporal (LineChart com ReferenceDot de pior momento) e chat bubbles categorizadas. |

*Status Geral de Implementação:*
Todas as 5 telas principais foram desenvolvidas e estão conectadas ao backend Django local, incluindo suporte a gráficos interativos e empty states resilientes.

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

## 5. Pontos de Atenção & Decisões Técnicas Aplicadas

1. **CORS:** Configurado no Django com cabeçalhos permissivos para o frontend local em `localhost:3000`.
2. **Resiliência a Empty States:** Quando o banco possui conversas mas sem rótulos ou sem matrizes de teste geradas via `avaliar --salvar`, o frontend renderiza estados vazios descritivos sem quebrar o layout.
3. **Biblioteca de Gráficos (Recharts):** Gráficos de rosca (`PieChart`), barras (`BarChart`) e linhas temporais (`LineChart`) integrados com `ResponsiveContainer`, tooltips dinâmicos e tipagem TypeScript adaptada.
4. **Filtro Client-Side:** Como a rota `/conversas` retorna até 500 registros, os filtros por status e declínio de sentimento operam diretamente em memória para resposta instantânea.
5. **Classificação via IA sob Demanda:** A tela `/upload` possui acionamento direto para `/api/conversas/analisar`, enviando parâmetros de modelo (padrão: `bertimbau`) e flag de processamento de pendentes.
6. **Dependências do Modelo de IA:** No backend, foi necessária a instalação explícita de `torch` e `transformers` para possibilitar a inferência do modelo BERTimbau na API Django.

## 6. Acompanhamento & Relatórios Periódicos

Para facilitar o acompanhamento do desenvolvimento e prover insumo estruturado para o **Artigo Científico** e **Relatórios de Extensão Universitária**, os dois documentos a seguir são mantidos e atualizados periodicamente:

- 🛠️ [Relatório Técnico](file:///c:/Users/ciacc/OneDrive/Documentos/AnalisadorDeSentimentos/docs/relatorios_frontend/RELATORIO_TECNICO.md): Detalhamento de código, arquitetura, rotas, Next.js, Tailwind, Recharts e integrações REST.
- 📄 [Relatório de Divulgação Científica / Leigo](file:///c:/Users/ciacc/OneDrive/Documentos/AnalisadorDeSentimentos/docs/relatorios_frontend/RELATORIO_LEIGO.md): Resumo executivo em linguagem acessível, abordando aspectos de IHC (Interação Humano-Computador), visualização de dados e impacto para a escrita do artigo.

