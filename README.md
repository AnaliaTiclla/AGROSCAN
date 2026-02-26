Cambios Implementados – E004 y E005
Esta rama introduce mejoras en el acceso a la base de datos del sistema AgroScan, alineadas con el Plan de Mantenimiento definido en la Fase 2 del proyecto.

Problemas Detectados:
  E004: Sobrecarga por múltiples conexiones a BD
  E005: Configuración ineficiente del acceso a datos

Solución Aplicada
1. Implementación de Pool de Conexiones (E004)
  Se agregó el archivo:
    DATA/db_pool.py     #Este módulo permite reutilizar conexiones existentes en lugar de crear una nueva en cada operación.

Beneficios:
Reduce latencia
Mejora rendimiento
Previene saturación del motor SQL

La función principal:
  def get_conn()       #Obtiene conexiones desde el pool en lugar de abrir nuevas constantemente.

  Además, se incluye:
  def get_conn_with_retry()     #Prepara al sistema para futuros escenarios de red o nube.

2. Migración a Connection String Centralizado (E005)
  Se agregó el archivo:
    DATA/db_config.py      #Este módulo construye dinámicamente la cadena de conexión según el entorno.

Permite:
Conexión local
Conexión por red (LAN)
Preparación para entorno cloud

Ejemplo de lógica:
MSSQL_MODE=LOCAL_NP -> conexión local
MSSQL_MODE=TCP      -> conexión LAN o cloud
Esto elimina configuraciones rígidas y mejora la flexibilidad del sistema.

3. Integración con el Backend de Datos
  El archivo:
    database_mssql.py

Fue actualizado para utilizar el nuevo sistema de conexiones:  
from DATA.db_pool import get_conn
Esto desacopla la lógica de negocio de la configuración de conexión.

