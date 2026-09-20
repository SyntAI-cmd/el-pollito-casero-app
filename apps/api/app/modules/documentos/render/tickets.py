"""Tickets de preparación para comandera de 80 mm: uno por pedido, un casillero por caja."""

from io import BytesIO

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.modules.documentos.datos import Contexto
from app.modules.documentos.render import kilos

ANCHO = 80 * mm
CASILLA = 6 * mm


def render(ctx: Contexto) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.setTitle("Tickets de preparación")
    for pedido in ctx.pedidos or []:
        filas_casillas = sum(max(1, ((item.cajas or 0) + 9) // 10) for item in pedido.items)
        alto = (40 + 10 * len(pedido.items)) * mm + filas_casillas * (CASILLA + 2 * mm) + 20 * mm
        c.setPageSize((ANCHO, alto))
        y = alto - 8 * mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(4 * mm, y, f"#{pedido.numero}")
        c.setFont("Helvetica", 8)
        c.drawRightString(ANCHO - 4 * mm, y, f"{pedido.fecha_reparto:%d/%m} · {pedido.turno}")
        y -= 7 * mm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(4 * mm, y, pedido.cliente_nombre[:30])
        y -= 5 * mm
        c.setFont("Helvetica", 8)
        c.drawString(4 * mm, y, f"{ctx.nombre(pedido.preventista_id)}"[:34])
        y -= 6 * mm
        for item in pedido.items:
            c.setFont("Helvetica-Bold", 10)
            detalle = f"{item.producto_nombre}: " + (
                f"{item.cajas} cajas" if item.cajas else f"{kilos(item.kg_pedidos)} kg"
            )
            c.drawString(4 * mm, y, detalle)
            y -= 4 * mm
            cajas = item.cajas or 1
            x = 4 * mm
            for n in range(cajas):
                if n and n % 10 == 0:
                    x = 4 * mm
                    y -= CASILLA + 2 * mm
                c.rect(x, y - CASILLA, CASILLA, CASILLA)
                x += CASILLA + 1.2 * mm
            y -= CASILLA + 4 * mm
        if pedido.observaciones:
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(4 * mm, y, pedido.observaciones[:36])
            y -= 5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.rect(4 * mm, y - 7 * mm, 7 * mm, 7 * mm)
        c.drawString(13 * mm, y - 5 * mm, "CARGADO AL CAMIÓN")
        c.showPage()
    if not ctx.pedidos:
        c.setPageSize((ANCHO, 40 * mm))
        c.drawString(4 * mm, 20 * mm, "Sin pedidos")
        c.showPage()
    c.save()
    return buffer.getvalue()
