# yolo_service.py
import os
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from ultralytics import YOLO
from UTILS.clases import CLASES_MAP  # usamos normalización externa

# =========================
# Configuración del modelo único
# =========================
RUTA_MODELO = r"D:\Data\CARRERA\EVO\AGROSCAN\SOFTWARE\models\Proyecto Esparrago.pt"

if not os.path.exists(RUTA_MODELO):
    raise FileNotFoundError(f"No se encontró el modelo en: {RUTA_MODELO}")

MODEL = YOLO(RUTA_MODELO)

# =========================
# Clasificación automática por niveles de calidad
# (NO rompe nada existente: solo agrega funciones nuevas)
# =========================
#
# Criterio propuesto (simple y robusto):
# - Se calcula % sano (sanos/total) y total detectados
# - Se asigna un nivel (A, B, C, D) en base al % sano
# - Si total es muy bajo (poca evidencia), se baja 1 nivel para evitar falsos "A"
#
# Puedes ajustar umbrales sin tocar UI/BD.
QUALITY_LEVELS = [
    ("A", 0.90),  # >= 90% sano
    ("B", 0.75),  # >= 75% sano
    ("C", 0.50),  # >= 50% sano
    ("D", 0.00),  # < 50% sano
]

MIN_DETECTIONS_FOR_CONFIDENCE = 5  # si hay menos de esto, reducimos 1 nivel (opcional)


def clasificar_calidad_por_niveles(detections: List[Dict]) -> Dict[str, Union[str, float, int]]:
    """
    Clasifica automáticamente por niveles de calidad (A/B/C/D) usando las detecciones.

    Retorna un dict listo para usar en UI/BD si deseas:
      {
        "nivel": "A"|"B"|"C"|"D",
        "pct_sano": 0.0..1.0,
        "sanos": int,
        "enfermos": int,
        "total": int,
        "score": 0..100
      }

    Nota: No modifica el flujo actual. Es una mejora añadida.
    """
    tot = conteo_sanos_enfermos(detections)
    sanos = int(tot.get("sanos", 0))
    enfermos = int(tot.get("enfermos", 0))
    total = int(tot.get("total", sanos + enfermos))

    if total <= 0:
        return {
            "nivel": "D",
            "pct_sano": 0.0,
            "sanos": 0,
            "enfermos": 0,
            "total": 0,
            "score": 0,
        }

    pct_sano = sanos / total

    # Determinar nivel por umbral de porcentaje sano
    nivel = "D"
    for lvl, thr in QUALITY_LEVELS:
        if pct_sano >= thr:
            nivel = lvl
            break

    # Regla anti-sesgo por baja evidencia: si hay muy pocas detecciones, baja 1 nivel (opcional)
    if total < MIN_DETECTIONS_FOR_CONFIDENCE:
        nivel = _bajar_un_nivel(nivel)

    # Score (0..100) directamente del % sano
    score = int(round(pct_sano * 100))

    return {
        "nivel": nivel,
        "pct_sano": float(pct_sano),
        "sanos": sanos,
        "enfermos": enfermos,
        "total": total,
        "score": score,
    }


def _bajar_un_nivel(nivel: str) -> str:
    orden = ["A", "B", "C", "D"]
    if nivel not in orden:
        return "D"
    i = orden.index(nivel)
    return orden[min(i + 1, len(orden) - 1)]


# =========================
# Utilidades de colores
# =========================
def _color_from_label(label: str) -> Tuple[int, int, int]:
    # BGR
    if "enfermo" in label.lower():
        return (36, 36, 220)   # rojo-ish
    if "sano" in label.lower():
        return (46, 204, 113)  # verde-ish
    h = hash(label)
    return ((h >> 0) & 0xFF, (h >> 8) & 0xFF, (h >> 16) & 0xFF)


# =========================
# NMS simple por IoU
# =========================
def _iou(box1: List[int], box2: List[int]) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter_w, inter_h = max(0, x2 - x1), max(0, y2 - y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0
    area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
    area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
    denom = float(area1 + area2 - inter_area)
    return inter_area / denom if denom > 0 else 0.0


def _nms_per_group(dets: List[Dict], iou_threshold: float) -> List[Dict]:
    keep: List[Dict] = []
    for d in sorted(dets, key=lambda x: -x["confidence"]):
        overlapped = any(_iou(d["box"], k["box"]) > iou_threshold for k in keep)
        if not overlapped:
            keep.append(d)
    return keep


# =========================
# Core de análisis
# =========================
def _run_model(img_or_path: Union[str, np.ndarray],
               conf_threshold: float = 0.25) -> List[Dict]:
    detections: List[Dict] = []
    res = MODEL(img_or_path, conf=conf_threshold)[0]

    for x1, y1, x2, y2, conf, cls in res.boxes.data.tolist():
        cls = int(cls)
        raw_name = res.names[cls] if hasattr(res, "names") else str(cls)
        name_norm = str(raw_name).strip().lower()
        label_es = CLASES_MAP.get(name_norm, raw_name)  # normalización desde clases.py

        detections.append({
            "name": raw_name,             # nombre crudo del modelo
            "label": label_es,            # normalizado (Espárrago sano/enfermo)
            "box": [int(x1), int(y1), int(x2), int(y2)],
            "confidence": float(conf),
            # (no afecta nada si no lo usas) puedes guardar si fue sano/enfermo:
            "es_sano": str(label_es).strip().lower() == "espárrago sano".lower(),
            "es_enfermo": str(label_es).strip().lower() == "espárrago enfermo".lower(),
        })
    return detections


def _group_and_nms(detections: List[Dict],
                   iou_threshold: float = 0.30) -> List[Dict]:
    groups: Dict[str, List[Dict]] = {}
    for d in detections:
        groups.setdefault(d["label"], []).append(d)
    final_dets: List[Dict] = []
    for _, dets in groups.items():
        final_dets.extend(_nms_per_group(dets, iou_threshold))
    return final_dets


def _draw_dets(image: np.ndarray, dets: List[Dict]) -> np.ndarray:
    out = image.copy()
    for d in dets:
        x1, y1, x2, y2 = d["box"]
        color = _color_from_label(d["label"])
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        txt = f"{d['label']} {d['confidence']*100:.1f}%"
        cv2.putText(out, txt, (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
    return out


def analizar_imagen_yolo(
    img_or_path: Union[str, np.ndarray],
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.30,
    draw: bool = True
) -> Tuple[List[Dict], Optional[np.ndarray]]:
    """
    Devuelve:
      - detections_final: [{"name","label","box","confidence"}, ...] (con NMS)
      - annotated_image: imagen con cajas o None si draw=False
    """
    img = cv2.imread(img_or_path) if isinstance(img_or_path, str) else img_or_path
    if img is None:
        return [], None

    raw = _run_model(img_or_path, conf_threshold=conf_threshold)
    final_dets = _group_and_nms(raw, iou_threshold=iou_threshold)
    annotated = _draw_dets(img, final_dets) if draw else None
    return final_dets, annotated


# =========================
# Resúmenes y conteos
# =========================
def conteos_por_label(detections: List[Dict]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for d in detections:
        summary[d["label"]] = summary.get(d["label"], 0) + 1
    return summary


def conteo_sanos_enfermos(detections: List[Dict]) -> Dict[str, int]:
    c = conteos_por_label(detections)
    sanos = c.get("Espárrago sano", 0)
    enfermos = c.get("Espárrago enfermo", 0)
    return {"sanos": sanos, "enfermos": enfermos, "total": sanos + enfermos}
