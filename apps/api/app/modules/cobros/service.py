import uuid
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import Conflicto, NoEncontrado, SinPermiso
from app.core.seguridad import Identidad, Rol
from app.core.tiempo import ahora, inicio_del_dia
from app.domain.cierre_caja import cerrar_caja, resumir_caja
from app.domain.dinero import CERO, a_importe
from app.domain.errores import ErrorDominio
from app.domain.pagos import (
    MEDIOS_CON_COMPROBANTE,
    Medio,
    ParteCobro,
    PedidoPendiente,
    aplicar_pago,
    validar_cierre_entrega,
    validar_cobro,
)
from app.domain.pedidos import Estado
from app.domain.remitos import formatear_numero
from app.domain.saldos import (
    Movimiento,
    PedidoACuenta,
    TipoMovimiento,
    extracto,
    movimiento_de_pago,
    movimientos_de_pedido,
    saldo_actual,
)
from app.integrations.storage import storage
from app.modules.auditoria.service import registrar
from app.modules.auth import service as auth
from app.modules.clientes import service as clientes
from app.modules.clientes.models import Cliente
from app.modules.cobros import repository
from app.modules.cobros.models import (
    AjusteCuenta,
    CierreCaja,
    Comprobante,
    Pago,
    TipoAjuste,
    TipoComprobante,
)
from app.modules.cobros.schemas import (
    AjusteEntrada,
    CierreEntrada,
    CierreSalida,
    ComprobanteSalida,
    CuentaACobrar,
    ExtractoSalida,
    LineaExtracto,
    PagoEntrada,
    PagoSalida,
    ParteSalida,
    ResumenCaja,
)
from app.modules.pedidos import service as pedidos
from app.modules.pedidos.models import Pedido

TIPOS_IMAGEN = {"image/jpeg", "image/png", "image/webp"}
TAMANO_MAXIMO = 4 * 1024 * 1024  # la app reduce a ~3,5 MB; el servidor tolera un poco más

# Los ajustes del extracto se traducen a los tipos del dominio para el saldo.
TIPO_DOMINIO = {
    TipoAjuste.REINTEGRO: TipoMovimiento.REINTEGRO,
    TipoAjuste.REPESADA: TipoMovimiento.AJUSTE_MANUAL,
    TipoAjuste.MANUAL: TipoMovimiento.AJUSTE_MANUAL,
    TipoAjuste.USO_SALDO: TipoMovimiento.AJUSTE_MANUAL,
}


# ---------- comprobantes ----------


async def subir_comprobante(
    sesion: AsyncSession,
    quien: Identidad,
    pedido_id: uuid.UUID | None,
    tipo: TipoComprobante,
    contenido: bytes,
    content_type: str,
) -> ComprobanteSalida:
    if content_type not in TIPOS_IMAGEN:
        raise ErrorDominio("El comprobante tiene que ser una foto (JPEG, PNG o WebP)")
    if not contenido or len(contenido) > TAMANO_MAXIMO:
        raise ErrorDominio("La foto está vacía o pesa más de 4 MB")
    sucursal_id = quien.sucursal_id
    if pedido_id is not None:
        pedido = await pedidos.obtener_modelo(sesion, quien, pedido_id)
        sucursal_id = pedido.sucursal_id
    comprobante = Comprobante(
        id=uuid.uuid4(),
        sucursal_id=sucursal_id,
        pedido_id=pedido_id,
        tipo=tipo,
        clave_storage="",
        tamano_bytes=len(contenido),
        subido_por=quien.usuario_id,
        creado_en=ahora(),
    )
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
    comprobante.clave_storage = (
        f"comprobantes/{comprobante.creado_en:%Y/%m/%d}/{comprobante.id}.{extension}"
    )
    await storage().guardar(comprobante.clave_storage, contenido, content_type)
    sesion.add(comprobante)
    registrar(
        sesion,
        quien,
        "comprobante.subir",
        "comprobante",
        comprobante.id,
        {"pedido_id": str(pedido_id) if pedido_id else None, "tipo": tipo},
    )
    await sesion.commit()
    return _comprobante_a_salida(comprobante)


