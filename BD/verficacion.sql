/* ============================
   Verificación base existente
   ============================ */
SELECT COUNT(*) AS usuarios FROM dbo.usuarios;
SELECT COUNT(*) AS reportes  FROM dbo.reportes;

SELECT TOP 5 * FROM dbo.usuarios  ORDER BY id;
SELECT TOP 5 * FROM dbo.reportes  ORDER BY id;

-- Ver 5 hectáreas
SELECT * FROM dbo.hectareas;
GO

/* ============================================
   (Opcional) Asignar H1 al agricultor id = 2
   ============================================ */
UPDATE dbo.asignaciones
   SET activo = 0,
       fin    = CAST(SYSUTCDATETIME() AS DATE)
 WHERE hectarea_id = 1
   AND activo = 1;

INSERT INTO dbo.asignaciones(agricultor_id, hectarea_id)
VALUES (2, 1);   -- ajusta si es otro agricultor
GO

/* ====================================================
   Simular 2 sesiones (aptos/no aptos) en reporte_cosecha
   (dos INSERTs separados para máxima compatibilidad)
   ==================================================== */
INSERT INTO dbo.reporte_cosecha(agricultor_id, hectarea_id, aptos, no_aptos)
VALUES (2, 1, 120, 25);

INSERT INTO dbo.reporte_cosecha(agricultor_id, hectarea_id, aptos, no_aptos)
VALUES (2, 1, 140, 15);
GO

-- Dashboards base
SELECT * FROM dbo.vw_dashboard_agricultor WHERE agricultor_id = 2;   -- ajusta si corresponde
SELECT * FROM dbo.vw_dashboard_supervisor;
SELECT * FROM dbo.vw_hectareas_asignadas;
GO


/* ==========================================
   Pruebas del MÓDULO TRANSACCIONAL (nuevo)
   ========================================== */

-- Parámetros de prueba
DECLARE @agri INT = 2;  -- ajusta a un agricultor real
DECLARE @hect INT = 1;  -- H1 (ajusta si es otra)

-- 1) Crear actividad de COSECHA (queda en 'pendiente')
EXEC dbo.sp_RegistrarActividadCampo
     @agricultor_id = @agri,
     @hectarea_id   = @hect,
     @tipo          = 'cosecha',
     @fecha_hora    = GETDATE(),
     @cantidad      = 100,
     @unidad        = N'kg',
     @costo         = 0,
     @notas         = N'Prueba transaccional',
     @aptos         = 80,
     @no_aptos      = 20,
     @cajas         = 10,
     @kilos         = 100;
GO

-- 2) Listar actividades del agricultor (debe verse la nueva en 'pendiente')
EXEC dbo.sp_ListarActividadesAgricultor
     @agricultor_id = @agri;
GO

-- (Opcional) Inspección directa
SELECT TOP 5 *
  FROM dbo.actividad_campo
 WHERE agricultor_id = @agri
 ORDER BY id DESC;

SELECT TOP 5 *
  FROM dbo.cosecha_detalle
 WHERE actividad_id IN (
       SELECT TOP 5 id
         FROM dbo.actividad_campo
        WHERE agricultor_id = @agri
        ORDER BY id DESC
 );
GO

-- 3) Aprobar la ÚLTIMA actividad creada (dispara trigger hacia reporte_cosecha)
DECLARE @id INT;
SELECT TOP 1 @id = ac.id
  FROM dbo.actividad_campo ac
 WHERE ac.agricultor_id = @agri
   AND ac.activo = 1
 ORDER BY ac.id DESC;

EXEC dbo.sp_ActualizarEstadoActividad
     @actividad_id  = @id,
     @estado        = 'aprobado',
     @supervisor_id = 1,
     @comentario    = N'OK';
GO

-- 4) Ver dashboards (deben reflejar el nuevo registro del día vía trigger)
SELECT * FROM dbo.vw_dashboard_agricultor WHERE agricultor_id = @agri;
SELECT * FROM dbo.vw_dashboard_supervisor;

-- (Opcional) Ver el asiento que se generó en reporte_cosecha
SELECT TOP 5 *
  FROM dbo.reporte_cosecha
 WHERE agricultor_id = @agri
 ORDER BY ts DESC;
GO

