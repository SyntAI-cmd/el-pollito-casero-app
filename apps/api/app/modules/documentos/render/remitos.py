"""
Remito interno: réplica del talonario impreso de 10 × 15 cm (logo, cuadro X, REMITO INTERNO,
N° y fecha, Cliente / Calle / Localidad / Cel., tabla KILOS · DETALLE · PRECIO X UNIDAD ·
PRECIO TOTAL, CAJAS ADEUDADAS y TOTAL). Dos formatos:

- `a4`: cuatro por hoja A4 (cada uno a 95 × 142,5 mm, misma proporción) con marcas de corte.
- `10x15`: uno por página de 100 × 150 mm, para imprimir directo en el talonario.

Todo se dibuja en un marco de referencia de 100 × 150 mm y se escala.
"""

from collections.abc import Callable
from datetime import date
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.modules.documentos.datos import Contexto
from app.modules.documentos.render import kilos, pesos
from app.modules.pedidos.schemas import PedidoSalida

RECURSOS = Path(__file__).parent / "recursos"
LOGO = RECURSOS / "logo_banner.png"

ANCHO_REF, ALTO_REF = 100.0, 150.0  # mm
FILAS = 12
GRIS_CLARO = 0.85
GRIS_TEXTO = 0.45
ROJO = (0.72, 0.09, 0.11)

# Columnas de la tabla, en mm desde el borde izquierdo del remito.
COL_KILOS, COL_DETALLE, COL_UNIDAD, COL_TOTAL = 0.0, 11.0, 56.0, 73.0

Formato = str


class _Lienzo:
    """Dibuja en milímetros relativos a la esquina superior izquierda de un remito, escalado."""

    def __init__(self, c: canvas.Canvas, x0: float, y_sup: float, ancho: float) -> None:
        self.c = c
        self.k = ancho / (ANCHO_REF * mm)  # puntos por mm de referencia, ya escalados
        self.x0 = x0
        self.y_sup = y_sup

    def x(self, valor: float) -> float:
        return self.x0 + valor * mm * self.k

    def y(self, valor: float) -> float:
        return self.y_sup - valor * mm * self.k

    def fuente(self, nombre: str, tamano: float) -> None:
        self.c.setFont(nombre, tamano * self.k)

    def texto(self, x: float, y: float, cadena: str) -> None:
        self.c.drawString(self.x(x), self.y(y), cadena)

    def texto_derecha(self, x: float, y: float, cadena: str) -> None:
        self.c.drawRightString(self.x(x), self.y(y), cadena)

    def texto_centro(self, x: float, y: float, cadena: str) -> None:
        self.c.drawCentredString(self.x(x), self.y(y), cadena)

    def linea(self, x1: float, y1: float, x2: float, y2: float, grosor: float = 0.3) -> None:
        self.c.setLineWidth(grosor * self.k)
        self.c.line(self.x(x1), self.y(y1), self.x(x2), self.y(y2))

    def rect(
        self,
        x: float,
        y: float,
        ancho: float,
        alto: float,
        grosor: float = 0.3,
        relleno: bool = False,
    ) -> None:
        self.c.setLineWidth(grosor * self.k)
        self.c.rect(
            self.x(x), self.y(y + alto), ancho * mm * self.k, alto * mm * self.k, fill=relleno
        )

    def imagen(self, ruta: Path, x: float, y: float, ancho: float, alto: float) -> None:
        self.c.drawImage(
            str(ruta),
            self.x(x),
            self.y(y + alto),
            ancho * mm * self.k,
            alto * mm * self.k,
            preserveAspectRatio=True,
            anchor="sw",
            mask="auto",
        )

    def recortar(self, cadena: str, ancho: float, fuente: str, tamano: float) -> str:
        """Acorta la cadena hasta que entre en `ancho` mm con la fuente dada."""
        limite = ancho * mm * self.k
        while cadena and self.c.stringWidth(cadena, fuente, tamano * self.k) > limite:
            cadena = cadena[:-1]
        return cadena


def _fecha_en_cajas(lz: _Lienzo, x: float, y: float, fecha: date) -> None:
    ancho, alto = 7.5, 4.0
    for i, parte in enumerate((f"{fecha:%d}", f"{fecha:%m}", f"{fecha:%Y}")):
        lz.rect(x + i * ancho, y, ancho, alto, grosor=0.25)
        lz.fuente("Helvetica", 7)
        lz.texto_centro(x + i * ancho + ancho / 2, y + 2.9, parte)


