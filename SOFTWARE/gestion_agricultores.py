from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QHBoxLayout, QHeaderView
)
from PyQt5.QtGui import QIcon, QColor, QFont
from PyQt5.QtCore import Qt
from database import obtener_agricultores, eliminar_agricultor
from gestion_reportes import GestionReportesWindow

class GestionAgricultoresWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestionar Agricultores")
        self.setGeometry(250, 150, 820, 410)
        self.setMinimumSize(680, 340)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        # Título elegante
        title = QLabel("GESTIÓN DE AGRICULTORES")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title.setStyleSheet("color: #386641; margin-bottom: 10px; margin-top: 8px;")
        layout.addWidget(title)

        self.tabla = QTableWidget()
        layout.addWidget(self.tabla)
        self.setLayout(layout)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet("""
            QTableWidget {
                background-color: #fafafa;
                alternate-background-color: #e8f6ef;
                border: 1px solid #b7b7b7;
                gridline-color: #b7b7b7;
            }
            QHeaderView::section {
                background: #6a994e;
                color: white;
                font-weight: bold;
                padding: 5px;
                border: 1px solid #b7b7b7;
            }
        """)
        self.cargar_agricultores()

    def cargar_agricultores(self):
        agricultores = obtener_agricultores()
        self.tabla.setRowCount(len(agricultores))
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["ID", "Usuario", "Correo", "Opciones"])

        # Ajustar columnas de forma proporcional
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        for i, (agri_id, username, email) in enumerate(agricultores):
            item_id = QTableWidgetItem(str(agri_id))
            item_id.setTextAlignment(Qt.AlignCenter)
            item_id.setFont(QFont("Segoe UI", 10))
            item_id.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            item_username = QTableWidgetItem(username)
            item_username.setTextAlignment(Qt.AlignCenter)
            item_username.setFont(QFont("Segoe UI", 10))
            item_username.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            item_email = QTableWidgetItem(email)
            item_email.setTextAlignment(Qt.AlignCenter)
            item_email.setFont(QFont("Segoe UI", 10))
            item_email.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            self.tabla.setItem(i, 0, item_id)
            self.tabla.setItem(i, 1, item_username)
            self.tabla.setItem(i, 2, item_email)

            # Opciones con botones estilizados y alineados horizontalmente
            cell_widget = QWidget()
            hbox = QHBoxLayout()
            hbox.setContentsMargins(2, 1, 2, 1)
            hbox.setSpacing(10)

            btn_reportes = QPushButton("Ver reportes")
            # Si quieres iconos, descomenta y agrega el archivo .png
            # btn_reportes.setIcon(QIcon("iconos/icon-report.png"))
            btn_reportes.setCursor(Qt.PointingHandCursor)
            btn_reportes.setStyleSheet("""
                QPushButton {
                    background-color: #f9c74f; 
                    border: 1px solid #d6ad39;
                    color: #333;
                    border-radius: 5px;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background-color: #fff3cd;
                }
            """)
            btn_reportes.clicked.connect(lambda _, uid=agri_id, uname=username: self.abrir_reportes(uid, uname))

            btn_eliminar = QPushButton("Eliminar")
            # btn_eliminar.setIcon(QIcon("iconos/icon-trash.png"))
            btn_eliminar.setCursor(Qt.PointingHandCursor)
            btn_eliminar.setStyleSheet("""
                QPushButton {
                    background-color: #ef233c;
                    color: white;
                    border: 1px solid #ba181b;
                    border-radius: 5px;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background-color: #ff7b7b;
                    color: #222;
                }
            """)
            btn_eliminar.clicked.connect(lambda _, uid=agri_id: self.eliminar_agricultor(uid))

            hbox.addWidget(btn_reportes)
            hbox.addWidget(btn_eliminar)
            hbox.setAlignment(Qt.AlignCenter)
            cell_widget.setLayout(hbox)
            self.tabla.setCellWidget(i, 3, cell_widget)

        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.horizontalHeader().setHighlightSections(False)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)

    def eliminar_agricultor(self, agricultor_id):
        resp = QMessageBox.question(self, "Confirmar", "¿Eliminar agricultor y todos sus reportes?", QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            eliminar_agricultor(agricultor_id)
            QMessageBox.information(self, "Listo", "Agricultor eliminado correctamente.")
            self.cargar_agricultores()

    def abrir_reportes(self, agricultor_id, username):
        self.rep_win = GestionReportesWindow(agricultor_id, username)
        self.rep_win.show()