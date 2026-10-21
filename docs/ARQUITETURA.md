# Arquitetura

## Visão geral

```
Next (frontend, não implementado)
        ↓  HTTP/JSON
Django  ──  analise/views.py      (4 endpoints)
              ↓
            importacao.py         (CSV/JSON → banco, transação atômica)
            classificador.py      (cache de módulo do modelo)
            indicadores.py        (trajetória da conversa, calculada por consulta)
            avaliacao.py          (split, F1 macro, McNemar)
              ↓
            modelos/              (lexico | classico | bertimbau)
              ↓
            SQLite  +  models/bertimbau/ (pesos em disco)
```

Um único app Django (`analise`). A inferência saiu da request: `POST /api/conversas/analisar`
divide as conversas em lotes de 50 (`LOTE_CONVERSAS`), enfileira um `group` do Celery
(`analise/tasks.py: classificar_lote`) e responde 202 com `tarefa_id`; o progresso sai de
`GET /api/conversas/analisar/<tarefa_id>`. Os workers (Redis como broker, `--pool=solo`, escala
com `docker compose up --scale worker=N`) rodam o BERTimbau int8 via ONNX Runtime, sem torch.

## Estrutura de arquivos

```
AnalisadorDeSentimentos/     projeto Django (settings, urls raiz, wsgi/asgi)
analise/
  models.py                  Conversa, Mensagem e as constantes de rótulo/autor
  importacao.py              leitura e validação de CSV/JSON
  classificador.py           aplica o modelo às mensagens já gravadas
  indicadores.py             indicadores de sessão
  avaliacao.py               split por conversa, F1 macro, matriz, McNemar
  views.py / urls.py         API
  tests.py                   26 testes
  modelos/
    __init__.py              registro dos degraus e factory `carregar(nome)`
    lexico.py                degrau 1
    lexico_pt.txt            118 linhas, léxico curado à mão
    classico.py              degrau 2
    bertimbau.py             degrau 3 (loop de treino manual em PyTorch)
  management/commands/
    importar_kaggle.py       dataset público → esquema do projeto
    importar_conversas.py    arquivo do usuário → esquema do projeto
    treinar_bertimbau.py     fine-tune
    avaliar.py               avaliação comparativa + McNemar
models/
  bertimbau/                 pesos salvos (config.json, model.safetensors, tokenizer)
  metricas.json              saída de `avaliar --salvar`, consumida por GET /api/metricas
```

## Modelo de dados

```
Conversa
  id, origem_id, fonte, criada_em
  UNIQUE(fonte, origem_id)      → reimportar atualiza, não duplica

Mensagem
  conversa (FK), ordem, autor, texto, enviada_em,
  rotulo_pred, score, rotulo_real
  UNIQUE(conversa, ordem)       → ordem é a posição na conversa, não pode repetir
  ordering = [conversa_id, ordem]
```

`autor` ∈ `usuario | atendente | sistema`. **Só mensagens de `usuario` são classificadas** —
mensagens de sistema ("você está na fila") e do atendente não representam o sentimento do
cliente e poluiriam os indicadores.

`rotulo_real` é o rótulo de referência (vem do rating do dataset público ou de anotação
manual); `rotulo_pred` e `score` são a saída do modelo. Os dois convivem: é o que permite
avaliar sem reimportar.

Indicadores de sessão **não são persistidos** — são calculados por consulta em
`indicadores.py`. Materializar só se ficar lento.

## Interface comum dos modelos

Todo degrau implementa a mesma coisa, para que a avaliação seja idêntica entre eles:

```python
treinar(textos, rotulos) -> None
prever(textos) -> (rotulos, scores)
nome: str
```

`carregar(nome)` resolve pelo `REGISTRO`. O `classico` e o `bertimbau` têm import tardio:
`sklearn` e `torch` pesam centenas de MB e o processo web não usa nenhum dos dois.

## Cache do modelo

`classificador.modelo()` é `@lru_cache(maxsize=2)` e vive no processo do worker, não no web.
Carregar o BERTimbau custa segundos e cada worker atende muitos lotes; `maxsize=2` permite
alternar entre dois degraus sem recarregar, sem segurar três modelos em memória. Para
`bertimbau` o cache guarda o `BertimbauOnnx` (`model.int8.onnx`, gerado por
`manage.py exportar_onnx`; `BERTIMBAU_ONNX` troca o arquivo e `ONNX_THREADS` limita os núcleos
por worker).

## Indicadores de sessão

Calculados sobre a sequência de `rotulo_pred` das mensagens do usuário, em ordem:

| Indicador | Definição |
|---|---|
| `abertura` | rótulo da primeira mensagem do usuário |
| `encerramento` | rótulo da última |
| `delta` | valor(encerramento) − valor(abertura), com positivo=1, neutro=0, negativo=−1 |
| `trocas_de_polaridade` | quantas vezes o sinal inverte, **ignorando neutros** |
| `pior_momento` | posição (1-based) da mensagem mais negativa |
| `n_mensagens` | mensagens de usuário com rótulo |

Neutros são descartados na contagem de trocas de propósito: `negativo → neutro → negativo`
é a mesma insatisfação continuando, não duas viradas.

Sem nenhuma mensagem rotulada, `indicadores()` devolve `None` — a conversa aparece na lista,
mas sem trajetória.

## Decisões deliberadas

- **CSRF desativado no upload** (`@csrf_exempt`). App local, single-user, sem autenticação.
  Reativar quando entrar auth ou dado real de empresa.
- **`DEBUG = True` e `SECRET_KEY` de desenvolvimento** no settings. Não é deploy.
- **SQLite.** Migrar para Postgres só quando houver dado real em volume.
- **Importação atômica.** `importar()` é `@transaction.atomic`: ou o arquivo inteiro entra, ou
  nada entra. Um CSV meio importado é pior que um erro.
- **Reimportar substitui.** Mesma `(fonte, origem_id)` → as mensagens antigas são apagadas e
  regravadas. Corrigir um arquivo e reenviar não duplica.
