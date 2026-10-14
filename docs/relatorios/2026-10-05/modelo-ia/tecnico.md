# Modelo IA: relatório técnico (30/09 a 05/10/2026)

Documentos-fonte conferidos: `docs/relatorio/04-MODELO-EMOCOES.md` (novo, ainda com alterações
não commitadas) e as pendências de `docs/relatorio/03-MODELO-IA.md` herdadas do relatório de 30/09.

Limitação desta conferência: o terminal ficou bloqueado na sessão em que este relatório foi
escrito. Git, métricas e histórico foram conferidos lendo os arquivos (`.git/logs/HEAD`,
`models/metricas_emocoes.json`, `models/emocoes/historico.json`). Contagens do banco vêm das
consultas feitas em 30/09 e não foram refeitas hoje. As datas dos artefatos não puderam ser
lidas com `stat`.

## 1. Estado atual

- **Classificador de emoções: treinado e avaliado (configuração A).** BERTimbau multi-rótulo,
  6 emoções de Ekman, treinado com BRIGHTER PT-BR + GoEmotions traduzido. F1 macro **0,448** no
  teste do BRIGHTER (humano, PT-BR) e **0,643** no teste do GoEmotions-PT (mesma distribuição do
  treino, por isso inflado).
- **O modelo quase não prevê neutro:** só 24,7% das mensagens neutras saem sem emoção, nos dois
  testes. Esse é o principal bloqueio para usar o modelo em chat.
- **Polaridade:** split congelado e testes funcionando. O BERTimbau de polaridade **continua sem
  pesos** (não foi retreinado), e por isso a API de classificação segue quebrada.
- **Chat real: nenhum.** As Fases 3 e 4 do plano (anotação humana e pseudo-rótulo) estão paradas
  por falta de dados, não de código.
- **Git:** o resultado do treino, os gráficos, o código dos gráficos e a seção 5 do doc **não
  estão commitados**. `origin/feat/emocoes` está em `1d17290`, 3 commits atrás da `main` local.

## 2. O que foi feito no período

| Commit | O quê |
|---|---|
| `ef0ecf9` | `pyjwt` no `pyproject.toml`; `manage.py test analise` volta a rodar |
| `a65100e` | Guarda de retreino do BERTimbau exige `model.safetensors`; sem pesos, `prever` levanta `RuntimeError` em vez de usar a cabeça aleatória |
| `024e90e` | Split de polaridade congelado em `models/splits/polaridade.json` (chave `fonte:origem_id`); `--fonte` aceita lista |
| `e2da36c` | Docs de polaridade atualizados (split e guarda) |
| `f4eed5c` | Modelo `RotuloEmocao` + migração `0003`: 6 booleanos, `intensidades`, `origem`, `anotador`, `semente_id`; FK `PROTECT` |
| `1c45223` | `importar_brighter` (track B, 4.652 mensagens) e `docs/emocoes/fontes.md` |
| `e91f649` | `docs/emocoes/guia-anotacao.md` e comando `anotacao exportar/importar/kappa` |
| `d9c3842` | `docs/relatorio/04-MODELO-EMOCOES.md` criado |
| `1d17290` | `scripts/goemotions_lotes.py`: subconjunto Ekman (20.596 textos, seed 42), lotes e validação |
| — | Tradução do subconjunto com Claude Sonnet: piloto de 400 local (75 mil tokens, US$ 0,47) e o resto numa sessão na nuvem (26 lotes de 800), entregue numa branch descartável já apagada |
| `26c1f80` | `importar_goemotions` (`[NAME]` → `[NOME]`, split original no `origem_id`) |
| `b019d91` | `analise/modelos/emocoes.py`, `analise/avaliacao_emocoes.py`, `treinar_emocoes`, `avaliar_emocoes` |
| `eac14ee` | Seção 4 do doc de emoções (modelo) |
| não commitado | Histórico de perda e F1 de validação por época; matrizes 2×2 e real × previsto; `.npz` com as probabilidades; `scripts/graficos_emocoes.py`; 9 PNGs em `docs/relatorio/img/emocoes/` |
| não commitado | Treino completo de 05/10: 18.715 exemplos, 2 épocas, 33,3 min em MPS (M4); `models/metricas_emocoes.json` |

Fonte rejeitada: o dataset de reviews de apps (Zenodo 10823148). O texto publicado passou por
stemming, e a emoção é função da polaridade (864 reviews positivos rotulados como tristeza).

### Resultados (`models/metricas_emocoes.json`)

| Emoção | BRIGHTER F1 [IC 95%] | sup. | GoEmotions-PT F1 [IC 95%] | sup. | Limiar |
|---|---|---|---|---|---|
| alegria | 0,673 [0,644; 0,700] | 555 | 0,713 [0,678; 0,744] | 481 | 0,55 |
| raiva | 0,639 [0,612; 0,666] | 699 | 0,692 [0,665; 0,716] | 726 | 0,50 |
| tristeza | 0,587 [0,537; 0,633] | 343 | 0,664 [0,625; 0,700] | 379 | 0,85 |
| medo | 0,346 [0,258; 0,422] | 139 | 0,663 [0,586; 0,730] | 98 | 0,95 |
| surpresa | 0,381 [0,310; 0,453] | 157 | 0,620 [0,550; 0,680] | 141 | 0,90 |
| nojo | 0,062 [0,000; 0,133] | 71 | 0,505 [0,422; 0,585] | 123 | 0,95 |
| **macro / micro** | **0,448 / 0,597** | 2.226 | **0,643 / 0,676** | 2.059 | |

