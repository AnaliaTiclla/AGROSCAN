
PRINT '==== 1️ Verificar actividades de prueba insertadas ====';

SELECT id, agricultor_id, hectarea_id, tipo, cantidad, unidad, estado, notas
FROM dbo.actividad_campo
WHERE notas LIKE N'Carga de prueba hectárea %'
ORDER BY agricultor_id, hectarea_id;

PRINT '==== 2️ Insertar (backfill) en reporte_cosecha si no existe ====';

INSERT INTO dbo.reporte_cosecha (agricultor_id, hectarea_id, ts, aptos, no_aptos, fuente)
SELECT ac.agricultor_id,
       ac.hectarea_id,
       ac.fecha_hora,
       ISNULL(cd.aptos,0) AS aptos,
       ISNULL(cd.no_aptos,0) AS no_aptos,
       N'BACKFILL'
FROM dbo.actividad_campo ac
LEFT JOIN dbo.cosecha_detalle cd ON cd.actividad_id = ac.id
WHERE ac.notas LIKE N'Carga de prueba hectárea %'
  AND ac.tipo = 'cosecha'
  AND ac.estado = 'aprobado'
  AND NOT EXISTS (
        SELECT 1 FROM dbo.reporte_cosecha rc
        WHERE rc.agricultor_id = ac.agricultor_id
          AND rc.hectarea_id = ac.hectarea_id
          AND CAST(rc.ts AS DATE) = CAST(ac.fecha_hora AS DATE)
     );

PRINT '==== 3️ Revisar los datos insertados en reporte_cosecha ====';

SELECT agricultor_id, hectarea_id, aptos, no_aptos, ts
FROM dbo.reporte_cosecha
WHERE fuente = N'BACKFILL'
ORDER BY agricultor_id, hectarea_id;

PRINT '==== Backfill completado correctamente ====';

GO
