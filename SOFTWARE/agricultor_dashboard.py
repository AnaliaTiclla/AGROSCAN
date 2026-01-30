# agricultor_dashboard.py — Dashboard del Agricultor
# Muestra resumen de sesiones registradas (vw_dashboard_agricultor en BD)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QDateEdit, QPushButton, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QIcon
from database import dashboard_agricultor
# Matplotlib embebido en PyQt5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

BASE_STYLESHEET = """
QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
QLabel#title { font-size: 20px; font-weight: 700; color: #386641; }
QFrame#kpi { background: #f6fff7; border: 1px solid #d2e59e; border-radius: 10px; padding: 12px; }
QLabel.kpilabel { color: #6a994e; font-weight: 600; }
QLabel.kpinum { font-size: 18px; font-weight: 700; color: #1b5e20; }
QPushButton { background: #a7c957; border: 1.5px solid #6a994e; color: #222; border-radius: 8px; padding: 8px 14px; }
QPushButton:hover { background: #386641; color: #fff; }
"""

class AgricultorDashboardWindow(QWidget):
    def __init__(self, agricultor_id: int, nombre_usuario: str):
        super().__init__()
        self.agricultor_id = agricultor_id
        self.nombre_usuario = nombre_usuario
        self.setStyleSheet(BASE_STYLESHEET)

        self._build_ui()
        self.refrescar_dashboard()  # carga inicial

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout()
        title = QLabel(f"Dashboard del Agricultor — {self.nombre_usuario}")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        root.addWidget(title)

        # Filtros de fecha
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Desde:"))
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("dd/MM/yyyy")
        self.dt_from.setDate(QDate.currentDate().addMonths(-1))
        filter_bar.addWidget(self.dt_from)

        filter_bar.addWidget(QLabel("Hasta:"))
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("dd/MM/yyyy")
        self.dt_to.setDate(QDate.currentDate())
        filter_bar.addWidget(self.dt_to)

        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.setIcon(QIcon("iconos/icon-refresh.png"))
        self.btn_refresh.clicked.connect(self._on_refresh)
        filter_bar.addStretch(1)
        filter_bar.addWidget(self.btn_refresh)
        root.addLayout(filter_bar)

        # KPIs
        kpi_bar = QHBoxLayout()
        self.card_aptos = self._make_kpi("Aptos", "0")
        self.card_noapt = self._make_kpi("No aptos", "0")
        self.card_pct   = self._make_kpi("% Aprobación", "0%")
        kpi_bar.addWidget(self.card_aptos)
        kpi_bar.addWidget(self.card_noapt)
        kpi_bar.addWidget(self.card_pct)
        root.addLayout(kpi_bar)

        # Tabla
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Hectárea", "Código", "Aptos", "No aptos", "Total", "% Aprob."
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table)

        # Gráfico (matplotlib)
        self.figure = Figure(figsize=(6, 3))
        self.canvas = FigureCanvas(self.figure)
        root.addWidget(self.canvas)

        self.setLayout(root)

        # Auto-refresh al cambiar fechas
        self.dt_from.dateChanged.connect(self._on_refresh)
        self.dt_to.dateChanged.connect(self._on_refresh)

    def _make_kpi(self, label: str, num: str) -> QFrame:
        card = QFrame()
        card.setObjectName("kpi")
        v = QVBoxLayout(card)
        l1 = QLabel(label); l1.setProperty("class", "kpilabel")
        l2 = QLabel(num);   l2.setProperty("class", "kpinum")
        v.addWidget(l1); v.addWidget(l2)
        v.setContentsMargins(12, 8, 12, 8)
        card._num = l2  # guardamos referencia
        return card

    # ---------------- HELPERS ----------------
    def _range_strings_inclusive(self):
        """Devuelve (desde_str, hasta_str) con horas inclusivas."""
        d1 = self.dt_from.date().toString("yyyy-MM-dd")
        d2 = self.dt_to.date().toString("yyyy-MM-dd")
        return f"{d1} 00:00:00", f"{d2} 23:59:59"

    def _center_item(self, txt):
        it = QTableWidgetItem(txt)
        it.setTextAlignment(Qt.AlignCenter)
        return it

    # ---------------- DATA ----------------
    def _on_refresh(self):
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Actualizando…")
        try:
            self.refrescar_dashboard()
            self.btn_refresh.setText("Actualizado ✓")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar el dashboard:\n{e}")
            self.btn_refresh.setText("Actualizar")
        finally:
            self.btn_refresh.setEnabled(True)

    def refrescar_dashboard(self):
        """Público: para llamarlo desde otras pestañas tras guardar."""
        desde_str, hasta_str = self._range_strings_inclusive()

        # Consulta a BD (espera rango inclusivo)
        rows = dashboard_agricultor(self.agricultor_id, desde_str, hasta_str)

        # KPIs globales
        total_aptos = sum(int(r.get("total_aptos") or 0) for r in rows)
        total_no    = sum(int(r.get("total_no_aptos") or 0) for r in rows)
        total       = total_aptos + total_no
        pct         = round((total_aptos / total) * 100, 2) if total else 0.0

        self.card_aptos._num.setText(str(total_aptos))
        self.card_noapt._num.setText(str(total_no))
        self.card_pct._num.setText(f"{pct}%")

        # Tabla
        self._fill_table(rows)

        # Gráfico
        self._plot_bars(rows)

    def _fill_table(self, rows):
        self.table.setSortingEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            hect = r.get("nombre_hectarea") or "-"
            code = r.get("codigo_hectarea") or "-"
            apt  = int(r.get("total_aptos") or 0)
            noap = int(r.get("total_no_aptos") or 0)
            tot  = int(r.get("total_registrados") or (apt + noap))
            pct  = r.get("pct_aptos")
            if pct is None:
                pct = round((apt / tot) * 100, 2) if tot else 0.0

            self.table.setItem(i, 0, self._center_item(str(hect)))
            self.table.setItem(i, 1, self._center_item(str(code)))
            self.table.setItem(i, 2, self._center_item(str(apt)))
            self.table.setItem(i, 3, self._center_item(str(noap)))
            self.table.setItem(i, 4, self._center_item(str(tot)))
            self.table.setItem(i, 5, self._center_item(f"{pct}%"))

        self.table.setSortingEnabled(True)
        # Ordena por % Aprob. desc al refrescar (opcional)
        # self.table.sortItems(5, Qt.DescendingOrder)

    def _plot_bars(self, rows):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        labels = [r.get("codigo_hectarea") or "" for r in rows] or ["Sin datos"]
        aptos  = [int(r.get("total_aptos") or 0) for r in rows] or [0]
        noapt  = [int(r.get("total_no_aptos") or 0) for r in rows] or [0]

        x = range(len(labels))
        width = 0.4

        ax.bar([i - width/2 for i in x], aptos, width, label="Aptos")
        ax.bar([i + width/2 for i in x], noapt, width, label="No aptos")

        ax.set_title("Aptos vs No aptos por Hectárea")
        ax.set_xlabel("Hectárea")
        ax.set_ylabel("Conteo")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels)
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.4)

        self.canvas.draw()