F1 macro na validação, com limiar 0,5: 0,5718 na época 1 e 0,5727 na época 2
(`historico.json`).

## 3. Conferência do documento-fonte (`04-MODELO-EMOCOES.md`)

| Afirmação | Status | Realidade | Fonte |
|---|---|---|---|
| Cabeçalho: "O modelo ainda não foi treinado de verdade (só um teste de fumaça)" | **diverge** | Treinado em 05/10; a própria seção 5 traz os resultados | `models/emocoes/limiares.json`, `metricas_emocoes.json` |
| BRIGHTER 2.226 / 200 / 2.226 | confere | Idem | saída de `importar_brighter` (30/09) |
| GoEmotions-PT 16.489 / 2.048 / 2.059 | confere | Idem | saída de `importar_goemotions` (30/09) |
| Chat real: 0 | confere em 30/09 | Não reconsultado hoje | consulta por fonte em 30/09 |
| Tabela do modelo: max_len 128, BCE com `pos_weight` (teto 50), grade 0,05–0,95, `PESO_FONTE` GoEmotions 0,3, etapa 2 com lr 1e-5 | confere | `self.lr / 2` = 1e-5 | `analise/modelos/emocoes.py:26-27,84,99` |
| Guarda: config + safetensors + limiares | confere | Idem | `emocoes.py:67` |
| Treino 18.715, validação 2.248, 33,3 min | confere | Idem | saída de `treinar_emocoes` (05/10) |
| Limiares 0,55 / 0,50 / 0,85 / 0,95 / 0,90 / 0,95 | confere | Idem | `models/emocoes/limiares.json` |
| Tabela de F1, IC e suporte | confere | Idem, arredondado | `metricas_emocoes.json` |
| "91% da validação vem do GoEmotions" | confere | 2.048 / 2.248 = 91,1% | idem |
| "medo: revocação 0,26 no ponto escolhido" | confere | 36 / 139 = 0,259 | matriz de medo, BRIGHTER |
| "Das neutras, só 24% saem sem emoção; 37–42% viram raiva; 21–30% viram alegria" | **diverge (pouco)** | O doc leu a fração da **linha** do gráfico, que divide por previsões, não por mensagens. Por mensagem: sem emoção 24,7% nos dois; raiva 38,6% (BRIGHTER) e 43,9% (GoEmotions); alegria 31,5% e 21,3% | `coocorrencia` ÷ `neutro_suporte` (616 e 287) |
| "35% do treino acaba com raiva" | **diverge (pouco)** | 34,1% no subconjunto GoEmotions inteiro (7.022 / 20.596) e 32,3% no BRIGHTER treino (718 / 2.226). Não há número exato só do treino, nem do que é sorteado com os pesos | `fontes.md`, `importar_brighter` |
| "2ª época: macro 0,57 → 0,57" | confere | 0,5718 → 0,5727 | `historico.json` |
| "Sem nojo, macro das 5 emoções-alvo = 0,525" | confere | 0,5252 | média dos F1 |

### Pendências do relatório de 30/09

| Pendência | Status |
|---|---|
| P0: pesos do BERTimbau de polaridade | **aberta**. O usuário escolheu adiar; não há registro de retreino |
| P1: `metricas.json` com os 3 degraus | **aberta**. O arquivo ainda só tem léxico e clássico. Depende do P0 |
| P1: congelar o split | **resolvida** (`024e90e`). Suporte 4.689 / 4.785 / 3.141 mantido |
| P2: efeito do anonimizador na polaridade | aberta |
| P2: testes sem `pyjwt` | **resolvida** (`ef0ecf9`). 65 testes passam (saída de 05/10) |

## 4. Riscos e pendências (por custo/benefício)

1. **Commitar o que está solto.** Hoje um `git checkout` perderia o código dos gráficos e os
   resultados.
   `git add analise scripts docs models/metricas_emocoes.json && git commit -m "feat: gráficos e histórico de treino do modelo de emoções; resultados da configuração A"`
   Depois, `git push origin main:feat/emocoes`.
2. **Corrigir o cabeçalho do `04-MODELO-EMOCOES.md`** e os percentuais de neutro (seção 3). Edição de texto.
3. **Neutro e raiva (retreino, ~33 min):** remapear raiva só para `anger` (mais talvez
   `annoyance`, sem `disapproval`). Os rótulos originais estão em `traduzido.jsonl`, então não
   precisa traduzir de novo. Ajustar no script, reimportar e retreinar. No mesmo treino, atenuar o
   `pos_weight` (raiz quadrada) e subir o peso do BRIGHTER.
4. **Limiares só no dev do BRIGHTER (~1 min, sem retreino):** melhora medo e surpresa no
   BRIGHTER. O custo é que o dev tem só 200 exemplos, então o ajuste fica ruidoso.
5. **P0 da polaridade:** `uv run manage.py treinar_bertimbau --epocas 1 --batch 32` (~46 min),
   depois `avaliar --modelos lexico classico bertimbau --salvar`.
6. **Chat real:** sem ele, as Fases 3, 4 e 7 (o `teste_chat`, que é o teste principal) não andam.
   Precisa de um export de conversas. Depois: `importar_conversas` e `anotacao exportar`.
7. Referência citada no plano, não conferida no artigo: o baseline oficial do BRIGHTER PT-BR fica
   em cerca de 0,68 de F1 macro. O 0,448 está bem abaixo, mas o nosso modelo é treinado numa
   mistura com GoEmotions e não foi ajustado para o BRIGHTER.
