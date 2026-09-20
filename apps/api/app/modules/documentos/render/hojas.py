"""
Hoja de pedidos del día (A4 apaisada, por turno y preventista) y hoja de ruta y rendición
(por preventista, 26 pedidos por hoja, columnas en blanco para efectivo / transferencia /
cheque / saldo y cuadro de rendición).
"""

from collections import defaultdict
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.domain.dinero import CERO
from app.modules.documentos.datos import Contexto
from app.modules.documentos.render import kilos, pesos
from app.modules.pedidos.schemas import PedidoSalida

FILAS_POR_HOJA = 26


def _cabecera(
    c: canvas.Canvas, ctx: Contexto, titulo: str, subtitulo: str, ancho: float, alto: float
) -> float:
    c.setFont("Helvetica-Bold", 14)
    c.drawString(12 * mm, alto - 14 * mm, f"{ctx.fiscal.fiscal_razon_social} · {titulo}")
    c.setFont("Helvetica", 9)
    fecha = ctx.fecha.strftime("%d/%m/%Y") if ctx.fecha else "varios días"
    c.drawString(
        12 * mm, alto - 20 * mm, f"{fecha} · {ctx.turno or 'todos los turnos'} · {subtitulo}"
    )
    c.line(12 * mm, alto - 23 * mm, ancho - 12 * mm, alto - 23 * mm)
    return float(alto - 30 * mm)


def _agrupar(ctx: Contexto) -> dict[str, list[PedidoSalida]]:
    grupos: dict[str, list[PedidoSalida]] = defaultdict(list)
    for p in ctx.pedidos:
        grupos[ctx.nombre(p.preventista_id)].append(p)
    return dict(sorted(grupos.items()))


def render_hoja_pedidos(ctx: Contexto) -> bytes:
    buffer = BytesIO()
    ancho, alto = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    c.setTitle("Hoja de pedidos")
    for preventista, lista in _agrupar(ctx).items() or {"Sin pedidos": []}.items():
        y = _cabecera(
            c, ctx, "Hoja de pedidos", f"{preventista} · {len(lista)} pedidos", ancho, alto
        )
        cols = [12 * mm, 30 * mm, 110 * mm, 175 * mm, 205 * mm, 235 * mm]
        c.setFont("Helvetica-Bold", 8)
        for etiqueta, cx in zip(
            ["N°", "Cliente y dirección", "Producto", "Cajas", "Kg pedidos", "Observación"],
            cols,
            strict=True,
        ):
            c.drawString(cx, y, etiqueta)
        y -= 4 * mm
        c.setFont("Helvetica", 8)
        for p in lista:
            for i, item in enumerate(p.items):
                if y < 15 * mm:
                    c.showPage()
                    y = _cabecera(c, ctx, "Hoja de pedidos", f"{preventista} (cont.)", ancho, alto)
                    c.setFont("Helvetica", 8)
                if i == 0:
                    c.setFont("Helvetica-Bold", 8)
                    c.drawString(cols[0], y, p.numero)
                    c.setFont("Helvetica", 8)
                    c.drawString(cols[1], y, f"{p.cliente_nombre} · {p.cliente_direccion}"[:55])
                    c.drawString(cols[5], y, p.observaciones[:30])
                c.drawString(cols[2], y, item.producto_nombre)
                c.drawString(cols[3], y, str(item.cajas or ""))
                c.drawString(cols[4], y, kilos(item.kg_pedidos) if item.kg_pedidos else "")
                y -= 4.5 * mm
            c.setStrokeGray(0.8)
            c.line(cols[0], y + 2 * mm, ancho - 12 * mm, y + 2 * mm)
            c.setStrokeGray(0)
            y -= 1.5 * mm
        c.showPage()
    c.save()
    return buffer.getvalue()


def render_hoja_ruta(ctx: Contexto) -> bytes:
    buffer = BytesIO()
    ancho, alto = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    c.setTitle("Hoja de ruta y rendición")
    grupos = _agrupar(ctx) or {"Sin pedidos": []}
    for preventista, lista in grupos.items():
        for inicio in range(0, max(len(lista), 1), FILAS_POR_HOJA):
            pagina = lista[inicio : inicio + FILAS_POR_HOJA]
            y = _cabecera(c, ctx, "Hoja de ruta y rendición", preventista, ancho, alto)
            cols = [
                12 * mm,
                28 * mm,
                110 * mm,
                130 * mm,
                158 * mm,
                186 * mm,
                214 * mm,
                242 * mm,
                270 * mm,
            ]
            titulos = [
                "N°",
                "Cliente",
                "Cajas ad.",
                "Total",
                "Efectivo",
                "Transf.",
                "Cheque",
                "Saldo",
            ]
            c.setFont("Helvetica-Bold", 8)
            for etiqueta, cx in zip(titulos, cols[:-1], strict=True):
                c.drawString(cx + 1, y, etiqueta)
            y -= 2 * mm
            c.setFont("Helvetica", 8)
            for p in pagina:
                y -= 6 * mm
                datos = ctx.clientes.get(p.cliente_id)
                envases = datos.envases if datos else 0
                c.drawString(cols[0] + 1, y + 1.5 * mm, p.numero)
                c.drawString(cols[1] + 1, y + 1.5 * mm, p.cliente_nombre[:48])
                c.drawString(cols[2] + 1, y + 1.5 * mm, str(envases) if envases > 0 else "")
                c.drawRightString(
                    cols[4] - 2, y + 1.5 * mm, pesos(p.total) if p.total > CERO else "sin pesar"
                )
                for cx in cols[:-1]:
                    c.rect(cx, y, cols[cols.index(cx) + 1] - cx, 6 * mm, stroke=1, fill=0)
            # Cuadro de rendición
            y -= 14 * mm
            c.setFont("Helvetica-Bold", 9)
            c.drawString(12 * mm, y, "RENDICIÓN")
            c.setFont("Helvetica", 8)
            filas = [
                ("Pedidos", str(len(lista))),
                ("Total a cobrar", pesos(sum((p.total for p in lista), CERO))),
                ("Efectivo recibido", ""),
                ("Transferencias", ""),
                ("Cheques", ""),
                ("A cuenta", ""),
                ("Diferencia", ""),
            ]
            for i, (etiqueta, valor) in enumerate(filas):
                fy = y - 6 * mm * (i + 1)
                c.rect(12 * mm, fy, 60 * mm, 6 * mm)
                c.drawString(13 * mm, fy + 1.5 * mm, etiqueta)
                c.drawRightString(71 * mm, fy + 1.5 * mm, valor)
            c.drawString(120 * mm, y - 30 * mm, "Firma preventista: ______________________")
            c.drawString(120 * mm, y - 40 * mm, "Firma administración: ___________________")
            c.showPage()
    c.save()
    return buffer.getvalue()
