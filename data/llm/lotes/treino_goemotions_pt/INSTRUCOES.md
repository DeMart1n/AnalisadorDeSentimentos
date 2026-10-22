# Rotulagem de emoções

Você anota emoções em mensagens curtas em português do Brasil.
Para cada emoção, dê uma nota de 0 a 1: a chance de a pessoa que escreveu estar expressando essa
emoção no texto. Várias emoções podem estar presentes ao mesmo tempo; nenhuma também é possível
(texto neutro, informativo ou só uma pergunta).

- alegria: felicidade, satisfação, gratidão, entusiasmo, alívio.
- raiva: irritação, indignação, frustração com alguém ou algo.
- tristeza: desânimo, decepção, pesar, solidão.
- medo: preocupação, ansiedade, receio, insegurança com o que pode acontecer.
- surpresa: espanto, algo inesperado (positivo ou negativo).
- nojo: repulsa, asco, desprezo moral ou físico.

Avalie a emoção expressa por quem escreve, não a que o texto provocaria no leitor.

## Como trabalhar

- Leia e julgue **cada mensagem você mesmo**. Não escreva script, regra de palavra-chave nem
  classificador: o objetivo é medir o julgamento do modelo.
- Cada `lote_NN.jsonl` tem uma mensagem por linha: `{"id", "anterior", "texto"}`. `anterior`
  é a mensagem que veio antes na conversa (vazia quando não há); use só como contexto.
- Para cada lote, grave `lote_NN.rotulado.jsonl` na mesma pasta, uma linha por mensagem, na
  mesma ordem, sem pular nenhuma:
  `{"id": "...", "alegria": 0.0, "raiva": 0.0, "tristeza": 0.0, "medo": 0.0, "surpresa": 0.0, "nojo": 0.0}`
- Notas entre 0 e 1. Faça um lote por vez e confira que o número de linhas bate.
