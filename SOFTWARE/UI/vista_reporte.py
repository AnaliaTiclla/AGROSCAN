import os
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QMessageBox, QHBoxLayout, QFrame
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt


class VistaReporteWindow(QWidget):
    def __init__(self, reporte_data):
        super().__init__()
        self.setWindowTitle(f"Detalles del Reporte #{reporte_data['id']}")
        self.setGeometry(300, 200, 700, 620)
        self.reporte = reporte_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Título
        titulo = QLabel(f"📝 Detalles del Reporte #{self.reporte['id']}")
        titulo.setFont(QFont("Segoe UI", 15, QFont.Bold))
        titulo.setStyleSheet("color: #bc3908;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)

        # Línea separadora
        linea = QFrame()
        linea.setFrameShape(QFrame.HLine)
        linea.setFrameShadow(QFrame.Sunken)
        layout.addWidget(linea)

        # Información detallada
        detalles_html = f"""
        <b>📅 Fecha:</b> {self.reporte['fecha']}<br>
        <b>🌱 Planta:</b> {self.reporte['planta']}<br>
        <b>🦠 Enfermedad:</b> {self.reporte['enfermedad']}<br>
        <b>🍎 Frutos detectados:</b> {self.reporte['num_frutos']}<br>
        <b>⏳ Maduración:</b> {self.reporte['maduracion']}<br>
        <b>📌 Estado:</b> {self.reporte['estado']}<br>
        <b>🗨️ Comentario del supervisor:</b> {self.reporte['comentario_supervisor'] or 'Ninguno'}
        """
        label_info = QLabel(detalles_html)
        label_info.setTextFormat(Qt.RichText)
        label_info.setAlignment(Qt.AlignLeft)
        label_info.setStyleSheet("margin: 10px; font-size: 13px;")
        layout.addWidget(label_info)

        # Imagen
        if self.reporte['path_imagen'] and os.path.exists(self.reporte['path_imagen']):
            imagen = QLabel()
            pixmap = QPixmap(self.reporte['path_imagen'])
            imagen.setPixmap(pixmap.scaledToWidth(420, Qt.SmoothTransformation))
            imagen.setAlignment(Qt.AlignCenter)
            layout.addWidget(imagen)
        else:
            sin_img = QLabel("❌ Imagen no encontrada.")
            sin_img.setStyleSheet("color: #c1121f; font-style: italic;")
            sin_img.setAlignment(Qt.AlignCenter)
            layout.addWidget(sin_img)

        # Ruta absoluta al PDF
        if self.reporte['path_reporte']:
            ruta_absoluta = os.path.abspath(self.reporte['path_reporte'])
            if os.path.exists(ruta_absoluta):
                btn_pdf = QPushButton("📂 Abrir PDF del Reporte")
                btn_pdf.setStyleSheet("margin-top: 10px; padding: 6px; font-weight: bold;")
                btn_pdf.clicked.connect(lambda: self.abrir_pdf(ruta_absoluta))
                layout.addWidget(btn_pdf)
            else:
                error_pdf = QLabel("❌ El archivo PDF no fue encontrado.")
                error_pdf.setStyleSheet("color: #d62828; font-style: italic;")
                error_pdf.setAlignment(Qt.AlignCenter)
                layout.addWidget(error_pdf)

        self.setLayout(layout)

    def abrir_pdf(self, path_pdf):
        try:
            os.startfile(path_pdf)  # Solo en Windows
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el archivo PDF:\n{e}")
