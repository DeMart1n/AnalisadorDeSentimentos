# Módulo Modelo IA

**Estado: concluído para a v1.** Os três degraus da escada estão implementados, treinados no
mesmo conjunto e comparados por McNemar. É a parte do projeto que entrega o resultado
científico sozinha — o web app é a camada de apresentação em cima disso.

Metodologia completa em [docs/TREINAMENTO.md](../TREINAMENTO.md); números e análise de erro em
[docs/RESULTADOS.md](../RESULTADOS.md). Este documento consolida os estudos que já temos.

## 1. A escada e por que ela existe

A pergunta do artigo é *quanto o transformer realmente compra acima de um baseline barato?*
Cada degrau é um piso para o seguinte: um degrau que não é superado indica erro de processo,
não sucesso do degrau.

| Degrau | Implementação | Treino | Interface comum |
|---|---|---|---|
| 1. Léxico | `modelos/lexico.py` + `lexico_pt.txt` (118 linhas curadas à mão) | nenhum (`treinar()` é no-op) | `treinar(textos, rotulos)` / `prever(textos) → (rotulos, scores)` |
| 2. TF-IDF + LR | `modelos/classico.py`, pipeline scikit-learn | segundos | idem |
| 3. BERTimbau | `modelos/bertimbau.py`, loop PyTorch manual | 46 min em MPS | idem |

`carregar(nome)` resolve pelo `REGISTRO`. O BERTimbau tem import tardio — `torch` demora
segundos a carregar e nem todo comando precisa dele.

### Degrau 1 — Léxico

Tokeniza com `[a-zà-ÿ]+` em minúsculas, soma os pesos do dicionário, e ao encontrar uma negação
(`não, nao, nunca, jamais, nem, nenhum, nenhuma`) **inverte a polaridade dos 3 tokens seguintes**.
Soma > 0 → positivo; < 0 → negativo; = 0 → neutro. `score = abs(soma)` — **não é probabilidade**,
não comparar com o score dos outros degraus.

### Degrau 2 — TF-IDF + Regressão Logística

| Componente | Configuração | Por quê |
|---|---|---|
| `TfidfVectorizer` | `ngram_range=(1,2)`, `min_df=2`, `sublinear_tf=True` | bigramas pegam negação ("não gostei") sem tratamento manual; `min_df=2` corta hapax; `sublinear_tf` amortece repetição |
| `LogisticRegression` | `max_iter=1000`, `class_weight="balanced"` | sem peso, colapsa na classe majoritária |

Mantido também por ser **inspecionável**: `termos_por_classe(n)` devolve os termos de maior
coeficiente por classe — material qualitativo para o artigo que o transformer não dá de graça.

### Degrau 3 — BERTimbau fine-tuned

Base `neuralmind/bert-base-portuguese-cased`: 12 camadas, hidden 768, 12 cabeças, vocabulário
29.794, ~109M parâmetros, com cabeça de 3 classes. Ordem `CLASSES = [positivo, negativo, neutro]`
gravada no `config.json` como `id2label`/`label2id` — os pesos salvos são auto-descritivos.

**Loop de treino escrito à mão em PyTorch**, sem o `Trainer` do `transformers`: evita trazer
`accelerate` + `datasets` como dependência só para isso e deixa explícito o que acontece a cada
passo.

| Hiperparâmetro | Valor |
|---|---|
| `max_len` | 128 tokens (padding fixo, truncamento acima) |
| `batch` | 32 |
| `lr` | 2e-5 |
| Otimizador | AdamW |
| Escalonador | `OneCycleLR`, `pct_start=0.1` (10% de warmup) |
| Perda | `CrossEntropyLoss` com peso de classe |
| Épocas | 2 no código / **1 no resultado atual** |
| Dispositivo | MPS se disponível, senão CPU |

Pesos de classe calculados no próprio `treinar()`: `peso_c = total / (n_classes * contagem_c)`.
Com a distribuição atual o neutro recebe ~1,34 e as demais ~0,88.

**Proteção contra retreino acidental:** `treinar()` é no-op se já existe modelo salvo e
`forcar=False`. Importa porque `avaliar` chama `treinar()` em todos os degraus
indistintamente — sem a guarda, avaliar o BERTimbau retreinaria 46 minutos a cada execução.
Efeito colateral a saber: com `models/bertimbau/` presente, `avaliar` mede os pesos em disco,
não um treino novo. Ao mudar hiperparâmetro, apagar os pesos ou reexecutar `treinar_bertimbau`.

## 2. Dados

Dataset `fredericods/ptbr-sentiment-analysis-datasets` (Kaggle), bases **b2w** e **olist** —
reviews de e-commerce pós-compra em português, nota de 1 a 5. As outras bases do dataset
(`buscape`, `utlc_apps`, `utlc_movies`) são aceitas pelo comando mas ficaram fora: domínios
ainda mais distantes de atendimento.

