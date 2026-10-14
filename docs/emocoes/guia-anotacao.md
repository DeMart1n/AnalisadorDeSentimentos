# Guia de anotação de emoções

Vale para os anotadores humanos e para o prompt da LLM (Fase 4). Se mudar o guia depois de
começar a anotação, registre a data e o que mudou no fim deste arquivo.

## O que anotar

- **Só mensagens do cliente.** Mensagens do atendente ou do bot ficam fora do escopo: não
  anote, mesmo que apareçam no CSV como contexto.
- **Unidade:** a mensagem (ou turno: mensagens seguidas do mesmo cliente, já agrupadas).
- **Contexto:** a coluna `anterior` mostra a mensagem anterior. Use-a para entender a
  mensagem atual, mas anote a emoção **da mensagem atual**.
- **Anote o que o texto expressa**, não o que você imagina que o cliente sente. Se precisa
  inventar uma história para justificar, é neutro.

## Emoções

Marque 1 em cada emoção presente. **Multi-rótulo:** pode marcar mais de uma. Se nenhuma for
marcada, a mensagem é neutra.

| Emoção | Quando marcar | Exemplos (marca) | Não confundir (não marca) |
|---|---|---|---|
| `alegria` | satisfação, alívio, gratidão genuína, entusiasmo | "resolveu!! muito obrigada, salvou meu dia"; "chegou antes do prazo, amei" | "ok obrigado" protocolar (neutro) |
| `raiva` | irritação, frustração, indignação, cobrança agressiva, ameaça (Procon, cancelar) | "já é a terceira vez que eu ligo"; "vou no Procon"; "QUE ABSURDO" | reclamação factual sem carga ("o boleto veio com valor errado") é neutro |
| `tristeza` | decepção, desânimo, lamento, sensação de perda | "era presente pro meu filho, agora não chega mais"; "tô desanimada, confiava na loja" | decepção com cobrança agressiva: marque raiva **e** tristeza |
| `medo` | preocupação, ansiedade, insegurança sobre o que vai acontecer | "e se cobrarem de novo?"; "tenho medo de ter sido golpe"; "meu nome vai pro SPC?" | pergunta informativa sem aflição ("qual o prazo?") é neutro |
| `surpresa` | espanto com algo inesperado, bom ou ruim | "como assim cancelado?? eu nem pedi"; "nossa, já chegou?" | **pergunta, dúvida ou confusão não é surpresa** ("não entendi o boleto" é neutro) |
| `nojo` | repulsa, desprezo, asco (produto estragado, falta de higiene, desprezo pela empresa) | "veio com cabelo dentro, que nojo"; "empresa lixo, vergonha" | raiva comum sem desprezo é só raiva |

Intensidade (opcional, 0–3) só se o CSV tiver a coluna; na dúvida, deixe vazia.

## Neutro

É neutra a mensagem sem emoção expressa. Casos típicos no atendimento:

- pergunta informativa: "qual o prazo de entrega?", "aceita pix?";
- confirmação protocolar: "ok", "certo", "ok obrigado", "blz";
- envio de dados: "segue o comprovante", "meu CPF é [CPF]", "pedido 4512".

## Sarcasmo

Anote a emoção real, não a literal. "adorei esperar 40 min" é **raiva**, não alegria.
"parabéns pelo atendimento, hein" depois de uma reclamação é **raiva**.

## Casos difíceis

- **Raiva educada:** "entendo, mas é a quarta vez que peço o reembolso" é raiva, mesmo sem
  palavrão ou caixa alta.
- **Duas emoções:** "fiquei muito triste e com raiva, era aniversário dela" marca tristeza e raiva.
- **Emoji sozinho:** 😡 é raiva, 😭 é tristeza, 🙏 sozinho é neutro, 😂 depende do contexto.
- **Caixa alta** sozinha não é raiva; "OK" continua neutro.
- **Marcadores de anonimização** (`[NOME]`, `[CPF]`, …) são texto normal; ignore-os.

## Processo

1. `uv run manage.py anotacao exportar <arquivo.csv> --n N` gera o CSV com amostra estratificada
   por conversa.
2. Cada anotador preenche **sozinho** uma cópia do CSV: 1 nas colunas de emoção presentes e 0 ou
   vazio nas demais. Não discutam casos antes de terminar.
3. `uv run manage.py anotacao importar <arquivo.csv> --anotador <nome>` grava os rótulos.
4. `uv run manage.py anotacao kappa <anotador_a> <anotador_b>` calcula o Kappa de Cohen por emoção.