def _comprobante_a_salida(c: Comprobante) -> ComprobanteSalida:
    return ComprobanteSalida(
        id=c.id,
        pedido_id=c.pedido_id,
        pago_id=c.pago_id,
        tipo=c.tipo,
        url=storage().url_firmada(c.clave_storage),
        creado_en=c.creado_en,
    )


async def comprobantes_de_pedido(
    sesion: AsyncSession, quien: Identidad, pedido_id: uuid.UUID
) -> list[ComprobanteSalida]:
    await pedidos.obtener_modelo(sesion, quien, pedido_id)
    return [
        _comprobante_a_salida(c) for c in await repository.comprobantes_de_pedido(sesion, pedido_id)
    ]


async def comprobantes_del_dia(
    sesion: AsyncSession, quien: Identidad, fecha: date, usuario_id: uuid.UUID | None
) -> list[ComprobanteSalida]:
    if quien.rol is not Rol.ADMIN:
        usuario_id = quien.usuario_id
    desde = inicio_del_dia(fecha)
    filas = await repository.comprobantes_entre(
        sesion,
        desde,
        desde + timedelta(days=1),
        usuario_id,
        None if quien.rol is Rol.ADMIN else quien.sucursal_id,
    )
    return [_comprobante_a_salida(c) for c in filas]


async def cantidad_fotos_de_pedido(sesion: AsyncSession, pedido_id: uuid.UUID) -> int:
    return len(await repository.comprobantes_de_pedido(sesion, pedido_id))


async def verificar_cierre_entrega(sesion: AsyncSession, pedido_id: uuid.UUID) -> None:
    """Una entrega no se cierra sin al menos una foto: comprobante o remito firmado."""
    validar_cierre_entrega(await cantidad_fotos_de_pedido(sesion, pedido_id))


# ---------- cuenta corriente ----------


async def _movimientos(sesion: AsyncSession, cliente_id: uuid.UUID) -> list[Movimiento]:
    movimientos: list[Movimiento] = []
    for p in await pedidos.a_cuenta_de_cliente(sesion, cliente_id):
        movimientos.extend(
            movimientos_de_pedido(
                PedidoACuenta(
                    id=formatear_numero(p.numero),
                    creado=p.creado_en,
                    importe_estimado=p.estimado,
                    importe_pesado=p.total if p.pesado_en else None,
                    pesado_en=p.pesado_en,
                    cancelado_en=p.cancelado_en,
                )
            )
        )
    for pago in await repository.pagos_de_cliente(sesion, cliente_id):
        if pago.pedido_id is not None:
            continue  # cobro en la entrega de un pedido no a cuenta: no toca la cuenta corriente
        medios = ", ".join(sorted({str(parte["medio"]) for parte in pago.partes}))
        movimientos.append(movimiento_de_pago(str(pago.id), pago.fecha, pago.total, medios))
    for ajuste in await repository.ajustes_de_cliente(sesion, cliente_id):
        movimientos.append(
            Movimiento(
                ajuste.fecha,
                TIPO_DOMINIO[ajuste.tipo],
                a_importe(ajuste.importe),
                ajuste.referencia or str(ajuste.id),
                ajuste.motivo,
            )
        )
    return movimientos


async def saldo_de(sesion: AsyncSession, cliente_id: uuid.UUID) -> Decimal:
    """Saldo de cuenta corriente: + deuda, − a favor."""
    return saldo_actual(await _movimientos(sesion, cliente_id))


def _pendientes(lista: Sequence[Pedido]) -> list[Pedido]:
    return [p for p in lista if not p.pagado and p.estado is not Estado.CANCELADO]


def _importe_en_cuenta(pedido: Pedido) -> Decimal:
    """Lo que vale en la cuenta: el estimado hasta pesar, el total después (como el cargo)."""
    return pedido.total if pedido.pesado_en else pedido.estimado