### Recuperação da classe neutra

O autor do dataset **descarta rating 3** e entrega base binária. Nós recuperamos:

| Rating | Rótulo |
|---|---|
| 1–2 | `negativo` |
| 3 | `neutro` |
| 4–5 | `positivo` |

É a decisão de dados mais consequente do projeto e a origem do principal risco (§5).

### Cada review vira uma conversa de uma mensagem

Duas razões: (1) mantém o split por conversa válido e trivial — não há vazamento possível
dentro de um review de uma mensagem; (2) deixa explícito pelo campo `fonte` que esses dados são
review e **não** atendimento. Nenhum número sobre `fonte='b2w'` pode ser apresentado como
medida do caso de uso.

### Amostragem

Estratificada por classe, `--por-classe 12000`, `--seed 42`:

| Fonte | positivo | negativo | neutro | total |
|---|---|---|---|---|
| b2w | 12.000 | 12.000 | 12.000 | 36.000 |
| olist | 12.000 | 11.407 | 3.664 | 27.071 |
| **total** | **24.000** | **23.407** | **15.664** | **63.071** |

b2w bate o teto nas três classes. Em olist o neutro **acaba** em 3.664 — a base não tem mais
rating 3. É por isso que o conjunto continua desbalanceado apesar da estratificação, e é por
isso que todo modelo aqui usa peso de classe.

Texto: b2w tem 151,5 caracteres em média (máx. 4.134); olist, 78,0 (máx. 208).

## 3. Protocolo de avaliação

Regras da spec, iguais para os três degraus:

- **Split por conversa, nunca por mensagem.** Mensagens da mesma sessão vazam informação. Com
  o dataset público cada conversa tem uma mensagem só, então a regra não muda nada *aqui* — mas
  precisa estar no código *antes* de entrar conversa real, não depois.
- **20% teste, seed 42.** Determinístico: `random.Random(42).shuffle` sobre IDs ordenados.
  Resultado: **50.456 treino / 12.615 teste**.
- **Mesmo conjunto de teste para todos.** `treinar_bertimbau` e `avaliar` usam a mesma
  `dividir_por_conversa` com a mesma seed. É pré-condição do McNemar — `mcnemar()` levanta
  `ValueError` se os `y_true` diferirem.
- **F1 macro é a métrica principal.** Acurácia não conta: base desbalanceada em neutro.
- **Matriz sempre na ordem `positivo, negativo, neutro`**, linhas = verdadeiro.
- **Comparação por McNemar exato**, nunca por diferença de número: `b` = A acertou e B errou,
  `c` = o inverso, `binomtest(b, b+c, 0.5)`.

## 4. Resultados

Conjunto de teste: 12.615 mensagens. Suporte por classe: positivo 4.689, negativo 4.785,
neutro 3.141.

| Degrau | F1 macro | F1 neutro | Acurácia | Custo de treino |
|---|---|---|---|---|
| 1. Léxico | 0,489 | 0,321 | 0,499 | zero |
| 2. TF-IDF + LR | 0,735 | 0,559 | 0,756 | segundos |
| 3. BERTimbau (1 época) | **0,764** | 0,600 | 0,790 | 46 min em MPS |

### Leitura principal — o ganho do transformer é pequeno perto do que ele custa

- Léxico → TF-IDF: **+24,7 pontos** de F1 macro, por segundos de treino.
- TF-IDF → BERTimbau: **+2,9 pontos**, por 46 minutos e 436 MB de pesos.

O salto está entre o degrau 1 e o 2, não entre o 2 e o 3. Em português, nesta tarefa e neste
dado, **um baseline barato e inspecionável chega a 96% do F1 macro do transformer fine-tuned**.
Esse é o resultado mais interessante do projeto para o artigo.

O ganho do degrau 3 se concentra onde deveria — no neutro (0,559 → 0,600) — mas o neutro segue
sendo a classe difícil nos três degraus.

### Matrizes de confusão

**Degrau 1 — Léxico**

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

