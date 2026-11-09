**O que encontramos:**

- Os três métodos marcaram poucos dados: **2,76%** (ARIMA), **2,21%** (Isolation Forest) e **2,86%** (Hampel) dos instantes.
- Eles **concordam pouco**. Dos 1.922 instantes marcados por algum método, **76%** foram marcados por um só, e apenas 134 pelos três. Cada método procura um tipo diferente de "estranho":
  - **ARIMA** pega mudanças bruscas que o passado não previa, como uma frente fria chegando ou uma chuva muito maior que a prevista.
  - **Isolation Forest** pega combinações raras das variáveis, como muito calor com ar muito seco, uma chuva forte depois de dias secos ou um salto brusco de um dia para o outro.
  - **Hampel** pega picos isolados em relação aos dias vizinhos.
- O ARIMA é o único aplicado também na chuva. Entre os casos de chuva marcados estão dias das enchentes de Porto Alegre em 2024.
- Em **Manaus**, o ARIMA e o Isolation Forest marcaram muito mais outliers em **2015** e em **2023–2024**. Esses anos tiveram El Niño e secas fortes na Amazônia. O Hampel não mostra esse padrão tão claro, porque quando um evento dura semanas a própria mediana da janela acompanha o evento.
- No **teste com picos artificiais** (temperatura e umidade, período de teste), o ARIMA encontrou **86%** dos picos, o Hampel **76%** e o Isolation Forest **69%**. O Hampel quase não gera alarmes falsos por causa dos picos (0,01 por pico), contra 0,07 do Isolation Forest e 0,13 do ARIMA. Picos na umidade são mais difíceis de achar que na temperatura, principalmente em lugares úmidos, onde a umidade já fica perto de 100%.
- Duas mudanças simples melhoraram muito o Isolation Forest: dar a ele o **salto** de cada variável em relação aos dias vizinhos e usar contaminação de 2%. Sem elas, ele achava só 14% dos picos de temperatura.

**Conclusão:** os métodos se **complementam**, nenhum substitui os outros.
O ARIMA acerta mais, o Hampel é o que menos dá alarme falso e o Isolation
Forest é o único que olha as variáveis juntas. Também vimos que **outlier
não é sinônimo de erro**: os casos marcados se parecem com eventos reais do
clima, como frentes frias, secas e chuvas fortes. Os erros de verdade que
achamos (Salvador sem dados e a chuva faltando todo dia 1º) apareceram na
análise exploratória, e não nos algoritmos.

**Limitações:** usamos só 4 municípios, dados de reanálise (não de
estação meteorológica) e não temos uma lista oficial de quais valores são
anômalos para conferir os resultados. O Hampel não foi aplicado na chuva,
porque com muitos zeros ele marcaria qualquer chuva moderada.

## Resumo

Este trabalho comparou três métodos de detecção de outliers (ARIMA com
Z-score, Isolation Forest e filtro de Hampel) em dados climáticos de
reanálise ERA5-Land de 2015 a 2025, com temperatura, umidade e chuva a cada
12 horas, para Manaus, Feira de Santana, Goiânia e Porto Alegre. Antes de
aplicar os métodos, removemos o ciclo anual e diário das séries. Os modelos
foram treinados e ajustados com os dados de 2015 a 2021. Os métodos
marcaram entre 2,2% e 2,9% dos dados, mas concordaram pouco: 76% dos
instantes marcados foram apontados por um único método. Em um teste com
picos artificiais em 2022–2025, o ARIMA encontrou 86% dos picos, o Hampel
76% e o Isolation Forest 69%, sendo o Hampel o que menos gerou alarmes
falsos. Os resultados mostram que os métodos são complementares e que
valores marcados como outliers muitas vezes são eventos climáticos reais,
e não erros nos dados.

**Palavras-chave:** outliers; séries temporais; clima; ARIMA; Isolation Forest; filtro de Hampel.
