# database_mssql.py
# Backend SQL Server para AgroScan
# - Conexión por Named Pipes (MSSQLSERVER) con Windows Authentication
# - SELECT de reportes devuelve EXACTAMENTE 11 columnas en este orden:
#   id, usuario_id, fecha, planta, enfermedad, num_frutos, maduracion,
#   path_imagen, path_reporte, estado(TEXT), comentario_supervisor

import os
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pyodbc

# ========================
# Configuración de conexión
# ========================

DATABASE = os.getenv("MSSQL_DATABASE", "AgroScanDB")

# Opción A (la que ya te funciona): Named Pipes
CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ANALIA\\SQLEXPRESS;"
    "DATABASE=AgroScanDB;"
    "Trusted_Connection=yes;"
    "Encrypt=yes;TrustServerCertificate=yes;"
)


# Opción B (cuando habilites TCP/1433), descomenta y comenta la anterior:
# CONN_STR = (
#     "DRIVER={ODBC Driver 17 for SQL Server};"
#     "SERVER=tcp:DESKTOP-PA2JFUM,1433;"
#     f"DATABASE={DATABASE};"
#     "Trusted_Connection=yes;"
#     "Encrypt=yes;TrustServerCertificate=yes;"
# )

def _conn():
    """Obtiene conexión pyodbc (sin autocommit)."""
    return pyodbc.connect(CONN_STR, autocommit=False)

# ========================
# Utilidades
# ========================

