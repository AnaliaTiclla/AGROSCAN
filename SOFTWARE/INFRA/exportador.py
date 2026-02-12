# exportador.py
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from datetime import datetime
from typing import Optional
import os

def generar_pdf_reporte(
    nombre_usuario,
    resumen,
    path_imagen: Optional[str] = None,
    nombre: str = "AgroScan",
    *,
    aptos: Optional[int] = None,
    no_aptos: Optional[int] = None,
    hectarea: Optional[str] = None,
    # NUEVO: imagen anotada opcional
    path_imagen_anotada: Optional[str] = None,
):
    """
    PDF generado por el agricultor.
    Retro-compatible; si pasas path_imagen_anotada se mostrarán 2 imágenes.
    """
    os.makedirs("reports", exist_ok=True)
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"reports/reporte_usuario_{str(nombre_usuario).replace(' ', '_')}_{fecha_str}.pdf"

    c = canvas.Canvas(nombre_archivo, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - margin

    # Título
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.darkgreen)
    c.drawCentredString(width / 2, y, f"Reporte de Detección - {nombre}")
    y -= 28

    # Línea
    c.setStrokeColor(colors.grey)
    c.setLineWidth(0.8)
    c.line(margin, y, width - margin, y)
    y -= 24

    # Datos
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(margin, y, "Fecha y hora:")
    c.setFont("Helvetica", 12)
    c.drawString(margin + 110, y, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    y -= 18

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Usuario:")
    c.setFont("Helvetica", 12)
    c.drawString(margin + 110, y, str(nombre_usuario))
    y -= 18

    # Hectárea (opcional)
    if hectarea:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Hectárea:")
        c.setFont("Helvetica", 12)
        c.drawString(margin + 110, y, str(hectarea))
        y -= 18
    else:
        y -= 2

    # KPIs aptos / no aptos (opcionales)
    if (aptos is not None) or (no_aptos is not None):
        a = aptos if aptos is not None else 0
        n = no_aptos if no_aptos is not None else 0
        total = a + n
        pct = round((a / total) * 100, 2) if total else 0.0

        y -= 6
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Resumen cuantitativo:")
        y -= 18
        c.setFont("Helvetica", 11)
        c.drawString(margin + 16, y, f"Aptos: {a}"); y -= 16
        c.drawString(margin + 16, y, f"No aptos: {n}"); y -= 16
        c.drawString(margin + 16, y, f"% Aprobación: {pct}%"); y -= 10

        # línea separadora
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.6)
        c.line(margin, y, width - margin, y)
        y -= 14

    # Resumen (lista)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(margin, y, "Resumen de resultados:")
    y -= 18
    c.setFont("Helvetica", 11)
    for linea in (resumen or "").split(";"):
        linea = linea.strip()
        if not linea:
            continue
        c.drawString(margin + 16, y, f"• {linea}")
        y -= 16
        if y < 180:  # dejamos más espacio por si van dos imágenes
            c.showPage()
            y = height - margin
            c.setFont("Helvetica", 11)

    # Imágenes (opcional: 1 o 2)
    _dibujar_imagenes(
        c, width, height, margin, y,
        path_original=path_imagen,
        path_anotada=path_imagen_anotada,
        titulo_original="Imagen original",
        titulo_anotada="Imagen anotada (detecciones)"
    )

    c.save()
    return nombre_archivo