async def extracto_de(
    sesion: AsyncSession, quien: Identidad, cliente_id: uuid.UUID
) -> ExtractoSalida:
    cliente = await clientes.obtener(sesion, quien, cliente_id)
    movimientos = await _movimientos(sesion, cliente.id)
    lineas = extracto(movimientos)
    saldo = lineas[-1].saldo if lineas else CERO
    pendientes = _pendientes(await pedidos.a_cuenta_de_cliente(sesion, cliente.id))
    return ExtractoSalida(
        cliente_id=cliente.id,
        saldo=saldo,
        saldo_a_favor=max(-saldo, CERO),
        pedidos_pendientes=len(pendientes),
        envases=await clientes.saldo_envases_de(sesion, cliente),
        lineas=[
            LineaExtracto(
                fecha=x.movimiento.fecha,
                tipo=x.movimiento.tipo,
                importe=x.movimiento.importe,
                saldo=x.saldo,
                referencia=x.movimiento.referencia,
                detalle=x.movimiento.detalle,
            )
            for x in lineas
        ],
    )


async def registrar_ajuste(
    sesion: AsyncSession,
    quien: Identidad,
    cliente_id: uuid.UUID,
    tipo: TipoAjuste,
    importe: Decimal,
    motivo: str,
    referencia: str | None = None,
    fecha: datetime | None = None,
) -> AjusteCuenta:
    """No commitea: viaja en la transacción de quien lo llama (borrado de pedido, repesada)."""
    cliente = await clientes.obtener_interno(sesion, cliente_id)
    importe = a_importe(importe)
    if importe == CERO:
        raise ErrorDominio("El ajuste no puede ser cero")
    ajuste = AjusteCuenta(
        sucursal_id=cliente.sucursal_id,
        cliente_id=cliente.id,
        fecha=fecha or ahora(),
        tipo=tipo,
        importe=importe,
        motivo=motivo,
        referencia=referencia,
        registrado_por=quien.usuario_id,
    )
    sesion.add(ajuste)
    registrar(
        sesion,
        quien,
        "cuenta.ajuste",
        "cliente",
        cliente.id,
        {"tipo": tipo, "importe": str(importe), "motivo": motivo},
    )
    return ajuste


async def ajuste_manual(
    sesion: AsyncSession, quien: Identidad, cliente_id: uuid.UUID, datos: AjusteEntrada
) -> ExtractoSalida:
    if quien.rol is not Rol.ADMIN:
        raise SinPermiso("Solo administración ajusta saldos a mano")
    await registrar_ajuste(
        sesion, quien, cliente_id, TipoAjuste.MANUAL, datos.importe, datos.motivo, fecha=datos.fecha
    )
    await sesion.commit()
    return await extracto_de(sesion, quien, cliente_id)


# ---------- pagos ----------


def _partes_dominio(datos: PagoEntrada) -> list[ParteCobro]:
    return [
        ParteCobro(
            p.medio, a_importe(p.importe), str(p.comprobante_id) if p.comprobante_id else None
        )
        for p in datos.partes
    ]


async def _verificar_comprobantes(
    sesion: AsyncSession, quien: Identidad, datos: PagoEntrada, pedido_id: uuid.UUID | None
) -> list[Comprobante]:
    comprobantes: list[Comprobante] = []
    for parte in datos.partes:
        if parte.medio not in MEDIOS_CON_COMPROBANTE:
            continue
        if parte.comprobante_id is None:
            raise ErrorDominio(f"El cobro por {parte.medio} necesita la foto del comprobante")
        comprobante = await repository.comprobante_por_id(sesion, parte.comprobante_id)
        if (
            comprobante is None
            or comprobante.subido_por != quien.usuario_id
            and quien.rol is not Rol.ADMIN
        ):
            raise NoEncontrado("Comprobante")
        if comprobante.pago_id is not None:
            raise Conflicto("Ese comprobante ya está atado a otro cobro")
        if comprobante.pedido_id is not None and comprobante.pedido_id != pedido_id:
            raise ErrorDominio("El comprobante es de otro pedido")
        comprobantes.append(comprobante)
    return comprobantes


