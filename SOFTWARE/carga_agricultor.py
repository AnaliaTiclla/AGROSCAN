from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QTextEdit, QLineEdit, QMessageBox, QFrame
)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QImage
from PyQt5.QtCore import Qt
# Proxy que apunta a SQL Server (database_mssql)
from database import (
    guardar_reporte,                 # reporte clásico (PDF + metadatos)
    hectarea_activa_de_agricultor,   # obtener hectárea asignada
    registrar_reporte_cosecha        # registrar aptos/no aptos para dashboards
)
from yolo_service import (
    analizar_imagen_yolo,
    conteos_por_label,
    conteo_sanos_enfermos,           # atajo sanos/enfermos/total
)
from exportador import generar_pdf_reporte
import os
import cv2

# ======= CONFIG =======
DEBUG_LABELS = False  # True para depurar en consola

BASE_STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QLabel#heading {
    font-size: 20px;
    font-weight: bold;
    color: #386641;
    margin-bottom: 16px;
    margin-top: 8px;
    qproperty-alignment: AlignCenter;
}
QPushButton {
    background-color: #a7c957;
    border: 1.5px solid #6a994e;
    color: #222;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #386641;
    color: white;
}
QPushButton:disabled {
    background-color: #e0e0e0;
    color: #888;
}
QLineEdit {
    padding: 7px;
    border-radius: 5px;
    border: 1px solid #b7b7b7;
    font-size: 13px;
}
QTextEdit {
    border-radius: 6px;
    border: 1px solid #b7b7b7;
    font-size: 13px;
    background: #f6fff7;
}
"""

# 👉 Etiquetas exactas (normalizadas por yolo_service/clases.py)
APTO_LABELS = {"Espárrago sano"}
NO_APTO_LABELS = {"Espárrago enfermo"}

class AnalisisChatWindow(QWidget):
    def __init__(self, usuario_id, nombre_usuario):
        super().__init__()
        self.usuario_id = usuario_id
        self.nombre_usuario = nombre_usuario
        self.setWindowTitle("Análisis y Chat - AgroScan")
        self.setGeometry(200, 200, 700, 530)
        self.path_imagen = None
        self.path_imagen_anotada = None  # <- NUEVO: guardamos PNG con cajas
        self.yolo_detections = []
        # Totales para dashboards (último análisis)
        self.aptos = 0
        self.no_aptos = 0
        self.total_detectados = 0
        self.setStyleSheet(BASE_STYLESHEET)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        lbl_heading = QLabel("Análisis de Imagen y Asistente AgroScan")
        lbl_heading.setObjectName("heading")
        layout.addWidget(lbl_heading)

        self.img_label = QLabel("No hay imagen cargada")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedHeight(200)
        self.img_label.setFrameShape(QFrame.Box)
        self.img_label.setStyleSheet("background: #f7fff6; border: 1.5px solid #d2e59e; font-size: 13px; color: #888;")

        btns = QHBoxLayout()
        self.btn_cargar = QPushButton("Cargar Imagen")
        self.btn_cargar.setIcon(QIcon("iconos/icon-image-add.png"))
        self.btn_capturar = QPushButton("Capturar Imagen (simulado)")
        self.btn_capturar.setIcon(QIcon("iconos/icon-camera.png"))
        btns.addWidget(self.btn_cargar)
        btns.addWidget(self.btn_capturar)

        layout.addLayout(btns)
        layout.addWidget(self.img_label)

        chat_label = QLabel("Chat con AgroScan")
        chat_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(chat_label)

        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setMinimumHeight(110)
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
        layout.setSpacing(13)
        self.setLayout(layout)

        self.btn_cargar.clicked.connect(self.cargar_imagen)
        self.btn_capturar.clicked.connect(self.capturar_imagen)
        self.send_btn.clicked.connect(self.enviar_pregunta)
        self.guardar_btn.clicked.connect(self.guardar_reporte)

    def cargar_imagen(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen", "", "Imágenes (*.png *.jpg *.jpeg)")
        if file_path:
            self.mostrar_imagen(file_path)

    def capturar_imagen(self):
        self.cargar_imagen()

    def mostrar_imagen(self, file_path):
        self.path_imagen = file_path
        self.chat_area.append("<span style='color:#38761d;'>Imagen cargada. Analizando con IA...</span>")
        self.guardar_btn.setEnabled(True)

        # ---- YOLO: análisis
        detections, image_with_boxes = analizar_imagen_yolo(
            file_path, conf_threshold=0.25, iou_threshold=0.30, draw=True
        )
        self.yolo_detections = detections

        # Mostrar imagen anotada en la UI
        if image_with_boxes is not None:
            rgb_image = cv2.cvtColor(image_with_boxes, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_image.shape
            bytes_per_line = 3 * width
            qimg = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.img_label.setPixmap(pixmap.scaled(self.img_label.width(), self.img_label.height(), Qt.KeepAspectRatio))
        else:
            self.img_label.setText("No se pudo procesar la imagen.")
            return

        # --- Guardar imagen anotada (para PDF y supervisor)
        self.path_imagen_anotada = None
        try:
            os.makedirs("reports/imagenes", exist_ok=True)
            base = os.path.splitext(os.path.basename(file_path))[0]
            out_name = f"reports/imagenes/{base}_anotada.png"
            cv2.imwrite(out_name, image_with_boxes)
            self.path_imagen_anotada = os.path.abspath(out_name)
        except Exception as e:
            self.chat_area.append(f"<span style='color:#ba1a1a;'>⚠️ No pude guardar la imagen anotada: {e}</span>")

        # Resumen por etiqueta y totales apto/no apto
        conteos = conteos_por_label(detections)
        if DEBUG_LABELS:
            print("DEBUG etiquetas:", conteos)

        totales = conteo_sanos_enfermos(detections)
        self.aptos = totales.get("sanos", 0)
        self.no_aptos = totales.get("enfermos", 0)
        self.total_detectados = totales.get("total", 0)

        # Mostrar resumen en el chat
        resumen_legible = self.resumir_resultados_yolo(detections)
        self.chat_area.append(f"<b>AgroScan IA:</b> {resumen_legible}")
        self.chat_area.append(f"<i>Conteo: Sanos={self.aptos} | Enfermos={self.no_aptos} | Total={self.total_detectados}</i>")

        # Registrar sesión en BD (dashboard) si hay hectárea asignada
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

    def resumir_resultados_yolo(self, detections):
        if not detections:
            return "No se detectaron espárragos en la imagen."

        conteo = {}
        # Tomamos la etiqueta normalizada ('label'), no 'name'
        for det in detections:
            etiqueta = det.get('label', '').strip()
            if etiqueta:
                conteo[etiqueta] = conteo.get(etiqueta, 0) + 1

        if not conteo:
            return "No se detectaron espárragos reconocidos en la imagen."

        # Ordenar para mostrar primero enfermos, luego sanos
        orden = ["Espárrago enfermo", "Espárrago sano"]
        parts = []
        for k in orden:
            if k in conteo:
                parts.append(f"{k}: {conteo[k]}")
        # añadir lo que no esté en el orden (por robustez)
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

    def guardar_reporte(self):
        if not self.path_imagen:
            QMessageBox.warning(self, "Error", "Debes cargar una imagen.")
            return

        resumen = self.resumir_resultados_yolo(self.yolo_detections)

        # Hectárea (si existe) para añadir al PDF
        asig = hectarea_activa_de_agricultor(self.usuario_id)
        hectarea = asig["codigo"] if asig else None

        # Usar la imagen ANOTADA si existe; si no, la original
        img_para_pdf = self.path_imagen_anotada or self.path_imagen

        # Generación de PDF (exportador.py)
        path_pdf = generar_pdf_reporte(
            self.nombre_usuario,
            resumen,
            img_para_pdf,
            aptos=self.aptos,
            no_aptos=self.no_aptos,
            hectarea=hectarea
        )

        # --- Guardar reporte "clásico" en BD ---
        planta = "Espárrago"
        enfermedad = "Detectado espárrago enfermo" if self.no_aptos > 0 else "Cultivo saludable"
        num_frutos = self.total_detectados  # sanos + enfermos
        maduracion = "No aplica"

        # Guardar la ruta de la imagen ANOTADA (preferible para revisión del supervisor)
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
