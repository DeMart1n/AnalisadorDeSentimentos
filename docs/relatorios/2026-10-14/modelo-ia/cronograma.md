# Modelo IA: cronograma (06/10 a 14/10/2026)

## Histórico do módulo até aqui

| Data | Marco | Fonte |
|---|---|---|
| 03/09 | Commit inicial: escada léxico → TF-IDF → BERTimbau | `a1ac1ae` |
| 28/08–30/09 | Primeiro treino do BERTimbau (F1 0,764); os pesos se perderam depois | `SPEC.md` §8.1; `models/bertimbau/config.json` (28/08) |
| 14/09 | Upload desacoplado da análise | `e0a8166` |
| 30/09 | Guarda de pesos, split congelado, `pyjwt` | `a65100e`, `024e90e`, `ef0ecf9` |
| 30/09 | Base do módulo de emoções: esquema, BRIGHTER, GoEmotions-PT, anotação, modelo | `f4eed5c`, `1c45223`, `e91f649`, `26c1f80`, `b019d91` |
| 05/10 | Primeiro treino completo do modelo de emoções (configuração A) | `models/emocoes/model.safetensors` (05/10 20:54) |
| 13/10 | Diagnóstico da inferência instável; retreino do BERTimbau (F1 0,768) | `models/bertimbau/model.safetensors` (13/10 14:29) |
| 13–14/10 | 160 testes, cobertura de 95%, 6 bugs corrigidos, branch única para a `main` | `558a8e5`, `4fcede7`, `b987f52` |

## Semana

| Data | O quê | Quem | Fonte |
|---|---|---|---|
| 13/10 | Diagnóstico: o `origin/main` não tinha a guarda de pesos, e sem os pesos o modelo classificava de forma aleatória | Cauã | [1], [2] |
| 13/10 | Retreino do BERTimbau: 1 época, 71,1 min, pesos salvos às 14:29 | Cauã | [3] |
| 13/10 | Avaliação dos 3 degraus e `metricas.json` regravado às 14:36 | Cauã | [4] |
| 13/10 | Branch `fix/pesos-bertimbau`: guarda, `pyjwt`, 503, modelo padrão | Cauã | [5] |
| 13/10 | 86 testes novos (cobertura de 73% para 95%) | Cauã | [6] |
| 13/10 | Branch `fix/bugs-ia`: 6 bugs corrigidos e 11 testes de regressão | Cauã | [7] |
| 14/10 | Commit do trabalho das emoções que estava solto (gráficos, histórico, matrizes) | Cauã | [8] |
| 14/10 | Commit do `metricas.json` e do relatório de 05/10 | Cauã | [9], [10] |
| 14/10 | Merge do `origin/main` e da `fix/bugs-ia` na `feat/emocoes-e-correcoes`, com 160 testes passando | Cauã | [11] |

De 06/10 a 12/10 não houve nenhum commit nem artefato no módulo. O commit `0d2880f` (06/10, Lucas
Ciacci) é dos relatórios do front-end, outro módulo.

## Fontes

1. `git diff main origin/main -- analise/modelos/bertimbau.py` (13/10): o `origin/main` não tem `pesos_salvos` nem o `raise` em `prever`
2. `frontend/src/app/upload/page.tsx:49-53`: o frontend envia `modelo: 'bertimbau'`
3. `stat models/bertimbau/model.safetensors` → 2026-10-13 14:29; log do treino "salvo em … (71.1 min)"
4. `stat models/metricas.json` → 2026-10-13 14:36
5. Commits `e924365`, `af3cb7e`, `979c312`
6. Commit `558a8e5`
7. Commit `4fcede7`
8. Commit `48039c4`
9. Commit `dfd892a`
10. Commit `82f0f6f`
11. Commits `fa18163` (merge do `origin/main`) e `b987f52` (merge da `fix/bugs-ia`); `uv run manage.py test analise` → 160 OK
