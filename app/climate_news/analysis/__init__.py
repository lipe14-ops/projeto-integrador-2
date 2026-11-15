"""Análises espaciais e sazonais em escala nacional (avaliação do professor).

Camadas, da regra científica à apresentação:

- ``seasons``: estações do Hemisfério Sul e episódios ENSO (regra do NOAA/CPC).
- ``classification``: definições operacionais que separam *anomalia
  estatística*, *extremo meteorológico relativo ao clima local* e *evento com
  impacto documentado* (nunca usados como sinônimos).
- ``thermal``: detector de anomalias de temperatura e umidade (climatologia de
  Fourier + AR(p) + Z sobre o resíduo de previsão de um passo).
- ``seasonal``: distribuição sazonal normalizada pela exposição (dias válidos),
  concentração, regiões, rankings e estratificação por ENSO.
- ``snapshot``: extração reprodutível do banco para arquivos Parquet.
- ``service``/``router``: API ``/api/analysis``.
- ``report``/``cli``: relatório reprodutível com tabelas, figuras e números.

Nada aqui altera os dados originais nem as anomalias já gravadas.
"""

ANALYSIS_VERSION = "seasonal-spatial/1.0.0"
