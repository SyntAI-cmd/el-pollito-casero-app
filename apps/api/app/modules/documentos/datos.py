"""Lo que necesitan los renderers, armado desde los services de pedidos, cobros y clientes."""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.seguridad import Identidad
from app.domain.dinero import CERO
from app.domain.pedidos import Estado
from app.domain.precios import Turno
from app.modules.auth import service as auth
from app.modules.clientes import service as clientes
from app.modules.cobros import service as cobros
from app.modules.pedidos import service as pedidos
from app.modules.pedidos.schemas import PedidoSalida


@dataclass
class DatosCliente:
    cuit: str | None
    saldo: Decimal  # saldo actual de la cuenta corriente
    envases: int
    localidad: str | None = None
    telefono: str | None = None


@dataclass
class Contexto:
    fecha: date | None
    turno: Turno | None
    pedidos: list[PedidoSalida]
    clientes: dict[uuid.UUID, DatosCliente]
    nombres: dict[uuid.UUID, str]
    fiscal: Settings
    preventista_id: uuid.UUID | None = None
    vehiculos: dict[uuid.UUID, str] = field(default_factory=dict)
    formato: str = "a4"  # remitos: "a4" (4 por hoja) o "10x15" (uno por página)

    def nombre(self, usuario_id: uuid.UUID | None) -> str:
        return self.nombres.get(usuario_id, "Sin asignar") if usuario_id else "Sin asignar"

    @property
    def kilos(self) -> Decimal:
        return sum((i.kg_pesados or CERO for p in self.pedidos for i in p.items), CERO)

    @property
    def importe(self) -> Decimal:
        return sum((p.total for p in self.pedidos), CERO)


async def armar(
    sesion: AsyncSession,
    quien: Identidad,
    fecha: date | None,
    turno: Turno | None,
    preventista_id: uuid.UUID | None,
    pedido_ids: list[uuid.UUID],
    formato: str = "a4",
) -> Contexto:
    if pedido_ids:
        lista = [await pedidos.obtener(sesion, quien, pid) for pid in pedido_ids]
    else:
        lista = await pedidos.listar(
            sesion, quien, fecha, turno, None, None, preventista_id, 2000, 0
        )
    lista = [p for p in lista if p.estado is not Estado.CANCELADO]
    lista.sort(key=lambda p: p.numero)
    datos: dict[uuid.UUID, DatosCliente] = {}
    for p in lista:
        if p.cliente_id in datos:
            continue
        cliente = await clientes.obtener_interno(sesion, p.cliente_id)
        datos[p.cliente_id] = DatosCliente(
            cuit=cliente.cuit,
            saldo=await cobros.saldo_de(sesion, cliente.id),
            envases=await clientes.saldo_envases_de(sesion, cliente),
            localidad=cliente.localidad,
            telefono=cliente.telefono,
        )
    return Contexto(
        fecha=fecha,
        turno=turno,
        pedidos=lista,
        clientes=datos,
        nombres={u.id: u.nombre for u in await auth.listar_todos(sesion)},
        fiscal=get_settings(),
        preventista_id=preventista_id,
        formato=formato,
    )
