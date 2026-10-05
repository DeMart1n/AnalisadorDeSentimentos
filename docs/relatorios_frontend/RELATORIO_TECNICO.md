# 🛠️ Relatório Técnico Semanal — Desenvolvimento Frontend & Integração

**Projeto:** Analisador de Sentimentos em Atendimentos via Chat (Extensão Universitária & Artigo Científico)  
**Módulo:** Frontend & Interface do Usuário  
**Stack Principal:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Lucide React / Material Symbols, Django REST API (Backend)  
**Status do Período:** Tela de Login concluída com design B2B premium e integração com ambiente local configurada.

---

## 1. Visão Geral da Arquitetura do Frontend

O frontend foi desenhado seguindo arquitetura moderna baseada em componentes reutilizáveis e consumo de API REST.

- **Framework:** Next.js 14 com App Router (`frontend/src/app`).
- **Estilização & Design System:** Tailwind CSS com paleta de tokens personalizada em `tailwind.config.ts` (design B2B profissional com suporte a modo escuro/nobre, glassmorphism e transparências).
- **Gerenciamento de Estado & Comunicação:** Axios / Fetch API para comunicação assíncrona com os endpoints Django.

---

## 2. Atividades Realizadas & Implementações

### 2.1. Configuração do Ambiente de Desenvolvimento
- Estruturação e inicialização do projeto Next.js na pasta `frontend/`.
- Configuração do backend Django local (`venv`, SQLite, migrations e superusuário de testes: `admin@email.com`).
- Garantia de execução paralela sem conflitos (Backend na porta `:8000` e Frontend na porta `:3000`).

### 2.2. Construção & Refinamento da Tela de Login (`/login`)
- **Layout Split 50/50:** Divisão equilibrada entre o painel visual demonstrativo (esquerda) e a área de formulário de autenticação (direita).
- **Cards Demonstrativos de Sentimento:**
  - **Positivo (Verde):** Exemplo de interação Zendesk com score de satisfação (+0.94).
  - **Neutro (Amarelo):** Exemplo de interação Intercom sem polaridade extrema.
  - **Alerta de Atrito (Vermelho):** Exemplo de interação WhatsApp com alerta de insatisfação e indicador de *Risco de Churn* (88%).
- **Indicadores de KPI Flutuantes:**
  - Badge de criptografia de sessão AES-256.
  - Badge de **"99.4% Precisão de análise"** ajustado para a posição inferior direita, sobrepondo de forma harmoniosa a área de simulação.
- **Compacção & Otimização de Layout:** Redução de espaçamentos (`padding`/`margin`) e ajuste de tipografia para eliminar a rolagem vertical (*scrollbar*) na resolução padrão de desktop.

---

## 3. Decisões Arquiteturais & Especificação de Endpoints

| Endpoint Django | Método | Função no Frontend | Status |
|---|---|---|---|
| `/api/token/` / `/api-auth/` | `POST` | Autenticação do usuário e obtenção de token/sessão | Configurado |
| `/api/upload/` | `POST` | Envio de arquivos de atendimento (CSV/JSON) para análise | Especificado |
| `/api/conversas/` | `GET` | Tabela com conversas, delta e trocas de polaridade | Especificado |
| `/api/metricas/` | `GET` | Dados estatísticos e matriz de confusão dos modelos (BERTimbau vs Léxico) | Especificado |

---

## 4. Próximos Passos

1. **Desenvolvimento da Tela de Dashboard (`/dashboard`):** Implementação de gráficos de distribuição de sentimento e comparativo de F1-Score dos modelos de IA.
2. **Desenvolvimento da Tela de Listagem (`/conversas`):** Tabela interativa com filtros por fonte e rótulo de sentimento.
3. **Desenvolvimento da Tela de Upload (`/upload`):** Área de drag-and-drop com validação de formato e relatório instantâneo de erros de esquema.
