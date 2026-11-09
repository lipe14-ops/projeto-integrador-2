"""create precipitacao_diaria materialized view

Total diário de chuva por município (dia UTC), no mesmo critério de
``aggregate_era5_12h_to_daily``: o dia D soma o acumulado de 12Z de D e o de
00Z de D+1; ``n_metades`` diz quantas metades existem (o dia só é válido com 2).
As linhas são gravadas em ordem (codigo_ibge, dia), então a série de um
município fica contígua no disco: a detecção nacional lê cada município em
milissegundos, em vez de ~10 s de leituras aleatórias na tabela de 8 GB.

Revision ID: c3a9e1f07b22
Revises: b7e2c4d91a05
Create Date: 2026-11-08
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c3a9e1f07b22"
down_revision: Union[str, Sequence[str], None] = "b7e2c4d91a05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SET LOCAL work_mem = '1GB'")
    op.execute(
        """
        CREATE MATERIALIZED VIEW precipitacao_diaria AS
        SELECT codigo_ibge,
               ((datetime - interval '1 hour') AT TIME ZONE 'UTC')::date AS dia,
               sum(precipitacao) AS precipitacao,
               count(precipitacao) AS n_metades
        FROM registro_climatico
        GROUP BY 1, 2
        ORDER BY 1, 2
        WITH DATA
        """
    )
    op.execute("CREATE UNIQUE INDEX ux_precipitacao_diaria ON precipitacao_diaria (codigo_ibge, dia)")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS precipitacao_diaria")
