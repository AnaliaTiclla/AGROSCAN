# DATA/db_pool.py
import time
import pyodbc
from DATA.db_config import build_conn_str

# Pooling global
pyodbc.pooling = True

_CONN_STR = build_conn_str()

def get_conn():
    """
    Obtiene conexión pyodbc (sin autocommit).
    Con pooling activado, abrir/cerrar es más barato (reduce latencia).
    """
    return pyodbc.connect(_CONN_STR, autocommit=False)

def get_conn_with_retry(retries: int = 2, delay_sec: float = 0.4):
    """
    Opcional: retry básico por fallos de red (útil en LAN / futuro cloud).
    """
    last_exc = None
    for _ in range(retries + 1):
        try:
            return get_conn()
        except Exception as e:
            last_exc = e
            time.sleep(delay_sec)
    raise last_exc
