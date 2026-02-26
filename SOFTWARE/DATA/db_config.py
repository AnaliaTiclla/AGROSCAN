# DATA/db_config.py
import os

def build_conn_str() -> str:
    """
    Modos:
      - MSSQL_MODE=LOCAL_NP -> Named Pipes (solo local)
      - MSSQL_MODE=TCP      -> TCP (LAN o cloud)
    Auth:
      - MSSQL_AUTH=trusted  -> Windows Auth
      - MSSQL_AUTH=sql      -> Usuario/Password
    """
    mode = os.getenv("MSSQL_MODE", "LOCAL_NP").upper()
    auth = os.getenv("MSSQL_AUTH", "trusted").lower()

    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
    database = os.getenv("MSSQL_DATABASE", "AgroScanDB")

    encrypt = os.getenv("MSSQL_ENCRYPT", "yes")
    trust_cert = os.getenv("MSSQL_TRUST_CERT", "yes")  # dev: yes | prod: no
    timeout = os.getenv("MSSQL_TIMEOUT", "15")

    parts = [
        f"DRIVER={{{driver}}};",
        f"DATABASE={database};",
        f"Encrypt={encrypt};",
        f"TrustServerCertificate={trust_cert};",
        f"Connection Timeout={timeout};",
    ]

    if mode == "LOCAL_NP":
        local_server = os.getenv("MSSQL_SERVER", r".\SQLEXPRESS")
        parts.insert(1, f"SERVER={local_server};")
        parts.append("Trusted_Connection=yes;")
        return "".join(parts)

    server = os.getenv("MSSQL_SERVER", "localhost")
    port = os.getenv("MSSQL_PORT", "1433")
    parts.insert(1, f"SERVER=tcp:{server},{port};")

    if auth == "trusted":
        parts.append("Trusted_Connection=yes;")
    else:
        user = os.getenv("MSSQL_USER", "")
        pwd = os.getenv("MSSQL_PASSWORD", "")
        parts.append(f"UID={user};PWD={pwd};")

    return "".join(parts)
