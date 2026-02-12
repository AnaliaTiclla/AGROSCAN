from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QTextEdit, QLineEdit, QMessageBox, QFrame, QInputDialog
)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QImage
from PyQt5.QtCore import Qt, QTimer

from DATA.database import (
    guardar_reporte,
    hectarea_activa_de_agricultor,
    registrar_reporte_cosecha
)
from INFRA.yolo_service import (
    analizar_imagen_yolo,
    conteos_por_label,
    conteo_sanos_enfermos,
)
from INFRA.exportador import generar_pdf_reporte
import os
import cv2
import time
import math

# ======= CONFIG =======
DEBUG_LABELS = False

CAM_PREVIEW_MS = 100        # ~10 fps
YOLO_ANALISIS_MS = 800      # YOLO cada 0.8s

YOLO_CONF = 0.25
YOLO_IOU = 0.30

ANTI_FLICKER_SEC = 0.35

# --- TRACKING (para no duplicar) ---
# Distancia máxima (en pixeles) para considerar que es el mismo objeto entre análisis YOLO
TRACK_MAX_DIST_PX = 70
# Cuántos "ticks" seguidos debe verse un objeto antes de contarlo (reduce falsos positivos)
TRACK_CONFIRM_FRAMES = 2
# Cuántos "ticks" puede desaparecer y seguir siendo el mismo track
TRACK_MAX_MISSES = 3

BASE_STYLESHEET = """
QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
QLabel#heading {
    font-size: 20px; font-weight: bold; color: #386641;
    margin-bottom: 16px; margin-top: 8px; qproperty-alignment: AlignCenter;
}
QPushButton {
    background-color: #a7c957; border: 1.5px solid #6a994e; color: #222;
    border-radius: 8px; padding: 8px 16px; font-size: 14px;
}
QPushButton:hover { background-color: #386641; color: white; }
QPushButton:disabled { background-color: #e0e0e0; color: #888; }
QLineEdit { padding: 7px; border-radius: 5px; border: 1px solid #b7b7b7; font-size: 13px; }
QTextEdit { border-radius: 6px; border: 1px solid #b7b7b7; font-size: 13px; background: #f6fff7; }
"""

APTO_LABELS = {"Espárrago sano"}
NO_APTO_LABELS = {"Espárrago enfermo"}


