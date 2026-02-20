# exportador.py
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
import os
import csv
import json

# =========================
# Clasificación automática por niveles de calidad (para PDF)
# =========================
QUALITY_LEVELS = [
    ("A", 0.90),  # >= 90% aptos
    ("B", 0.75),  # >= 75% aptos
    ("C", 0.50),  # >= 50% aptos
    ("D", 0.00),  # < 50% aptos
]
MIN_DETECTIONS_FOR_CONFIDENCE = 5  # si total < esto, baja 1 nivel


def _bajar_un_nivel(nivel: str) -> str:
    orden = ["A", "B", "C", "D"]
    if nivel not in orden:
        return "D"
    i = orden.index(nivel)
    return orden[min(i + 1, len(orden) - 1)]


def _clasificar_calidad_desde_kpis(aptos: int, no_aptos: int) -> Tuple[str, int, float, int]:
    """
    Retorna:
      (nivel, score_0_100, pct_aptos_0_1, total)
    """
    a = int(aptos or 0)
    n = int(no_aptos or 0)
    total = a + n
    if total <= 0:
        return ("D", 0, 0.0, 0)

    pct = a / total  # 0..1
    nivel = "D"
    for lvl, thr in QUALITY_LEVELS:
        if pct >= thr:
            nivel = lvl
            break

    if total < MIN_DETECTIONS_FOR_CONFIDENCE:
        nivel = _bajar_un_nivel(nivel)

    score = int(round(pct * 100))
    return (nivel, score, float(pct), total)


# =========================
# NUEVO: Analítica (parseo del resumen + exports CSV/JSON + PDF analítico)
# =========================
def _parse_resumen_a_conteos(resumen: str) -> Dict[str, int]:
    """
    Convierte el string 'Etiqueta: n; Etiqueta2: m' a dict.
    Soporta tu formato actual (separado por ';').
    """
    conteos: Dict[str, int] = {}
    if not resumen:
        return conteos

    parts = [p.strip() for p in str(resumen).split(";") if p.strip()]
    for p in parts:
        # ejemplo: "Espárrago enfermo: 1"
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        k = k.strip()
        v = v.strip()
        try:
            conteos[k] = int(v)
        except:
            # si no es int, lo ignoramos
            continue
    return conteos


