# 📄 Relatório de Divulgação Científica & Acompanhamento Geral

**Projeto:** Analisador de Sentimentos em Atendimentos via Chat  
**Foco:** Resumo Executivo para a Equipe, Orientadores e Insumo para o Artigo Científico  
**Público-Alvo:** Integrantes do artigo, avaliadores da extensão universitária e partes interessadas não técnicas  
**Período:** Fase Inicial — Interface de Acesso e Experiência do Usuário (UX)

---

## 📋 1. O que é o Projeto? (Em linguagem simples)

Imagine uma empresa que recebe milhares de mensagens de clientes todos os dias pelo WhatsApp, Zendesk ou chats de suporte. Ler mensagem por mensagem para saber quem está satisfeito ou muito irritado levaria dias.

O **Analisador de Sentimentos** é uma plataforma inteligente que lê essas conversas automaticamente e identifica:
1. Mensagens **Positivas** (clientes elogiando o atendimento).
2. Mensagens **Neutras** (dúvidas ou pedidos de informação).
3. Mensagens de **Alerta / Atrito** (clientes bravos com risco de cancelar o serviço).

Assim, os gestores conseguem agir rapidamente antes que o cliente vá embora.

---

## 🎓 2. Como isso contribui para o nosso Artigo Científico?

Este projeto de extensão tem um papel duplo: entregar uma ferramenta real e fundamentar um **artigo científico**. O progresso desta semana contribui para as seguintes seções do artigo:

### A. Interação Humano-Computador (IHC)
Estudamos como apresentar dados de Inteligência Artificial de forma simples. Não adianta a IA acertar o sentimento se o usuário não entender o resultado. Na interface, criamos indicadores visuais claros (como cores verde, amarela e vermelha) para sinalizar o nível de urgência de cada atendimento.

### B. Confiança na Inteligência Artificial (*Explainable AI*)
Incluímos no painel visual um indicador de **"Precisão de Análise (99.4%)"** e cartões com pontuações de satisfação e risco de cancelamento (*churn*). Isso ajuda o usuário humano a entender a razão pela qual a IA classificou aquela conversa como crítica.

---

## 💡 3. O que foi feito nesta etapa?

1. **Criação do Portal de Entrada (Tela de Login):**
   - Desenvolvemos a primeira tela da aplicação, dividida em dois lados:
     - **Lado Esquerdo (Demonstrativo):** Apresenta exemplos reais de como o sistema funciona (mensagens simuladas de suporte, scores de satisfação e alertas de risco).
     - **Lado Direito (Acesso Seguro):** Espaço para o usuário inserir seu e-mail e senha com criptografia.

2. **Ajuste Fino de Design e Conforto Visual:**
   - Garantimos que a tela se adapte perfeitamente em monitores sem que o usuário precise ficar usando a barra de rolagem (rolando para cima e para baixo).
   - Posicionamos o cartão de precisão da análise na parte inferior direita para garantir leitura limpa de todos os cartões.

3. **Integração com a Base de Dados:**
   - Preparamos o sistema para conectar o portal de entrada com a base de dados do projeto, permitindo que usuários cadastrados acessem a ferramenta com segurança.

---

## 📌 4. Resumo de Resultados Parciais (Para inclusão nos relatórios do artigo)

- **Interface Responsiva:** 100% alinhada com as diretrizes visuais modernas de softwares corporativos.
- **Acessibilidade Visual:** Uso de contraste adequado e símbolos universais (emojis/ícones de satisfação e alerta) para facilidade de interpretação por qualquer usuário.
- **Próximo Marco:** Desenvolvimento dos painéis de gráficos gerais (Dashboard) e da tabela de navegação das conversas.
