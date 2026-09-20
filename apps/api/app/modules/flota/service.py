import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import Conflicto, NoEncontrado, SinPermiso
from app.core.seguridad import Identidad, Rol
from app.core.tiempo import ahora
from app.core.tiempo_real import difusor
from app.domain.errores import ErrorDominio
from app.domain.pedidos import (
    Estado,
    faltantes_para_cerrar,
    validar_cierre_camion,
    validar_preventistas_salida,
)
from app.modules.auditoria.service import registrar
from app.modules.auth import service as auth
from app.modules.flota import repository
from app.modules.flota.models import Salida, SalidaTrack, Vehiculo
from app.modules.flota.schemas import (
    FaltanteSalida,
    PosicionEntrada,
    PosicionSalida,
    SalidaEntrada,
    SalidaSalida,
    VehiculoCambios,
    VehiculoEntrada,
)
from app.modules.pedidos import service as pedidos
from app.modules.sucursales.service import verificar_sucursal

# ---------- vehículos ----------


async def listar_vehiculos(
    sesion: AsyncSession, quien: Identidad, incluir_inactivos: bool
) -> list[Vehiculo]:
    return list(
        await repository.listar_vehiculos(
            sesion,
            None if quien.rol is Rol.ADMIN else quien.sucursal_id,
            incluir_inactivos and quien.rol is Rol.ADMIN,
        )
    )


async def crear_vehiculo(
    sesion: AsyncSession, quien: Identidad, datos: VehiculoEntrada
) -> Vehiculo:
    patente = datos.patente.replace(" ", "").upper()
    if await repository.vehiculo_por_patente(sesion, patente):
        raise Conflicto(f"Ya existe un vehículo con patente {patente}")
    vehiculo = Vehiculo(
        sucursal_id=datos.sucursal_id or quien.sucursal_id,
        nombre=datos.nombre.strip(),
        patente=patente,
        nota=datos.nota.strip(),
    )
    sesion.add(vehiculo)
    await sesion.flush()
    registrar(sesion, quien, "vehiculo.crear", "vehiculo", vehiculo.id)
    await sesion.commit()
    return vehiculo


async def modificar_vehiculo(
    sesion: AsyncSession, quien: Identidad, vehiculo_id: uuid.UUID, cambios: VehiculoCambios
) -> Vehiculo:
    vehiculo = await repository.vehiculo_por_id(sesion, vehiculo_id)
    if vehiculo is None:
        raise NoEncontrado("Vehículo")
    datos = cambios.model_dump(exclude_unset=True)
    if "patente" in datos:
        datos["patente"] = datos["patente"].replace(" ", "").upper()
        otro = await repository.vehiculo_por_patente(sesion, datos["patente"])
        if otro is not None and otro.id != vehiculo.id:
            raise Conflicto(f"Ya existe un vehículo con patente {datos['patente']}")
    for campo, valor in datos.items():
        setattr(vehiculo, campo, valor.strip() if isinstance(valor, str) else valor)
    registrar(sesion, quien, "vehiculo.modificar", "vehiculo", vehiculo.id)
    await sesion.commit()
    return vehiculo


# ---------- salidas ----------


