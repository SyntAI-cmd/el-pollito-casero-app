import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errores import Conflicto, NoEncontrado, SinPermiso
from app.core.seguridad import (
    Identidad,
    Rol,
    TokenInvalido,
    emitir_acceso,
    emitir_refresh,
    hashear_clave,
    leer_refresh,
    verificar_clave,
)
from app.core.tiempo import ahora
from app.modules.auditoria.service import registrar
from app.modules.auth import repository
from app.modules.auth.models import SesionRefresh, Usuario
from app.modules.auth.schemas import UsuarioCambios, UsuarioEntrada


def identidad_de(usuario: Usuario) -> Identidad:
    return Identidad(
        usuario_id=usuario.id,
        sucursal_id=usuario.sucursal_id,
        rol=usuario.rol,
        nombre=usuario.nombre,
    )


async def _abrir_sesion(sesion: AsyncSession, usuario: Usuario) -> tuple[str, str]:
    fila = SesionRefresh(
        id=uuid.uuid4(),
        usuario_id=usuario.id,
        creado_en=ahora(),
        expira_en=ahora() + timedelta(days=get_settings().jwt_refresh_dias),
    )
    sesion.add(fila)
    return emitir_acceso(identidad_de(usuario)), emitir_refresh(usuario.id, fila.id)


async def login(sesion: AsyncSession, nombre_usuario: str, clave: str) -> tuple[str, str, Usuario]:
    usuario = await repository.por_usuario(sesion, nombre_usuario.strip().lower())
    # Mismo mensaje exista o no el usuario: no se revela cuál de los dos datos falló.
    if usuario is None or not verificar_clave(clave, usuario.clave_hash):
        raise TokenInvalido("Usuario o clave incorrectos")
    if not usuario.activo:
        raise SinPermiso("El usuario está dado de baja")
    acceso, refresh = await _abrir_sesion(sesion, usuario)
    await sesion.commit()
    return acceso, refresh, usuario


async def refrescar(sesion: AsyncSession, token_refresh: str) -> tuple[str, str, Usuario]:
    """Rotación: cada refresh revoca el anterior; uno robado deja de servir en el primer uso."""
    usuario_id, jti = leer_refresh(token_refresh)
    fila = await repository.sesion_refresh(sesion, jti)
    if fila is None or fila.usuario_id != usuario_id or fila.revocado_en is not None:
        raise TokenInvalido("La sesión ya no es válida, volvé a entrar")
    if fila.expira_en < ahora():
        raise TokenInvalido("La sesión venció, volvé a entrar")
    usuario = await repository.por_id(sesion, usuario_id)
    if usuario is None or not usuario.activo:
        raise SinPermiso("El usuario está dado de baja")
    fila.revocado_en = ahora()
    acceso, refresh = await _abrir_sesion(sesion, usuario)
    await sesion.commit()
    return acceso, refresh, usuario


async def cerrar_sesion(sesion: AsyncSession, token_refresh: str) -> None:
    try:
        _, jti = leer_refresh(token_refresh)
    except TokenInvalido:
        return
    fila = await repository.sesion_refresh(sesion, jti)
    if fila is not None and fila.revocado_en is None:
        fila.revocado_en = ahora()
        await sesion.commit()


async def yo(sesion: AsyncSession, identidad: Identidad) -> Usuario:
    usuario = await repository.por_id(sesion, identidad.usuario_id)
    if usuario is None:
        raise NoEncontrado("Usuario")
    return usuario


async def listar_usuarios(sesion: AsyncSession, quien: Identidad) -> list[Usuario]:
    return list(
        await repository.listar(sesion, None if quien.rol is Rol.ADMIN else quien.sucursal_id)
    )


async def crear_usuario(sesion: AsyncSession, quien: Identidad, datos: UsuarioEntrada) -> Usuario:
    if await repository.por_usuario(sesion, datos.usuario):
        raise Conflicto(f"Ya existe el usuario {datos.usuario}")
    usuario = Usuario(
        sucursal_id=datos.sucursal_id,
        nombre=datos.nombre.strip(),
        usuario=datos.usuario,
        clave_hash=hashear_clave(datos.clave),
        rol=datos.rol,
        telefono=datos.telefono,
        cuit=datos.cuit,
    )
    sesion.add(usuario)
    await sesion.flush()
    registrar(sesion, quien, "usuario.crear", "usuario", usuario.id, {"rol": datos.rol})
    await sesion.commit()
    return usuario


async def modificar_usuario(
    sesion: AsyncSession, quien: Identidad, usuario_id: uuid.UUID, cambios: UsuarioCambios
) -> Usuario:
    usuario = await repository.por_id(sesion, usuario_id)
    if usuario is None:
        raise NoEncontrado("Usuario")
    if usuario.id == quien.usuario_id and cambios.activo is False:
        raise Conflicto("No podés darte de baja a vos mismo")
    datos = cambios.model_dump(exclude_unset=True)
    clave = datos.pop("clave", None)
    if clave:
        usuario.clave_hash = hashear_clave(clave)
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)
    registrar(sesion, quien, "usuario.modificar", "usuario", usuario.id, {"campos": sorted(datos)})
    await sesion.commit()
    return usuario
