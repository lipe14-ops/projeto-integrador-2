from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MunicipioDetails(Base):
    __tablename__ = "municipio_details"

    codigo_ibge: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "municipio.codigo_ibge",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    municipio: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    uf: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    regiao: Mapped[str | None] = mapped_column(
        String(50)
    )

    mesorregiao: Mapped[str | None] = mapped_column(
        String(150)
    )

    microrregiao: Mapped[str | None] = mapped_column(
        String(150)
    )

    populacao: Mapped[int | None] = mapped_column(
        BigInteger
    )

    ano_populacao: Mapped[int | None] = mapped_column(
        SmallInteger
    )

    bioma: Mapped[str | None] = mapped_column(
        String(100)
    )

    geomorfologia: Mapped[str | None] = mapped_column(
        String(255)
    )

    regiao_geomorfologica: Mapped[str | None] = mapped_column(
        String(255)
    )

    dominio_geomorfologico: Mapped[str | None] = mapped_column(
        String(255)
    )

    area_km2: Mapped[float | None] = mapped_column(
        Numeric(15, 2)
    )

    municipio_ref = relationship(
        "Municipio",
        back_populates="details",
    )