def _encabezado(lz: _Lienzo, pedido: PedidoSalida, ctx: Contexto) -> None:
    fiscal = ctx.fiscal
    lz.rect(0, 0, ANCHO_REF, 35, grosor=0.5)
    lz.linea(44, 0, 44, 35, grosor=0.5)

    if LOGO.exists():
        lz.imagen(LOGO, 4, 6, 36, 11)
    else:
        lz.fuente("Helvetica-Bold", 10)
        lz.c.setFillColorRGB(*ROJO)
        lz.texto(4, 11, fiscal.fiscal_razon_social)
        lz.c.setFillGray(0)
        lz.fuente("Helvetica-Bold", 6)
        lz.texto(4, 15, fiscal.fiscal_lema)
    lz.fuente("Helvetica", 6.5)
    lz.texto(6, 22, fiscal.fiscal_whatsapp)
    lz.texto(6, 26, fiscal.fiscal_domicilio)
    lz.c.setFillGray(GRIS_TEXTO)
    lz.fuente("Helvetica", 5.5)
    lz.texto(6, 30, fiscal.fiscal_condicion_iva)
    lz.c.setFillGray(0)

    # Cuadro con la X del comprobante interno
    lz.rect(44.5, 8.5, 10, 10, grosor=0.5)
    lz.fuente("Helvetica-Bold", 20)
    lz.texto_centro(49.5, 16.5, "X")

    lz.fuente("Helvetica-Bold", 10.5)
    lz.texto(58, 12, "REMITO INTERNO")
    lz.c.setFillGray(GRIS_TEXTO)
    lz.fuente("Helvetica-Bold", 5)
    lz.texto(58, 15, "DOCUMENTO NO VÁLIDO COMO FACTURA")
    lz.fuente("Helvetica", 4.6)
    lz.texto(58, 18.2, f"C.U.I.T.: {fiscal.fiscal_cuit} - Ingresos Brutos: {fiscal.fiscal_iibb}")
    lz.texto(58, 21.2, f"Inicio de Actividades: {fiscal.fiscal_inicio_actividades}")
    lz.c.setFillGray(0)
    lz.fuente("Helvetica", 7)
    lz.texto(58, 25.5, "N°:")
    lz.fuente("Helvetica-Bold", 8)
    lz.texto(64, 25.5, str(pedido.numero))
    lz.fuente("Helvetica", 7)
    lz.texto(58, 30.5, "Fecha:")
    _fecha_en_cajas(lz, 68, 27.2, pedido.fecha_reparto)


def _cliente(lz: _Lienzo, pedido: PedidoSalida, ctx: Contexto) -> None:
    datos = ctx.clientes.get(pedido.cliente_id)
    lz.rect(0, 35, ANCHO_REF, 18, grosor=0.5)
    etiqueta, valor = "Helvetica", "Helvetica-Bold"

    def campo(x: float, y: float, nombre: str, texto: str, ancho: float) -> None:
        lz.fuente(etiqueta, 7)
        lz.texto(x, y, nombre)
        desplazamiento = lz.c.stringWidth(nombre + " ", etiqueta, 7 * lz.k) / (mm * lz.k)
        lz.fuente(valor, 7)
        lz.texto(x + desplazamiento, y, lz.recortar(texto, ancho - desplazamiento, valor, 7))
        lz.c.setStrokeGray(0.7)
        lz.linea(x + desplazamiento, y + 0.8, x + ancho, y + 0.8, grosor=0.2)
        lz.c.setStrokeGray(0)

    campo(5, 41, "Cliente:", pedido.cliente_nombre, 84)
    campo(5, 45.5, "Calle:", pedido.cliente_direccion or "", 84)
    campo(5, 50, "Localidad:", (datos.localidad if datos else "") or "", 42)
    campo(52, 50, "Cel.:", (datos.telefono if datos else "") or "", 37)
    lz.c.setFillGray(GRIS_TEXTO)
    lz.fuente("Helvetica", 5)
    lz.texto_derecha(96, 38.5, f"Prev.: {ctx.nombre(pedido.preventista_id)} · {pedido.turno}")
    lz.c.setFillGray(0)


def _tabla(lz: _Lienzo, pedido: PedidoSalida) -> None:
    top, alto_encabezado, alto_fila = 53.0, 5.5, 6.3
    fondo = top + alto_encabezado + FILAS * alto_fila
    cols = (COL_KILOS, COL_DETALLE, COL_UNIDAD, COL_TOTAL, ANCHO_REF)

    lz.c.setFillGray(GRIS_CLARO)
    lz.rect(0, top, ANCHO_REF, alto_encabezado, grosor=0.5, relleno=True)
    lz.c.setFillGray(0)
    lz.fuente("Helvetica-Bold", 6)
    for titulo, xi, xf in zip(
        ("KILOS", "DETALLE", "PRECIO X UNIDAD", "PRECIO TOTAL"), cols[:4], cols[1:], strict=True
    ):
        lz.texto_centro((xi + xf) / 2, top + 3.9, titulo)

    for i in range(FILAS + 1):
        lz.linea(
            0,
            top + alto_encabezado + i * alto_fila,
            ANCHO_REF,
            top + alto_encabezado + i * alto_fila,
        )
    for x in cols[1:4]:
        lz.linea(x, top, x, fondo)
    lz.rect(0, top, ANCHO_REF, fondo - top, grosor=0.5)

    filas: list[tuple[str, str, str, str]] = []
    for item in pedido.items:
        detalle = item.producto_nombre + (f" · {item.cajas} cajas" if item.cajas else "")
        filas.append(
            (
                kilos(item.kg_pesados) if item.kg_pesados is not None else "",
                detalle,
                pesos(item.precio) if item.precio else "",
                pesos(item.importe) if item.importe else "",
            )
        )
    if pedido.observaciones:
        filas.append(("", f"Obs.: {pedido.observaciones}", "", ""))
    lz.fuente("Helvetica", 7)
    for i, (kg, detalle, unidad, total) in enumerate(filas[:FILAS]):
        y = top + alto_encabezado + (i + 1) * alto_fila - 2.1
        lz.texto_centro((COL_KILOS + COL_DETALLE) / 2, y, kg)
        lz.texto(
            COL_DETALLE + 1.5, y, lz.recortar(detalle, COL_UNIDAD - COL_DETALLE - 3, "Helvetica", 7)
        )
        lz.texto_derecha(COL_TOTAL - 1.5, y, unidad)
        lz.texto_derecha(ANCHO_REF - 1.5, y, total)


