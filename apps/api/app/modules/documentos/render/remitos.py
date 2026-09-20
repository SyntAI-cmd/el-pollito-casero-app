"""
Remito: 4 por hoja A4 (cada uno un A6 de 105 × 148,5 mm, proporción del talonario 10 × 15).
Logo/datos fiscales, N° correlativo, tabla KILOS · DETALLE · PRECIO X UN. · PRECIO TOTAL,
CAJAS ADEUDADAS, SALDO de cuenta corriente, TOTAL y firma conforme.
"""

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.modules.documentos.datos import Contexto
from app.modules.documentos.render import kilos, pesos
from app.modules.pedidos.schemas import PedidoSalida

ANCHO, ALTO = A4
CUADRANTES = [(0, ALTO / 2), (ANCHO / 2, ALTO / 2), (0, 0), (ANCHO / 2, 0)]
MARGEN = 6 * mm


def _remito(c: canvas.Canvas, x0: float, y0: float, pedido: PedidoSalida, ctx: Contexto) -> None:
    ancho, alto = ANCHO / 2, ALTO / 2
    x, y = x0 + MARGEN, y0 + alto - MARGEN
    fiscal = ctx.fiscal
    c.setDash(2, 2)
    c.setStrokeGray(0.6)
    c.rect(x0, y0, ancho, alto)
    c.setDash()
    c.setStrokeGray(0)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y - 10, fiscal.fiscal_razon_social)
    c.setFont("Helvetica", 6.5)
    c.drawString(x, y - 18, fiscal.fiscal_lema)
    c.drawString(
        x,
        y - 25,
        f"CUIT {fiscal.fiscal_cuit} · IIBB {fiscal.fiscal_iibb} · "
        f"Inicio {fiscal.fiscal_inicio_actividades}",
    )
    c.drawString(x, y - 32, fiscal.fiscal_condicion_iva)
    c.drawString(x, y - 39, fiscal.fiscal_domicilio)
    c.drawString(x, y - 46, f"WhatsApp {fiscal.fiscal_whatsapp}")

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(x0 + ancho - MARGEN, y - 10, f"REMITO N° {pedido.numero}")
    c.setFont("Helvetica", 7.5)
    c.drawRightString(
        x0 + ancho - MARGEN, y - 20, f"Fecha {pedido.fecha_reparto:%d/%m/%Y} · {pedido.turno}"
    )
    c.drawRightString(
        x0 + ancho - MARGEN, y - 28, f"Preventista: {ctx.nombre(pedido.preventista_id)}"
    )

    datos = ctx.clientes.get(pedido.cliente_id)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x, y - 60, f"Sr./es: {pedido.cliente_nombre}")
    c.setFont("Helvetica", 7.5)
    c.drawString(x, y - 69, f"Domicilio: {pedido.cliente_direccion or '—'}")
    c.drawString(x, y - 77, f"CUIT: {datos.cuit if datos and datos.cuit else '—'}")

    # Tabla
    top = y - 86
    cols = [x, x + 20 * mm, x + 62 * mm, x + 78 * mm, x0 + ancho - MARGEN]
    c.setFont("Helvetica-Bold", 6.5)
    for etiqueta, cx in zip(
        ["KILOS", "DETALLE", "PRECIO X UN.", "PRECIO TOTAL"], cols[:4], strict=True
    ):
        c.drawString(cx + 1, top - 7, etiqueta)
    c.line(x, top - 9, cols[-1], top - 9)
    c.setFont("Helvetica", 7.5)
    fila = top - 18
    for item in pedido.items:
        c.drawString(cols[0] + 1, fila, kilos(item.kg_pesados))
        detalle = item.producto_nombre + (f" ({item.cajas} cajas)" if item.cajas else "")
        c.drawString(cols[1] + 1, fila, detalle[:34])
        c.drawRightString(cols[3] - 2, fila, pesos(item.precio) if item.precio else "—")
        c.drawRightString(cols[4] - 1, fila, pesos(item.importe))
        fila -= 9
    if pedido.observaciones:
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(x, fila, f"Obs.: {pedido.observaciones[:70]}")

    # Pie
    base = y0 + MARGEN
    c.setFont("Helvetica", 7.5)
    envases = datos.envases if datos else 0
    c.drawString(x, base + 40, f"CAJAS ADEUDADAS: {envases if envases > 0 else ''}")
    saldo = datos.saldo if datos else None
    c.drawString(x, base + 30, f"SALDO CTA. CTE.: {pesos(saldo) if saldo is not None else '—'}")
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(cols[-1], base + 30, f"TOTAL {pesos(pedido.total)}")
    c.line(cols[-1] - 45 * mm, base + 12, cols[-1], base + 12)
    c.setFont("Helvetica", 6.5)
    c.drawRightString(cols[-1], base + 5, "Firma conforme")


def render(ctx: Contexto) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle("Remitos")
    for i, pedido in enumerate(ctx.pedidos):
        x0, y0 = CUADRANTES[i % 4]
        _remito(c, x0, y0, pedido, ctx)
        if i % 4 == 3:
            c.showPage()
    if not ctx.pedidos or len(ctx.pedidos) % 4 != 0:
        c.showPage()
    c.save()
    return buffer.getvalue()
