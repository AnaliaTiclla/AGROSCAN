import sqlite3, pyodbc
from datetime import datetime

# --- Origen (SQLite) ---
SQLITE = "agroassistant.db"

# --- Destino (SQL Server por Named Pipes) ---
CONN_MSSQL = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=np:\\.\pipe\sql\query;"   # instancia por defecto (MSSQLSERVER) por Named Pipes
    "DATABASE=AgroScanDB;"
    "Trusted_Connection=yes;"
    "Encrypt=yes;TrustServerCertificate=yes;"
)

def parse_dt(text):
    if not text:
        return datetime.utcnow()
    text = text.replace("T", " ")
    # Acepta 'YYYY-MM-DD HH:MM:SS'
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")

# 1) Lee datos de SQLite
sconn = sqlite3.connect(SQLITE)
sconn.row_factory = sqlite3.Row
scur = sconn.cursor()

usuarios = scur.execute(
    "SELECT id, username, email, password_hash, rol, fecha_registro FROM usuarios"
).fetchall()

reportes = scur.execute(
    """SELECT id, usuario_id, fecha, planta, enfermedad, num_frutos, maduracion,
              path_imagen, path_reporte, estado, comentario_supervisor
       FROM reportes"""
).fetchall()

# 2) Conecta a SQL Server
mconn = pyodbc.connect(CONN_MSSQL, autocommit=False)
mcur  = mconn.cursor()

# 2.1) Mapas de catálogos
rol_map    = {r.rol: r.id for r in mcur.execute("SELECT id, rol FROM dbo.roles")}
estado_map = {e.estado: e.id for e in mcur.execute("SELECT id, estado FROM dbo.reporte_estados")}

# 3) Migra usuarios (conservar IDs)
mcur.execute("SET IDENTITY_INSERT dbo.usuarios ON;")
for u in usuarios:
    rol_id = rol_map.get(u["rol"], rol_map["agricultor"])
    f = parse_dt(u["fecha_registro"])
    mcur.execute("""
        INSERT INTO dbo.usuarios
          (id, username, email, password_hash, rol_id, fecha_registro, is_active, created_at, updated_at)
        VALUES (?,  ?,        ?,     ?,            ?,      ?,             1,        SYSUTCDATETIME(), SYSUTCDATETIME())
    """, (u["id"], u["username"], u["email"], u["password_hash"], rol_id, f))
mcur.execute("SET IDENTITY_INSERT dbo.usuarios OFF;")

# 4) Migra reportes (conservar IDs)
mcur.execute("SET IDENTITY_INSERT dbo.reportes ON;")
for r in reportes:
    f = parse_dt(r["fecha"])
    estado_id = estado_map.get(r["estado"], estado_map["pendiente"])
    mcur.execute("""
        INSERT INTO dbo.reportes
          (id, usuario_id, fecha, planta, enfermedad, num_frutos, maduracion,
           path_imagen, path_reporte, estado_id, comentario_supervisor,
           created_at, updated_at)
        VALUES (?,  ?,          ?,     ?,      ?,          ?,         ?,
                ?,           ?,           ?,         ?,
                SYSUTCDATETIME(), SYSUTCDATETIME())
    """, (r["id"], r["usuario_id"], f, r["planta"], r["enfermedad"], r["num_frutos"], r["maduracion"],
          r["path_imagen"], r["path_reporte"], estado_id, r["comentario_supervisor"]))
mcur.execute("SET IDENTITY_INSERT dbo.reportes OFF;")

mconn.commit()
mconn.close()
sconn.close()
print("✅ Migración completada por Named Pipes.")

