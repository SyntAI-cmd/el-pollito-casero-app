import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ConFechas, ConId
from app.core.tipos import IMPORTE, enum_sql
from app.domain.precios import Lista, Turno


class Producto(ConId, ConFechas, Base):
    """Cortes del catálogo. `codigo` es el id de dominio ("entero", "alas"…) de los precios."""

    __tablename__ = "productos"

    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(60))
    descripcion: Mapped[str] = mapped_column(String(200), default="")
    orden: Mapped[int] = mapped_column(default=0)
    activo: Mapped[bool] = mapped_column(default=True)


class ListaPrecio(ConId, ConFechas, Base):
    """Precio de lista por producto, lista, turno y zona (zona nula = general de la sucursal)."""

    __tablename__ = "listas_precio"
    __table_args__ = (UniqueConstraint("sucursal_id", "producto_id", "lista", "turno", "zona_id"),)

    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"), index=True)
    producto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("productos.id"))
    lista: Mapped[Lista] = mapped_column(enum_sql(Lista, "lista_precio"))
    turno: Mapped[Turno] = mapped_column(enum_sql(Turno, "turno"))
    zona_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zonas.id"))
    precio: Mapped[Decimal] = mapped_column(IMPORTE)
