# Modelo de IA: o que mudou nesta semana (06/10 a 14/10/2026)

## O que o sistema faz

O sistema lê as mensagens que os clientes mandam num atendimento e diz se cada uma é positiva,
negativa ou neutra. Uma segunda parte, ainda em teste, tenta dizer qual emoção aparece na
mensagem: alegria, raiva, tristeza, medo, surpresa ou nojo.

## O que avançou

A equipe percebeu que a mesma mensagem recebia uma classificação diferente a cada vez, e nesta
semana achamos o motivo. O que o modelo aprendeu no treino fica guardado num arquivo grande, que
não vai junto com o código. Quem baixava o projeto ficava com um modelo que nunca tinha aprendido
nada e que respondia no chute. Como o chute mudava sempre que o sistema reiniciava, a resposta
mudava também. Agora, quando esse arquivo falta, o sistema avisa que não pode classificar.

Treinamos o modelo de novo, num processo de pouco mais de uma hora. Ele acerta cerca de 4 de cada
5 mensagens. Vai bem com mensagens claramente boas ou ruins. Nas neutras, acerta 3 de cada 5.

Também comparamos o modelo com duas alternativas mais simples. A que só conta palavras boas e
ruins acerta metade das mensagens. Um método estatístico simples acerta 3 de cada 4, ou seja, o
modelo principal é melhor, mas a diferença é pequena.

Por fim, escrevemos 160 testes automáticos, que conferem sozinhos se cada parte continua
funcionando depois de uma mudança. Esses testes encontraram seis defeitos, que já corrigimos. O
mais grave podia apagar dados já importados se alguém enviasse um arquivo no formato errado.

## O que falta, e por quê

- Mandar o arquivo do modelo para o resto da equipe. Ele é grande demais para ir junto com o
  código e, sem ele, o sistema não classifica nas outras máquinas.
- Juntar o trabalho à versão principal do projeto. O código está pronto; falta uma liberação de
  acesso no site onde ele fica guardado.
- Ligar a parte das emoções ao sistema. Ela reconhece bem alegria, raiva e tristeza, tem
  dificuldade com medo e surpresa e ainda não identifica nojo.
- Testar com conversas de atendimento de verdade. Todos os números acima vêm de avaliações de
  produtos em lojas online, que se parecem com uma conversa com um atendente, mas não são a mesma
  coisa. É provável que o resultado caia um pouco em conversas reais. Para saber quanto, a equipe
  precisa marcar à mão um conjunto dessas conversas.
