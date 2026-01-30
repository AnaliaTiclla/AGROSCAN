# yolo_service.py
import os
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Iterable, Union
from ultralytics import YOLO
from clases import CLASES_MAP  # usamos normalización externa

# =========================
# Configuración del modelo único
# =========================
RUTA_MODELO = r"D:\Data\CARRERA\EVO\AGROSCAN\SOFTWARE\models\Proyecto Esparrago.pt"

if not os.path.exists(RUTA_MODELO):
    raise FileNotFoundError(f"No se encontró el modelo en: {RUTA_MODELO}")

MODEL = YOLO(RUTA_MODELO)

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
    area1 = max(0, box1[2]-box1[0]) * max(0, box1[3]-box1[1])
    area2 = max(0, box2[2]-box2[0]) * max(0, box2[3]-box2[1])
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
            "confidence": float(conf)
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