class AnalisisChatWindow(QWidget):
    def __init__(self, usuario_id, nombre_usuario):
        super().__init__()
        self.usuario_id = usuario_id
        self.nombre_usuario = nombre_usuario
        self.setWindowTitle("Análisis y Chat - AgroScan")
        self.setGeometry(200, 200, 900, 640)

        # Imagen (modo archivo / captura)
        self.path_imagen = None
        self.path_imagen_anotada = None
        self.yolo_detections = []

        # Totales último análisis (modo imagen / captura)
        self.aptos = 0
        self.no_aptos = 0
        self.total_detectados = 0

        # --- Cámara en vivo ---
        self.cap = None
        self.camara_activa = False
        self.ultimo_frame = None
        self._yolo_en_proceso = False

        # ✅ Anti-parpadeo
        self._ultimo_frame_anotado = None
        self._ultimo_frame_anotado_ts = 0.0

        # ✅ Acumulado "real" sin duplicar usando tracking
        self.live_aptos_unique = 0
        self.live_noaptos_unique = 0
        self.live_total_unique = 0

        # Tracker state
        self._track_next_id = 1
        self._tracks = {}  # id -> {'cx','cy','label','misses','hits','counted'}
        self._yolo_tick = 0

        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.actualizar_preview)

        self.yolo_timer = QTimer()
        self.yolo_timer.timeout.connect(self.analizar_frame_en_vivo)

        self.setStyleSheet(BASE_STYLESHEET)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        lbl_heading = QLabel("Análisis de Imagen y Asistente AgroScan")
        lbl_heading.setObjectName("heading")
        layout.addWidget(lbl_heading)

        # --- Panel imagen/video ---
        self.img_label = QLabel("No hay imagen cargada")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedHeight(260)
        self.img_label.setFrameShape(QFrame.Box)
        self.img_label.setStyleSheet(
            "background: #f7fff6; border: 1.5px solid #d2e59e; font-size: 13px; color: #888;"
        )

        # Contadores: Actual + Acumulado real (unique)
        counters_row = QHBoxLayout()

        self.lbl_aptos = QLabel("Aptos (actual): 0")
        self.lbl_noaptos = QLabel("No aptos (actual): 0")
        self.lbl_total = QLabel("Total (actual): 0")

        for lbl in (self.lbl_aptos, self.lbl_noaptos, self.lbl_total):
            lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
            lbl.setStyleSheet("color:#1b5e20;")
        self.lbl_noaptos.setStyleSheet("color:#ba1a1a;")

        self.lbl_aptos_acum = QLabel("Aptos (unique): 0")
        self.lbl_noaptos_acum = QLabel("No aptos (unique): 0")
        self.lbl_total_acum = QLabel("Total (unique): 0")

        for lbl in (self.lbl_aptos_acum, self.lbl_noaptos_acum, self.lbl_total_acum):
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl.setStyleSheet("color:#1b5e20;")
        self.lbl_noaptos_acum.setStyleSheet("color:#ba1a1a;")

        counters_row.addWidget(self.lbl_aptos)
        counters_row.addWidget(self.lbl_noaptos)
        counters_row.addWidget(self.lbl_total)

        counters_row.addSpacing(18)

        counters_row.addWidget(self.lbl_aptos_acum)
        counters_row.addWidget(self.lbl_noaptos_acum)
        counters_row.addWidget(self.lbl_total_acum)

        counters_row.addStretch(1)

        # Botones
        btns = QHBoxLayout()

        self.btn_cargar = QPushButton("Cargar Imagen")
        self.btn_cargar.setIcon(QIcon("iconos/icon-image-add.png"))

        self.btn_camara = QPushButton("Cámara en vivo")
        self.btn_camara.setIcon(QIcon("iconos/icon-camera.png"))

        self.btn_capturar = QPushButton("Capturar para reporte")
        self.btn_capturar.setIcon(QIcon("iconos/icon-save.png"))
        self.btn_capturar.setEnabled(False)

        self.btn_reset_unique = QPushButton("Reset unique")
        self.btn_reset_unique.setIcon(QIcon("iconos/icon-refresh.png"))
        self.btn_reset_unique.setEnabled(False)

        btns.addWidget(self.btn_cargar)
        btns.addWidget(self.btn_camara)
        btns.addWidget(self.btn_capturar)
        btns.addWidget(self.btn_reset_unique)

        layout.addLayout(btns)
        layout.addWidget(self.img_label)
        layout.addLayout(counters_row)

        # --- Chat ---
        chat_label = QLabel("Chat con AgroScan")
        chat_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(chat_label)

        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setMinimumHeight(140)

        self.input_line = QLineEdit()
        self.send_btn = QPushButton("Enviar")
        self.send_btn.setIcon(QIcon("iconos/icon-send.png"))

        chat_h = QHBoxLayout()
        chat_h.addWidget(self.input_line)
        chat_h.addWidget(self.send_btn)

        layout.addWidget(self.chat_area)
        layout.addLayout(chat_h)

        self.guardar_btn = QPushButton("Guardar reporte (PDF)")
        self.guardar_btn.setIcon(QIcon("iconos/icon-save.png"))
        self.guardar_btn.setEnabled(False)
        layout.addWidget(self.guardar_btn)

        layout.setContentsMargins(30, 18, 30, 18)
        layout.setSpacing(12)
        self.setLayout(layout)

        # Conexiones
        self.btn_cargar.clicked.connect(self.cargar_imagen)
        self.btn_camara.clicked.connect(self.toggle_camara)
        self.btn_capturar.clicked.connect(self.capturar_frame_para_reporte)
        self.btn_reset_unique.clicked.connect(self.reset_unique_live)
        self.send_btn.clicked.connect(self.enviar_pregunta)
        self.guardar_btn.clicked.connect(self.guardar_reporte)

    # ==========================
    # MODO ARCHIVO (igual que antes)
    # ==========================
    def cargar_imagen(self):
        if self.camara_activa:
            self.detener_camara()

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", "", "Imágenes (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.mostrar_imagen(file_path)

    def mostrar_imagen(self, file_path):
        self.path_imagen = file_path
        self.chat_area.append("<span style='color:#38761d;'>Imagen cargada. Analizando con IA...</span>")
        self.guardar_btn.setEnabled(True)

        detections, image_with_boxes = analizar_imagen_yolo(
            file_path, conf_threshold=YOLO_CONF, iou_threshold=YOLO_IOU, draw=True
        )
        self.yolo_detections = detections

        if image_with_boxes is not None:
            self._set_pixmap_from_bgr(image_with_boxes)
        else:
            self.img_label.setText("No se pudo procesar la imagen.")
            return

        self.path_imagen_anotada = None
        try:
            os.makedirs("reports/imagenes", exist_ok=True)
            base = os.path.splitext(os.path.basename(file_path))[0]
            out_name = f"reports/imagenes/{base}_anotada.png"
            cv2.imwrite(out_name, image_with_boxes)
            self.path_imagen_anotada = os.path.abspath(out_name)
        except Exception as e:
            self.chat_area.append(f"<span style='color:#ba1a1a;'>⚠️ No pude guardar la imagen anotada: {e}</span>")

        if DEBUG_LABELS:
            print("DEBUG etiquetas:", conteos_por_label(detections))

        totales = conteo_sanos_enfermos(detections)
        self.aptos = totales.get("sanos", 0)
        self.no_aptos = totales.get("enfermos", 0)
        self.total_detectados = totales.get("total", 0)

        self._update_counters(self.aptos, self.no_aptos, self.total_detectados)

        resumen_legible = self.resumir_resultados_yolo(detections)
        self.chat_area.append(f"<b>AgroScan IA:</b> {resumen_legible}")
        self.chat_area.append(
            f"<i>Conteo: Sanos={self.aptos} | Enfermos={self.no_aptos} | Total={self.total_detectados}</i>"
        )

        asig = hectarea_activa_de_agricultor(self.usuario_id)
        if not asig:
            self.chat_area.append("<span style='color:#ba1a1a;'>⚠️ No tienes una hectárea asignada. Pide al supervisor que te asigne una.</span>")
            return

        try:
            new_id = registrar_reporte_cosecha(
                agricultor_id=self.usuario_id,
                hectarea_id=asig["hectarea_id"],
                aptos=self.aptos,
                no_aptos=self.no_aptos,
                fuente="YOLO"
            )
            if new_id:
                self.chat_area.append(f"<span style='color:#1b5e20;'>✅ Sesión registrada (id={new_id}) en {asig['codigo']}.</span>")
            else:
                self.chat_area.append("<span style='color:#ba1a1a;'>❌ No se pudo registrar la sesión en la base de datos.</span>")
        except Exception as e:
            self.chat_area.append(f"<span style='color:#ba1a1a;'>❌ Error al registrar sesión: {e}</span>")

    # ==========================
    # CÁMARA EN VIVO (unique sin duplicar)
    # ==========================
    def toggle_camara(self):
        if self.camara_activa:
            self.detener_camara()
        else:
            self.iniciar_camara_con_seleccion()

    def iniciar_camara_con_seleccion(self):
        indices = self._detectar_camaras(max_index=5)
        if not indices:
            QMessageBox.critical(self, "Cámara", "No se detectaron cámaras disponibles (0-5).")
            return

        opciones = [f"Cámara {i}" for i in indices]
        seleccion, ok = QInputDialog.getItem(
            self, "Seleccionar cámara", "Elige la cámara:", opciones, 0, False
        )
        if not ok:
            return

        cam_index = int(seleccion.split()[-1])

        cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(cam_index)
            if not cap.isOpened():
                QMessageBox.critical(self, "Cámara", f"No se pudo abrir la cámara {cam_index}.")
                return

        if self.camara_activa:
            self.detener_camara()

        self.cap = cap
        self.camara_activa = True
        self.ultimo_frame = None
        self._yolo_en_proceso = False

        # Reset unique
        self._reset_tracker()

        # UI
        self.btn_camara.setText("Detener cámara")
        self.btn_capturar.setEnabled(True)
        self.btn_reset_unique.setEnabled(True)

        self.chat_area.append("<span style='color:#38761d;'>Cámara iniciada. Analizando en vivo (unique sin duplicar)...</span>")

        self.preview_timer.start(CAM_PREVIEW_MS)
        self.yolo_timer.start(YOLO_ANALISIS_MS)

    def detener_camara(self):
        self.preview_timer.stop()
        self.yolo_timer.stop()
        self.camara_activa = False
        self.btn_camara.setText("Cámara en vivo")
        self.btn_capturar.setEnabled(False)
        self.btn_reset_unique.setEnabled(False)

        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None

        self.chat_area.append("<span style='color:#888;'>Cámara detenida.</span>")

    def reset_unique_live(self):
        self._reset_tracker()
        self.chat_area.append("<span style='color:#38761d;'>✅ Unique reiniciado (tracker limpio).</span>")

    def actualizar_preview(self):
        if not self.camara_activa or self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        self.ultimo_frame = frame.copy()

        # Anti-parpadeo: no pisar el frame anotado recién mostrado
        if self._ultimo_frame_anotado_ts and (time.time() - self._ultimo_frame_anotado_ts) < ANTI_FLICKER_SEC:
            return

        self._set_pixmap_from_bgr(frame)

    def analizar_frame_en_vivo(self):
        if not self.camara_activa or self.ultimo_frame is None:
            return
        if self._yolo_en_proceso:
            return

        self._yolo_en_proceso = True
        self._yolo_tick += 1
        frame = self.ultimo_frame.copy()

        try:
            os.makedirs("reports/capturas_live", exist_ok=True)
            temp_path = os.path.join("reports/capturas_live", "live_frame.jpg")
            cv2.imwrite(temp_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

            detections, image_with_boxes = analizar_imagen_yolo(
                temp_path, conf_threshold=YOLO_CONF, iou_threshold=YOLO_IOU, draw=True
            )

            # Conteo actual (frame)
            totales = conteo_sanos_enfermos(detections)
            aptos = totales.get("sanos", 0)
            no_aptos = totales.get("enfermos", 0)
            total = totales.get("total", 0)
            self._update_counters(aptos, no_aptos, total)

            # ✅ Tracking: actualizar tracks con detecciones y sumar unique SOLO cuando un ID se confirma
            det_items = self._detections_to_centroids(detections)
            self._update_tracks(det_items)

            # UI unique
            self._update_unique_labels()

            # Mostrar anotada
            if image_with_boxes is not None:
                self._ultimo_frame_anotado = image_with_boxes
                self._ultimo_frame_anotado_ts = time.time()
                self._set_pixmap_from_bgr(image_with_boxes)

            if DEBUG_LABELS:
                print("LIVE labels:", conteos_por_label(detections))
                print("TRACKS:", {k: (v["label"], v["hits"], v["misses"], v["counted"]) for k, v in self._tracks.items()})

        except Exception as e:
            self.chat_area.append(f"<span style='color:#ba1a1a;'>⚠️ Error en análisis en vivo: {e}</span>")
        finally:
            self._yolo_en_proceso = False

    def capturar_frame_para_reporte(self):
        if not self.camara_activa or self.ultimo_frame is None:
            QMessageBox.warning(self, "Captura", "No hay frame disponible para capturar.")
            return

        try:
            os.makedirs("reports/capturas", exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join("reports/capturas", f"captura_{ts}.jpg")
            cv2.imwrite(out_path, self.ultimo_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

            self.detener_camara()
            self.mostrar_imagen(os.path.abspath(out_path))

        except Exception as e:
            QMessageBox.critical(self, "Captura", f"No se pudo guardar la captura: {e}")

    def _detectar_camaras(self, max_index=5):
        disponibles = []
        for i in range(0, max_index + 1):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap is None or not cap.isOpened():
                try:
                    cap.release()
                except:
                    pass
                cap = cv2.VideoCapture(i)

            if cap is not None and cap.isOpened():
                disponibles.append(i)
            try:
                cap.release()
            except:
                pass
        return disponibles

    # ==========================
    # TRACKER (simple, sin librerías)
    # ==========================
    def _reset_tracker(self):
        self.live_aptos_unique = 0
        self.live_noaptos_unique = 0
        self.live_total_unique = 0
        self._track_next_id = 1
        self._tracks = {}
        self._yolo_tick = 0
        self._ultimo_frame_anotado = None
        self._ultimo_frame_anotado_ts = 0.0
        self._update_unique_labels()

    def _label_group(self, label: str) -> str:
        label = (label or "").strip()
        if label in APTO_LABELS:
            return "apto"
        if label in NO_APTO_LABELS:
            return "noapto"
        return "otro"

    def _detections_to_centroids(self, detections):
        """
        Devuelve lista: [{'cx':..,'cy':..,'label':..}] SOLO si logra extraer bbox.
        Soporta varias formas comunes de bbox.
        """
        items = []
        for det in detections or []:
            label = (det.get("label") or det.get("class") or det.get("name") or "").strip()
            bbox = self._extract_bbox(det)
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            items.append({"cx": cx, "cy": cy, "label": label})
        return items

    def _extract_bbox(self, det):
        """
        Intenta extraer (x1,y1,x2,y2) desde keys típicas.
        Ajusta aquí si tu yolo_service usa otro formato.
        """
        # 1) bbox como lista/tupla [x1,y1,x2,y2]
        bbox = det.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])

        # 2) box como lista/tupla
        box = det.get("box")
        if isinstance(box, (list, tuple)) and len(box) == 4:
            return float(box[0]), float(box[1]), float(box[2]), float(box[3])

        # 3) xyxy
        xyxy = det.get("xyxy")
        if isinstance(xyxy, (list, tuple)) and len(xyxy) == 4:
            return float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])

        # 4) bbox como dict {'x1':..,'y1':..,'x2':..,'y2':..}
        if isinstance(bbox, dict):
            keys = ("x1", "y1", "x2", "y2")
            if all(k in bbox for k in keys):
                return float(bbox["x1"]), float(bbox["y1"]), float(bbox["x2"]), float(bbox["y2"])

        # 5) bbox como dict {'left','top','right','bottom'}
        if isinstance(bbox, dict):
            keys = ("left", "top", "right", "bottom")
            if all(k in bbox for k in keys):
                return float(bbox["left"]), float(bbox["top"]), float(bbox["right"]), float(bbox["bottom"])

        # 6) det directo con x1,y1,x2,y2
        if all(k in det for k in ("x1", "y1", "x2", "y2")):
            return float(det["x1"]), float(det["y1"]), float(det["x2"]), float(det["y2"])

        return None

    def _dist(self, a, b):
        return math.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"])

    def _update_tracks(self, det_items):
        """
        Matching greedy por distancia + misma clase (grupo label).
        - Actualiza hits/misses.
        - Crea nuevos IDs para no-match.
        - Cuenta UNIQUE solo cuando un track se confirma (hits >= TRACK_CONFIRM_FRAMES) y aún no fue contado.
        """
        # 1) marcar todos como no vistos en este tick
        for tid in list(self._tracks.keys()):
            self._tracks[tid]["seen_this_tick"] = False

        # 2) construir lista de pares posibles (tid, det_idx, dist) que cumplan umbral + misma clase/grupo
        pairs = []
        for det_idx, det in enumerate(det_items):
            det_group = self._label_group(det["label"])
            for tid, tr in self._tracks.items():
                tr_group = self._label_group(tr["label"])
                # Restricción: misma categoría (apto/noapto/otro)
                if det_group != tr_group:
                    continue
                d = math.hypot(det["cx"] - tr["cx"], det["cy"] - tr["cy"])
                if d <= TRACK_MAX_DIST_PX:
                    pairs.append((d, tid, det_idx))

        # ordenar por menor distancia
        pairs.sort(key=lambda x: x[0])

        matched_tracks = set()
        matched_dets = set()

        # 3) greedy matching
        for d, tid, det_idx in pairs:
            if tid in matched_tracks or det_idx in matched_dets:
                continue
            matched_tracks.add(tid)
            matched_dets.add(det_idx)

            det = det_items[det_idx]
            tr = self._tracks[tid]
            tr["cx"] = det["cx"]
            tr["cy"] = det["cy"]
            tr["label"] = det["label"]  # mantener label actual
            tr["misses"] = 0
            tr["hits"] += 1
            tr["seen_this_tick"] = True

            # ✅ contar unique SOLO cuando se confirma por hits y no contado
            if (not tr["counted"]) and tr["hits"] >= TRACK_CONFIRM_FRAMES:
                tr["counted"] = True
                self._inc_unique_by_label(tr["label"])

        # 4) tracks no matched => misses++
        for tid, tr in list(self._tracks.items()):
            if not tr.get("seen_this_tick"):
                tr["misses"] += 1

        # 5) dets no matched => crear nuevos tracks
        for det_idx, det in enumerate(det_items):
            if det_idx in matched_dets:
                continue
            tid = self._track_next_id
            self._track_next_id += 1
            self._tracks[tid] = {
                "cx": det["cx"],
                "cy": det["cy"],
                "label": det["label"],
                "misses": 0,
                "hits": 1,
                "counted": False,
                "seen_this_tick": True,
            }
            # NO se cuenta de inmediato; se cuenta al confirmar (hits>=TRACK_CONFIRM_FRAMES)

        # 6) eliminar tracks viejos
        for tid in list(self._tracks.keys()):
            if self._tracks[tid]["misses"] > TRACK_MAX_MISSES:
                del self._tracks[tid]

    def _inc_unique_by_label(self, label):
        grp = self._label_group(label)
        if grp == "apto":
            self.live_aptos_unique += 1
        elif grp == "noapto":
            self.live_noaptos_unique += 1
        else:
            # si quisieras contar "otros", agrégalo aquí
            pass
        self.live_total_unique = self.live_aptos_unique + self.live_noaptos_unique

    def _update_unique_labels(self):
        self.lbl_aptos_acum.setText(f"Aptos (unique): {self.live_aptos_unique}")
        self.lbl_noaptos_acum.setText(f"No aptos (unique): {self.live_noaptos_unique}")
        self.lbl_total_acum.setText(f"Total (unique): {self.live_total_unique}")

    # ==========================
    # UTILIDADES UI
    # ==========================
    def _set_pixmap_from_bgr(self, bgr_image):
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self.img_label.setPixmap(
            pixmap.scaled(self.img_label.width(), self.img_label.height(), Qt.KeepAspectRatio)
        )

    def _update_counters(self, aptos, no_aptos, total):
        self.lbl_aptos.setText(f"Aptos (actual): {aptos}")
        self.lbl_noaptos.setText(f"No aptos (actual): {no_aptos}")
        self.lbl_total.setText(f"Total (actual): {total}")

    # ==========================
    # CHAT
    # ==========================
    def resumir_resultados_yolo(self, detections):
        if not detections:
            return "No se detectaron espárragos en la imagen."

        conteo = {}
        for det in detections:
            etiqueta = det.get('label', '').strip()
            if etiqueta:
                conteo[etiqueta] = conteo.get(etiqueta, 0) + 1

        if not conteo:
            return "No se detectaron espárragos reconocidos en la imagen."

        orden = ["Espárrago enfermo", "Espárrago sano"]
        parts = []
        for k in orden:
            if k in conteo:
                parts.append(f"{k}: {conteo[k]}")
        for k, v in conteo.items():
            if k not in {"Espárrago sano", "Espárrago enfermo"}:
                parts.append(f"{k}: {v}")
        return "; ".join(parts)

    def enviar_pregunta(self):
        pregunta = self.input_line.text().strip()
        if not pregunta:
            return
        self.chat_area.append(f"<b>Tú:</b> {pregunta}")
        respuesta = self.respuesta_chatbot(pregunta)
        self.chat_area.append(f"<b>AgroScan:</b> {respuesta}")
        self.input_line.clear()

    def respuesta_chatbot(self, pregunta):
        pregunta = pregunta.lower()
        total = len(self.yolo_detections or [])
        if "espárrago" in pregunta or "esparrago" in pregunta or "fruto" in pregunta or "vegetal" in pregunta:
            return f"Detecté {total} espárrago(s)." if total else "No detecté espárragos."
        return "No entiendo la pregunta. Intenta ser más específico."

    # ==========================
    # REPORTE
    # ==========================
    def guardar_reporte(self):
        if not self.path_imagen:
            QMessageBox.warning(self, "Error", "Debes cargar una imagen o capturar un frame para reporte.")
            return

        resumen = self.resumir_resultados_yolo(self.yolo_detections)

        asig = hectarea_activa_de_agricultor(self.usuario_id)
        hectarea = asig["codigo"] if asig else None

        img_para_pdf = self.path_imagen_anotada or self.path_imagen

        path_pdf = generar_pdf_reporte(
            self.nombre_usuario,
            resumen,
            img_para_pdf,
            aptos=self.aptos,
            no_aptos=self.no_aptos,
            hectarea=hectarea
        )

        planta = "Espárrago"
        enfermedad = "Detectado espárrago enfermo" if self.no_aptos > 0 else "Cultivo saludable"
        num_frutos = self.total_detectados
        maduracion = "No aplica"

        img_rel = os.path.relpath(self.path_imagen_anotada or self.path_imagen, os.getcwd())

        ok, msg = guardar_reporte(
            self.usuario_id, planta, enfermedad, num_frutos, maduracion,
            img_rel, path_pdf
        )
        if ok:
            QMessageBox.information(self, "Éxito", "Reporte guardado correctamente como PDF.")
            self.guardar_btn.setEnabled(False)
            self.guardar_btn.setText("Guardado ✅")
        else:
            QMessageBox.critical(self, "Error", msg)

    # ==========================
    # CIERRE
    # ==========================
    def closeEvent(self, event):
        try:
            if self.camara_activa:
                self.detener_camara()
        except:
            pass
        event.accept()
