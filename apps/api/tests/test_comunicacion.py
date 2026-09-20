from httpx import AsyncClient


async def test_noticias_del_equipo(
    cliente: AsyncClient, como_admin: dict[str, str], como_preventista: dict[str, str]
) -> None:
    assert (
        await cliente.post("/noticias", json={"titulo": "Hola"}, headers=como_preventista)
    ).status_code == 403
    fijada = await cliente.post(
        "/noticias",
        json={"titulo": "Mañana no hay reparto a La Paz", "cuerpo": "Feriado", "fijada": True},
        headers=como_admin,
    )
    assert fijada.status_code == 201
    otra = await cliente.post("/noticias", json={"titulo": "Cambia la tara"}, headers=como_admin)
    lista = await cliente.get("/noticias", headers=como_preventista)
    assert [n["titulo"] for n in lista.json()] == [
        "Mañana no hay reparto a La Paz",
        "Cambia la tara",
    ]
    await cliente.patch(
        f"/noticias/{otra.json()['id']}", json={"archivada": True}, headers=como_admin
    )
    assert len((await cliente.get("/noticias", headers=como_preventista)).json()) == 1
    assert (
        len(
            (
                await cliente.get(
                    "/noticias", params={"incluir_archivadas": "true"}, headers=como_admin
                )
            ).json()
        )
        == 2
    )


async def test_chat_interno(
    cliente: AsyncClient, como_admin: dict[str, str], como_preventista: dict[str, str]
) -> None:
    enviado = await cliente.post(
        "/mensajes", json={"cuerpo": "Salgo a las 6"}, headers=como_preventista
    )
    assert enviado.status_code == 201 and enviado.json()["autor_nombre"] == "Franco"
    await cliente.post("/mensajes", json={"cuerpo": "Dale"}, headers=como_admin)
    mensajes = await cliente.get("/mensajes", headers=como_admin)
    assert [m["cuerpo"] for m in mensajes.json()] == ["Salgo a las 6", "Dale"]


async def test_rendicion_del_dia_solo_admin(
    cliente: AsyncClient, como_admin: dict[str, str], como_preventista: dict[str, str]
) -> None:
    from app.core.tiempo import hoy

    assert (
        await cliente.get(
            "/caja/rendicion", params={"fecha": hoy().isoformat()}, headers=como_preventista
        )
    ).status_code == 403
    assert (
        await cliente.get(
            "/caja/rendicion", params={"fecha": hoy().isoformat()}, headers=como_admin
        )
    ).json() == []
