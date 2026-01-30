# operaciones_agricultor.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QComboBox,
    QDateTimeEdit, QDoubleSpinBox, QSpinBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt, QDateTime
from database import (
    hectarea_activa_de_agricultor,
    registrar_actividad_campo, listar_actividades_agricultor, eliminar_actividad
)

BASE_STYLESHEET = """
QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
QLabel#title { font-size: 18px; font-weight: 700; color: #386641; }
QPushButton { background: #a7c957; border: 1.5px solid #6a994e; color: #222; border-radius: 8px; padding: 6px 12px; }
QPushButton:hover { background: #386641; color: #fff; }
"""

class OperacionesAgricultorWindow(QWidget):
    def __init__(self, agricultor_id: int, nombre_usuario: str):
        super().__init__()
        self.agricultor_id = agricultor_id
        self.nombre = nombre_usuario
        self.setStyleSheet(BASE_STYLESHEET)
        self._build_ui()
        self._load_table()

    def _build_ui(self):
        root = QVBoxLayout()
        title = QLabel("Operaciones de Campo"); title.setObjectName("title"); title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        # --- Formulario ---
        form = QHBoxLayout()
        self.cmb_tipo = QComboBox(); self.cmb_tipo.addItems(["siembra","riego","fumigacion","cosecha","otros"])
        self.dt = QDateTimeEdit(QDateTime.currentDateTime()); self.dt.setCalendarPopup(True); self.dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.sp_cant = QDoubleSpinBox(); self.sp_cant.setRange(0, 1e9); self.sp_cant.setDecimals(2)
        self.txt_unid = QLineEdit(); self.txt_unid.setPlaceholderText("kg / cajas / lts …")
        self.sp_costo = QDoubleSpinBox(); self.sp_costo.setRange(0, 1e9); self.sp_costo.setDecimals(2)
        self.txt_notas = QLineEdit()

        # campos de cosecha
        self.sp_aptos = QSpinBox(); self.sp_aptos.setRange(0, 10**7)
        self.sp_noapt = QSpinBox(); self.sp_noapt.setRange(0, 10**7)

        def add(lbl, w):
            box = QVBoxLayout(); l = QLabel(lbl); box.addWidget(l); box.addWidget(w); form.addLayout(box)

        add("Tipo", self.cmb_tipo)
        add("Fecha/Hora", self.dt)
        add("Cantidad", self.sp_cant)
        add("Unidad", self.txt_unid)
        add("Costo", self.sp_costo)
        add("Notas", self.txt_notas)
        add("Aptos (solo cosecha)", self.sp_aptos)
        add("No aptos (solo cosecha)", self.sp_noapt)

        self.btn_guardar = QPushButton("Registrar"); self.btn_guardar.clicked.connect(self._guardar)
        self.btn_refrescar = QPushButton("Refrescar"); self.btn_refrescar.clicked.connect(self._load_table)
        form.addWidget(self.btn_guardar); form.addWidget(self.btn_refrescar)
        root.addLayout(form)

        # --- Tabla ---
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(["ID","Fecha","Hectárea","Tipo","Cantidad","Unidad","Costo","Aptos","No aptos","Estado"])
        h = self.table.horizontalHeader()
        for i in range(10): h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table)
        self.setLayout(root)

        self.cmb_tipo.currentTextChanged.connect(self._toggle_cosecha)
        self._toggle_cosecha(self.cmb_tipo.currentText())

    def _toggle_cosecha(self, tipo):
        is_cosecha = (tipo == "cosecha")
        self.sp_aptos.setEnabled(is_cosecha)
        self.sp_noapt.setEnabled(is_cosecha)

    def _guardar(self):
        asig = hectarea_activa_de_agricultor(self.agricultor_id)
        if not asig:
            QMessageBox.warning(self, "Hectárea", "No tienes una hectárea asignada.")
            return
        hect_id = asig["hectarea_id"]

        tipo = self.cmb_tipo.currentText()
        try:
            new_id = registrar_actividad_campo(
                agricultor_id=self.agricultor_id, hectarea_id=hect_id, tipo=tipo,
                fecha_hora=self.dt.dateTime().toPyDateTime(),
                cantidad=float(self.sp_cant.value()) if self.sp_cant.value() else None,
                unidad=self.txt_unid.text().strip() or None,
                costo=float(self.sp_costo.value()) if self.sp_costo.value() else 0.0,
                notas=self.txt_notas.text().strip() or None,
                aptos=int(self.sp_aptos.value()) if tipo=="cosecha" else None,
                no_aptos=int(self.sp_noapt.value()) if tipo=="cosecha" else None
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar la actividad:\n{e}")
            return

        if new_id:
            QMessageBox.information(self, "OK", f"Actividad registrada (id={new_id}).")
            self._load_table()
        else:
            QMessageBox.warning(self, "Atención", "No se registró la actividad.")

    def _load_table(self):
        # rango amplio por defecto (último mes)
        desde = QDateTime.currentDateTime().addMonths(-1).toPyDateTime().replace(hour=0, minute=0, second=0)
        hasta = QDateTime.currentDateTime().toPyDateTime().replace(hour=23, minute=59, second=59)
        rows = listar_actividades_agricultor(self.agricultor_id, desde, hasta)

        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            cells = [
                str(r.get("id")),
                str(r.get("fecha_hora")),
                str(r.get("codigo_hectarea") or "-"),
                str(r.get("tipo")),
                str(r.get("cantidad") or ""),
                str(r.get("unidad") or ""),
                str(r.get("costo") or ""),
                str(r.get("aptos") or ""),
                str(r.get("no_aptos") or ""),
                str(r.get("estado")),
            ]
            for j, txt in enumerate(cells):
                it = QTableWidgetItem(txt); it.setTextAlignment(Qt.AlignCenter); self.table.setItem(i, j, it)
