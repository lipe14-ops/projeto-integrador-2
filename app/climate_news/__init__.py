"""Detecção de anomalias de precipitação e investigação de notícias.

Pacote organizado em camadas independentes:

- ``detection``: preparação dos dados e modelo ARIMA + Z-Score (sem banco).
- ``agents``: agentes especialistas coordenados pelo orquestrador.
- ``news``: busca e extração de notícias (HTTP, RSS, HTML).
- ``models``/``repository``/``router``: persistência e API REST.
"""

ALGORITHM_VERSION = "arima-zscore/1.0.0"
