# supervisor.py — Ventana principal del Supervisor con pestañas
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QTabWidget
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from supervisor_dashboard import SupervisorDashboardWindow
from gestion_agricultores import GestionAgricultoresWindow  # pestaña de gestión de usuarios/agricultores
# 👉 NUEVO: pestaña de gestión de actividades (aprobar/rechazar + PDF)
from gestion_actividades import GestionActividadesWindow

BASE_STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
}
QLabel#heading {
    font-size: 21px;
    font-weight: bold;
    color: #386641;
    margin-bottom: 12px;
    margin-top: 8px;
    qproperty-alignment: AlignCenter;
}
QPushButton {
    background-color: #a7c957;
    border: 1.5px solid #6a994e;
    color: #222;
    border-radius: 8px;
    padding: 10px 22px;
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

class MainSupervisorWindow(QMainWindow):
    def __init__(self, user_id, username, parent_login_window=None):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.parent_login_window = parent_login_window
        self.setWindowTitle("AgroScan - Supervisor")
        self.setGeometry(150, 100, 1100, 740)  # tamaño amplio para dashboard
        self.setStyleSheet(BASE_STYLESHEET)
        self._build_ui()

    def _build_ui(self):
        # Tabs
        self.tabs = QTabWidget()

        # Pestaña 1: Dashboard (ve las 5 hectáreas)
        # Nota: pasamos también el supervisor_id para usar el botón "Gestión de Actividades" interno, si lo usas.
        self.tab_dashboard = SupervisorDashboardWindow(self.username, self.user_id)
        self.tabs.addTab(self.tab_dashboard, QIcon("iconos/icon-dashboard.png"), "Dashboard")

        # Pestaña 2: Gestión de Agricultores
        # (Asumo que esta clase es QWidget en tu proyecto)
        self.tab_gestion = GestionAgricultoresWindow()
        self.tabs.addTab(self.tab_gestion, QIcon("iconos/icon-users.png"), "Gestión")

        # 👉 Pestaña 3: Actividades (transaccional)
        self.tab_actividades = GestionActividadesWindow(self.user_id, self.username)
        # Si tienes un icono, colócalo en iconos/icon-activities.png
        self.tabs.addTab(self.tab_actividades, QIcon("iconos/icon-activities.png"), "Actividades")

        # Botón de logout
        self.logout_btn = QPushButton("Cerrar sesión")
        self.logout_btn.setIcon(QIcon("iconos/icon-logout.png"))
        self.logout_btn.clicked.connect(self.logout)

        # Layout principal
        central = QWidget()
        lay = QVBoxLayout(central)

        lbl = QLabel(f"Bienvenido, {self.username} (Supervisor)")
        lbl.setObjectName("heading")
        lbl.setAlignment(Qt.AlignCenter)

        lay.addWidget(lbl)
        lay.addWidget(self.tabs)
        lay.addWidget(self.logout_btn, alignment=Qt.AlignRight)

        self.setCentralWidget(central)

        # Dashboard por defecto
        self.tabs.setCurrentIndex(0)

        # Refrescar dashboard cuando el usuario vuelva a esa pestaña
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # 🔗 Integración mínima: si en "Actividades" hay cambios (aprobar/rechazar),
        # refrescamos automáticamente el dashboard
        if hasattr(self.tab_actividades, "data_changed"):
            self.tab_actividades.data_changed.connect(self.tab_dashboard.refrescar_dashboard)

    def _on_tab_changed(self, idx: int):
        # Si volvemos al dashboard, refrescamos datos
        if self.tabs.widget(idx) is self.tab_dashboard:
            try:
                # usa el método público de refresh del dashboard
                self.tab_dashboard.refrescar_dashboard()
            except Exception:
                pass

    def logout(self):
        self.close()
        if self.parent_login_window:
            self.parent_login_window.show()