async def _a_salida(sesion: AsyncSession, pago: Pago, cliente: Cliente | None = None) -> PagoSalida:
    if cliente is None:
        cliente = await clientes.obtener_interno(sesion, pago.cliente_id)
    nombres = {u.id: u.nombre for u in await auth.listar_todos(sesion)}
    return PagoSalida(
        id=pago.id,
        cliente_id=pago.cliente_id,
        cliente_nombre=cliente.nombre_comercial,
        pedido_id=pago.pedido_id,
        fecha=pago.fecha,
        total=pago.total,
        partes=[
            ParteSalida(
                medio=Medio(str(p["medio"])),
                importe=a_importe(str(p["importe"])),
                comprobante_id=uuid.UUID(str(p["comprobante_id"]))
                if p.get("comprobante_id")
                else None,
            )
            for p in pago.partes
        ],
        pedidos_cubiertos=[str(x) for x in pago.pedidos_cubiertos],
        saldo_a_favor_usado=pago.saldo_a_favor_usado,
        nota=pago.nota,
        cobrado_por=pago.cobrado_por,
        cobrado_por_nombre=nombres.get(pago.cobrado_por, ""),
    )


async def registrar_pago(sesion: AsyncSession, quien: Identidad, datos: PagoEntrada) -> PagoSalida:
    """
    Cobro en la entrega (con pedido): las partes suman el total del pedido menos el saldo a favor
    que se descuenta; el pedido queda pagado. Pago a cuenta (sin pedido): cubre pedidos a cuenta
    del más viejo al más nuevo; lo que sobra queda como saldo a favor.
    """
    existente = await repository.pago_por_idempotencia(sesion, datos.idempotencia)
    if existente is not None:
        return await _a_salida(sesion, existente)  # reintento offline: mismo cobro, sin duplicar
    cliente = await clientes.obtener(sesion, quien, datos.cliente_id)
    partes = _partes_dominio(datos)
    comprobantes = await _verificar_comprobantes(sesion, quien, datos, datos.pedido_id)
    pago = Pago(
        id=uuid.uuid4(),
        sucursal_id=cliente.sucursal_id,
        cliente_id=cliente.id,
        pedido_id=datos.pedido_id,
        cobrado_por=quien.usuario_id,
        fecha=ahora(),
        total=CERO,
        partes=[
            {"medio": p.medio, "importe": str(p.importe), "comprobante_id": p.comprobante_id}
            for p in partes
        ],
        nota=datos.nota.strip(),
        idempotencia=datos.idempotencia,
    )
    saldo_usado = CERO
    cubiertos: list[str] = []

    if datos.pedido_id is not None:
        pedido = await pedidos.obtener_modelo(sesion, quien, datos.pedido_id)
        if pedido.cliente_id != cliente.id:
            raise ErrorDominio("El pedido es de otro cliente")
        if pedido.pagado:
            raise Conflicto(f"El pedido {formatear_numero(pedido.numero)} ya está cobrado")
        if pedido.total <= CERO:
            raise ErrorDominio("El pedido no tiene importe: falta pesar o poner precio")
        if pedido.a_cuenta:
            raise ErrorDominio("Es un pedido a cuenta: registrá un pago a cuenta sin pedido")
        a_favor = max(-(await saldo_de(sesion, cliente.id)), CERO)
        saldo_usado = min(a_favor, pedido.total)
        a_cobrar = pedido.total - saldo_usado
        if a_cobrar == CERO:
            raise ErrorDominio("El saldo a favor cubre todo el pedido: no hay nada que cobrar")
        pago.total = validar_cobro(partes, a_cobrar)
        if saldo_usado > CERO:
            await registrar_ajuste(
                sesion,
                quien,
                cliente.id,
                TipoAjuste.USO_SALDO,
                saldo_usado,
                f"Saldo a favor aplicado al pedido {formatear_numero(pedido.numero)}",
                referencia=formatear_numero(pedido.numero),
            )
        await pedidos.marcar_pagados(sesion, quien, [pedido], pago.id)
        cubiertos = [formatear_numero(pedido.numero)]
    else:
        pago.total = validar_cobro(partes, sum((p.importe for p in partes), CERO))
        todos = await pedidos.a_cuenta_de_cliente(sesion, cliente.id)
        pendientes = _pendientes(todos)
        pendientes_total = sum((_importe_en_cuenta(p) for p in pendientes), CERO)
        saldo = await saldo_de(sesion, cliente.id)
        # Crédito no atribuido a ningún pedido: lo ya pagado que excede la deuda pendiente.
        credito_previo = max(pendientes_total - saldo, CERO)
        aplicacion = aplicar_pago(
            [PedidoPendiente(str(p.id), _importe_en_cuenta(p), p.creado_en) for p in pendientes],
            pago.total,
            credito_previo,
        )
        cubiertos_modelos = [p for p in pendientes if str(p.id) in aplicacion.cubiertos]
        await pedidos.marcar_pagados(sesion, quien, cubiertos_modelos, pago.id)
        cubiertos = [formatear_numero(p.numero) for p in cubiertos_modelos]

    pago.pedidos_cubiertos = cubiertos
    pago.saldo_a_favor_usado = saldo_usado
    sesion.add(pago)
    await sesion.flush()
    for comprobante in comprobantes:
        comprobante.pago_id = pago.id
    registrar(
        sesion,
        quien,
        "pago.registrar",
        "pago",
        pago.id,
        {
            "cliente_id": str(cliente.id),
            "total": str(pago.total),
            "partes": pago.partes,
            "cubiertos": cubiertos,
            "saldo_usado": str(saldo_usado),
        },
    )
    await sesion.commit()
    return await _a_salida(sesion, pago, cliente)


