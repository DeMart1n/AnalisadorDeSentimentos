# Modelo IA: cronograma

Período do relatório: **24/09 a 30/09/2026**. Primeiro relatório da série, então o histórico do módulo vem completo.

## Histórico do módulo até aqui

| Data | O quê | Quem | Fonte |
|---|---|---|---|
| 27/08 23:01 | Primeira conversa de teste gravada no banco (`fonte='amostra'`) | Cauã | [A1] |
| 28/08 13:36 | Fim do fine-tune do BERTimbau (1 época, cerca de 46 min, então começou por volta de 12:50) e pesos salvos | Cauã | [A2], [D1] |
| 28/08 14:35 | `metricas.json` gravado só com léxico e TF-IDF | Cauã | [A3] |
| 28/08 17:38 | Primeira conversa de atendimento real importada (3 mensagens, sem rótulo) e classificada | Cauã | [A1] |
| 03/09 | Todo o código do módulo entra no git: três degraus, avaliação, comandos de treino e importação | Cauã | [C1] |
| 09/09 | Relatório por módulo (`03-MODELO-IA.md`) e correção de divergências nos docs | Cauã | [C2] |
| 18/09 09:11 | `models/bertimbau/` alterado. O `model.safetensors` deixa de existir (causa não registrada) | ? | [A2] |
| 23/09 | Anonimizador entra no fluxo de importação e muda o texto que chega ao modelo | Luiz | [C3] |

## Semana 24/09 a 30/09

| Data | O quê | Quem | Fonte |
|---|---|---|---|
| 28/09 | Telas do front, incluindo a que consome `/api/metricas` (só 2 dos 3 degraus aparecem) | Lucas | [C4] |
| 30/09 | Conferência de `03-MODELO-IA.md` contra código, banco e artefatos: 4 divergências (pesos ausentes, split de treino +2, anonimizador não documentado, testes sem `pyjwt`) | Cauã | [D2], [T1] |
| 30/09 | Skill `relatorio-semanal` criada e este relatório gerado com ela | Cauã | [T2] |

Commits no módulo nesta semana: **nenhum**.

## Fontes

**Commits**
- [C1] `a1ac1ae`, 03/09: Commit inicial: analisador de sentimentos em atendimentos
- [C2] `43e88ad` / `2effafd`, 09/09: Relatório do sistema por módulo e correção das divergências nos docs
- [C3] `7b1b901`, 23/09: feat: criar anonimizador e implementar no fluxo de upload/importacao
- [C4] `204ebfa`, 28/09: telas do front end

**Artefatos fora do git (data de modificação)**
- [A1] `db.sqlite3`, tabela `analise_conversa.criada_em`
- [A2] `models/bertimbau/` (pasta: 18/09 09:11; `config.json` e tokenizer: 28/08 13:36)
- [A3] `models/metricas.json` (28/08 14:35)

**Documentos**
- [D1] `SPEC.md:112`: treino de 1 época em 46 min no M4
- [D2] `docs/relatorio/03-MODELO-IA.md`

**Relatórios desta pasta**
- [T1] `tecnico.md`, seção 3
- [T2] `.claude/skills/relatorio-semanal/SKILL.md`
