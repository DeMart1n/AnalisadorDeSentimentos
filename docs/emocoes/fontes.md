# Fontes de dados de emoção

Nenhum dado destas fontes é commitado. Os comandos de importação baixam para `data/` (no
`.gitignore`) e gravam no `db.sqlite3`, também fora do git.

| Fonte (`Conversa.fonte`) | Status | Licença | Comando |
|---|---|---|---|
| `brighter_ptbr` | importada | CC BY 4.0 | `uv run manage.py importar_brighter` |
| `apps_zenodo` | **rejeitada** | CC BY 4.0 | — |
| `goemotions_pt` | pendente (opcional) | Apache 2.0 (original) | — |

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

Pendente. Falta decidir o tradutor. Mapeamento previsto: o oficial do GoEmotions para Ekman,
com `curiosity`, `confusion` e `realization` fora de surpresa.
