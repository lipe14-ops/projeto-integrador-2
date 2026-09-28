from sqlalchemy import BigInteger, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from app.database import Base


class Municipio(Base):
    __tablename__ = "municipio"

    codigo_ibge: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7)
    )

    longitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7)
    )

    geometry: Mapped[object] = mapped_column(
        Geometry(
            geometry_type="MULTIPOLYGON",
            srid=4326,
        ),
        nullable=False,
    )

    details = relationship(
        "MunicipioDetails",
        back_populates="municipio_ref",
        uselist=False,
        cascade="all, delete-orphan",
    )

    registros_climaticos = relationship(
        "RegistroClimatico",
        back_populates="municipio",
        cascade="all, delete-orphan",
    )