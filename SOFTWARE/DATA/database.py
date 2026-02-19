# database.py  -> proxy hacia SQL Server
# No cambies los imports en el resto de archivos: este módulo reexporta
# las mismas funciones que usabas en SQLite, pero ahora desde SQL Server.

from DATA.database_mssql import *  # noqa: F401,F403
