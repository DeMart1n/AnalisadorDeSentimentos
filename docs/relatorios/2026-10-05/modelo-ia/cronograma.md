# Modelo IA: cronograma

Período do relatório: **30/09 (depois do relatório anterior) a 05/10/2026**. Horários em
Brasília, convertidos dos timestamps de `.git/logs/HEAD`.

## Histórico do módulo até aqui

| Data | O quê | Quem | Fonte |
|---|---|---|---|
| 28/08 | Fine-tune do BERTimbau de polaridade (1 época, 46 min); `metricas.json` gravado só com léxico e TF-IDF | Cauã | [R1] |
| 03/09 | Código do módulo entra no git: três degraus, avaliação e comandos | Cauã | [C0] |
| 09/09 | `03-MODELO-IA.md` e correção de divergências nos docs | Cauã | [R1] |
| 18/09 | O `model.safetensors` do BERTimbau some do disco | ? | [R1] |
| 23/09 | Anonimizador entra no fluxo de importação | Luiz | [R1] |
| 30/09 | Relatório anterior: 4 divergências e plano de emoções | Cauã | [R1] |

## Período 30/09 a 05/10

| Data | O quê | Quem | Fonte |
|---|---|---|---|
| 30/09 20:02 | `pyjwt` adicionado; testes voltam a rodar | Cauã | [C1] |
| 30/09 20:02 | Guarda de retreino exige `model.safetensors` | Cauã | [C2] |
| 30/09 20:04 | Split de polaridade congelado (`polaridade.json`); `--fonte` aceita lista | Cauã | [C3] |
| 30/09 20:05 | Docs de polaridade atualizados | Cauã | [C4] |
| 30/09 20:06 | Esquema `RotuloEmocao` (migração 0003) | Cauã | [C5] |
| 30/09 20:08 | BRIGHTER PT-BR importado (4.652); dataset do Zenodo rejeitado; `fontes.md` | Cauã | [C6], [D2] |
| 30/09 20:09 | Guia de anotação e comando `anotacao` | Cauã | [C7] |
| 30/09 20:09 | `04-MODELO-EMOCOES.md` criado | Cauã | [C8] |
| 30/09 | Piloto de tradução: 400 textos com Claude Sonnet, 75 mil tokens, US$ 0,47 | Cauã | [D2] |
| 30/09 20:24 | Script do subconjunto do GoEmotions; push de `feat/emocoes` | Cauã | [C9], [G1] |
| 30/09 20:24–22:28 | Tradução de 20.596 textos numa sessão do Claude Code na nuvem; branch descartável conferida e apagada | Cauã | [D2] |
| 30/09 22:28 | GoEmotions-PT importado (20.596) | Cauã | [C10] |
| 30/09 22:34 | Classificador de emoções e comandos de treino e avaliação (teste de fumaça com 64 exemplos) | Cauã | [C11] |
| 30/09 22:34 | Seção do modelo no doc de emoções | Cauã | [C12] |
| 05/10 noite | Histórico de treino, matrizes e script de gráficos (não commitado) | Cauã | [A4] |
| 05/10 noite | Treino completo, 2 épocas, 33,3 min; avaliação: F1 macro 0,448 (BRIGHTER) e 0,643 (GoEmotions-PT); 9 gráficos | Cauã | [A1], [A2], [A3] |
| 05/10 | Seção 5 (resultados) do `04-MODELO-EMOCOES.md` (não commitada) e este relatório | Cauã | [D1], [T1] |

Commits no módulo no período: **12**, todos em 30/09. O trabalho de 05/10 ainda não foi commitado.

## Fontes

**Commits** (`.git/logs/HEAD`)
- [C0] `a1ac1ae`, 03/09: Commit inicial
- [C1] `ef0ecf9`: chore: adicionar pyjwt às dependências
- [C2] `a65100e`: fix: guarda de retreino do BERTimbau checa model.safetensors
- [C3] `024e90e`: feat: congelar split de polaridade
- [C4] `e2da36c`: docs: split congelado e guarda de pesos
- [C5] `f4eed5c`: feat: modelo RotuloEmocao
- [C6] `1c45223`: feat: importar_brighter e registro de fontes
- [C7] `e91f649`: feat: guia de anotação e comando anotacao
- [C8] `d9c3842`: docs: relatório do módulo de emoções
- [C9] `1d17290`: feat: script de subconjunto e lotes do GoEmotions
- [C10] `26c1f80`: feat: importar_goemotions
- [C11] `b019d91`: feat: classificador de emoções multi-rótulo
- [C12] `eac14ee`: docs: modelo de emoções no relatório

**Git remoto**
- [G1] `.git/logs/refs/remotes/origin/feat/emocoes`: push de `1d17290` em 30/09 20:24

**Artefatos fora do git** (datas sem `stat`; terminal bloqueado na sessão)
- [A1] `models/emocoes/` (pesos, `limiares.json`, `historico.json`, `predicoes_*.npz`)
- [A2] `models/metricas_emocoes.json`
- [A3] `docs/relatorio/img/emocoes/*.png`
- [A4] `scripts/graficos_emocoes.py` e alterações em `analise/` (não commitados)

**Documentos**
- [D1] `docs/relatorio/04-MODELO-EMOCOES.md`
- [D2] `docs/emocoes/fontes.md`

**Relatórios**
- [R1] `docs/relatorios/2026-09-30/modelo-ia/` (tecnico.md e cronograma.md)
- [T1] `tecnico.md` desta pasta, seção 3
