# Treinamento

Tudo neste documento é reprodutível a partir do repositório. O treino acontece **fora do
Django em runtime** — é um comando de gerenciamento offline, nunca uma request.

## 1. Dados

### Origem

Dataset `fredericods/ptbr-sentiment-analysis-datasets` (Kaggle), bases **b2w** e **olist**.
São reviews de e-commerce pós-compra em português, com nota de 1 a 5.

As outras bases do dataset (`buscape`, `utlc_apps`, `utlc_movies`) estão aceitas pelo comando
mas ficaram fora: são domínios ainda mais distantes de atendimento.

### Recuperação da classe neutra

O autor do dataset **descarta rating 3** e entrega uma base binária. Nós recuperamos o 3
como neutro, porque o projeto precisa de três classes:

| Rating | Rótulo |
|---|---|
| 1–2 | `negativo` |
| 3 | `neutro` |
| 4–5 | `positivo` |

Essa é a decisão de dados mais consequente do projeto e a origem do principal risco (§5).

### Cada review vira uma conversa de uma mensagem

`importar_kaggle.py` grava cada review como uma `Conversa` com uma única `Mensagem` de
`autor=usuario`. Duas razões:

1. Mantém o split por conversa válido e trivial — não há vazamento possível entre treino e
   teste dentro de um review de uma mensagem só.
2. Deixa explícito, pelo campo `fonte`, que esses dados são review e **não** atendimento.
   Nenhum número gerado sobre `fonte='b2w'` pode ser apresentado como medida do caso de uso.

### Amostragem

Amostra estratificada por classe, `--por-classe 12000`, `--seed 42`. Resultado no banco:

| Fonte | positivo | negativo | neutro | total |
|---|---|---|---|---|
| b2w | 12.000 | 12.000 | 12.000 | 36.000 |
| olist | 12.000 | 11.407 | 3.664 | 27.071 |
| **total** | **24.000** | **23.407** | **15.664** | **63.071** |

b2w bate o teto nas três classes. Em olist o neutro **acaba** em 3.664 — a base não tem mais
rating 3. É por isso que o conjunto final continua desbalanceado apesar da amostragem
estratificada, e é por isso que todo modelo treinado aqui usa peso de classe.

Estatística de texto: b2w tem 151,5 caracteres em média (máx. 4.134); olist, 78,0 (máx. 208).

### Reconstruir a base do zero

```bash
uv run python -c "import kagglehub; print(kagglehub.dataset_download('fredericods/ptbr-sentiment-analysis-datasets'))"
uv run manage.py importar_kaggle --dir <caminho impresso acima> --bases b2w olist --por-classe 12000 --seed 42
```

O comando é idempotente por fonte: apaga as conversas daquela `fonte` antes de gravar.

## 2. Split

Regra da spec, obrigatória para os três degraus:

- **Split por conversa, nunca por mensagem.** Mensagens da mesma sessão vazam informação entre
  treino e teste. Com o dataset público cada conversa tem uma mensagem só, então a regra não
  muda nada aqui — mas ela precisa estar no código *antes* de entrar conversa real de verdade,
  não depois.
- **Proporção 20% teste, seed 42.** Determinístico: `random.Random(42).shuffle` sobre a lista
  ordenada de IDs de conversa.
- **Mesmo conjunto de teste para todos os modelos.** `treinar_bertimbau` e `avaliar` usam a
  mesma função `dividir_por_conversa` com a mesma seed, por isso o conjunto de teste do
  BERTimbau nunca entra no treino dele e é idêntico ao dos baselines. Isso é pré-condição do
  McNemar — `mcnemar()` levanta `ValueError` se os `y_true` diferirem.

Resultado: **50.456 de treino, 12.615 de teste**.

## 3. Os três degraus

A escada existe para responder uma pergunta do artigo: *quanto o transformer realmente compra
acima de um baseline barato?* Um degrau que não é superado indica erro no processo, não
sucesso do degrau.

### Degrau 1 — Léxico (piso, sem treino)

