# Módulo Modelo de Emoções

**Estado: em construção (Fases 0–3 e 6 do plano, 30/09/2026).** Esquema, BRIGHTER, GoEmotions-PT e
o código do modelo estão prontos. O modelo ainda não foi treinado de verdade (só um teste de fumaça). Falta chat real para anotar.

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
| GoEmotions-PT | 16.489 treino / 2.048 dev / 2.059 teste (subconjunto) | importado (`importar_goemotions`), traduzido com Claude Sonnet |
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

## 4. Modelo (`analise/modelos/emocoes.py`)

| Item | Escolha |
|---|---|
| Base | `neuralmind/bert-base-portuguese-cased` |
| Entrada | par (mensagem anterior, mensagem atual), `max_len` 128; sem anterior, o primeiro segmento fica vazio |
| Cabeça | 6 saídas sigmoide |
| Perda | `BCEWithLogitsLoss` com `pos_weight` = neg/pos por emoção, calculado sobre a distribuição **ponderada** do sorteio, com teto de 50 |
| Otimização | AdamW, lr 2e-5, OneCycle (10% de aquecimento), batch 32, 2 épocas |
| Limiares | um por emoção, grade 0,05–0,95, o que maximiza o F1 na validação; salvos em `models/emocoes/limiares.json` |
| Amostragem | `WeightedRandomSampler` com `PESO_FONTE` (GoEmotions-PT 0,3; demais 1) |
| Duas etapas | `--duas-etapas`: depois da etapa 1, 1 época com lr 1e-5 só com exemplos de chat (exige que existam) |
| Guarda | treinado = `config.json` + `model.safetensors` + `limiares.json` |

Os textos já chegam anonimizados, porque os importadores aplicam `anonimizar_texto`.

**Rótulo por mensagem:** se houver mais de um, vale a prioridade humano > dataset original > LLM.
**Split:** o original de cada fonte pública (`train` → treino, `dev` → validação, `test` →
`teste_<fonte>`). Fonte sem split congelado (chat real, sintético) faz `split_emocoes` falhar,
em vez de deixá-la vazar para o treino.

**Avaliação:** `avaliar_emocoes` reporta, **por conjunto de teste e separadamente**, o F1 por
emoção com IC 95% (bootstrap de 1.000 reamostragens), o F1 macro e micro, o suporte e os limiares.
`--salvar` grava em `models/metricas_emocoes.json`.

## 5. Resultados — configuração A (BRIGHTER + GoEmotions-PT), 05/10/2026

Treino: 18.715 exemplos, 2 épocas, batch 32, MPS (MacBook Air M4), **33,3 min**. Validação: 2.248
(BRIGHTER dev 200 + GoEmotions dev 2.048). Limiares escolhidos: alegria 0,55, raiva 0,50,
tristeza 0,85, medo 0,95, surpresa 0,90, nojo 0,95.

| Emoção | BRIGHTER teste: F1 [IC 95%] | suporte | GoEmotions-PT teste: F1 [IC 95%] | suporte |
|---|---|---|---|---|
| alegria | 0,673 [0,643; 0,700] | 555 | 0,713 [0,678; 0,744] | 481 |
| raiva | 0,638 [0,612; 0,666] | 699 | 0,692 [0,665; 0,716] | 726 |
| tristeza | 0,587 [0,537; 0,633] | 343 | 0,664 [0,625; 0,700] | 379 |
| medo | 0,346 [0,258; 0,421] | 139 | 0,663 [0,586; 0,730] | 98 |
| surpresa | 0,381 [0,309; 0,453] | 157 | 0,620 [0,550; 0,680] | 141 |
| nojo | 0,062 [0,000; 0,133] | 71 | 0,505 [0,422; 0,585] | 123 |
| **F1 macro** | **0,448** | 2.226 | **0,643** | 2.059 |
| F1 micro | 0,597 | | 0,676 | |

O teste que importa é o do **BRIGHTER**: anotação humana feita direto em PT-BR. O GoEmotions-PT
está na mesma distribuição do treino (mesma tradução, mesmo mapeamento), por isso o número dele
sai inflado. Mesmo o BRIGHTER ainda é rede social, não chat; o teste principal continua sendo o
`teste_chat`, que ainda não existe.

Leitura dos gráficos (`docs/relatorio/img/emocoes/`):

1. **Neutro quase não é previsto.** Das mensagens neutras, só 24% saem sem emoção nos dois
   testes; 37–42% viram raiva e 21–30% viram alegria. Para chat, onde a maior parte das mensagens
   é neutra ("ok", "segue o comprovante"), este é o problema mais grave.
2. **Raiva absorve tudo.** É a coluna mais escura da matriz real × previsto: 59% do nojo, 35% do
   medo e da surpresa e 29% da tristeza do BRIGHTER são previstos como raiva. Causa provável: o
   mapeamento oficial do GoEmotions joga `annoyance` e `disapproval` em raiva, e 35% do treino
   acaba com raiva.
3. **Limiares ajustados para o GoEmotions.** 91% da validação vem do GoEmotions, por isso os
   limiares de medo, surpresa e nojo ficaram em 0,90–0,95. Nas curvas PR do BRIGHTER, o ponto
   escolhido fica em revocação baixa (medo: 0,26).
4. **Nojo do BRIGHTER não foi aprendido.** A curva PR fica achatada em precisão ~0,15 em
   qualquer limiar: o nojo do BRIGHTER (desprezo, quase sempre junto de raiva) é outro conceito,
   diferente do `disgust` do Reddit. O plano já previa F1 baixo para nojo.
5. **A 2ª época quase não mexeu na validação** (macro 0,57 → 0,57 com limiar 0,5), embora a perda
   tenha continuado a cair. Mais épocas não é a alavanca.

Sem nojo, o macro das 5 emoções-alvo no BRIGHTER é 0,525.

## Como regenerar

```bash
uv run manage.py migrate
uv run manage.py importar_brighter   # baixa para data/brighter/ se preciso
uv run manage.py importar_goemotions # precisa de data/goemotions/traduzido.jsonl (ver fontes.md)
uv run manage.py treinar_emocoes --epocas 2 --batch 32
uv run manage.py avaliar_emocoes --salvar
uv run --with matplotlib python scripts/graficos_emocoes.py   # PNGs em docs/relatorio/img/emocoes/
```
