from sqlalchemy import CheckConstraint, Float, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EnsoMensal(Base):
    __tablename__ = "enso_mensal"
    __table_args__ = (
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_enso_mensal_month"),
    )

    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    month: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    enso_index: Mapped[float | None] = mapped_column(Float)