async def _a_salida(
    sesion: AsyncSession, salida: Salida, con_faltantes: bool = False
) -> SalidaSalida:
    vehiculo = await repository.vehiculo_por_id(sesion, salida.vehiculo_id)
    nombres = {u.id: u.nombre for u in await auth.listar_todos(sesion)}
    preventistas = {salida.preventista_id} | (
        {salida.segundo_preventista_id} if salida.segundo_preventista_id else set()
    )
    del_dia = await pedidos.modelos_para_salida(
        sesion, salida.sucursal_id, salida.fecha, preventistas
    )
    entregados = 0
    if salida.cerrada_en is not None:
        # Una vez cerrada, lo que cuenta son los pedidos atados a la salida.
        del_dia = await pedidos.modelos_de_salida(sesion, salida.id)
        entregados = sum(1 for p in del_dia if p.estado is Estado.ENTREGADO)
    faltantes: list[FaltanteSalida] = []
    if con_faltantes and salida.cerrada_en is None:
        faltantes = [
            FaltanteSalida(
                pedido_id=uuid.UUID(f.pedido_id),
                numero=f.numero,
                sin_pesar=f.sin_pesar,
                sin_cargar=f.sin_cargar,
            )
            for f in faltantes_para_cerrar(await pedidos.para_cargar(sesion, del_dia))
        ]
    posicion = await repository.ultima_posicion(sesion, salida.id)
    return SalidaSalida(
        id=salida.id,
        sucursal_id=salida.sucursal_id,
        vehiculo_id=salida.vehiculo_id,
        vehiculo_nombre=vehiculo.nombre if vehiculo else "",
        vehiculo_patente=vehiculo.patente if vehiculo else "",
        fecha=salida.fecha,
        hora_salida=salida.hora_salida,
        preventista_id=salida.preventista_id,
        preventista_nombre=nombres.get(salida.preventista_id, ""),
        segundo_preventista_id=salida.segundo_preventista_id,
        segundo_preventista_nombre=nombres.get(salida.segundo_preventista_id)
        if salida.segundo_preventista_id
        else None,
        cerrada_en=salida.cerrada_en,
        motivo_cierre=salida.motivo_cierre,
        pedidos=len(del_dia),
        pedidos_entregados=entregados,
        ultima_posicion=PosicionSalida.model_validate(posicion) if posicion else None,
        faltantes=faltantes,
    )


def _puede_ver_salida(quien: Identidad, salida: Salida) -> bool:
    if quien.rol is Rol.ADMIN:
        return True
    if salida.sucursal_id != quien.sucursal_id:
        return False
    return quien.usuario_id in (salida.preventista_id, salida.segundo_preventista_id)


async def _obtener(sesion: AsyncSession, quien: Identidad, salida_id: uuid.UUID) -> Salida:
    salida = await repository.salida_por_id(sesion, salida_id)
    if salida is None or not _puede_ver_salida(quien, salida):
        raise NoEncontrado("Salida")
    return salida


async def listar_salidas(sesion: AsyncSession, quien: Identidad, fecha: date) -> list[SalidaSalida]:
    if quien.rol is Rol.COBRADOR:
        raise SinPermiso("El cobrador no ve la flota")
    salidas = await repository.salidas_del_dia(
        sesion, None if quien.rol is Rol.ADMIN else quien.sucursal_id, fecha
    )
    return [await _a_salida(sesion, s) for s in salidas if _puede_ver_salida(quien, s)]


async def obtener_salida(
    sesion: AsyncSession, quien: Identidad, salida_id: uuid.UUID
) -> SalidaSalida:
    salida = await _obtener(sesion, quien, salida_id)
    return await _a_salida(sesion, salida, con_faltantes=True)


