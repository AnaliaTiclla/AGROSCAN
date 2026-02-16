import pyodbc
DATABASE = "AgroScanDB"

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=np:\\.\pipe\sql\query;"    # tubería de la instancia por defecto (MSSQLSERVER)
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "Encrypt=yes;TrustServerCertificate=yes;",
    autocommit=False
)
print("✅ Conexión OK por Named Pipes")
conn.close()