def generar_pdf_reporte_detallado(
    nombre_usuario,
    fecha,
    planta,
    enfermedad,
    num_frutos,
    maduracion,
    estado,
    comentario_supervisor,
    path_imagen: Optional[str] = None,
    nombre: str = "AgroScan",
    destino: Optional[str] = None,
    *,
    aptos: Optional[int] = None,
    no_aptos: Optional[int] = None,
    hectarea: Optional[str] = None,
    # NUEVO: imagen anotada opcional
    path_imagen_anotada: Optional[str] = None,
):
    """
    PDF “completo” con datos de supervisor.
    Retro-compatible; si pasas path_imagen_anotada se mostrarán 2 imágenes.
    """
    os.makedirs("reports", exist_ok=True)
    if destino:
        nombre_archivo = destino
    else:
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"reports/reporte_usuario_{str(nombre_usuario).replace(' ', '_')}_{fecha_str}.pdf"

    c = canvas.Canvas(nombre_archivo, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - margin

    # Título
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.darkgreen)
    c.drawCentredString(width / 2, y, f"Reporte de Detección - {nombre}")
    y -= 28

    # Línea
    c.setStrokeColor(colors.grey)
    c.setLineWidth(0.8)
    c.line(margin, y, width - margin, y)
    y -= 24

    # Datos del reporte
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(margin, y, "Fecha y hora:")
    c.setFont("Helvetica", 12)
    c.drawString(margin + 120, y, str(fecha))
    y -= 18

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Usuario:")
    c.setFont("Helvetica", 12)
    c.drawString(margin + 120, y, str(nombre_usuario))
    y -= 18

    if hectarea:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Hectárea:")
        c.setFont("Helvetica", 12)
        c.drawString(margin + 120, y, str(hectarea))
        y -= 18

    # KPIs (opcionales)
    if (aptos is not None) or (no_aptos is not None):
        a = aptos if aptos is not None else 0
        n = no_aptos if no_aptos is not None else 0
        total = a + n
        pct = round((a / total) * 100, 2) if total else 0.0

        y -= 6
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Resumen cuantitativo:")
        y -= 18
        c.setFont("Helvetica", 11)
        c.drawString(margin + 16, y, f"Aptos: {a}"); y -= 16
        c.drawString(margin + 16, y, f"No aptos: {n}"); y -= 16
        c.drawString(margin + 16, y, f"% Aprobación: {pct}%"); y -= 10

        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.6)
        c.line(margin, y, width - margin, y)
        y -= 14

    # Detalle de análisis
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Detalle de análisis:")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(margin + 16, y, f"Planta: {planta or '-'}"); y -= 16
    c.drawString(margin + 16, y, f"Enfermedad: {enfermedad or '-'}"); y -= 16
    c.drawString(margin + 16, y, f"Frutos detectados: {num_frutos if num_frutos is not None else '-'}"); y -= 16
    c.drawString(margin + 16, y, f"Maduración: {maduracion or '-'}"); y -= 20

    # Revisión del supervisor
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Revisión del supervisor:")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(margin + 16, y, f"Estado: {estado or 'pendiente'}"); y -= 16

    if comentario_supervisor:
        y = _draw_multiline_text(c, f"Comentario: {comentario_supervisor}", margin + 16, y, width - margin - 16)
    else:
        c.drawString(margin + 16, y, "Comentario: —"); y -= 16

    # Imágenes (opcional: 1 o 2)
    _dibujar_imagenes(
        c, width, height, margin, y,
        path_original=path_imagen,
        path_anotada=path_imagen_anotada,
        titulo_original="Imagen original",
        titulo_anotada="Imagen anotada (detecciones)"
    )

    c.save()
    return nombre_archivo


# ============================
# NUEVO: comprobante de actividad
# ============================
def generar_pdf_actividad(
    nombre_agricultor: str,
    codigo_hectarea: str,
    tipo: str,
    fecha_hora,
    cantidad=None,
    unidad: Optional[str] = None,
    costo: Optional[float] = None,
    notas: Optional[str] = None,
    estado: str = "aprobado",
    comentario_supervisor: Optional[str] = None,
    aptos: Optional[int] = None,
    no_aptos: Optional[int] = None,
    cajas=None,
    kilos=None,
    destino: Optional[str] = None,
) -> str:
    """
    Genera un comprobante PDF de una ACTIVIDAD DE CAMPO.
    Si tipo == 'cosecha', incluye aptos/no aptos y (opcional) cajas/kilos.
    """
    os.makedirs("reports", exist_ok=True)
    if not destino:
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = f"reports/actividad_{tipo}_{fecha_str}.pdf"

    c = canvas.Canvas(destino, pagesize=letter)
    w, h = letter
    m = 50
    y = h - m

    # Título
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.darkgreen)
    c.drawCentredString(w/2, y, "Comprobante de Actividad de Campo - AgroScan")
    y -= 26
    c.setStrokeColor(colors.grey); c.setLineWidth(0.8)
    c.line(m, y, w-m, y); y -= 18

    # Helper de fila
    def row(lbl, val):
        nonlocal y
        c.setFont("Helvetica-Bold", 11); c.setFillColor(colors.black)
        c.drawString(m, y, f"{lbl}:")
        c.setFont("Helvetica", 11)
        c.drawString(m+120, y, str(val) if val not in (None, "") else "-")
        y -= 16

    # Datos principales
    row("Fecha/Hora", fecha_hora)
    row("Agricultor", nombre_agricultor)
    row("Hectárea", codigo_hectarea)
    row("Tipo", tipo.capitalize())
    row("Cantidad", f"{cantidad} {unidad}".strip() if cantidad is not None else None)
    if costo is not None:
        row("Costo", f"S/ {float(costo):.2f}")
    if notas:
        y = _draw_multiline_text(c, f"Notas: {notas}", m, y, w-m)

    # Estado / comentario
    y -= 4
    row("Estado", estado)
    if comentario_supervisor:
        y = _draw_multiline_text(c, f"Comentario supervisor: {comentario_supervisor}", m, y, w-m)

    # Detalle de cosecha (si aplica)
    if tipo.lower() == "cosecha":
        y -= 6
        c.setFont("Helvetica-Bold", 12); c.drawString(m, y, "Detalle de cosecha:"); y -= 16
        c.setFont("Helvetica", 11)
        a = aptos if aptos is not None else 0
        n = no_aptos if no_aptos is not None else 0
        total = a + n
        pct = round((a / total) * 100, 2) if total else 0.0
        row("Aptos", a)
        row("No aptos", n)
        if cajas is not None: row("Cajas", cajas)
        if kilos is not None: row("Kilos", kilos)
        row("% Aprobación", f"{pct}%")

    c.save()
    return destino


