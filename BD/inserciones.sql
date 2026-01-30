-- =========================================================
-- INSERCIONES MASIVAS DE COSECHAS (300 aptos, 50 no aptos)
-- Para agricultores 1 y 4, hectáreas 1–5
-- Esquema: actividad_campo(fecha_hora, notas) y cosecha_detalle(sin observaciones)
-- =========================================================
USE AgroScanDB;
GO

DECLARE @fecha DATETIME = GETDATE();

-- 🔹 Agricultor 1
DECLARE @agricultor_id INT = 1;
DECLARE @hectarea INT = 1;

WHILE @hectarea <= 5
BEGIN
    INSERT INTO dbo.actividad_campo
        (agricultor_id, hectarea_id, tipo, fecha_hora, cantidad, unidad, costo, notas, estado)
    VALUES
        (@agricultor_id, @hectarea, 'cosecha', @fecha, 350, 'kg', 0,
         CONCAT('Carga de prueba hectárea ', @hectarea, ' (agricultor ', @agricultor_id, ')'),
         'aprobado');

    DECLARE @actividad_id INT = SCOPE_IDENTITY();

    INSERT INTO dbo.cosecha_detalle (actividad_id, aptos, no_aptos, cajas, kilos)
    VALUES (@actividad_id, 300, 50, NULL, 350);

    SET @hectarea += 1;
END;

-- 🔹 Agricultor 4
SET @agricultor_id = 4;
SET @hectarea = 1;

WHILE @hectarea <= 5
BEGIN
    INSERT INTO dbo.actividad_campo
        (agricultor_id, hectarea_id, tipo, fecha_hora, cantidad, unidad, costo, notas, estado)
    VALUES
        (@agricultor_id, @hectarea, 'cosecha', @fecha, 350, 'kg', 0,
         CONCAT('Carga de prueba hectárea ', @hectarea, ' (agricultor ', @agricultor_id, ')'),
         'aprobado');

    DECLARE @actividad_id2 INT = SCOPE_IDENTITY();

    INSERT INTO dbo.cosecha_detalle (actividad_id, aptos, no_aptos, cajas, kilos)
    VALUES (@actividad_id2, 300, 50, NULL, 350);

    SET @hectarea += 1;
END;