def construir_reporte_analitico(
    *,
    nombre_usuario: str,
    hectarea: Optional[str],
    resumen: str,
    aptos: Optional[int],
    no_aptos: Optional[int],
    fecha_hora: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Arma un JSON analítico estándar a partir de lo que YA tienes hoy.
    No requiere detections ni tocar UI.
    """
    a = int(aptos or 0)
    n = int(no_aptos or 0)
    nivel, score, pct01, total = _clasificar_calidad_desde_kpis(a, n)
    pct = round(pct01 * 100, 2) if total else 0.0

    conteos = _parse_resumen_a_conteos(resumen)

    # Métricas derivadas desde conteos
    total_por_conteos = sum(conteos.values()) if conteos else total
    distribucion = []
    if conteos and total_por_conteos > 0:
        for etiqueta, cnt in sorted(conteos.items(), key=lambda x: (-x[1], x[0])):
            distribucion.append({
                "etiqueta": etiqueta,
                "conteo": cnt,
                "porcentaje": round((cnt / total_por_conteos) * 100, 2)
            })

    return {
        "metadata": {
            "sistema": "AgroScan",
            "usuario": str(nombre_usuario),
            "hectarea": str(hectarea) if hectarea else None,
            "fecha_hora": fecha_hora or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "kpis": {
            "aptos": a,
            "no_aptos": n,
            "total": total,
            "pct_aprobacion": pct,
            "nivel_calidad": nivel,
            "score": score,
        },
        "analitica": {
            "conteos_por_etiqueta": conteos,
            "distribucion_por_etiqueta": distribucion,
        },
        "resumen_texto": resumen or "",
    }


def exportar_reporte_analitico_csv(reporte: Dict[str, Any], destino: Optional[str] = None) -> str:
    """
    Exporta una fila (o puedes ir acumulando múltiples).
    CSV "plano" ideal para Excel/PowerBI.
    """
    os.makedirs("reports", exist_ok=True)
    if not destino:
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = f"reports/reporte_analitico_{fecha_str}.csv"

    md = reporte.get("metadata", {})
    k = reporte.get("kpis", {})
    conteos = reporte.get("analitica", {}).get("conteos_por_etiqueta", {}) or {}

    # columnas base
    row = {
        "fecha_hora": md.get("fecha_hora"),
        "usuario": md.get("usuario"),
        "hectarea": md.get("hectarea"),
        "aptos": k.get("aptos"),
        "no_aptos": k.get("no_aptos"),
        "total": k.get("total"),
        "pct_aprobacion": k.get("pct_aprobacion"),
        "nivel_calidad": k.get("nivel_calidad"),
        "score": k.get("score"),
    }

    # aplanar conteos por etiqueta como columnas adicionales
    # ejemplo: conteo_Espárrago sano, conteo_Espárrago enfermo, etc.
    for etiqueta, cnt in conteos.items():
        col = f"conteo_{etiqueta}"
        row[col] = cnt

    # escribir CSV
    headers = list(row.keys())
    with open(destino, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow(row)

    return destino


def exportar_reporte_analitico_json(reporte: Dict[str, Any], destino: Optional[str] = None) -> str:
    os.makedirs("reports", exist_ok=True)
    if not destino:
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = f"reports/reporte_analitico_{fecha_str}.json"

    with open(destino, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    return destino


def generar_pdf_reporte_analitico(
    reporte: Dict[str, Any],
    *,
    path_imagen: Optional[str] = None,
    path_imagen_anotada: Optional[str] = None,
    nombre: str = "AgroScan",
    destino: Optional[str] = None,
) -> str:
    """
    PDF analítico extendido (nuevo). No reemplaza tu PDF clásico.
    """
    os.makedirs("reports", exist_ok=True)
    if not destino:
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = f"reports/reporte_analitico_{fecha_str}.pdf"

    md = reporte.get("metadata", {})
    k = reporte.get("kpis", {})
    distrib = reporte.get("analitica", {}).get("distribucion_por_etiqueta", []) or []

    c = canvas.Canvas(destino, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - margin

    # Título
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.darkgreen)
    c.drawCentredString(width / 2, y, f"Reporte Analítico - {nombre}")
    y -= 28

    c.setStrokeColor(colors.grey)
    c.setLineWidth(0.8)
    c.line(margin, y, width - margin, y)
    y -= 22

    # Metadata
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(margin, y, "Fecha y hora:")
    c.setFont("Helvetica", 12)
    c.drawString(margin + 110, y, str(md.get("fecha_hora", "")))
    y -= 18

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Usuario:")
    c.setFont("Helvetica", 12)
    c.drawString(margin + 110, y, str(md.get("usuario", "")))
    y -= 18

    if md.get("hectarea"):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Hectárea:")
        c.setFont("Helvetica", 12)
        c.drawString(margin + 110, y, str(md.get("hectarea")))
        y -= 18

    # KPIs
    y -= 6
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "KPIs y calidad:")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(margin + 16, y, f"Aptos: {k.get('aptos', 0)}"); y -= 16
    c.drawString(margin + 16, y, f"No aptos: {k.get('no_aptos', 0)}"); y -= 16
    c.drawString(margin + 16, y, f"Total: {k.get('total', 0)}"); y -= 16
    c.drawString(margin + 16, y, f"% Aprobación: {k.get('pct_aprobacion', 0)}%"); y -= 16
    c.drawString(margin + 16, y, f"Nivel de calidad: {k.get('nivel_calidad', 'D')} (Score: {k.get('score', 0)}/100)"); y -= 10

    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.6)
    c.line(margin, y, width - margin, y)
    y -= 14

    # Tabla analítica por etiqueta (distribución)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(margin, y, "Distribución por etiqueta:")
    y -= 16

    if not distrib:
        c.setFont("Helvetica", 11)
        c.drawString(margin + 16, y, "— No hay datos de etiquetas para analizar."); y -= 16
    else:
        # cabecera tabla
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin + 16, y, "Etiqueta")
        c.drawString(width - margin - 160, y, "Conteo")
        c.drawString(width - margin - 90, y, "%")
        y -= 12
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.6)
        c.line(margin + 16, y, width - margin, y)
        y -= 14

        c.setFont("Helvetica", 11)
        for item in distrib[:20]:  # límite para no desbordar
            etiqueta = str(item.get("etiqueta", ""))
            cnt = str(item.get("conteo", 0))
            pct = f"{item.get('porcentaje', 0)}%"
            c.drawString(margin + 16, y, etiqueta[:55])
            c.drawRightString(width - margin - 135, y, cnt)
            c.drawRightString(width - margin - 60, y, pct)
            y -= 14
            if y < 180:
                c.showPage()
                y = height - margin
                c.setFont("Helvetica", 11)

    # Imágenes (opcional)
    _dibujar_imagenes(
        c, width, height, margin, y,
        path_original=path_imagen,
        path_anotada=path_imagen_anotada,
        titulo_original="Imagen original",
        titulo_anotada="Imagen anotada (detecciones)"
    )

    c.save()
    return destino


# =========================
# PDF clásico (tu versión) - SIN romper nada
# =========================
def generar_pdf_reporte(
    nombre_usuario,
    resumen,
    path_imagen: Optional[str] = None,
    nombre: str = "AgroScan",
    *,
    aptos: Optional[int] = None,
    no_aptos: Optional[int] = None,
    hectarea: Optional[str] = None,
    path_imagen_anotada: Optional[str] = None,
):
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

    if hectarea:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Hectárea:")
        c.setFont("Helvetica", 12)
        c.drawString(margin + 110, y, str(hectarea))
        y -= 18
    else:
        y -= 2

    # KPIs
    if (aptos is not None) or (no_aptos is not None):
        a = aptos if aptos is not None else 0
        n = no_aptos if no_aptos is not None else 0

        nivel, score, pct01, total = _clasificar_calidad_desde_kpis(a, n)
        pct = round(pct01 * 100, 2) if total else 0.0

        y -= 6
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Resumen cuantitativo:")
        y -= 18
        c.setFont("Helvetica", 11)
        c.drawString(margin + 16, y, f"Aptos: {a}"); y -= 16
        c.drawString(margin + 16, y, f"No aptos: {n}"); y -= 16
        c.drawString(margin + 16, y, f"Total: {total}"); y -= 16
        c.drawString(margin + 16, y, f"% Aprobación: {pct}%"); y -= 16
        c.drawString(margin + 16, y, f"Nivel de calidad: {nivel} (Score: {score}/100)"); y -= 10

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
        if y < 180:
            c.showPage()
            y = height - margin
            c.setFont("Helvetica", 11)

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
    path_imagen_anotada: Optional[str] = None,
):
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

    # KPIs
    if (aptos is not None) or (no_aptos is not None):
        a = aptos if aptos is not None else 0
        n = no_aptos if no_aptos is not None else 0

        nivel, score, pct01, total = _clasificar_calidad_desde_kpis(a, n)
        pct = round(pct01 * 100, 2) if total else 0.0

        y -= 6
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "Resumen cuantitativo:")
        y -= 18
        c.setFont("Helvetica", 11)
        c.drawString(margin + 16, y, f"Aptos: {a}"); y -= 16
        c.drawString(margin + 16, y, f"No aptos: {n}"); y -= 16
        c.drawString(margin + 16, y, f"Total: {total}"); y -= 16
        c.drawString(margin + 16, y, f"% Aprobación: {pct}%"); y -= 16
        c.drawString(margin + 16, y, f"Nivel de calidad: {nivel} (Score: {score}/100)"); y -= 10

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

    _dibujar_imagenes(
        c, width, height, margin, y,
        path_original=path_imagen,
        path_anotada=path_imagen_anotada,
        titulo_original="Imagen original",
        titulo_anotada="Imagen anotada (detecciones)"
    )

    c.save()
    return nombre_archivo


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
    os.makedirs("reports", exist_ok=True)
    if not destino:
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = f"reports/actividad_{tipo}_{fecha_str}.pdf"

    c = canvas.Canvas(destino, pagesize=letter)
    w, h = letter
    m = 50
    y = h - m

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.darkgreen)
    c.drawCentredString(w/2, y, "Comprobante de Actividad de Campo - AgroScan")
    y -= 26
    c.setStrokeColor(colors.grey); c.setLineWidth(0.8)
    c.line(m, y, w-m, y); y -= 18

    def row(lbl, val):
        nonlocal y
        c.setFont("Helvetica-Bold", 11); c.setFillColor(colors.black)
        c.drawString(m, y, f"{lbl}:")
        c.setFont("Helvetica", 11)
        c.drawString(m+120, y, str(val) if val not in (None, "") else "-")
        y -= 16

    row("Fecha/Hora", fecha_hora)
    row("Agricultor", nombre_agricultor)
    row("Hectárea", codigo_hectarea)
    row("Tipo", tipo.capitalize())
    row("Cantidad", f"{cantidad} {unidad}".strip() if cantidad is not None else None)
    if costo is not None:
        row("Costo", f"S/ {float(costo):.2f}")
    if notas:
        y = _draw_multiline_text(c, f"Notas: {notas}", m, y, w-m)

    y -= 4
    row("Estado", estado)
    if comentario_supervisor:
        y = _draw_multiline_text(c, f"Comentario supervisor: {comentario_supervisor}", m, y, w-m)

    if tipo.lower() == "cosecha":
        y -= 6
        c.setFont("Helvetica-Bold", 12); c.drawString(m, y, "Detalle de cosecha:"); y -= 16
        a = aptos if aptos is not None else 0
        n = no_aptos if no_aptos is not None else 0

        nivel, score, pct01, total = _clasificar_calidad_desde_kpis(a, n)
        pct = round(pct01 * 100, 2) if total else 0.0

        row("Aptos", a)
        row("No aptos", n)
        if cajas is not None: row("Cajas", cajas)
        if kilos is not None: row("Kilos", kilos)
        row("% Aprobación", f"{pct}%")
        row("Nivel de calidad", f"{nivel} (Score: {score}/100)")

    c.save()
    return destino


# --------------------------
# Helpers de maquetación
# --------------------------
def _draw_multiline_text(c, text, x, y, max_x):
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
    paths = []
    if path_original and os.path.exists(path_original):
        paths.append(("original", path_original, titulo_original))
    if path_anotada and os.path.exists(path_anotada):
        paths.append(("anotada", path_anotada, titulo_anotada))

    if not paths:
        return

    max_w_page = width - 2 * margin
    max_h_block = 300

    if y < (max_h_block + 80):
        c.showPage()
        y = height - margin

    if len(paths) == 1:
        _, pth, title = paths[0]
        try:
            img = ImageReader(pth)
            img_w, img_h = img.getSize()
            disp_w, disp_h = _scale_to_fit(img_w, img_h, max_w_page, max_h_block)

            c.setFont("Helvetica-Bold", 12)
            c.drawString(margin, y - 10, f"{title}:")
            y_img = y - 26 - disp_h
            x_img = (width - disp_w) / 2
            c.drawImage(img, x_img, y_img, width=disp_w, height=disp_h)
        except Exception as e:
            print(f"Error al agregar imagen al PDF: {e}")
        return

    (k1, p1, t1), (k2, p2, t2) = paths[:2]
    gutter = 16
    col_w = (max_w_page - gutter) / 2.0

    try:
        i1 = ImageReader(p1); w1, h1 = i1.getSize()
        i2 = ImageReader(p2); w2, h2 = i2.getSize()
        d1_w, d1_h = _scale_to_fit(w1, h1, col_w, max_h_block)
        d2_w, d2_h = _scale_to_fit(w2, h2, col_w, max_h_block)
        row_h = max(d1_h, d2_h)

        if (y - 26 - row_h) < 60:
            c.showPage()
            y = height - margin

        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y - 10, f"{t1}:")
        c.drawString(margin + col_w + gutter, y - 10, f"{t2}:")

        y_img = y - 26 - row_h
        c.drawImage(i1, margin, y_img + (row_h - d1_h), width=d1_w, height=d1_h)
        c.drawImage(i2, margin + col_w + gutter, y_img + (row_h - d2_h), width=d2_w, height=d2_h)
    except Exception as e:
        print(f"Error al agregar imágenes al PDF: {e}")
