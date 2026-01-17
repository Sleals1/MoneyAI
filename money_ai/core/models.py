from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    records = relationship("Record", back_populates="user", cascade="all, delete-orphan")


class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    date = Column(String, index=True, nullable=False)  # "YYYY-MM-DD"
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)

    category = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)

    source = Column(String, default="manual", nullable=False)  # manual | recurring | import
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="records")


class RecurringRule(Base):
    __tablename__ = "recurring_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    name = Column(String, nullable=False)               # "Nómina", "Renta"
    amount = Column(Float, nullable=False)              # + ingreso, - gasto
    category = Column(String, nullable=False)           # "Ingreso", "Renta", etc.

    schedule = Column(String, default="monthly", nullable=False)  # monthly | weekly | biweekly (Fase 1: monthly)
    day_of_month = Column(Integer, default=1, nullable=False)     # 1-31 (MVP: usamos 1-28)
    active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
