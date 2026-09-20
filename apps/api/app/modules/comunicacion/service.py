import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import NoEncontrado, SinPermiso
from app.core.seguridad import Identidad, Rol
from app.core.tiempo import ahora
from app.core.tiempo_real import difusor
from app.modules.auditoria.service import registrar
from app.modules.auth import service as auth
from app.modules.comunicacion import repository
from app.modules.comunicacion.models import Mensaje, Noticia
from app.modules.comunicacion.schemas import (
    MensajeEntrada,
    MensajeSalida,
    NoticiaCambios,
    NoticiaEntrada,
    NoticiaSalida,
)


async def listar_noticias(
    sesion: AsyncSession, quien: Identidad, incluir_archivadas: bool
) -> list[NoticiaSalida]:
    filas = await repository.noticias(
        sesion, quien.sucursal_id, incluir_archivadas and quien.rol is Rol.ADMIN
    )
    return [NoticiaSalida.model_validate(n) for n in filas]


async def publicar_noticia(
    sesion: AsyncSession, quien: Identidad, datos: NoticiaEntrada
) -> NoticiaSalida:
    noticia = Noticia(
        sucursal_id=quien.sucursal_id,
        autor_id=quien.usuario_id,
        titulo=datos.titulo.strip(),
        cuerpo=datos.cuerpo.strip(),
        fijada=datos.fijada,
    )
    sesion.add(noticia)
    await sesion.flush()
    registrar(sesion, quien, "noticia.publicar", "noticia", noticia.id)
    await sesion.commit()
    await sesion.refresh(noticia)
    await difusor.publicar(
        quien.sucursal_id, "noticia", {"id": str(noticia.id), "titulo": noticia.titulo}
    )
    return NoticiaSalida.model_validate(noticia)


async def modificar_noticia(
    sesion: AsyncSession, quien: Identidad, noticia_id: uuid.UUID, cambios: NoticiaCambios
) -> NoticiaSalida:
    if quien.rol is not Rol.ADMIN:
        raise SinPermiso("Solo administración fija o archiva noticias")
    noticia = await repository.noticia_por_id(sesion, noticia_id)
    if noticia is None or noticia.sucursal_id != quien.sucursal_id:
        raise NoEncontrado("Noticia")
    for campo, valor in cambios.model_dump(exclude_unset=True).items():
        setattr(noticia, campo, valor.strip() if isinstance(valor, str) else valor)
    registrar(sesion, quien, "noticia.modificar", "noticia", noticia.id)
    await sesion.commit()
    return NoticiaSalida.model_validate(noticia)


def _a_mensaje(m: Mensaje, nombres: dict[uuid.UUID, str]) -> MensajeSalida:
    return MensajeSalida(
        id=m.id,
        autor_id=m.autor_id,
        autor_nombre=nombres.get(m.autor_id, ""),
        cuerpo=m.cuerpo,
        creado_en=m.creado_en,
    )


async def listar_mensajes(
    sesion: AsyncSession, quien: Identidad, limite: int
) -> list[MensajeSalida]:
    nombres = {u.id: u.nombre for u in await auth.listar_todos(sesion)}
    filas = await repository.mensajes(sesion, quien.sucursal_id, limite)
    return [_a_mensaje(m, nombres) for m in filas]


async def enviar_mensaje(
    sesion: AsyncSession, quien: Identidad, datos: MensajeEntrada
) -> MensajeSalida:
    mensaje = Mensaje(
        sucursal_id=quien.sucursal_id,
        autor_id=quien.usuario_id,
        cuerpo=datos.cuerpo.strip(),
        creado_en=ahora(),
    )
    sesion.add(mensaje)
    await sesion.commit()
    salida = _a_mensaje(mensaje, {quien.usuario_id: quien.nombre})
    await difusor.publicar(quien.sucursal_id, "mensaje", salida.model_dump(mode="json"))
    return salida