def _pie(lz: _Lienzo, pedido: PedidoSalida, ctx: Contexto) -> None:
    top, alto = 134.1, 8.5
    datos = ctx.clientes.get(pedido.cliente_id)
    lz.rect(0, top, ANCHO_REF, alto, grosor=0.5)
    lz.linea(44, top, 44, top + alto, grosor=0.5)
    lz.linea(61, top, 61, top + alto, grosor=0.5)
    lz.linea(COL_TOTAL, top, COL_TOTAL, top + alto, grosor=0.5)

    lz.fuente("Helvetica-Bold", 6)
    lz.texto(2, top + 3.6, "CAJAS ADEUDADAS:")
    envases = datos.envases if datos else 0
    lz.fuente("Helvetica-Bold", 8)
    lz.texto(27, top + 3.6, str(envases) if envases > 0 else "")
    saldo = datos.saldo if datos else None
    if saldo is not None and saldo != 0:
        lz.fuente("Helvetica", 5.5)
        lz.texto(2, top + 7, f"Saldo cta. cte.: {pesos(saldo)}")

    lz.fuente("Helvetica-Bold", 11)
    lz.texto_centro(52.5, top + 6.2, "TOTAL:")
    lz.fuente("Helvetica-Bold", 9)
    lz.texto_derecha(ANCHO_REF - 1.5, top + 5.8, pesos(pedido.total))


def _remito(
    c: canvas.Canvas, x0: float, y_sup: float, ancho: float, pedido: PedidoSalida, ctx: Contexto
) -> None:
    lz = _Lienzo(c, x0, y_sup, ancho)
    c.setStrokeGray(0)
    c.setFillGray(0)
    _encabezado(lz, pedido, ctx)
    _cliente(lz, pedido, ctx)
    _tabla(lz, pedido)
    _pie(lz, pedido, ctx)


def _marcas_de_corte(c: canvas.Canvas, ancho: float, alto: float) -> None:
    c.setDash(2, 3)
    c.setStrokeGray(0.6)
    c.setLineWidth(0.3)
    c.line(ancho / 2, 0, ancho / 2, alto)
    c.line(0, alto / 2, ancho, alto / 2)
    c.setDash()
    c.setStrokeGray(0)


def _render_a4(ctx: Contexto, c: canvas.Canvas) -> None:
    ancho_hoja, alto_hoja = A4
    ancho, alto = 95 * mm, 142.5 * mm
    margen_x = (ancho_hoja / 2 - ancho) / 2
    margen_y = (alto_hoja / 2 - alto) / 2
    posiciones = [
        (margen_x, alto_hoja - margen_y),
        (ancho_hoja / 2 + margen_x, alto_hoja - margen_y),
        (margen_x, alto_hoja / 2 - margen_y),
        (ancho_hoja / 2 + margen_x, alto_hoja / 2 - margen_y),
    ]
    for i, pedido in enumerate(ctx.pedidos):
        if i % 4 == 0:
            _marcas_de_corte(c, ancho_hoja, alto_hoja)
        x0, y_sup = posiciones[i % 4]
        _remito(c, x0, y_sup, ancho, pedido, ctx)
        if i % 4 == 3:
            c.showPage()
    if not ctx.pedidos or len(ctx.pedidos) % 4 != 0:
        c.showPage()


def _render_10x15(ctx: Contexto, c: canvas.Canvas) -> None:
    c.setPageSize((ANCHO_REF * mm, ALTO_REF * mm))
    for pedido in ctx.pedidos:
        c.setPageSize((ANCHO_REF * mm, ALTO_REF * mm))
        _remito(c, 0, ALTO_REF * mm, ANCHO_REF * mm, pedido, ctx)
        c.showPage()
    if not ctx.pedidos:
        c.showPage()


FORMATOS: dict[Formato, Callable[[Contexto, canvas.Canvas], None]] = {
    "a4": _render_a4,
    "10x15": _render_10x15,
}


def render(ctx: Contexto) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle("Remitos")
    FORMATOS.get(ctx.formato, _render_a4)(ctx, c)
    c.save()
    return buffer.getvalue()
