# A parte de inteligência artificial: resumo da semana

*5 de outubro de 2026*

## O que essa parte faz

Até a semana passada, o sistema lia as mensagens de clientes num atendimento e dizia se cada uma
era positiva, negativa ou neutra. Agora estamos ensinando o sistema a dizer também **qual
emoção** a mensagem expressa: alegria, raiva, tristeza, medo, surpresa ou nojo. Uma mensagem
pode ter mais de uma ("fiquei triste e com raiva") ou nenhuma ("qual o prazo de entrega?").

## O que avançou

**Arrumamos o que estava quebrado.** Os testes automáticos do sistema voltaram a rodar. O
conjunto de mensagens que usamos para medir o desempenho ficou fixo: antes, qualquer mensagem
nova embaralhava esse conjunto, e os resultados de semanas diferentes deixavam de ser comparáveis.

**Juntamos exemplos para ensinar emoções.** Não existe uma coleção pública de conversas de
atendimento em português marcadas com emoções. Por isso usamos duas coleções de outro tipo:

- cerca de 4.600 frases de redes sociais em português, marcadas por pessoas;
- cerca de 20.600 comentários de um fórum em inglês, traduzidos para o português com IA. Antes
  de traduzir tudo, conferimos uma amostra à mão.

Uma terceira coleção foi descartada: o texto vinha cortado em pedaços de palavras, e as emoções
marcadas não faziam sentido (avaliações elogiosas aparecendo como "tristeza").

**Treinamos o primeiro modelo de emoções.** O treino levou 33 minutos num notebook. Testado em
frases marcadas por pessoas que ele nunca tinha visto:

- reconhece **alegria e raiva** em cerca de 2 de cada 3 casos, e **tristeza** um pouco menos;
- erra bastante em **medo e surpresa** e praticamente não reconhece **nojo**;
- o problema mais sério: de cada 4 mensagens **sem** emoção, só 1 é reconhecida como neutra. As
  outras ganham uma emoção que não têm, quase sempre raiva.

Funciona como um aluno que aprendeu a reconhecer bem raiva e passou a ver raiva em todo lugar.
Para atendimento, onde a maioria das mensagens é "ok", "obrigado" ou "segue o comprovante", isso
precisa ser corrigido antes de qualquer uso.

## O que falta e por quê

- **Corrigir o excesso de raiva.** Já sabemos a causa provável: uma das coleções chama de raiva
  coisas mais leves, como discordância e irritação. Dá para corrigir sem traduzir de novo, com
  mais um treino de cerca de 30 minutos.
- **Conversas reais de atendimento.** Ainda não temos nenhuma. Sem elas, não dá para saber quanto
  o sistema acerta no uso de verdade, que é o objetivo do projeto. Já preparamos o guia e a
  ferramenta para que duas pessoas marquem as emoções quando as conversas chegarem.
- **O modelo antigo, de positivo, negativo e neutro**, continua sem o arquivo de treino de
  agosto. Refazer leva cerca de 46 minutos e ficou para depois.
- Parte do trabalho desta semana (os gráficos e os resultados) ainda não foi salva no
  histórico do projeto.
