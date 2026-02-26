import os
import sys
import importlib
import pkgutil

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QComboBox, QHBoxLayout
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

# ✅ 1) FIJAR WORKDIR al folder del main.py (para que iconos/ y rutas funcionen en otra PC)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# ✅ 2) IMPORTS por carpetas (nuevo)
from DATA.database import registrar_usuario, login_usuario


BASE_STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QLabel#heading {
    font-size: 22px;
    font-weight: bold;
    color: #386641;
    margin-bottom: 18px;
    margin-top: 8px;
    qproperty-alignment: AlignCenter;
}
QPushButton {
    background-color: #a7c957;
    border: 1px solid #6a994e;
    color: #222;
    border-radius: 8px;
    padding: 7px 18px;
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
QLineEdit, QComboBox {
    padding: 7px;
    border-radius: 6px;
    border: 1px solid #b7b7b7;
    font-size: 13px;
    margin-bottom: 8px;
}
QComboBox {
    background: #f7ffe0;
}
"""


def precargar_modulos_ui():
    """
    ✅ Carga (importa) todos los módulos dentro de la carpeta UI/
    Esto evita que en otra PC tengas que "ejecutar uno por uno".
    No abre ventanas; solo deja todo importado/registrado.

    Si algún módulo UI falla por un import viejo, aquí te saldrá el error de una vez,
    y lo corriges rápido.
    """
    try:
        import UI  # paquete UI
        for module_info in pkgutil.iter_modules(UI.__path__):
            name = module_info.name
            # evita importar __init__ implícitos raros, y salta archivos que no quieres
            if name.startswith("_"):
                continue
            importlib.import_module(f"UI.{name}")
    except Exception as e:
        # No reventamos toda la app por esto, pero sí avisamos
        print(f"[WARN] No se pudo precargar UI completo: {e}")


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Iniciar sesión - AgroScan")
        self.setGeometry(200, 140, 390, 350)
        self.setStyleSheet(BASE_STYLESHEET)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        lbl_heading = QLabel("Iniciar Sesión en AgroScan")
        lbl_heading.setObjectName("heading")
        layout.addWidget(lbl_heading)

        self.email_label = QLabel("Correo electrónico:")
        self.email_input = QLineEdit()
        self.password_label = QLabel("Contraseña:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_btn = QPushButton("Iniciar sesión")
        self.login_btn.setIcon(QIcon(os.path.join("iconos", "icon-login.png")))

        self.register_btn = QPushButton("Crear cuenta")
        self.register_btn.setIcon(QIcon(os.path.join("iconos", "icon-user-plus.png")))

        layout.addWidget(self.email_label)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.login_btn)
        btn_row.addWidget(self.register_btn)
        layout.addLayout(btn_row)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        self.setLayout(layout)
        self.login_btn.clicked.connect(self.handle_login)
        self.register_btn.clicked.connect(self.open_register)

    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        if not email or not password:
            QMessageBox.warning(self, "Error", "Por favor ingresa correo y contraseña.")
            return

        ok, *result = login_usuario(email, password)
        if ok:
            iduser, username, rol = result

            if rol == "agricultor":
                # ✅ Import correcto desde UI
                from UI.agricultor import MainAgricultorWindow
                self.hide()
                self.main_window = MainAgricultorWindow(iduser, username, parent_login_window=self)
                self.main_window.show()
                QMessageBox.information(
                    self.main_window,
                    "Bienvenido",
                    f"Bienvenido {username}, tu rol es: agricultor en AgroScan."
                )

            elif rol == "supervisor":
                # ✅ Import correcto desde UI
                from UI.supervisor import MainSupervisorWindow
                self.hide()
                self.main_window = MainSupervisorWindow(iduser, username, parent_login_window=self)
                self.main_window.show()
                QMessageBox.information(
                    self.main_window,
                    "Bienvenido",
                    f"Bienvenido {username}, tu rol es: supervisor en AgroScan."
                )
            else:
                QMessageBox.critical(self, "Error", f"Rol desconocido: {rol}")
        else:
            QMessageBox.critical(self, "Error", result[0])

    def open_register(self):
        self.register_window = RegisterWindow(self)
        self.register_window.show()
        self.hide()


class RegisterWindow(QWidget):
    def __init__(self, login_window):
        super().__init__()
        self.login_window = login_window
        self.setWindowTitle("Registro - AgroScan")
        self.setGeometry(220, 140, 420, 440)
        self.setStyleSheet(BASE_STYLESHEET)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        lbl_heading = QLabel("Crear Nueva Cuenta en AgroScan")
        lbl_heading.setObjectName("heading")
        layout.addWidget(lbl_heading)

        self.username_label = QLabel("Nombre de usuario:")
        self.username_input = QLineEdit()
        self.email_label = QLabel("Correo electrónico:")
        self.email_input = QLineEdit()
        self.password_label = QLabel("Contraseña:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.repeat_label = QLabel("Repetir contraseña:")
        self.repeat_input = QLineEdit()
        self.repeat_input.setEchoMode(QLineEdit.Password)
        self.rol_label = QLabel("Selecciona el rol:")
        self.rol_combo = QComboBox()
        self.rol_combo.addItems(["agricultor", "supervisor"])

        self.register_btn = QPushButton("Registrar")
        self.register_btn.setIcon(QIcon(os.path.join("iconos", "icon-save.png")))

        self.back_btn = QPushButton("Volver a login")
        self.back_btn.setIcon(QIcon(os.path.join("iconos", "icon-back.png")))

        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.email_label)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.repeat_label)
        layout.addWidget(self.repeat_input)
        layout.addWidget(self.rol_label)
        layout.addWidget(self.rol_combo)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.register_btn)
        btn_row.addWidget(self.back_btn)
        layout.addLayout(btn_row)

        layout.setContentsMargins(32, 20, 32, 24)
        layout.setSpacing(10)

        self.setLayout(layout)
        self.register_btn.clicked.connect(self.handle_register)
        self.back_btn.clicked.connect(self.back_to_login)

    def handle_register(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        repeat = self.repeat_input.text().strip()
        rol = self.rol_combo.currentText()

        if not username or not email or not password or not repeat:
            QMessageBox.warning(self, "Error", "Completa todos los campos.")
            return
        if password != repeat:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            return

        ok, msg = registrar_usuario(username, email, password, rol)
        if ok:
            # Login automático tras registro exitoso
            ok_login, *result = login_usuario(email, password)
            if ok_login:
                iduser, username, rol_usuario = result

                if rol_usuario == "agricultor":
                    from UI.agricultor import MainAgricultorWindow
                    self.hide()
                    self.main_window = MainAgricultorWindow(iduser, username, parent_login_window=self.login_window)
                    self.main_window.show()
                    QMessageBox.information(
                        self.main_window,
                        "¡Bienvenido!",
                        f"Registro y acceso exitoso.\nBienvenido {username}, tu rol es: agricultor en AgroScan."
                    )

                elif rol_usuario == "supervisor":
                    from UI.supervisor import MainSupervisorWindow
                    self.hide()
                    self.main_window = MainSupervisorWindow(iduser, username, parent_login_window=self.login_window)
                    self.main_window.show()
                    QMessageBox.information(
                        self.main_window,
                        "¡Bienvenido!",
                        f"Registro y acceso exitoso.\nBienvenido {username}, tu rol es: supervisor en AgroScan."
                    )
            else:
                QMessageBox.warning(
                    self,
                    "Atención",
                    "Registrado pero error al ingresar automáticamente. Ingresa manualmente."
                )
                self.back_to_login()
        else:
            QMessageBox.critical(self, "Error", msg)

    def back_to_login(self):
        self.hide()
        self.login_window.show()


def main():
    # ✅ Precarga UI para que todo quede importado/registrado al iniciar
    precargar_modulos_ui()

    app = QApplication(sys.argv)
    login_win = LoginWindow()
    login_win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