async def pago_por_id(sesion: AsyncSession, quien: Identidad, pago_id: uuid.UUID) -> PagoSalida:
    pago = await repository.pago_por_id(sesion, pago_id)
    if pago is None:
        raise NoEncontrado("Pago")
    if quien.rol is not Rol.ADMIN and pago.cobrado_por != quien.usuario_id:
        raise NoEncontrado("Pago")
    return await _a_salida(sesion, pago)


# ---------- cobrador ----------


async def cuentas_a_cobrar(sesion: AsyncSession, quien: Identidad) -> list[CuentaACobrar]:
    """Clientes con saldo deudor, ordenados por zona y nombre."""
    visibles = await clientes.visibles_para_cobrar(sesion, quien)
    ultimos = await repository.ultimo_pago_por_cliente(sesion, [c.id for c in visibles])
    cuentas: list[CuentaACobrar] = []
    for cliente in visibles:
        saldo = await saldo_de(sesion, cliente.id)
        if saldo <= CERO:
            continue
        pendientes = _pendientes(await pedidos.a_cuenta_de_cliente(sesion, cliente.id))
        cuentas.append(
            CuentaACobrar(
                cliente_id=cliente.id,
                nombre=cliente.nombre_comercial,
                direccion=cliente.direccion,
                telefono=cliente.telefono,
                zona_id=cliente.zona_id,
                lat=cliente.lat,
                lng=cliente.lng,
                saldo=saldo,
                pedidos_pendientes=len(pendientes),
                ultimo_pago=ultimos.get(cliente.id),
            )
        )
    return sorted(cuentas, key=lambda c: (str(c.zona_id or ""), c.nombre))


# ---------- caja ----------


