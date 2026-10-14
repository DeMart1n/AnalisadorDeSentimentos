# 🛠️ Relatório Técnico Semanal — Desenvolvimento Frontend & Integração com IA

**Projeto:** Analisador de Sentimentos em Atendimentos via Chat (Extensão Universitária & Artigo Científico)  
**Módulo:** Frontend, Visualização de Dados & Integração REST com Pipeline de ML  
**Stack Principal:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, TanStack Query, Django REST Framework, BERTimbau / PyTorch  
**Status do Período:** Conclusão das 5 telas principais da aplicação (Login, Dashboard, Upload, Listagem e Detalhes), integração de gráficos analíticos com Recharts e estabilização do endpoint de inferência do modelo de IA.

---

## 1. Visão Geral da Arquitetura do Frontend

O frontend foi concebido como uma Single Page Application (SPA) analítica e moderna, focada em fornecer insights sobre o ciclo emocional de atendimentos ao cliente:

- **Framework:** Next.js 14 com App Router (`frontend/src/app`).
- **Gerenciamento de Estado de Rede & Cache:** TanStack Query (`@tanstack/react-query` v5), garantindo caching, revalidações sob demanda e mutações assíncronas consistentes.
- **Visualização de Dados:** Biblioteca `recharts` para renderização declarativa e responsiva de gráficos vetoriais em SVG (rosca/donut, barras comparativas e linhas temporais).
- **Estilização & Design System:** Tailwind CSS com paleta de tokens personalizada inspirada no Stitch (identidade corporativa com suporte a modo claro/escuro, tons semânticos de sentimento — verde `#10b981`, vermelho `#ef4444`, cinza/ardósia `#64748b`).
- **Comunicação REST:** Wrapper tipado em Axios (`frontend/src/lib/api.ts`) com interceptores para injeção de token JWT `Bearer` e tratamento de erros.

---

## 2. Atividades Realizadas & Telas Concluídas

### 2.1. Portal de Autenticação (`/login`)
- **Layout Split 50/50:** Painel esquerdo interativo apresentando exemplos práticos de mensageria (Zendesk, Intercom, WhatsApp) com scores de polaridade e riscos de atrito/churn; painel direito com formulário de login e cadastro.
- **Segurança & Sessão:** Extração e persistência do JWT (`access_token` e `refresh_token`), redirecionamento automático para a raiz (`/`) e persistência de dados do usuário via contexto de autenticação.

### 2.2. Dashboard Principal de Analytics (`/`)
- **Métricas Agregadas (KPIs de Topo):** Total de conversas processadas, proporções percentuais e contagens absolutas de sentimentos Positivos, Negativos e Neutros consumidos de `GET /api/metricas`.
- **Distribuição de Sentimento Final (Donut Chart):** Implementado com `PieChart` e `ResponsiveContainer` do Recharts, com indicação central e legenda semântica.
- **Comparativo de Modelos de IA (Bar Chart):** Gráfico de barras comparando o F1-Macro entre BERTimbau, ML Clássico e Léxico. Desenvolvido com tratamento gracioso de *empty state* quando a rotina de avaliação de teste ainda não foi gerada no banco.
- **Casos Críticos Recentes:** Tabela de intervenção prioritária identificando atendimentos com maior queda emocional ($\Delta < 0$), permitindo acesso direto à auditoria do atendimento.

### 2.3. Módulo de Upload & Classificação de IA (`/upload`)
- **Ingestão de Dados:** Área de *drag & drop* com suporte a arquivos `.json` e `.csv`, com validação de esquema e progresso visual via `POST /api/upload`.
- **Gatilho de Inferência de IA:** Integração com o botão funcional **"Classificar com IA"** que aciona `POST /api/conversas/analisar`, enviando parâmetros de modelo (`bertimbau`) e processamento de registros pendentes.
- **Histórico de Arquivos:** Tabela com fontes importadas, contagem de conversas e mensagens processadas.

### 2.4. Listagem e Filtragem de Atendimentos (`/conversas`)
- **Filtragem Client-Side com Latência Zero:** Consumo de lote otimizado de até 500 conversas (`GET /api/conversas?limite=500`) com filtros reativos na interface:
  - *Todas* as conversas;
  - *Negativas / Críticas* (encerramento desfavorável);
  - *Positivas* (encerramento favorável);
  - *Com Queda* ($\Delta < 0$, cliente iniciou satisfeito/neutro e encerrou irritado);
  - *Pendentes* (conversas importadas aguardando classificação).
- **Indicadores Visuais:** Badges semânticos de polaridade, contagem de trocas de sentimento e atalho direto para a conversa.

### 2.5. Auditoria Detalhada da Conversa (`/conversas/[id]`)
- **Cards Analíticos do Atendimento:** Sentimento predominante do cliente, trajetória (abertura $\to$ desfecho), e identificação do pior momento do atendimento.
- **Gráfico de Evolução Temporal (Line Chart):** Gráfico interativo que mapeia a polaridade ao longo de cada mensagem da conversa (escala de -1 a +1), destacando visualmente através de um `ReferenceDot` o *turning point* (ponto de maior atrito).
- **Timeline de Mensagens:** Histórico cronológico em formato de balões de conversa diferenciando atendente e cliente, acompanhados de badges com rótulo atribuído e score de confiança do modelo.

---

## 3. Diagnóstico e Resolução Técnica de Backend

Durante os testes de integração do botão **"Classificar com IA"** na tela de upload, identificou-se um erro de status `500 Internal Server Error` disparado pela rota `POST /api/conversas/analisar`:
- **Causa Raiz:** O ambiente Python local não possuía instaladas as dependências de Deep Learning necessárias para carregar a arquitetura do modelo de linguagem (ausência de `torch` e `transformers`).
- **Resolução:** Execução de `pip install torch transformers` no ambiente virtual e reinicialização do daemon do servidor Django (`manage.py runserver`).
- **Validação:** A rota passou a carregar o modelo de embeddings/classificação BERTimbau com sucesso, processando as mensagens do SQLite e retornando o payload de confirmação para o frontend.

---

## 4. Contribuição para a Escrita do Artigo Científico

Este desenvolvimento fornece evidências e artefatos empíricos fundamentais para a redação do artigo:

1. **Interação Humano-Computador (IHC) em Sistemas de IA:** Como a transformação de saídas probabilísticas complexas (scores e logits de redes neurais) em representações visuais intuitivas (gráficos temporais de trajetória e badges de polaridade) reduz a carga cognitiva do operador humano.
2. **Arquitetura Desacoplada e Eficiência:** A separação estrita entre um backend de inferência NLP em Python e um cliente SPA em Next.js/React com cache via TanStack Query e renderização SVG via Recharts, mitigando travamentos de UI durante o processamento de lotes.
3. **Métricas Comparativas Empíricas:** O dashboard foi estruturado para expor diretamente métricas de F1-Macro e testes de significância estatística (McNemar), fornecendo subsídio quantitativo para a seção de Resultados e Discussão do artigo.

---

## 5. Próximos Passos & Melhorias Futuras

1. **Granularidade Emocional:** Evoluir a classificação para suportar detecção de emoções específicas (ex: raiva, decepção, empatia) com base na branch `feat/emocoes`.
2. **Exportação de Relatórios Acadêmicos:** Implementar ferramenta de exportação em PDF/CSV dos gráficos do dashboard e das tabelas de métricas para inclusão direta em trabalhos acadêmicos.
3. **Paginação Server-Side:** Adicionar suporte a paginação paginada no backend caso a base de conversas ultrapasse dezenas de milhares de registros.