# --------------------------
# Helpers de maquetación
# --------------------------
def _draw_multiline_text(c, text, x, y, max_x):
    """Salto de línea simple por palabras para comentarios largos."""
    c.setFont("Helvetica", 11)
    max_width = max_x - x
    words = str(text).split()
    line = ""
    line_height = 14
    for w in words:
        tmp = (line + " " + w).strip()
        if c.stringWidth(tmp, "Helvetica", 11) <= max_width:
            line = tmp
        else:
            c.drawString(x, y, line)
            y -= line_height
            line = w
            if y < 100:
                c.showPage()
                y = letter[1] - 60
                c.setFont("Helvetica", 11)
    if line:
        c.drawString(x, y, line)
        y -= line_height
    return y

def _scale_to_fit(img_w, img_h, max_w, max_h):
    """Escala manteniendo aspecto para caber en max_w x max_h."""
    aspect = img_h / img_w if img_w else 1.0
    disp_w = max_w
    disp_h = disp_w * aspect
    if disp_h > max_h:
        disp_h = max_h
        disp_w = disp_h / aspect if aspect else max_w
    return disp_w, disp_h

def _dibujar_imagenes(
    c, width, height, margin, y,
    *,
    path_original: Optional[str],
    path_anotada: Optional[str],
    titulo_original: str = "Imagen original",
    titulo_anotada: str = "Imagen anotada"
):
    """
    Dibuja 0, 1 o 2 imágenes. Con dos: intenta colocarlas lado a lado,
    si no entra, pasa a nueva página.
    """
    paths = []
    if path_original and os.path.exists(path_original):
        paths.append(("original", path_original, titulo_original))
    if path_anotada and os.path.exists(path_anotada):
        paths.append(("anotada", path_anotada, titulo_anotada))

    if not paths:
        return

    # Calculamos área disponible
    max_w_page = width - 2 * margin
    max_h_block = 300  # alto máx del bloque de imágenes en una página

    # Si hay poco espacio vertical, saltamos de página
    if y < (max_h_block + 80):
        c.showPage()
        y = height - margin

    if len(paths) == 1:
        # Una imagen centrada
        kind, pth, title = paths[0]
        try:
            img = ImageReader(pth)
            img_w, img_h = img.getSize()
            disp_w, disp_h = _scale_to_fit(img_w, img_h, max_w_page, max_h_block)

            # Título
            c.setFont("Helvetica-Bold", 12)
            c.drawString(margin, y - 10, f"{title}:")
            y_img = y - 26 - disp_h
            x_img = (width - disp_w) / 2
            c.drawImage(img, x_img, y_img, width=disp_w, height=disp_h)
        except Exception as e:
            print(f"Error al agregar imagen al PDF: {e}")
        return

    # Dos imágenes: dividir el ancho disponible
    (k1, p1, t1), (k2, p2, t2) = paths[:2]
    gutter = 16  # separación entre imágenes
    col_w = (max_w_page - gutter) / 2.0

    try:
        i1 = ImageReader(p1); w1, h1 = i1.getSize()
        i2 = ImageReader(p2); w2, h2 = i2.getSize()
        d1_w, d1_h = _scale_to_fit(w1, h1, col_w, max_h_block)
        d2_w, d2_h = _scale_to_fit(w2, h2, col_w, max_h_block)
        row_h = max(d1_h, d2_h)

        # Si no cabe, nueva página
        if (y - 26 - row_h) < 60:
            c.showPage()
            y = height - margin

        # Títulos
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y - 10, f"{t1}:")
        c.drawString(margin + col_w + gutter, y - 10, f"{t2}:")

        # Imágenes
        y_img = y - 26 - row_h
        c.drawImage(i1, margin, y_img + (row_h - d1_h), width=d1_w, height=d1_h)
        c.drawImage(i2, margin + col_w + gutter, y_img + (row_h - d2_h), width=d2_w, height=d2_h)
    except Exception as e:
        print(f"Error al agregar imágenes al PDF: {e}")