def _sha256_hex(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()

def _one(cur, sql, params=()):
    """Devuelve una fila o None."""
    return cur.execute(sql, params).fetchone()

def _rows_to_dicts(cur) -> List[Dict]:
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

# ========================
# Funciones usadas por la app (existentes)
# ========================

def registrar_usuario(username: str, email: str, password: str, rol_texto: str):
    """
    Crea usuario. rol_texto debe existir en dbo.roles (agricultor/supervisor).
    Devuelve (True, msg) o (False, msg).
    """
    pw = _sha256_hex(password)
    try:
        with _conn() as c:
            cur = c.cursor()
            rol = _one(cur, "SELECT id FROM dbo.roles WHERE rol = ?", (rol_texto,))
            if not rol:
                return False, f"Rol inválido: {rol_texto}"

            cur.execute(
                """
                INSERT INTO dbo.usuarios (username, email, password_hash, rol_id, fecha_registro, is_active)
                VALUES (?, ?, ?, ?, SYSUTCDATETIME(), 1)
                """,
                (username, email, pw, rol.id),
            )
            c.commit()
        return True, "Usuario registrado exitosamente."
    except pyodbc.IntegrityError:
        return False, "Nombre de usuario o email ya existe."
    except Exception as e:
        return False, f"Error al registrar usuario: {e}"

def login_usuario(email: str, password: str):
    """
    Login por email + password (sha256 hex).
    Devuelve (True, id, username, rol_texto) o (False, msg).
    """
    pw = _sha256_hex(password)
    with _conn() as c:
        cur = c.cursor()
        row = _one(
            cur,
            "SELECT u.id, u.username, r.rol "
            "FROM dbo.usuarios u JOIN dbo.roles r ON r.id = u.rol_id "
            "WHERE u.email = ? AND u.password_hash = ? AND u.is_active = 1",
            (email, pw),
        )
    if row:
        return True, row.id, row.username, row.rol
    return False, "Credenciales incorrectas."

def guardar_reporte(
    usuario_id: int,
    planta: str,
    enfermedad: str,
    num_frutos: int,
    maduracion: str,
    path_imagen: str,
    path_reporte: str,
):
    """
    Inserta un reporte con estado 'pendiente'.
    """
    try:
        with _conn() as c:
            cur = c.cursor()
            estado_pend = _one(cur, "SELECT id FROM dbo.reporte_estados WHERE estado='pendiente'").id
            cur.execute(
                """
                INSERT INTO dbo.reportes
                (usuario_id, fecha, planta, enfermedad, num_frutos, maduracion,
                 path_imagen, path_reporte, estado_id, comentario_supervisor)
                VALUES (?, SYSUTCDATETIME(), ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (usuario_id, planta, enfermedad, num_frutos, maduracion, path_imagen, path_reporte, estado_pend),
            )
            c.commit()
        return True, "Reporte guardado correctamente."
    except Exception as e:
        return False, f"Error al guardar el reporte: {e}"

def listar_reportes(usuario_id: int | None = None, rol: str = "agricultor"):
    """
    Devuelve EXACTAMENTE 11 columnas en este orden:
    id, usuario_id, fecha, planta, enfermedad, num_frutos, maduracion,
    path_imagen, path_reporte, estado(TEXT), comentario_supervisor
    - Si rol == 'supervisor' o usuario_id es None: lista todos.
    - Si rol == 'agricultor': filtra por usuario_id.
    """
    sql_base = (
        "SELECT r.id, r.usuario_id, r.fecha, r.planta, r.enfermedad, r.num_frutos, r.maduracion, "
        "       r.path_imagen, r.path_reporte, e.estado, r.comentario_supervisor "
        "FROM dbo.reportes r "
        "JOIN dbo.reporte_estados e ON e.id = r.estado_id "
    )
    order = " ORDER BY r.fecha DESC"
    with _conn() as c:
        cur = c.cursor()
        if rol == "supervisor" or usuario_id is None:
            cur.execute(sql_base + order)
        else:
            cur.execute(sql_base + " WHERE r.usuario_id = ?" + order, (usuario_id,))
        filas = cur.fetchall()
        return [tuple(f) for f in filas]

def obtener_agricultores():
    """
    Devuelve lista de agricultores (id, username, email).
    """
    with _conn() as c:
        cur = c.cursor()
        rows = cur.execute(
            "SELECT id, username, email FROM dbo.usuarios "
            "WHERE rol_id = (SELECT id FROM dbo.roles WHERE rol='agricultor') "
            "ORDER BY username"
        ).fetchall()
        return [tuple(r) for r in rows]

def obtener_reportes_agricultor(agricultor_id: int):
    """
    Mismo formato de 11 columnas que listar_reportes, pero filtrado por usuario.
    """
    with _conn() as c:
        cur = c.cursor()
        rows = cur.execute(
            "SELECT r.id, r.usuario_id, r.fecha, r.planta, r.enfermedad, r.num_frutos, r.maduracion, "
            "       r.path_imagen, r.path_reporte, e.estado, r.comentario_supervisor "
            "FROM dbo.reportes r "
            "JOIN dbo.reporte_estados e ON e.id = r.estado_id "
            "WHERE r.usuario_id = ? "
            "ORDER BY r.fecha DESC",
            (agricultor_id,),
        ).fetchall()
        return [tuple(r) for r in rows]

def actualizar_estado_reporte(reporte_id: int, nuevo_estado: str, comentario_supervisor: str = ""):
    """
    Actualiza estado (texto) y comentario de un reporte.
    """
    with _conn() as c:
        cur = c.cursor()
        estado = _one(cur, "SELECT id FROM dbo.reporte_estados WHERE estado = ?", (nuevo_estado,))
        if not estado:
            return False
        cur.execute(
            "UPDATE dbo.reportes SET estado_id = ?, comentario_supervisor = ? WHERE id = ?",
            (estado.id, comentario_supervisor, reporte_id),
        )
        c.commit()
    return True

def eliminar_reporte(reporte_id: int, usuario_id: int):
    """
    Elimina un reporte SOLO si pertenece al usuario y está en estado 'pendiente'.
    Mantiene la lógica original de tu app.
    """
    with _conn() as c:
        cur = c.cursor()
        row = _one(
            cur,
            "SELECT r.id "
            "FROM dbo.reportes r "
            "JOIN dbo.reporte_estados e ON e.id = r.estado_id "
            "WHERE r.id = ? AND r.usuario_id = ? AND e.estado = 'pendiente'",
            (reporte_id, usuario_id),
        )
        if row:
            cur.execute("DELETE FROM dbo.reportes WHERE id = ? AND usuario_id = ?", (reporte_id, usuario_id))
            c.commit()
            return True
    return False

def eliminar_agricultor(agricultor_id: int):
    """
    Elimina un agricultor (ON DELETE CASCADE borra sus reportes).
    """
    with _conn() as c:
        cur = c.cursor()
        cur.execute(
            "DELETE FROM dbo.usuarios "
            "WHERE id = ? AND rol_id = (SELECT id FROM dbo.roles WHERE rol='agricultor')",
            (agricultor_id,),
        )
        c.commit()
    return True

# ========================
# NUEVO: Hectáreas, Asignaciones y Dashboards
# ========================

def hectareas_disponibles() -> List[Dict]:
    """Listado de hectáreas con su agricultor asignado (si lo hay)."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT h.id, h.codigo, h.nombre, h.activa,
                   ISNULL(a.agricultor_id, 0) AS agricultor_asignado
            FROM dbo.hectareas h
            LEFT JOIN (
                SELECT hectarea_id, agricultor_id
                FROM dbo.asignaciones
                WHERE activo=1
            ) a ON a.hectarea_id = h.id
            ORDER BY h.id;
        """)
        return _rows_to_dicts(cur)

def asignar_hectarea(agricultor_id: int, hectarea_id: int) -> bool:
    """
    Asigna una hectárea a un agricultor:
    - Cierra asignaciones activas previas (del agricultor o de la hectárea).
    - Crea una nueva asignación activa.
    """
    try:
        with _conn() as c:
            cur = c.cursor()
            cur.execute("""
                UPDATE dbo.asignaciones
                   SET activo=0, fin=CAST(SYSUTCDATETIME() AS DATE)
                 WHERE activo=1 AND (agricultor_id=? OR hectarea_id=?);
            """, (agricultor_id, hectarea_id))
            cur.execute("INSERT INTO dbo.asignaciones(agricultor_id, hectarea_id) VALUES (?,?);",
                        (agricultor_id, hectarea_id))
            c.commit()
        return True
    except Exception:
        return False

def hectarea_activa_de_agricultor(agricultor_id: int) -> Optional[Dict]:
    """Devuelve la hectárea activa (si existe) del agricultor."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT TOP 1 a.id AS asignacion_id, h.id AS hectarea_id, h.codigo, h.nombre
            FROM dbo.asignaciones a
            JOIN dbo.hectareas h ON h.id = a.hectarea_id
            WHERE a.activo=1 AND a.agricultor_id=?
            ORDER BY a.inicio DESC;
        """, (agricultor_id,))
        row = cur.fetchone()
        if row:
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))
    return None

def registrar_reporte_cosecha(agricultor_id: int, hectarea_id: int,
                              aptos: int, no_aptos: int, fuente: str="YOLO") -> Optional[int]:
    """
    Inserta una sesión de conteo (aptos/no aptos) para dashboards.
    Devuelve el id del registro insertado o None si falla.
    """
    try:
        with _conn() as c:
            cur = c.cursor()
            cur.execute("""
                INSERT INTO dbo.reporte_cosecha(agricultor_id, hectarea_id, aptos, no_aptos, fuente)
                OUTPUT INSERTED.id VALUES (?,?,?,?,?);
            """, (agricultor_id, hectarea_id, int(aptos), int(no_aptos), fuente))
            new_id = int(cur.fetchone()[0])
            c.commit()
            return new_id
    except Exception:
        return None

def dashboard_agricultor(agricultor_id: int,
                         date_from: Optional[str]=None,
                         date_to: Optional[str]=None) -> List[Dict]:
    """
    Lee la vista vw_dashboard_agricultor.
    date_from / date_to formato 'YYYY-MM-DD' (opcional).
    """
    with _conn() as c:
        cur = c.cursor()
        if date_from and date_to:
            cur.execute("""
                SELECT * FROM dbo.vw_dashboard_agricultor
                WHERE agricultor_id=? AND ultima_fecha BETWEEN ? AND ?
                ORDER BY hectarea_id;
            """, (agricultor_id, date_from, date_to))
        else:
            cur.execute("""
                SELECT * FROM dbo.vw_dashboard_agricultor
                WHERE agricultor_id=?
                ORDER BY hectarea_id;
            """, (agricultor_id,))
        return _rows_to_dicts(cur)

def dashboard_supervisor(date_from: Optional[str]=None,
                         date_to: Optional[str]=None) -> List[Dict]:
    """Lee la vista vw_dashboard_supervisor (resumen por hectárea)."""
    with _conn() as c:
        cur = c.cursor()
        if date_from and date_to:
            cur.execute("""
                SELECT * FROM dbo.vw_dashboard_supervisor
                WHERE ultima_fecha BETWEEN ? AND ?
                ORDER BY hectarea_id;
            """, (date_from, date_to))
        else:
            cur.execute("SELECT * FROM dbo.vw_dashboard_supervisor ORDER BY hectarea_id;")
        return _rows_to_dicts(cur)

# =========================================================
# NUEVO: Control de Cosecha (Transaccional - Actividad Campo)
#   -> Requiere los SPs: sp_RegistrarActividadCampo,
#                         sp_ListarActividadesAgricultor,
#                         sp_ListarActividadesSupervisor,
#                         sp_ActualizarEstadoActividad,
#                         sp_EliminarActividad
# =========================================================

def registrar_actividad_campo(agricultor_id: int, hectarea_id: int, tipo: str,
                              fecha_hora: datetime, cantidad=None, unidad: Optional[str]=None,
                              costo: float = 0.0, notas: Optional[str]=None,
                              aptos: Optional[int]=None, no_aptos: Optional[int]=None,
                              cajas=None, kilos=None) -> int:
    """
    Inserta una actividad (y si es 'cosecha', su detalle). Devuelve el id.
    """
    with _conn() as c:
        cur = c.cursor()
        cur.execute(
            "EXEC dbo.sp_RegistrarActividadCampo ?,?,?,?,?,?,?,?,?,?,?,?",
            (agricultor_id, hectarea_id, tipo, fecha_hora, cantidad, unidad,
             costo, notas, aptos, no_aptos, cajas, kilos)
        )
        row = cur.fetchone()
        c.commit()
        return int(row[0]) if row else 0

def listar_actividades_agricultor(agricultor_id: int,
                                  desde: Optional[datetime]=None,
                                  hasta: Optional[datetime]=None) -> List[Dict]:
    """Listado del agricultor (rango opcional)."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("EXEC dbo.sp_ListarActividadesAgricultor ?, ?, ?", (agricultor_id, desde, hasta))
        return _rows_to_dicts(cur)

def listar_actividades_supervisor(estado: Optional[str]=None,
                                  desde: Optional[datetime]=None,
                                  hasta: Optional[datetime]=None) -> List[Dict]:
    """Listado para supervisor (filtro por estado + rango)."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("EXEC dbo.sp_ListarActividadesSupervisor ?, ?, ?", (estado, desde, hasta))
        return _rows_to_dicts(cur)

def actualizar_estado_actividad(actividad_id: int, estado: str,
                                supervisor_id: int, comentario: Optional[str]=None) -> bool:
    """Aprueba/Rechaza/Pendiente + comentario. Devuelve True si actualizó."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("EXEC dbo.sp_ActualizarEstadoActividad ?, ?, ?, ?", (actividad_id, estado, supervisor_id, comentario))
        row = cur.fetchone()
        c.commit()
        rows_affected = int(row[0]) if row else 0
        return rows_affected > 0

def eliminar_actividad(actividad_id: int, agricultor_id: int) -> bool:
    """Borrado lógico por el agricultor si está 'pendiente'."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("EXEC dbo.sp_EliminarActividad ?, ?", (actividad_id, agricultor_id))
        row = cur.fetchone()
        c.commit()
        rows_affected = int(row[0]) if row else 0
        return rows_affected > 0

# ==============
# Prueba manual
# ==============
if __name__ == "__main__":
    # Smoke test de conexión
    with _conn() as c:
        print("Conectado a:", c.getinfo(pyodbc.SQL_SERVER_NAME))

    # Ejemplo de listado general (supervisor)
    rows = listar_reportes(usuario_id=None, rol="supervisor")
    print("Reportes (clásicos):", len(rows))

    # Hectáreas y dashboards
    print("Hectáreas:", hectareas_disponibles())
    print("Hectárea activa agricultor 2:", hectarea_activa_de_agricultor(2))
    print("Dashboard agricultor 2:", dashboard_agricultor(2))
    print("Dashboard supervisor:", dashboard_supervisor())

    # Transaccional (sanity quick)
    # print("Actividades agri2:", listar_actividades_agricultor(2))

