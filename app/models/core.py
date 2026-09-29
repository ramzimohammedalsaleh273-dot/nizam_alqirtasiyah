from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True)
    sku: Mapped[str | None] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    category: Mapped[str | None] = mapped_column(String(150))
    cost_price: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    sale_price: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    min_stock: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    max_stock: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    credit_limit: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