`analise/modelos/lexico.py`. Dicionário curado à mão em `lexico_pt.txt` (118 linhas, formato
`palavra peso`, peso negativo = polaridade negativa), focado em vocabulário de atendimento.

Algoritmo:
1. Tokeniza com `[a-zà-ÿ]+` em minúsculas.
2. Soma os pesos dos tokens encontrados.
3. Ao encontrar uma negação (`não, nao, nunca, jamais, nem, nenhum, nenhuma`), **inverte a
   polaridade dos 3 tokens seguintes** (`JANELA_NEGACAO = 3`).
4. Soma > 0 → positivo; < 0 → negativo; = 0 → neutro. O `score` é `abs(soma)`.

`treinar()` é no-op — existe só para manter a interface.

Limitação assumida: lista curada pequena. A troca por OpLexicon ou SentiLex-PT está marcada
no arquivo, e só vale a pena se o piso ficar fraco a ponto de deixar de ser informativo.

### Degrau 2 — TF-IDF + Regressão Logística

`analise/modelos/classico.py`. Pipeline scikit-learn:

| Componente | Configuração | Por quê |
|---|---|---|
| `TfidfVectorizer` | `ngram_range=(1,2)`, `min_df=2`, `sublinear_tf=True` | bigramas capturam negação ("não gostei") sem tratamento manual; `min_df=2` corta hapax; `sublinear_tf` amortece repetição |
| `LogisticRegression` | `max_iter=1000`, `class_weight="balanced"` | sem o peso, o modelo colapsa na classe majoritária |

Este degrau é mantido também por ser **inspecionável**: `termos_por_classe(n)` devolve os
termos de maior coeficiente por classe, o que dá material qualitativo para o artigo que o
transformer não dá de graça.

### Degrau 3 — BERTimbau fine-tuned (alvo)

`analise/modelos/bertimbau.py`. Base: `neuralmind/bert-base-portuguese-cased`
(12 camadas, hidden 768, 12 cabeças de atenção, vocabulário 29.794 — ~109M parâmetros),
com cabeça de classificação de 3 classes.

Ordem das classes fixada em `CLASSES = [positivo, negativo, neutro]` e gravada no
`config.json` como `id2label`/`label2id`, para que os pesos salvos sejam auto-descritivos.

**Loop de treino escrito à mão em PyTorch**, sem o `Trainer` do `transformers`. O motivo é
não trazer `accelerate` + `datasets` como dependência só para isso, e deixar explícito o que
acontece a cada passo.

#### Hiperparâmetros

| Parâmetro | Valor | Nota |
|---|---|---|
| `max_len` | 128 tokens | padding para tamanho fixo, truncamento acima disso |
| `batch` | 32 | |
| `lr` | 2e-5 | |
| Otimizador | AdamW | |
| Escalonador | `OneCycleLR`, `pct_start=0.1` | 10% de warmup, depois decaimento |
| Perda | `CrossEntropyLoss` com peso de classe | |
| Épocas | 2 (padrão) / **1 (resultado atual)** | |
| Dispositivo | MPS se disponível, senão CPU | sem CUDA no ambiente de desenvolvimento |

#### Pesos de classe

Calculados no próprio `treinar()`, a partir da distribuição do conjunto de treino:

```
peso_c = total / (n_classes * contagem_c)
```

Com a distribuição da §1, o neutro recebe peso ~1,34 e as demais ~0,88. Sem isso o modelo
abandona a classe minoritária — é o risco declarado na spec, tratado com a técnica mais barata
antes de considerar qualquer coisa mais cara.

#### Truncamento

`max_len=128` cobre a maioria dos textos (média de 151 caracteres em b2w ≈ 40 tokens; olist é
metade disso). Reviews longos de b2w — até 4.134 caracteres — são truncados. Subir `max_len`
é o primeiro experimento pendente, junto com a 2ª época.

#### Proteção contra retreino acidental

`treinar()` é **no-op se já existe modelo salvo** em `models/bertimbau/` e `forcar=False`.
Isso importa porque `avaliar` chama `treinar()` em todos os degraus indistintamente: sem essa
guarda, avaliar o BERTimbau retreinaria 46 minutos de modelo a cada execução. Só
`treinar_bertimbau` passa `forcar=True`.