async def guardar_salida(
    sesion: AsyncSession, quien: Identidad, datos: SalidaEntrada
) -> SalidaSalida:
    """Alta o cambio de la salida del día de un vehículo. Un preventista va en un solo camión."""
    vehiculo = await repository.vehiculo_por_id(sesion, datos.vehiculo_id)
    if vehiculo is None or not vehiculo.activo:
        raise NoEncontrado("Vehículo")
    verificar_sucursal(quien, vehiculo.sucursal_id)
    preventistas = validar_preventistas_salida(
        [str(datos.preventista_id)]
        + ([str(datos.segundo_preventista_id)] if datos.segundo_preventista_id else [])
    )
    if quien.rol is Rol.PREVENTISTA and str(quien.usuario_id) not in preventistas:
        raise SinPermiso("Un preventista arma la salida en la que va él")
    salida = await repository.salida_de_vehiculo(sesion, vehiculo.id, datos.fecha)
    if salida is not None and salida.cerrada_en is not None:
        raise Conflicto("El camión ya salió: la salida no se modifica")
    for pid in preventistas:
        otra = await repository.salida_de_preventista(sesion, uuid.UUID(pid), datos.fecha)
        if otra is not None and (salida is None or otra.id != salida.id):
            raise ErrorDominio("Ese preventista ya va en otro vehículo ese día")
    if salida is None:
        salida = Salida(
            sucursal_id=vehiculo.sucursal_id, vehiculo_id=vehiculo.id, fecha=datos.fecha
        )
        sesion.add(salida)
    salida.preventista_id = datos.preventista_id
    salida.segundo_preventista_id = datos.segundo_preventista_id
    salida.hora_salida = datos.hora_salida
    await sesion.flush()
    registrar(sesion, quien, "salida.guardar", "salida", salida.id, {"fecha": str(datos.fecha)})
    await sesion.commit()
    return await _a_salida(sesion, salida, con_faltantes=True)


async def cerrar_camion(
    sesion: AsyncSession, quien: Identidad, salida_id: uuid.UUID, motivo: str | None
) -> SalidaSalida:
    """Despacha los pedidos de los preventistas del camión. Con faltantes, exige motivo."""
    salida = await _obtener(sesion, quien, salida_id)
    if salida.cerrada_en is not None:
        raise Conflicto("El camión ya salió")
    preventistas = {salida.preventista_id} | (
        {salida.segundo_preventista_id} if salida.segundo_preventista_id else set()
    )
    del_dia = await pedidos.modelos_para_salida(
        sesion, salida.sucursal_id, salida.fecha, preventistas
    )
    if not del_dia:
        raise ErrorDominio("No hay pedidos para despachar en esta salida")
    faltantes = validar_cierre_camion(await pedidos.para_cargar(sesion, del_dia), motivo)
    await pedidos.despachar(sesion, quien, del_dia, salida.id)
    salida.cerrada_en = ahora()
    salida.motivo_cierre = motivo.strip() if motivo else None
    if salida.hora_salida is None:
        salida.hora_salida = salida.cerrada_en.time().replace(microsecond=0)
    registrar(
        sesion,
        quien,
        "salida.cerrar",
        "salida",
        salida.id,
        {"pedidos": len(del_dia), "faltantes": [f.numero for f in faltantes], "motivo": motivo},
    )
    await sesion.commit()
    await pedidos.publicar_despacho(del_dia)
    await difusor.publicar(salida.sucursal_id, "salida.cerrada", {"salida_id": str(salida.id)})
    return await _a_salida(sesion, salida)


async def registrar_posicion(
    sesion: AsyncSession, quien: Identidad, salida_id: uuid.UUID, datos: PosicionEntrada
) -> None:
    salida = await _obtener(sesion, quien, salida_id)
    if quien.rol is not Rol.PREVENTISTA:
        raise SinPermiso("La posición la manda el celular del repartidor")
    sesion.add(
        SalidaTrack(
            salida_id=salida.id,
            lat=datos.lat,
            lng=datos.lng,
            velocidad=datos.velocidad,
            registrado_en=datos.registrado_en or ahora(),
        )
    )
    await sesion.commit()
    await difusor.publicar(
        salida.sucursal_id,
        "flota.posicion",
        {
            "salida_id": str(salida.id),
            "vehiculo_id": str(salida.vehiculo_id),
            "lat": str(datos.lat),
            "lng": str(datos.lng),
            "velocidad": str(datos.velocidad) if datos.velocidad is not None else None,
        },
        roles=frozenset({Rol.ADMIN}),
    )


async def recorrido(
    sesion: AsyncSession, quien: Identidad, salida_id: uuid.UUID
) -> list[PosicionSalida]:
    salida = await _obtener(sesion, quien, salida_id)
    return [PosicionSalida.model_validate(p) for p in await repository.recorrido(sesion, salida.id)]
