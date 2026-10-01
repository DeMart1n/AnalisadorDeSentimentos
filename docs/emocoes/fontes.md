# Fontes de dados de emoção

Nenhum dado destas fontes é commitado. Os comandos de importação baixam para `data/` (no
`.gitignore`) e gravam no `db.sqlite3`, também fora do git.

| Fonte (`Conversa.fonte`) | Status | Licença | Comando |
|---|---|---|---|
| `brighter_ptbr` | importada | CC BY 4.0 | `uv run manage.py importar_brighter` |
| `apps_zenodo` | **rejeitada** | CC BY 4.0 | — |
| `goemotions_pt` | importada (subconjunto traduzido) | Apache 2.0 (original) | `scripts/goemotions_lotes.py` + `importar_goemotions` |

## BRIGHTER PT-BR (SemEval-2025 Task 11)

- Origem: <https://github.com/emotion-analysis-project/SemEval2025-Task11>, arquivos
  `task-dataset/semeval-2025-task11-dataset/track_b/{train,dev,test}/ptbr.csv`.
- Licença: CC BY 4.0 (README do repositório). Exige atribuição: Muhammad et al., *BRIGHTER:
  BRIdging the Gap in Human-Annotated Textual Emotion Recognition Datasets for 28 Languages*, 2025.
- Conteúdo: 2.226 treino / 200 dev / 2.226 teste, 6 emoções de Ekman, multi-rótulo, intensidade 0–3.
  Uso a track B; a presença (intensidade > 0) é idêntica à track A (conferido em 30/09/2026).
- Split original preservado no `origem_id` (`ptbr_{train,dev,test}_track_b_NNNNN`). O `test` é
  o teste secundário.
- Domínio: posts de redes sociais, não atendimento.
- Suporte no treino: raiva 718, alegria 581, tristeza 322, surpresa 153, medo 109, nojo 75,
  neutro 632.
- Anonimização: `anonimizar_texto` alterou 4 de 4.652 textos (telefones).

## Reviews de apps (Siqueira et al., 2024), Zenodo 10.5281/zenodo.10823148

Rejeitada em 30/09/2026 por dois motivos:

1. **O texto está pré-processado**: stemming e remoção de stopwords (ex.: "app bom prát fácil
   entend porém algum vend man…"). O texto original não está publicado, e BERT precisa dele.
2. **A emoção é função da polaridade**: `positive` → só `happiness` (319), `sadness` (864) ou
   `surprise` (4); `negative` → só `anger`, `disgust`, `fear`. Há 864 reviews positivos
   rotulados como tristeza, o que sugere um erro de mapeamento dos rótulos.

Rótulo único por texto (3.011 linhas). Não importar sem o texto bruto e sem uma checagem dos rótulos.

## GoEmotions traduzido

- Origem: <https://github.com/google-research/google-research/tree/master/goemotions>
  (Demszky et al., 2020). 58 mil comentários do Reddit, 27 emoções. Licença Apache 2.0.
- **Mapeamento para Ekman:** o oficial (`ekman_mapping.json`), **exceto surpresa**, que fica
  só com `surprise`. `curiosity`, `confusion` e `realization` não viram surpresa; texto que só
  tem essas três é descartado (4.141 textos). Sem isso, toda pergunta do chat viraria surpresa.
  Cuidado: no mapeamento oficial, `approval`, `admiration` e `caring` entram em alegria e
  `disapproval` e `annoyance` entram em raiva; é uma alegria e uma raiva mais amplas que as do guia.
- **Subconjunto (seed 42):** tudo que tem raiva, medo, surpresa, nojo ou tristeza (13.596), mais
  4.000 só de alegria e 3.000 neutros, num total de 20.596. Split original preservado no
  `origem_id` (`train_<id>`, `dev_<id>`, `test_<id>`): 16.489 / 2.048 / 2.059.
- **Tradução (30/09/2026):** Claude Sonnet, em 26 lotes de 800 numa sessão do Claude Code na nuvem,
  com um prompt que manda preservar o tom, o sarcasmo, os palavrões e os emojis em PT-BR
  informal. Piloto de 400 conferido à mão.
  `scripts/goemotions_lotes.py juntar` valida ids e ordem. 28 linhas ficaram idênticas ao
  original porque são intraduzíveis ("[NAME]!", "RemindMe! 3 days", "XD"); 4 perderam um `[NAME]`.
- Na importação, `[NAME]` vira `[NOME]`, o marcador do nosso anonimizador.
- Suporte: alegria 5.228, raiva 7.022, tristeza 4.032, medo 929, surpresa 1.330, nojo 1.013,
  neutro 3.000.
- Para refazer: `python3 scripts/goemotions_lotes.py lotes`, traduzir os lotes
  (`lote_NNN.pt.jsonl`), `python3 scripts/goemotions_lotes.py juntar` e
  `uv run manage.py importar_goemotions`.