Modo de falha claro: **o léxico não vê negativo.** Recall 0,340 — 2.745 dos 4.785 negativos
caem em neutro, porque a insatisfação está expressa sem nenhuma palavra do dicionário ("comprei
dia 3 e até hoje nada"). Quando ele *diz* negativo, acerta (precisão 0,780); ele quase nunca diz.
Do lado oposto, o neutro vira lata de lixo (precisão 0,254): toda soma zero cai ali por
construção. É o que se espera de um piso — e por isso ele é útil.

**Degrau 2 — TF-IDF + LR**

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

Duas mudanças de figura: (1) a confusão positivo↔negativo praticamente some — 250 erros em
9.474 exemplos, 2,6%: o modelo aprendeu a polaridade; (2) **todo o erro restante é neutro** —
1.482 dos 3.079 erros confundem uma classe polarizada com neutro, e o neutro verdadeiro se
divide quase igualmente entre positivo (674) e negativo (673) quando erra.

Esse segundo ponto é a evidência quantitativa da limitação declarada: **rating 3 é ambivalente,
não é ausência de sentimento**. Um review nota 3 contém elogio e reclamação, e o modelo tem que
decidir por um. O erro é do rótulo, não do classificador.

**Degrau 3 — BERTimbau**

F1 macro 0,764 · F1 neutro 0,600 · acurácia 0,790.

> A matriz de confusão do BERTimbau **não está em `models/metricas.json`** — a última execução
> de `avaliar --salvar` incluiu apenas léxico e clássico. Os números vêm da execução do treino
> registrada na spec. É a lacuna mais barata de fechar do projeto inteiro.

### Significância estatística (McNemar exato, pareado)

| Comparação | Só A acerta | Só B acerta | p | Veredito |
|---|---|---|---|---|
| léxico × clássico | 1.343 | 4.584 | < 0,0001 | clássico supera |
| léxico × BERTimbau | — | — | < 0,0001 | BERTimbau supera |
| clássico × BERTimbau | — | — | < 0,0001 | BERTimbau supera |

Os três pares se sustentam. Vale registrar o que isso **não** significa: com n = 12.615,
+2,9 pontos de F1 macro é uma diferença **real e pequena**. O teste confirma que o BERTimbau é
melhor; ele não diz que a diferença compense o custo.

(As contagens de discordância dos pares com BERTimbau voltam ao `metricas.json` quando o
comando for reexecutado com os três degraus.)

## 5. Limitações declaradas — não são bugs, são o resultado a reportar

1. **Domínio errado.** b2w e olist são review de e-commerce pós-compra, não diálogo de
   atendimento. A queda ao aplicar em conversa real é esperada e é ela própria um resultado.
2. **O neutro treinado não é o neutro do caso de uso.** Rating 3 é avaliação *morna* — tem
   sentimento, é ambivalente. O neutro que atendimento precisa detectar é *ausência* de
   sentimento ("meu pedido é o 4512"). São fenômenos diferentes com o mesmo nome; o modelo
   aprendeu o primeiro e será cobrado pelo segundo.
3. **Não existe conjunto de teste de domínio.** Sem conversa real anotada pelo grupo — com guia
   de anotação e Kappa entre anotadores — não existe número honesto sobre o caso de uso.
   Repetir isto em todo relatório derivado.
4. **Neutro é a classe difícil nos três degraus** e continua sendo depois do fine-tune (F1
   0,600). O peso de classe atenua, não resolve.
5. **Os indicadores de sessão nunca foram avaliados.** Abertura, encerramento, delta, trocas de
   polaridade e pior momento são calculados, mas não há referência anotada contra a qual
   medi-los. Precisam de conversa real com CSAT ou anotação.
6. **Truncamento em 128 tokens.** Cobre a maioria (b2w ≈ 40 tokens de média, olist metade),
   mas reviews de até 4.134 caracteres são cortados. Custo não medido.

## 6. Custo medido

| | |
|---|---|
| Hardware | MacBook Air M4, 16 GB, backend MPS (sem CUDA no ambiente) |
| Configuração | 1 época, batch 32, `max_len` 128, lr 2e-5 |
| Treino | 50.456 mensagens (~1.577 passos) |
| **Tempo** | **46 minutos** |
| Modelo salvo | 436 MB (`model.safetensors`, float32) |

Os pesos **não estão no repositório** (passam do limite do GitHub) — são artefato
reconstrutível.

## 7. Experimentos pendentes, por custo/benefício

1. **Reavaliar e regravar `metricas.json` com os três degraus.** Fecha a lacuna da matriz do
   BERTimbau e do McNemar completo, e conserta o que a API serve. Custo: uma execução.
2. **2 épocas.** O padrão do código já é 2; o resultado atual é de 1. Custo ~46 min.
3. **`max_len` 256.** Mede quanto o truncamento de reviews longos de b2w está custando.
4. **Conjunto de teste anotado pelo grupo**, com guia de anotação e Kappa. Único item que ataca
   a limitação nº 2, e o mais caro.

Fora do escopo v1 por decisão: LLM zero-shot/few-shot, arquitetura maior que BERT-base,
rótulo indireto via CSAT/NPS.

## Como regenerar tudo

```bash
uv run python -c "import kagglehub; print(kagglehub.dataset_download('fredericods/ptbr-sentiment-analysis-datasets'))"
uv run manage.py importar_kaggle --dir <caminho impresso acima> --bases b2w olist --por-classe 12000 --seed 42
uv run manage.py treinar_bertimbau --epocas 1 --batch 32
uv run manage.py avaliar --modelos lexico classico bertimbau --salvar
```

`--seed` precisa casar entre `treinar_bertimbau` e `avaliar` (padrão 42 nos dois).
