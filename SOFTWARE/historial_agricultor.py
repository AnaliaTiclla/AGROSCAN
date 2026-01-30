# historial_agricultor.py

import os
import webbrowser
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from database import listar_reportes, eliminar_reporte
from vista_reporte import VistaReporteWindow

# Estilo visual
BASE_STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QLabel#heading {
    font-size: 19px;
    font-weight: bold;
    color: #386641;
    margin-bottom: 6px;
    margin-top: 8px;
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
    border: 1px solid #555;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 13px;
}
QPushButton:disabled {
    background-color: #e0e0e0;
    color: #888;
}
"""

class HistorialReportesAgricultor(QWidget):
    def __init__(self, usuario_id):
        super().__init__()
        self.usuario_id = usuario_id
        self.setWindowTitle("Historial de Reportes - AgroScan")
        self.setGeometry(200, 200, 970, 430)
        self.setStyleSheet(BASE_STYLESHEET)
        self.init_ui()

    # ---------- UI ----------
    def init_ui(self):
        layout = QVBoxLayout()

        # Cabecera con título + botón Actualizar
        head = QHBoxLayout()
        lbl = QLabel("Tus reportes")
        lbl.setObjectName("heading")
        head.addWidget(lbl)
        head.addStretch(1)

        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setIcon(QIcon("iconos/icon-refresh.png"))
        self.btn_actualizar.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff;
                color: white;
                border: 1.5px solid #2b85d3;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1f78d1; }
        """)
        self.btn_actualizar.clicked.connect(self.recargar_historial)
        head.addWidget(self.btn_actualizar)

        layout.addLayout(head)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Planta", "Estado", "Fecha", "Evaluacion", "Comentario supervisor", "Eliminar", "Ver"
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

        layout.addWidget(self.tabla)
        self.setLayout(layout)

        # Carga inicial
        self.cargar_reportes()

    # ---------- Carga / Recarga ----------
    def recargar_historial(self):
        """Refresca la tabla sin cerrar sesión."""
        self.btn_actualizar.setEnabled(False)
        self.btn_actualizar.setText("Actualizando…")
        try:
            # Guardar estado visual (scroll y selección)
            scroll_val = self.tabla.verticalScrollBar().value()
            selected_row = self.tabla.currentRow()

            self.cargar_reportes()

            # Restaurar estado
            self.tabla.verticalScrollBar().setValue(scroll_val)
            if 0 <= selected_row < self.tabla.rowCount():
                self.tabla.selectRow(selected_row)

            self.btn_actualizar.setText("Actualizado ✓")
        except Exception as e:
            QMessageBox.warning(self, "Actualizar", f"No se pudo actualizar el historial:\n{e}")
            self.btn_actualizar.setText("Actualizar")
        finally:
            self.btn_actualizar.setEnabled(True)

    def cargar_reportes(self):
        reportes = listar_reportes(usuario_id=self.usuario_id, rol='agricultor')

        self.tabla.setSortingEnabled(False)
        self.tabla.clearContents()
        self.tabla.setRowCount(len(reportes))

        for i, rep in enumerate(reportes):
            (reporte_id, usuario_id, fecha, planta, enfermedad, num_frutos,
             maduracion, path_imagen, path_reporte, estado, comentario) = rep

            self.tabla.setItem(i, 0, self.centrado(str(reporte_id)))
            self.tabla.setItem(i, 1, self.centrado(planta))
            self.tabla.setItem(i, 2, self.centrado(enfermedad))
            self.tabla.setItem(i, 3, self.centrado(str(fecha)))
            self.tabla.setItem(i, 4, self.centrado(estado))
            self.tabla.setItem(i, 5, QTableWidgetItem(comentario or ""))

            # Botón Eliminar
            btn_eliminar = QPushButton("🗑 Eliminar")
            btn_eliminar.setCursor(Qt.PointingHandCursor)
            btn_eliminar.setStyleSheet("""
                QPushButton {
                    background-color: #d62828;
                    color: white;
                    border: 1px solid #a4161a;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 4px 10px;
                }
                QPushButton:hover { background-color: #9d0208; }
            """)
            if estado != "pendiente":
                btn_eliminar.setEnabled(False)
            else:
                btn_eliminar.clicked.connect(lambda _, rid=reporte_id: self.eliminar_reporte(rid))
            self.tabla.setCellWidget(i, 6, btn_eliminar)

            # Botón Ver
            btn_ver = QPushButton("👁 Ver")
            btn_ver.setCursor(Qt.PointingHandCursor)
            btn_ver.setStyleSheet("""
                QPushButton {
                    background-color: #fcbf49;
                    color: #222;
                    border: 1px solid #f77f00;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: #f77f00; color: white; }
            """)
            btn_ver.clicked.connect(lambda _, rep=rep: self.ver_reporte(rep))
            self.tabla.setCellWidget(i, 7, btn_ver)

        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSortingEnabled(True)
        # Ordenar por fecha (columna 3) descendente
        self.tabla.sortItems(3, Qt.DescendingOrder)

    # ---------- Utils / Actions ----------
    def centrado(self, texto):
        item = QTableWidgetItem(texto)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def eliminar_reporte(self, reporte_id):
        confirmado = QMessageBox.question(
            self, "Confirmar", "¿Seguro que quieres eliminar este reporte?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirmado == QMessageBox.Yes:
            exito = eliminar_reporte(reporte_id, self.usuario_id)
            if exito:
                QMessageBox.information(self, "Eliminado", "Reporte eliminado correctamente.")
                self.recargar_historial()  # refrescar tras eliminar
            else:
                QMessageBox.warning(self, "No permitido", "Solo puedes eliminar reportes pendientes propios.")

    def ver_reporte(self, reporte):
        datos = {
            "id": reporte[0],
            "usuario_id": reporte[1],
            "fecha": reporte[2],
            "planta": reporte[3],
            "enfermedad": reporte[4],
            "num_frutos": reporte[5],
            "maduracion": reporte[6],
            "path_imagen": reporte[7],
            "path_reporte": reporte[8],
            "estado": reporte[9],
            "comentario_supervisor": reporte[10]
        }
        self.ventana_vista = VistaReporteWindow(datos)
        self.ventana_vista.show()

    # Atajo: F5 para actualizar
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.recargar_historial()
        else:
            super().keyPressEvent(event)
