# gestion_reportes.py

import os
from typing import Any, Dict, Tuple

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QMessageBox, QLineEdit, QHeaderView, QComboBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from database import obtener_reportes_agricultor, actualizar_estado_reporte
from vista_reporte import VistaReporteWindow
from exportador import generar_pdf_reporte_detallado  # Regenerar PDF con estado/comentario/imagen

BASE_STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QLabel#heading {
    font-size: 19px;
    font-weight: bold;
    color: #386641;
    margin-bottom: 14px;
    margin-top: 7px;
    qproperty-alignment: AlignCenter;
}
QTableWidget {
    background-color: #f6fff7;
    alternate-background-color: #e8f6ef;
    border: 1px solid #b7b7b7;
}
QHeaderView::section {
    background: #6a994e;
    color: white;
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #b7b7b7;
}
QPushButton {
    background-color: #a7c957;
    border: 1.5px solid #6a994e;
    color: #222;
    border-radius: 7px;
    padding: 4px 10px;
    font-size: 13px;
}
QPushButton:hover { background-color: #386641; color: white; }
QPushButton:disabled { background-color: #e0e0e0; color: #888; }
"""

# ---- Helpers ---------------------------------------------------------------

def _get_value(row: Any, key: str, pos_fallback: int, default=None):
    """
    Obtiene un valor de la fila 'row' que puede ser:
      - dict/RowMapping (por nombre de columna)
      - tuple/list (por posición)
    """
    # dict-like
    if isinstance(row, dict):
        return row.get(key, default)
    # registro de librerías tipo pyodbc/psycopg que exponen .keys()
    if hasattr(row, "keys") and callable(getattr(row, "keys")):
        try:
            return row[key]
        except Exception:
            return default
    # tuple/list
    try:
        return row[pos_fallback]
    except Exception:
        return default

def _coerce_rep(row: Any) -> Dict[str, Any]:
    """
    Normaliza una fila a un dict con las llaves esperadas.
    Acepta variaciones en orden/longitud.
    """
    # Posiciones fallback (ajústalas si tu SELECT cambia)
    return {
        "reporte_id":        _get_value(row, "id",             0),
        "usuario_id":        _get_value(row, "usuario_id",     1),
        "fecha":             _get_value(row, "fecha",          2),
        "planta":            _get_value(row, "planta",         3),
        "enfermedad":        _get_value(row, "enfermedad",     4),
        "num_frutos":        _get_value(row, "num_frutos",     5),
        "maduracion":        _get_value(row, "maduracion",     6),
        "path_imagen":       _get_value(row, "path_imagen",    7),
        "path_reporte":      _get_value(row, "path_reporte",   8),
        "estado":            _get_value(row, "estado",         9, "pendiente"),
        "comentario":        _get_value(row, "comentario",    10, ""),
    }

# ---- UI --------------------------------------------------------------------

class GestionReportesWindow(QWidget):
    def __init__(self, agricultor_id, agricultor_nombre):
        super().__init__()
        self.agricultor_id = agricultor_id
        self.agricultor_nombre = agricultor_nombre
        self.setWindowTitle(f"Reportes de {agricultor_nombre} - AgroScan")
        self.setGeometry(220, 220, 1020, 480)
        self.setStyleSheet(BASE_STYLESHEET)
        self._detalles = []  # Mantener referencias a subventanas
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        lbl = QLabel(f"Reportes del agricultor: {self.agricultor_nombre}")
        lbl.setObjectName("heading")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        self.tabla = QTableWidget()
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.tabla)
        self.setLayout(layout)

        # Config tabla
        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Planta", "Estado", "Fecha", "Evaluacion", "Comentario", "Guardar", "Ver", "Imagen"
        ])
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.tabla.verticalHeader().setVisible(False)

        self.cargar_reportes()

    def cargar_reportes(self):
        try:
            reportes = obtener_reportes_agricultor(self.agricultor_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los reportes:\n{e}")
            reportes = []

        self.tabla.setRowCount(len(reportes))

        estados = ["pendiente", "aprobado", "rechazado", "objetado"]

        for fila, raw in enumerate(reportes):
            rep = _coerce_rep(raw)

            # ID
            it_id = QTableWidgetItem(str(rep["reporte_id"] or ""))
            it_id.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(fila, 0, it_id)

            # Planta
            it_planta = QTableWidgetItem(rep["planta"] or "")
            it_planta.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(fila, 1, it_planta)

            # Enfermedad
            it_enf = QTableWidgetItem(rep["enfermedad"] or "")
            it_enf.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(fila, 2, it_enf)

            # Fecha
            it_fecha = QTableWidgetItem(str(rep["fecha"] or ""))
            it_fecha.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(fila, 3, it_fecha)

            # Estado (ComboBox)
            combo_estado = QComboBox()
            combo_estado.addItems(estados)
            estado_norm = (rep["estado"] or "pendiente").lower()
            idx = combo_estado.findText(estado_norm)
            combo_estado.setCurrentIndex(idx if idx >= 0 else 0)
            self.tabla.setCellWidget(fila, 4, combo_estado)

            # Comentario (editable)
            comentario_edit = QLineEdit(rep["comentario"] or "")
            comentario_edit.setPlaceholderText("Observaciones del supervisor…")
            self.tabla.setCellWidget(fila, 5, comentario_edit)

            # Guardar
            btn_guardar = QPushButton("Guardar")
            btn_guardar.setIcon(QIcon("iconos/icon-save.png"))
            btn_guardar.setStyleSheet("""
                QPushButton {
                    background-color: #4da6ff;
                    border: 1.5px solid #2b85d3;
                    color: white;
                    border-radius: 7px;
                    padding: 4px 10px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #1f78d1; }
            """)
            btn_guardar.clicked.connect(
                lambda _, rid=rep["reporte_id"], ce=comentario_edit, cb=combo_estado, rdict=rep:
                    self._guardar_y_pdf(rid, cb.currentText(), ce.text(), rdict)
            )
            self.tabla.setCellWidget(fila, 6, btn_guardar)

            # Ver detalle
            btn_ver = QPushButton("Ver")
            btn_ver.setIcon(QIcon("iconos/icon-eye.png"))
            btn_ver.setStyleSheet("""
                QPushButton {
                    background-color: #ffcc00;
                    border: 1.5px solid #e6b800;
                    color: black;
                    border-radius: 7px;
                    padding: 4px 10px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #e6b800; }
            """)
            btn_ver.clicked.connect(lambda _, rr=rep: self._ver_detalle(rr))
            self.tabla.setCellWidget(fila, 7, btn_ver)

            # Indicador de imagen
            abs_img = os.path.abspath(rep["path_imagen"]) if rep["path_imagen"] else ""
            it_img = QTableWidgetItem("Sí" if (abs_img and os.path.exists(abs_img)) else "No")
            it_img.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(fila, 8, it_img)

        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)

    def _guardar_y_pdf(self, reporte_id, nuevo_estado, comentario, rep_dict: Dict[str, Any]):
        # 1) Guardar en BD
        try:
            actualizar_estado_reporte(reporte_id, nuevo_estado, comentario)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el estado/comentario:\n{e}")
            return

        # 2) Regenerar el PDF (sobrescribe si hay ruta guardada)
        path_imagen = rep_dict.get("path_imagen")
        path_reporte = rep_dict.get("path_reporte")
        abs_img = os.path.abspath(path_imagen) if path_imagen else None
        if abs_img and not os.path.exists(abs_img):
            abs_img = None  # Evita fallos si la imagen no existe

        destino = os.path.abspath(path_reporte) if path_reporte else None

        try:
            generar_pdf_reporte_detallado(
                nombre_usuario=self.agricultor_nombre,
                fecha=rep_dict.get("fecha"),
                planta=rep_dict.get("planta"),
                enfermedad=rep_dict.get("enfermedad"),
                num_frutos=rep_dict.get("num_frutos"),
                maduracion=rep_dict.get("maduracion"),
                estado=nuevo_estado,
                comentario_supervisor=comentario,
                path_imagen=abs_img,
                destino=destino,
            )
        except Exception as e:
            QMessageBox.warning(self, "PDF", f"Se guardó el estado/comentario, pero no se pudo regenerar el PDF:\n{e}")
        else:
            QMessageBox.information(self, "Guardado", "Estado y comentario guardados. PDF actualizado.")
            self.cargar_reportes()

    def _ver_detalle(self, rep: Dict[str, Any]):
        datos = {
            "id": rep.get("reporte_id"),
            "usuario_id": rep.get("usuario_id"),
            "fecha": rep.get("fecha"),
            "planta": rep.get("planta"),
            "enfermedad": rep.get("enfermedad"),
            "num_frutos": rep.get("num_frutos"),
            "maduracion": rep.get("maduracion"),
            "path_imagen": rep.get("path_imagen"),
            "path_reporte": rep.get("path_reporte"),
            "estado": rep.get("estado"),
            "comentario_supervisor": rep.get("comentario"),
        }
        win = VistaReporteWindow(datos)
        self._detalles.append(win)
        win.show()
