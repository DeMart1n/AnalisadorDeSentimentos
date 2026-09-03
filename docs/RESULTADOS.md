# Resultados

Todos os números abaixo vêm do mesmo conjunto de teste: **12.615 mensagens**, split por
conversa com `seed=42`, sobre b2w + olist (63.071 reviews). Nenhum modelo viu esse conjunto
durante o treino.

Metodologia, hiperparâmetros e limitações do dado em [TREINAMENTO.md](TREINAMENTO.md).

## Resumo da escada

| Degrau | F1 macro | F1 neutro | Acurácia | Custo de treino |
|---|---|---|---|---|
| 1. Léxico | 0,489 | 0,321 | 0,499 | zero (sem treino) |
| 2. TF-IDF + LR | 0,735 | 0,559 | 0,756 | segundos |
| 3. BERTimbau (1 época) | **0,764** | 0,600 | 0,790 | 46 min em MPS |

Suporte por classe no teste: positivo 4.689, negativo 4.785, neutro 3.141.

## Leitura principal

**O ganho do transformer é pequeno perto do que ele custa.**

- Léxico → TF-IDF: **+24,7 pontos** de F1 macro, por segundos de treino.
- TF-IDF → BERTimbau: **+2,9 pontos**, por 46 minutos de treino e 436 MB de pesos.

O salto está entre o degrau 1 e o 2, não entre o 2 e o 3. Esse é o resultado mais interessante
do projeto para o artigo: em português, nesta tarefa e neste dado, um baseline barato e
inspecionável chega a 96% do F1 macro do transformer fine-tuned.

O ganho do degrau 3 se concentra onde deveria — no **neutro** (0,559 → 0,600) — mas o neutro
segue sendo a classe difícil nos três degraus.

## Matrizes de confusão

Linhas = verdadeiro, colunas = predito. Ordem: positivo, negativo, neutro.

### Degrau 1 — Léxico

|  | → positivo | → negativo | → neutro |
|---|---|---|---|
| **positivo** | **3.303** | 114 | 1.272 |
| **negativo** | 414 | **1.626** | 2.745 |
| **neutro** | 1.430 | 345 | **1.366** |

| Classe | Precisão | Recall | F1 |
|---|---|---|---|
| positivo | 0,642 | 0,704 | 0,672 |
| negativo | 0,780 | 0,340 | 0,473 |
| neutro | 0,254 | 0,435 | 0,321 |

O modo de falha é claro e esperado: **o léxico não vê negativo**. Recall de 0,340 — 2.745 dos
4.785 negativos caem em neutro, porque a insatisfação está expressa sem nenhuma palavra do
dicionário ("comprei dia 3 e até hoje nada"). Quando o léxico *diz* negativo ele acerta
(precisão 0,780); ele simplesmente quase nunca diz.

Do lado oposto, o neutro vira lata de lixo: precisão 0,254. Toda soma zero — texto sem palavra
conhecida — cai ali por construção do algoritmo.

Isso é o que se espera de um piso, e é por isso que ele é útil: qualquer modelo treinado que
não supere 0,489 tem erro de processo, não problema de modelo.

### Degrau 2 — TF-IDF + Regressão Logística

|  | → positivo | → negativo | → neutro |
|---|---|---|---|
| **positivo** | **3.645** | 163 | 881 |
| **negativo** | 87 | **4.097** | 601 |
| **neutro** | 674 | 673 | **1.794** |

| Classe | Precisão | Recall | F1 |
|---|---|---|---|
| positivo | 0,827 | 0,777 | 0,802 |
| negativo | 0,831 | 0,856 | 0,843 |
| neutro | 0,548 | 0,571 | 0,559 |

Duas coisas mudam de figura:

1. **A confusão positivo↔negativo praticamente some.** 163 + 87 = 250 erros entre os dois
   polos, em 9.474 exemplos — 2,6%. O modelo aprendeu a polaridade.
2. **Todo o erro restante é neutro.** 1.482 dos 3.079 erros envolvem confundir uma classe
   polarizada com neutro, e o neutro verdadeiro se divide quase igualmente entre positivo (674)
   e negativo (673) quando erra.

Esse segundo ponto é a evidência quantitativa da limitação declarada na spec: **rating 3 é
ambivalente, não é ausência de sentimento**. Um review nota 3 contém elogio e reclamação, e o
modelo tem que decidir por um dos dois. O erro é do rótulo, não do classificador.

### Degrau 3 — BERTimbau

F1 macro 0,764 · F1 neutro 0,600 · acurácia 0,790.

> A matriz de confusão do BERTimbau **não está em `models/metricas.json`**: a última execução
> de `avaliar --salvar` incluiu apenas léxico e clássico. Os números acima vêm da execução do
> treino registrada na spec. Reexecutar `avaliar --modelos lexico classico bertimbau --salvar`
> para fechar essa lacuna — é o item 3 dos experimentos pendentes.

## Significância estatística (McNemar)

Teste exato pareado sobre o mesmo conjunto de teste, contando apenas onde os modelos discordam.

| Comparação | Só A acerta | Só B acerta | p | Veredito |
|---|---|---|---|---|
| léxico × clássico | 1.343 | 4.584 | < 0,0001 | clássico supera |
| léxico × BERTimbau | — | — | < 0,0001 | BERTimbau supera |
| clássico × BERTimbau | — | — | < 0,0001 | BERTimbau supera |

Os três pares se sustentam estatisticamente. Vale registrar o que isso significa e o que não
significa: com n = 12.615, **+2,9 pontos de F1 macro é uma diferença real e pequena**. O teste
confirma que o BERTimbau é melhor; ele não diz que a diferença compense o custo.

(Os pares com BERTimbau vêm da execução registrada na spec; as contagens de discordância
voltam ao `metricas.json` quando o comando for reexecutado com os três degraus.)

## O que estes números *não* medem

Repetir isto em qualquer relatório derivado deste documento:

1. **Não medem atendimento.** O dado é review de e-commerce pós-compra, uma mensagem por
   "conversa". Não há diálogo, não há trajetória, não há contexto de sessão. A queda ao aplicar
   em conversa real é esperada e é ela própria um resultado a reportar.
2. **Não medem o neutro que interessa.** O modelo aprendeu neutro = nota 3 = avaliação morna.
   O caso de uso precisa de neutro = ausência de sentimento ("meu pedido é o 4512"). São
   fenômenos diferentes com o mesmo nome.
3. **Não há conjunto de teste de domínio.** Sem conversa real anotada pelo grupo — com guia de
   anotação e Kappa entre anotadores — não existe número honesto sobre o caso de uso.
4. **Os indicadores de sessão nunca foram avaliados.** Abertura, encerramento, delta, trocas de
   polaridade e pior momento são calculados, mas não existe referência anotada contra a qual
   medi-los. Precisam de conversa real com CSAT ou anotação.

## Como regenerar

```bash
uv run manage.py avaliar --modelos lexico classico bertimbau --salvar
```

Sobrescreve `models/metricas.json`, que é servido por `GET /api/metricas`. Sem `--salvar`, só
imprime. `--seed` precisa casar com a usada em `treinar_bertimbau` (padrão 42 nos dois).
