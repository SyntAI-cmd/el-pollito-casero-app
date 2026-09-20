"""Importa todos los modelos para que Base.metadata (Alembic, tests) vea el esquema completo."""

from app.modules.auditoria.models import AuditLog
from app.modules.auth.models import SesionRefresh, TokenPush, Usuario
from app.modules.catalogo.models import ListaPrecio, Producto
from app.modules.clientes.models import Cliente, MovimientoEnvases, PrecioCliente
from app.modules.cobros.models import CierreCaja, Comprobante, Pago
from app.modules.comunicacion.models import Mensaje, Noticia
from app.modules.flota.models import Salida, SalidaTrack, Vehiculo
from app.modules.pedidos.models import Contador, Pedido, PedidoEvento, PedidoItem
from app.modules.pesada.models import Cajon
from app.modules.sucursales.models import Sucursal, Zona

__all__ = [
    "AuditLog",
    "Cajon",
    "CierreCaja",
    "Cliente",
    "Comprobante",
    "Contador",
    "ListaPrecio",
    "Mensaje",
    "MovimientoEnvases",
    "Noticia",
    "Pago",
    "Pedido",
    "PedidoEvento",
    "PedidoItem",
    "PrecioCliente",
    "Producto",
    "Salida",
    "SalidaTrack",
    "SesionRefresh",
    "Sucursal",
    "TokenPush",
    "Usuario",
    "Vehiculo",
    "Zona",
]
