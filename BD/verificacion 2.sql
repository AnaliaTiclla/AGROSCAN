USE AgroScanDB;
GO

PRINT '==== Restaurando registros de H1, H3, H4 y H5 para agricultor_id = 1 ====';

INSERT INTO dbo.reporte_cosecha (agricultor_id, hectarea_id, ts, aptos, no_aptos, fuente)
SELECT ac.agricultor_id,
       ac.hectarea_id,
       ac.fecha_hora,
       ISNULL(cd.aptos,0),
       ISNULL(cd.no_aptos,0),
       N'RESTAURACION'
FROM dbo.actividad_campo ac
LEFT JOIN dbo.cosecha_detalle cd 
       ON cd.actividad_id = ac.id
WHERE ac.agricultor_id = 1
  AND ac.tipo = 'cosecha'
  AND ac.estado = 'aprobado'
  AND ac.hectarea_id IN (
      SELECT id FROM dbo.hectareas 
      WHERE codigo IN ('H1','H3','H4','H5')
  )
  AND NOT EXISTS (
      SELECT 1 FROM dbo.reporte_cosecha rc
      WHERE rc.agricultor_id = ac.agricultor_id
        AND rc.hectarea_id = ac.hectarea_id
        AND CAST(rc.ts AS DATE) = CAST(ac.fecha_hora AS DATE)
  );

PRINT '==== Restauración completada correctamente ====';

--  Verificar que los registros hayan sido restaurados
SELECT rc.id, h.codigo, rc.agricultor_id, rc.aptos, rc.no_aptos, rc.ts
FROM dbo.reporte_cosecha rc
JOIN dbo.hectareas h ON h.id = rc.hectarea_id
WHERE rc.agricultor_id = 1
ORDER BY h.codigo;
