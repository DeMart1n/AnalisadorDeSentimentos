# Módulo Modelo de Emoções

**Estado: em construção (Fases 0–3 do plano, 30/09/2026).** O esquema e o primeiro dataset
público estão prontos. Ainda não há modelo treinado. Falta chat real para anotar.

Classificador **separado** da polaridade (que continua em [03-MODELO-IA.md](03-MODELO-IA.md)).
Taxonomia de Ekman, multi-rótulo: `alegria`, `raiva`, `tristeza`, `medo`, `surpresa`, `nojo`.
Neutro é a ausência de todas.

## 1. Esquema

`RotuloEmocao` (`analise/models.py`) guarda um rótulo por mensagem **e por anotador**. Uma
mensagem pode ter vários rótulos (dois humanos, duas passadas de LLM, o do dataset), e é daí
que sai o Kappa.

| Campo | Conteúdo |
|---|---|
| `mensagem` | FK para `Mensagem`, que já tem conversa, ordem, autor e texto anonimizado |
| `origem` | `humano`, `llm` ou `original_dataset` |
| `anotador` | nome da pessoa, ou modelo + prompt da LLM, ou o nome do dataset |
| 6 booleanos | um por emoção |
| `intensidades` | JSON opcional, 0–3 por emoção (o BRIGHTER traz) |
| `semente_id` | só para dados sintéticos |
| `criado_em` | data do rótulo |

A fonte fica em `Conversa.fonte` (`brighter_ptbr`, `goemotions_pt`, `sintetico` ou a fonte do
chat real). A FK é `PROTECT`: `importar` apaga e recria as mensagens ao reimportar uma
conversa, e isso levaria junto a anotação humana. Com `PROTECT`, a reimportação falha.

## 2. Dados

| Fonte | Mensagens | Status |
|---|---|---|
| BRIGHTER PT-BR | 2.226 treino / 200 dev / 2.226 teste | importado (`importar_brighter`) |
| Reviews de apps (Zenodo) | 3.011 | rejeitado: texto com stemming, rótulo de emoção derivado da polaridade |
| GoEmotions-PT | — | pendente: falta decidir o tradutor |
| Chat real | 0 | **bloqueio: não há conversa real no banco** |

Detalhes e licenças: [docs/emocoes/fontes.md](../emocoes/fontes.md).

O split do BRIGHTER é o original e está gravado no `origem_id`. O split congelado de emoções
(`models/splits/emocoes.json`) será gerado quando entrar o chat real (`teste_chat` e
`treino_chat`) e o sintético (por semente).

## 3. Anotação

Guia: [docs/emocoes/guia-anotacao.md](../emocoes/guia-anotacao.md). Ciclo:

```bash
uv run manage.py anotacao exportar amostra.csv --fontes <fonte do chat> --n 1000
uv run manage.py anotacao importar amostra_ana.csv --anotador ana
uv run manage.py anotacao kappa ana bruno
```

A amostra é estratificada por conversa: uma mensagem de cada conversa por rodada, para que
conversas longas não dominem. Só entram mensagens do cliente; a coluna `anterior` dá o
contexto. Uma linha sem nenhum 1 (nem em `neutro`) é tratada como "não anotada" e pulada, não
como neutra.

## Como regenerar

```bash
uv run manage.py migrate
uv run manage.py importar_brighter   # baixa para data/brighter/ se preciso
```