async def resumen_caja(
    sesion: AsyncSession, quien: Identidad, fecha: date, usuario_id: uuid.UUID | None
) -> ResumenCaja:
    if quien.rol is not Rol.ADMIN:
        usuario_id = quien.usuario_id
    if usuario_id is None:
        raise ErrorDominio("Indicá de quién es la caja")
    desde = inicio_del_dia(fecha)
    pagos = await repository.pagos_entre(sesion, desde, desde + timedelta(days=1), usuario_id)
    partes = [
        ParteCobro(Medio(str(p["medio"])), a_importe(str(p["importe"])), p.get("comprobante_id"))
        for pago in pagos
        for p in pago.partes
    ]
    resumen = resumir_caja(partes)
    cierre = await repository.cierre_de(sesion, usuario_id, fecha)
    nombres = {u.id: u.nombre for u in await auth.listar_todos(sesion)}
    return ResumenCaja(
        usuario_id=usuario_id,
        usuario_nombre=nombres.get(usuario_id, ""),
        fecha=fecha,
        efectivo_esperado=resumen.efectivo_esperado,
        transferencias=resumen.transferencias,
        cheques=resumen.cheques,
        total_cobrado=resumen.total_cobrado,
        cantidad_cobros=len(pagos),
        pagos=[await _a_salida(sesion, p) for p in pagos],
        cierre=CierreSalida.model_validate(cierre) if cierre else None,
    )


async def cerrar(sesion: AsyncSession, quien: Identidad, datos: CierreEntrada) -> CierreSalida:
    usuario_id = datos.usuario_id or quien.usuario_id
    if quien.rol is not Rol.ADMIN and usuario_id != quien.usuario_id:
        raise SinPermiso("Solo administración cierra la caja de otra persona")
    if await repository.cierre_de(sesion, usuario_id, datos.fecha):
        raise Conflicto("La caja de ese día ya está cerrada")
    resumen = await resumen_caja(sesion, quien, datos.fecha, usuario_id)
    cierre_dominio = cerrar_caja(
        resumir_caja(
            [
                ParteCobro(p.medio, p.importe, str(p.comprobante_id) if p.comprobante_id else None)
                for pago in resumen.pagos
                for p in pago.partes
            ]
        ),
        datos.efectivo_recibido,
        datos.nota,
    )
    fila = CierreCaja(
        sucursal_id=quien.sucursal_id,
        usuario_id=usuario_id,
        fecha=datos.fecha,
        efectivo_esperado=cierre_dominio.efectivo_esperado,
        efectivo_recibido=cierre_dominio.efectivo_recibido,
        transferencias=resumen.transferencias,
        cheques=resumen.cheques,
        diferencia=cierre_dominio.diferencia,
        nota=cierre_dominio.nota,
        cerrado_por=quien.usuario_id,
        cerrado_en=ahora(),
    )
    sesion.add(fila)
    await sesion.flush()
    registrar(
        sesion,
        quien,
        "caja.cerrar",
        "cierre_caja",
        fila.id,
        {"usuario_id": str(usuario_id), "diferencia": str(fila.diferencia)},
    )
    await sesion.commit()
    return CierreSalida.model_validate(fila)


async def cierres_del_dia(
    sesion: AsyncSession, quien: Identidad, fecha: date
) -> list[CierreSalida]:
    if quien.rol is not Rol.ADMIN:
        raise SinPermiso("Solo administración ve todas las cajas")
    return [
        CierreSalida.model_validate(c)
        for c in await repository.cierres_del_dia(sesion, fecha, None)
    ]


async def rendicion_del_dia(
    sesion: AsyncSession, quien: Identidad, fecha: date
) -> list[ResumenCaja]:
    """Una caja por persona que cobró ese día (o que ya la cerró), para la pantalla de rendición."""
    if quien.rol is not Rol.ADMIN:
        raise SinPermiso("Solo administración ve la rendición completa")
    desde = inicio_del_dia(fecha)
    pagos = await repository.pagos_entre(sesion, desde, desde + timedelta(days=1))
    cierres = await repository.cierres_del_dia(sesion, fecha, None)
    usuarios = {p.cobrado_por for p in pagos} | {c.usuario_id for c in cierres}
    resumenes = [await resumen_caja(sesion, quien, fecha, u) for u in usuarios]
    return sorted(resumenes, key=lambda r: r.usuario_nombre)
