from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QTabWidget
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
from UI.carga_agricultor import AnalisisChatWindow
from UI.historial_agricultor import HistorialReportesAgricultor
from UI.agricultor_dashboard import AgricultorDashboardWindow  # dashboard nuevo
# 👉 NUEVO: pestaña transaccional (registro de actividades)
from UI.operaciones_agricultor import OperacionesAgricultorWindow

BASE_STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QLabel#heading {
    font-size: 20px;
    font-weight: bold;
    color: #386641;
    margin-bottom: 22px;
    margin-top: 8px;
    qproperty-alignment: AlignCenter;
}
QPushButton {
    background-color: #a7c957;
    border: 1.5px solid #6a994e;
    color: #222;
    border-radius: 8px;
    padding: 9px 18px;
    font-size: 15px;
}
QPushButton:hover {
    background-color: #386641;
    color: white;
}
QPushButton:disabled {
    background-color: #e0e0e0;
    color: #888;
}
"""

class MainAgricultorWindow(QMainWindow):
    def __init__(self, user_id, username, parent_login_window=None):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.parent_login_window = parent_login_window
        self.setWindowTitle("AgroScan - Agricultor")
        self.setGeometry(160, 120, 950, 650)
        self.setStyleSheet(BASE_STYLESHEET)
        self.init_ui()

    def init_ui(self):
        # Tabs
        self.tabs = QTabWidget()

        # Tab Dashboard
        self.dashboard_tab = AgricultorDashboardWindow(self.user_id, self.username)
        self.tabs.addTab(self.dashboard_tab, QIcon("iconos/icon-dashboard.png"), "Dashboard")

        # Tab Análisis (IA)
        self.analisis_tab = AnalisisChatWindow(self.user_id, self.username)
        self.tabs.addTab(self.analisis_tab, QIcon("iconos/icon-image-add.png"), "Análisis")

        # Tab Historial (reportes PDF clásicos)
        self.historial_tab = HistorialReportesAgricultor(self.user_id)
        self.tabs.addTab(self.historial_tab, QIcon("iconos/icon-history.png"), "Historial")

        # 👉 NUEVA Tab Operaciones (módulo transaccional)
        self.operaciones_tab = OperacionesAgricultorWindow(self.user_id, self.username)
        # Si tienes un ícono, colócalo en iconos/icon-ops.png (opcional)
        self.tabs.addTab(self.operaciones_tab, QIcon("iconos/icon-ops.png"), "Operaciones")

        # Logout
        self.logout_btn = QPushButton("Cerrar sesión")
        self.logout_btn.setIcon(QIcon("iconos/icon-logout.png"))
        self.logout_btn.clicked.connect(self.logout)

        # Layout principal
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        lbl_heading = QLabel(f"Bienvenido, {self.username} (Agricultor)")
        lbl_heading.setObjectName("heading")
        lbl_heading.setAlignment(Qt.AlignCenter)

        layout.addWidget(lbl_heading)
        layout.addWidget(self.tabs)
        layout.addWidget(self.logout_btn, alignment=Qt.AlignRight)

        self.setCentralWidget(central_widget)

        # 👉 por defecto se abre el Dashboard
        self.tabs.setCurrentIndex(0)

        # ---------------------------
        # INTEGRACIÓN MÍNIMA (señales)
        # ---------------------------
        # Cuando el análisis registre sesión YOLO o guarde PDF clásico:
        if hasattr(self.analisis_tab, "data_changed"):
            self.analisis_tab.data_changed.connect(self.dashboard_tab.refresh)
            self.analisis_tab.data_changed.connect(self.historial_tab.cargar_reportes)

        # Cuando se registre una actividad manual en Operaciones:
        if hasattr(self.operaciones_tab, "data_changed"):
            self.operaciones_tab.data_changed.connect(self.dashboard_tab.refresh)

        # (Opcional) refrescar dashboard al volver a su pestaña
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, idx: int):
        # Si el usuario vuelve al dashboard, recarga para ver datos frescos
        if self.tabs.tabText(idx) == "Dashboard":
            if hasattr(self.dashboard_tab, "refresh"):
                self.dashboard_tab.refresh()

    def logout(self):
        self.close()
        if self.parent_login_window:
            self.parent_login_window.show()