Efeito colateral a saber: se `models/bertimbau/` existe, `avaliar --modelos bertimbau` mede os
pesos que estão em disco, não um treino novo. É o comportamento desejado, mas significa que os
pesos precisam ser apagados (ou `treinar_bertimbau` reexecutado) ao mudar hiperparâmetro.

### Executar o treino

```bash
uv run manage.py treinar_bertimbau --epocas 1 --batch 32
```

Flags: `--fonte` limita a uma base, `--seed` deve casar com a de `avaliar`, `--amostra N`
limita o treino a N mensagens (útil para teste de fumaça em CPU).

Saída: progresso a cada 100 passos com época, passo/total, perda e minutos decorridos. Ao
final, `save_pretrained` do modelo e do tokenizer em `models/bertimbau/`.

### Custo medido

| | |
|---|---|
| Hardware | MacBook Air M4, 16 GB, backend MPS |
| Configuração | 1 época, batch 32, `max_len` 128, lr 2e-5 |
| Conjunto de treino | 50.456 mensagens (~1.577 passos) |
| **Tempo** | **46 minutos** |
| Tamanho do modelo salvo | 436 MB (`model.safetensors`, float32) |

## 4. Avaliação

```bash
uv run manage.py avaliar --modelos lexico classico bertimbau --salvar
```

O comando: carrega as mensagens de usuário com `rotulo_real`, divide por conversa, treina cada
degrau no mesmo treino, prevê no mesmo teste e imprime F1 macro, `classification_report` e
matriz de confusão; depois roda McNemar em todos os pares. Com `--salvar`, grava
`models/metricas.json`, que é o que `GET /api/metricas` devolve.

Regras (as três valem igualmente para os três degraus):

- **F1 macro é a métrica principal.** Acurácia não conta — a base é desbalanceada em neutro e
  um modelo que ignore a classe minoritária ainda pontua bem em acurácia.
- **Matriz de confusão sempre na ordem `positivo, negativo, neutro`.**
- **Comparação entre modelos por McNemar exato**, nunca por diferença de número. Conta só onde
  os dois discordam: `b` = A acertou e B errou, `c` = o inverso; `binomtest(b, b+c, 0.5)`.
  `p < 0,05` autoriza afirmar que um supera o outro.

Resultados em [RESULTADOS.md](RESULTADOS.md).

## 5. Limitações do treino, declaradas

Estas não são bugs. São o resultado a reportar no artigo.

1. **Domínio errado.** b2w e olist são review de e-commerce pós-compra, não diálogo de
   atendimento. A queda ao aplicar em conversa real é esperada.
2. **O neutro treinado não é o neutro do caso de uso.** Rating 3 é avaliação *morna* — tem
   sentimento, é ambivalente. O neutro que atendimento precisa detectar é *ausência* de
   sentimento ("meu pedido é o 4512"). O modelo aprendeu a primeira coisa e será cobrado pela
   segunda. Esta é a principal razão para o conjunto de teste anotado manualmente pelo grupo.
3. **Não existe conjunto de teste de domínio.** Enquanto não houver conversa real anotada, os
   números medem a base pública, não o caso de uso. Registrar em todo relatório.
4. **Neutro é a classe difícil nos três degraus** e continua sendo depois do fine-tune
   (F1 0,60). O peso de classe atenua, não resolve.

## 6. Experimentos pendentes

Em ordem de custo/benefício, antes de considerar arquitetura maior:

1. **2 épocas** — o padrão do código já é 2; o resultado atual é de 1. Custo: ~46 min.
2. **`max_len` 256** — mede quanto o truncamento de reviews longos de b2w está custando.
3. **Reavaliar e regravar `metricas.json` com os três degraus.** O arquivo em disco hoje tem só
   léxico e clássico: a última execução com `--salvar` não incluiu o BERTimbau.
4. **Conjunto de teste anotado pelo grupo**, com guia de anotação e Kappa entre anotadores.
   É o único item que ataca a limitação nº 2, e o mais caro.
