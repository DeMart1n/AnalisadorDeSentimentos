# A parte de inteligência artificial: resumo da semana

*30 de setembro de 2026*

## O que essa parte faz

O sistema lê mensagens de clientes numa conversa de atendimento e diz se cada uma é positiva, negativa ou neutra. Para ensinar o computador a fazer isso, usamos cerca de 63 mil avaliações de compras feitas em lojas online brasileiras, cada uma com a nota que o próprio cliente deu.

Testamos três formas de fazer isso, da mais simples para a mais sofisticada:

1. **Lista de palavras.** Procura palavras como "ótimo" ou "péssimo" e soma. Acerta mais ou menos metade das mensagens.
2. **Estatística simples.** Aprende com os exemplos quais palavras e pares de palavras indicam cada sentimento. Leva segundos para aprender e acerta cerca de 3 em cada 4.
3. **Modelo de linguagem grande**, parecido com os que estão por trás dos assistentes de IA. Levou 46 minutos para aprender e acerta cerca de 8 em cada 10.

O que concluímos: o grande salto vem da primeira forma para a segunda. A terceira é melhor, e a diferença foi confirmada por teste estatístico, mas melhora pouco perto do custo a mais que tem.

## O que aconteceu nesta semana

Nesta semana não houve mudança nessa parte do sistema. O trabalho foi conferir se a documentação ainda descreve o que existe de verdade. Quase tudo conferiu: os números, as configurações e os resultados.

Encontrei um problema. O arquivo com o "cérebro" do terceiro modelo, gerado no treino de agosto, não está mais no computador. Os resultados que já medimos continuam valendo. O que não funciona hoje é usar esse modelo para analisar conversas novas. Enquanto o arquivo não voltar, essa função do sistema fica parada.

Além disso, outro colega colocou no sistema uma proteção que esconde dados pessoais (nomes, CPF, e-mail) antes da análise. É uma mudança boa, mas o modelo aprendeu com textos que não tinham essa proteção, e ainda não medimos se isso atrapalha.

## O que falta

- **Recuperar ou refazer o treino do terceiro modelo.** Leva uns 46 minutos no computador. É o mais urgente.
- **Atualizar o painel de resultados.** Hoje ele mostra só os dois primeiros modelos.
- **Testar com conversas reais de atendimento.** Até agora só usamos avaliações de compras, que são um tipo de texto diferente. Sem esse teste, ainda não sabemos quanto o sistema acerta no uso real.
