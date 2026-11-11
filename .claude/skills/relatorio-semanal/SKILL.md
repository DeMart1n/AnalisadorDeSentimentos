---
name: relatorio-semanal
description: Gera o relatório semanal de um módulo do projeto (modelo-ia, backend, frontend...) em 3 arquivos — técnico, não técnico (pra leigos) e cronograma dia a dia com fontes — numa pasta datada em docs/relatorios/. Antes de escrever, confere o documento do módulo contra o código e o banco. Trigger: /relatorio-semanal, "relatório da semana", "o que fizemos na semana".
---

# Relatório semanal por módulo

Entrada: `$ARGUMENTS` = `<modulo> [caminho do .md do módulo] [--desde AAAA-MM-DD]`.
- `modulo`: slug da pasta (`modelo-ia`, `backend`, `frontend`, `visao-geral`). Se faltar, perguntar.
- `.md`: documento do módulo (padrão: `docs/relatorio/NN-<MODULO>.md`).
- `--desde`: início do período (padrão: 7 dias antes de hoje).

Saída: `docs/relatorios/<AAAA-MM-DD de hoje>/<modulo>/` com exatamente:
- `tecnico.md`, `leigo.md`, `cronograma.md`.

Nunca sobrescrever uma pasta de data anterior — elas são o histórico do avanço. Se a de hoje já existir, atualizar só ela.

## 1. Levantar fontes (antes de escrever qualquer coisa)

- `git log --since=<desde> --date=short --pretty='%h %ad %an %s' --stat` — o que entrou na semana, de quem.
- `git log --date=short -- <arquivos do módulo>` — histórico do módulo.
- Artefatos fora do git (pesos, `models/metricas.json`, `db.sqlite3`): `stat -f '%Sm %N'` dá a data real de quando foram gerados. Usar isso no cronograma quando o git não cobre.
- A pasta de relatório anterior mais recente em `docs/relatorios/` (se houver): o que mudou desde ela.

## 2. Conferir o documento contra a realidade

Todo número e afirmação do `.md` do módulo é hipótese até ser checado. Para cada um:
- Hiperparâmetros, nomes, caminhos → ler o código citado.
- Números de dados (contagens, splits, médias) → consultar o banco (`sqlite3 db.sqlite3` ou `uv run python` com `django.setup()`).
- Métricas → `models/metricas.json`.
- Artefatos citados (pesos, arquivos) → existem no disco? carregam?
- O que mudou no projeto depois da data do documento e ele não menciona (commits de outros módulos que afetam este).

Classificar cada item: **confere** / **diverge** (com o valor real e a fonte) / **não verificável** (e por quê). Não editar o `.md` de origem — as divergências vão no relatório técnico; corrigir o doc só se o usuário pedir.

## 3. Escrever os três relatórios

Regras comuns: PT-BR, fato em vez de adjetivo, número com fonte, e sempre uma seção do que **não** andou ou está quebrado. Semana sem commit no módulo se diz com essas palavras.

### tecnico.md
1. Estado atual em 3–5 linhas (o que funciona hoje, o que não).
2. O que foi feito na semana (com commit/arquivo).
3. Conferência do documento-fonte: tabela `afirmação | status | realidade | fonte (arquivo:linha, commit, comando)`.
4. Riscos e pendências, ordenados por custo/benefício, cada um com o comando ou passo que resolve.

### leigo.md
Para quem não é da área (professor de outra disciplina, família, banca geral).
- Sem nome de arquivo, biblioteca, métrica em sigla. Traduz o efeito: "acerta 3 de cada 4 mensagens" em vez de "F1 0,76".
- Uma analogia no máximo.
- Ordem: o que o sistema faz → o que avançou → o que falta e por quê.
- Até ~1 página. Se a skill `humanizer` estiver disponível, passar o texto por ela.

### cronograma.md
- Tabela dia a dia do período: `data | o quê | quem | fonte`. Dia sem nada: omitir, não inventar.
- Antes da tabela da semana, o histórico do módulo até aqui (marcos com data), pra mostrar o avanço.
- Seção **Fontes** no fim: commits (hash), arquivos, docs e datas de artefato usados. Toda linha da tabela aponta para uma delas.

## 4. Fechar

No chat: caminho da pasta criada e a lista curta de divergências encontradas. Nada de repetir o conteúdo dos relatórios.
