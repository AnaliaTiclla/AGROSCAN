# gestion_actividades.py
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, QDate, QUrl
from PyQt5.QtGui import QDesktopServices
from database import listar_actividades_supervisor, actualizar_estado_actividad
from exportador import generar_pdf_actividad

BASE_STYLESHEET = """
QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
QLabel#title { font-size: 18px; font-weight: 700; color: #386641; }
QPushButton { background: #a7c957; border: 1.5px solid #6a994e; color: #222; border-radius: 8px; padding: 6px 12px; }
QPushButton:hover { background: #386641; color: #fff; }
"""

class GestionActividadesWindow(QWidget):
    def __init__(self, supervisor_id: int, nombre_supervisor: str):
        super().__init__()
        self.supervisor_id = supervisor_id
        self.nombre = nombre_supervisor
        self.setWindowTitle("Gestión de Actividades - AgroScan")
        self.setMinimumSize(980, 620)
        self.setStyleSheet(BASE_STYLESHEET)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout()
        title = QLabel("Gestión de Actividades"); title.setObjectName("title"); title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        bar = QHBoxLayout()
        self.dp_desde = QDateEdit(); self.dp_desde.setCalendarPopup(True); self.dp_desde.setDate(QDate.currentDate().addMonths(-1))
        self.dp_hasta = QDateEdit(); self.dp_hasta.setCalendarPopup(True); self.dp_hasta.setDate(QDate.currentDate())
        self.cmb_estado = QComboBox(); self.cmb_estado.addItems(["(todos)","pendiente","aprobado","rechazado"])
        self.btn_ref = QPushButton("Actualizar"); self.btn_ref.clicked.connect(self._load)

        bar.addWidget(QLabel("Desde:")); bar.addWidget(self.dp_desde)
        bar.addWidget(QLabel("Hasta:")); bar.addWidget(self.dp_hasta)
        bar.addWidget(QLabel("Estado:")); bar.addWidget(self.cmb_estado)
        bar.addStretch(1); bar.addWidget(self.btn_ref)
        root.addLayout(bar)

        self.tbl = QTableWidget(0, 12)
        self.tbl.setHorizontalHeaderLabels(["ID","Fecha","Hect.","Agricultor","Tipo","Cant.","Unidad","Aptos","No aptos","Estado","Comentario","Acción"])
        h = self.tbl.horizontalHeader()
        for i in range(12): h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.tbl.setAlternatingRowColors(True)
        root.addWidget(self.tbl)

        self.setLayout(root)

    def _load(self):
        desde = self.dp_desde.date().toString("yyyy-MM-dd") + " 00:00:00"
        hasta = self.dp_hasta.date().toString("yyyy-MM-dd") + " 23:59:59"
        estado = None if self.cmb_estado.currentText() == "(todos)" else self.cmb_estado.currentText()
        try:
            rows = listar_actividades_supervisor(estado, desde, hasta)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar actividades:\n{e}")
            return

        self.tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            # columnas que usamos luego para el PDF:
            agricultor_nombre = r.get("agricultor") or str(r.get("agricultor_id"))
            codigo_hectarea   = r.get("codigo_hectarea") or "-"
            tipo              = r.get("tipo") or "-"
            # celdas visibles
            cells = [
                str(r.get("id")),
                str(r.get("fecha_hora")),
                str(codigo_hectarea),
                str(agricultor_nombre),
                str(tipo),
                str(r.get("cantidad") or ""),
                str(r.get("unidad") or ""),
                str(r.get("aptos") or ""),
                str(r.get("no_aptos") or ""),
                str(r.get("estado") or ""),
            ]
            for j, txt in enumerate(cells):
                it = QTableWidgetItem(txt); it.setTextAlignment(Qt.AlignCenter); self.tbl.setItem(i, j, it)

            # Comentario + botones aprobar/rechazar
            ed = QLineEdit(r.get("comentario_supervisor") or "")
            self.tbl.setCellWidget(i, 10, ed)

            b_ap = QPushButton("Aprobar")
            b_re = QPushButton("Rechazar")
            # capturar variables por defecto en lambda:
            b_ap.clicked.connect(lambda _, rid=r["id"], ed=ed, rr=r: self._set_estado(rid, "aprobado", ed.text(), rr))
            b_re.clicked.connect(lambda _, rid=r["id"], ed=ed, rr=r: self._set_estado(rid, "rechazado", ed.text(), rr))
            lay = QHBoxLayout(); lay.addWidget(b_ap); lay.addWidget(b_re); lay.setContentsMargins(0,0,0,0)
            w = QWidget(); w.setLayout(lay)
            self.tbl.setCellWidget(i, 11, w)

    def _set_estado(self, actividad_id: int, estado: str, comentario: str, row: dict):
        try:
            ok = actualizar_estado_actividad(actividad_id, estado, self.supervisor_id, comentario or None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar:\n{e}")
            return

        if not ok:
            QMessageBox.warning(self, "Sin cambios", "La actividad no se actualizó (¿ya no está activa?).")
            return

        # Si aprobamos, generamos automáticamente el PDF de comprobante
        if estado == "aprobado":
            try:
                pdf_path = generar_pdf_actividad(
                    nombre_agricultor = row.get("agricultor") or str(row.get("agricultor_id")),
                    codigo_hectarea   = row.get("codigo_hectarea") or "-",
                    tipo              = row.get("tipo") or "",
                    fecha_hora        = row.get("fecha_hora"),
                    cantidad          = row.get("cantidad"),
                    unidad            = row.get("unidad"),
                    costo             = row.get("costo"),
                    notas             = row.get("notas"),
                    estado            = estado,
                    comentario_supervisor = comentario or "",
                    aptos             = row.get("aptos"),
                    no_aptos          = row.get("no_aptos"),
                    cajas             = row.get("cajas"),
                    kilos             = row.get("kilos"),
                )
                # abrir PDF
                self._open_file(pdf_path)
            except Exception as e:
                # No bloquea el flujo si falla el PDF
                QMessageBox.warning(self, "PDF", f"Actividad aprobada, pero hubo un problema al generar/abrir el PDF:\n{e}")

        QMessageBox.information(self, "OK", f"Actividad {estado}.")
        self._load()

    def _open_file(self, path: str):
        try:
            if os.name == "nt" and hasattr(os, "startfile"):
                os.startfile(path)  # Windows
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(path)))
        except Exception:
            pass
