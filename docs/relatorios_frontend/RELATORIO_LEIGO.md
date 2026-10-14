# 📄 Relatório de Divulgação Científica & Acompanhamento Geral

**Projeto:** Analisador de Sentimentos em Atendimentos via Chat  
**Foco:** Resumo Executivo para a Equipe, Orientadores e Insumo para o Artigo Científico  
**Público-Alvo:** Integrantes do artigo científico, avaliadores da extensão universitária e partes interessadas não técnicas  
**Período:** Conclusão da Interface Completa (5 Telas), Gráficos Interativos e Integração com Inteligência Artificial

---

## 📋 1. O que é o Projeto? (Em linguagem simples)

Imagine que uma empresa recebe milhares de atendimentos todos os dias via WhatsApp, Zendesk ou chats de suporte ao cliente. Ler mensagem por mensagem para saber quem foi bem atendido e quem saiu furioso exigiria uma equipe gigantesca e levaria dias.

O **Analisador de Sentimentos** resolve essa dor: ele funciona como um "leitor inteligente" que processa centenas de diálogos em poucos segundos, classificando cada fala como **Positiva**, **Neutra** ou **Negativa**. 

Além de classificar cada frase isolada, o sistema acompanha a **trajetória da conversa**: ele consegue perceber se um cliente começou tranquilo e foi ficando irritado ao longo do tempo, alertando a gestão sobre atendimentos críticos que exigem socorro imediato.

---

## 🚀 2. O que foi Concluído nesta Etapa?

A aplicação agora conta com o fluxo de ponta a ponta finalizado e funcional:

```
[1. Login Seguro] ➔ [2. Dashboard Geral] ➔ [3. Envio de Arquivos & IA] ➔ [4. Listagem & Filtros] ➔ [5. Raio-X da Conversa]
```

### 🖥️ As 5 Telas em Detalhes:

1. **Portal de Entrada (Login):**
   - Página segura para acesso ao sistema. O lado esquerdo serve como uma vitrine que demonstra exemplos reais de mensagens classificadas (positivas, neutras e alertas de atrito).

2. **Painel Geral (Dashboard):**
   - É o "painel de controle" do gestor.
   - **Indicadores de topo:** Mostram rapidamente o total de conversas no sistema e a porcentagem de atendimentos felizes vs insatisfeitos.
   - **Gráfico de Rosca:** Permite bater o olho e entender a distribuição geral dos sentimentos dos clientes.
   - **Gráfico de Barras de IA:** Compara o desempenho dos diferentes modelos de Inteligência Artificial do projeto (mostrando qual modelo acerta mais).
   - **Tabela de Alertas Críticos:** Lista automaticamente as 5 conversas mais problemáticas que necessitam de intervenção urgente.

3. **Inserir Conversas & Disparar a IA (Upload):**
   - O usuário pode simplesmente arrastar arquivos de planilhas (`.csv`) ou de dados (`.json`) para a tela.
   - Conta com o botão **"Classificar com IA"**: ao clicar, a Inteligência Artificial (modelo *BERTimbau*) lê todas as mensagens pendentes e calcula os sentimentos na hora.

4. **Lista de Conversas (Explorador com Filtros Rápidos):**
   - Uma tabela limpa com todos os atendimentos cadastrados.
   - Botões de filtro em um clique: permite ver apenas conversas que terminaram mal, conversas que tiveram queda de humor ao longo do atendimento, ou conversas que foram um sucesso.

5. **Auditoria e Raio-X do Atendimento (Detalhes):**
   - É a tela mais rica da pesquisa!
   - Apresenta um **Gráfico de Linha da Trajetória Emocional**: uma "montanha-russa" visual que mostra como o cliente se sentiu a cada mensagem enviada.
   - **Destaque do Ponto Crítico (*Turning Point*):** O gráfico coloca uma bolinha de alerta exatamente na mensagem em que o cliente ficou mais chateado, permitindo que o gestor entenda o motivo exato do problema sem precisar ler dezenas de mensagens anteriores.
   - Visualização estilo balões de chat (como no WhatsApp), identificando quem falou o quê e o sentimento de cada frase.

---

## 🎓 3. Como essas Entregas Ajudam no Nosso Artigo Científico?

Para os colegas que estão escrevendo o artigo, o trabalho feito traz contribuições práticas que enriquecem a metodologia e os resultados da publicação:

### A. Interação Humano-Computador (IHC) e Visualização de Dados
- **Problema de Pesquisa:** Como apresentar dados complexos de IA sem sobrecarregar o usuário?
- **Solução apresentada:** Em vez de exibir apenas números brutos de probabilidade, criamos gráficos temporais e cartões com cores intuitivas (verde para positivo, vermelho para negativo). Isso permite provar no artigo que uma boa interface reduz o tempo que um gestor leva para tomar uma decisão.

### B. Inteligência Artificial Explicável (*Explainable AI - XAI*)
- Muitos sistemas de IA são vistos como "caixas pretas" onde ninguém sabe por que a decisão foi tomada.
- No nosso sistema, ao mostrar a timeline mensagem a mensagem e marcar o **pior momento**, a IA "explica" de forma transparente o motivo pelo qual aquele atendimento foi rotulado como negativo.

### C. Comparação Empírica de Modelos
- A interface foi desenhada para comparar visualmente o modelo de dicionário (léxico) com o modelo neural profundo (*BERTimbau*). Isso fornecerá os gráficos e tabelas necessários para a seção de Discussão de Resultados do artigo.

---

## 📚 4. Glossário Rápido para a Equipe do Artigo

Termos e conceitos importantes usados no sistema para referência na escrita acadêmica:

- **BERTimbau:** Modelo avançado de Inteligência Artificial treinado especificamente na língua portuguesa, capaz de entender gírias, ironias e contexto de frases.
- **Delta ($\Delta$) de Sentimento:** Mede a diferença entre como o cliente começou o atendimento e como ele terminou. Se o delta for negativo, significa que a experiência piorou ao longo do chat.
- **Pior Momento (*Turning Point*):** A mensagem exata da conversa com a pontuação emocional mais baixa (pico de frustração do cliente).
- **F1-Score / F1-Macro:** Métrica científica que avalia o equilíbrio entre precisão e sensibilidade da IA. Quanto mais próximo de 100%, melhor o modelo.

---

## 📌 5. Resumo de Status Atual

- **Frontend:** 100% das telas desenhadas no Stitch foram construídas, integradas e estilizadas.
- **Gráficos:** Gráficos responsivos de rosca, barras e linhas temporais plenamente funcionais.
- **Integração:** Conexão estabelecida com a base de dados local e com a rota de classificação da IA.
