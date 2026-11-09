"""create clima_mensal materialized view

Agregado mensal por município (o mesmo cálculo do endpoint
/municipios/{codigo}/clima/mensal). Em registro_climatico as linhas de um
município ficam espalhadas por ~8 mil páginas de uma tabela de ~8 GB, e a
consulta fria levava de 10 a 80 s por I/O aleatório. A visão tem ~735 mil linhas
e responde em milissegundos. Atualize após cada carga climática com
``uv run codigo run atualizar-clima-mensal``.

Revision ID: b7e2c4d91a05
Revises: 9f764edda274
Create Date: 2026-11-08
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b7e2c4d91a05"
down_revision: Union[str, Sequence[str], None] = "9f764edda274"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW clima_mensal AS
        SELECT codigo_ibge,
               date_trunc('month', datetime, 'UTC') AS mes,
               avg(umidade) AS umidade,
               avg(temperatura) AS temperatura,
               sum(precipitacao) AS precipitacao,
               count(*) AS n_registros
        FROM registro_climatico
        GROUP BY codigo_ibge, date_trunc('month', datetime, 'UTC')
        WITH DATA
        """
    )
    # índice único: permite REFRESH ... CONCURRENTLY e atende a consulta por município
    op.execute("CREATE UNIQUE INDEX ux_clima_mensal_codigo_mes ON clima_mensal (codigo_ibge, mes)")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS clima_mensal")
