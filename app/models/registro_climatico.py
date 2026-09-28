from datetime import datetime as DateTimeValue

from sqlalchemy import DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RegistroClimatico(Base):
    __tablename__ = "registro_climatico"
    __table_args__ = (
        Index("ix_registro_climatico_datetime", "datetime"),
    )

    codigo_ibge: Mapped[int] = mapped_column(
        ForeignKey("municipio.codigo_ibge", ondelete="CASCADE"),
        primary_key=True,
    )

    datetime: Mapped[DateTimeValue] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
    )

    umidade: Mapped[float | None] = mapped_column(Float)
    temperatura: Mapped[float | None] = mapped_column(Float)
    precipitacao: Mapped[float | None] = mapped_column(Float)

    municipio = relationship(
        "Municipio",
        back_populates="registros_climaticos",
    )