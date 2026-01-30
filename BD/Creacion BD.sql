-- 0) Crear BD
IF DB_ID('AgroScanDB') IS NULL
BEGIN
  CREATE DATABASE AgroScanDB;
END
GO
USE AgroScanDB;
GO

-- 1) Catálogo de roles
IF OBJECT_ID('dbo.roles','U') IS NULL
BEGIN
  CREATE TABLE dbo.roles (
    id  INT IDENTITY(1,1) PRIMARY KEY,
    rol NVARCHAR(40) NOT NULL UNIQUE
  );
  INSERT INTO dbo.roles(rol) VALUES (N'agricultor'), (N'supervisor');
END
GO

-- 2) Catálogo de estados de reporte
IF OBJECT_ID('dbo.reporte_estados','U') IS NULL
BEGIN
  CREATE TABLE dbo.reporte_estados (
    id     INT IDENTITY(1,1) PRIMARY KEY,
    estado NVARCHAR(40) NOT NULL UNIQUE
  );
  INSERT INTO dbo.reporte_estados(estado) VALUES (N'pendiente'), (N'aprobado'), (N'rechazado');
END
GO

-- 3) Usuarios
IF OBJECT_ID('dbo.usuarios','U') IS NULL
BEGIN
  CREATE TABLE dbo.usuarios (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    username       NVARCHAR(80)   NOT NULL,
    email          NVARCHAR(120)  NOT NULL,
    password_hash  NVARCHAR(64)   NOT NULL,   -- compat con SQLite
    rol_id         INT            NOT NULL,
    fecha_registro DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME(),
    is_active      BIT            NOT NULL DEFAULT 1,
    created_at     DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at     DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_usuarios_username UNIQUE(username),
    CONSTRAINT UQ_usuarios_email    UNIQUE(email),
    CONSTRAINT FK_usuarios_roles    FOREIGN KEY (rol_id) REFERENCES dbo.roles(id)
  );
END
GO

IF OBJECT_ID('dbo.trg_usuarios_updated','TR') IS NOT NULL DROP TRIGGER dbo.trg_usuarios_updated;
GO
CREATE TRIGGER dbo.trg_usuarios_updated ON dbo.usuarios
AFTER UPDATE AS
BEGIN
  SET NOCOUNT ON;
  UPDATE u SET updated_at = SYSUTCDATETIME()
  FROM dbo.usuarios u
  JOIN inserted i ON u.id = i.id;
END
GO

-- 4) Reportes
IF OBJECT_ID('dbo.reportes','U') IS NULL
BEGIN
  CREATE TABLE dbo.reportes (
    id                    INT IDENTITY(1,1) PRIMARY KEY,
    usuario_id            INT            NOT NULL,
    fecha                 DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME(),
    planta                NVARCHAR(120)  NULL,
    enfermedad            NVARCHAR(120)  NULL,
    num_frutos            INT            NULL,
    maduracion            NVARCHAR(60)   NULL,
    path_imagen           NVARCHAR(300)  NULL,
    path_reporte          NVARCHAR(300)  NULL,
    estado_id             INT            NOT NULL,
    comentario_supervisor NVARCHAR(MAX)  NULL,
    created_at            DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at            DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_reportes_usuarios  FOREIGN KEY (usuario_id)   REFERENCES dbo.usuarios(id) ON DELETE CASCADE,
    CONSTRAINT FK_reportes_estados   FOREIGN KEY (estado_id)    REFERENCES dbo.reporte_estados(id)
  );
END
GO

IF OBJECT_ID('dbo.trg_reportes_updated','TR') IS NOT NULL DROP TRIGGER dbo.trg_reportes_updated;
GO
CREATE TRIGGER dbo.trg_reportes_updated ON dbo.reportes
AFTER UPDATE AS
BEGIN
  SET NOCOUNT ON;
  UPDATE r SET updated_at = SYSUTCDATETIME()
  FROM dbo.reportes r
  JOIN inserted i ON r.id = i.id;
END
GO

-- 5) Índices
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_usuarios_email' AND object_id=OBJECT_ID('dbo.usuarios'))
  CREATE INDEX IX_usuarios_email ON dbo.usuarios(email);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_reportes_usuario_fecha' AND object_id=OBJECT_ID('dbo.reportes'))
  CREATE INDEX IX_reportes_usuario_fecha ON dbo.reportes(usuario_id, fecha DESC);
GO

/* =========================================================
   6) HECTÁREAS, ASIGNACIONES Y REPORTES DE COSECHA (APTOS/NO APTOS)
   ========================================================= */

-- 6.1) Hectáreas (catálogo)
IF OBJECT_ID('dbo.hectareas','U') IS NULL
BEGIN
  CREATE TABLE dbo.hectareas(
    id         INT IDENTITY(1,1) PRIMARY KEY,
    codigo     NVARCHAR(20)  NOT NULL UNIQUE,  -- H1..H5
    nombre     NVARCHAR(80)  NOT NULL,
    area_ha    DECIMAL(6,2)  NOT NULL CONSTRAINT DF_hect_area DEFAULT (1.00),
    ubicacion  NVARCHAR(120) NULL,
    activa     BIT           NOT NULL CONSTRAINT DF_hect_activa DEFAULT (1),
    created_at DATETIME2(0)  NOT NULL CONSTRAINT DF_hect_created DEFAULT SYSUTCDATETIME()
  );
END;
GO

-- Seed de 5 hectáreas (idempotente)
MERGE dbo.hectareas AS T
USING (VALUES
  (N'H1', N'Hectárea 1', 1.00, NULL, 1),
  (N'H2', N'Hectárea 2', 1.00, NULL, 1),
  (N'H3', N'Hectárea 3', 1.00, NULL, 1),
  (N'H4', N'Hectárea 4', 1.00, NULL, 1),
  (N'H5', N'Hectárea 5', 1.00, NULL, 1)
) AS S(codigo, nombre, area_ha, ubicacion, activa)
ON T.codigo = S.codigo
WHEN NOT MATCHED THEN
  INSERT (codigo, nombre, area_ha, ubicacion, activa)
  VALUES (S.codigo, S.nombre, S.area_ha, S.ubicacion, S.activa);
GO

-- 6.2) Asignaciones Agricultor ↔ Hectárea
IF OBJECT_ID('dbo.asignaciones','U') IS NULL
BEGIN
  CREATE TABLE dbo.asignaciones(
    id            INT IDENTITY(1,1) PRIMARY KEY,
    agricultor_id INT        NOT NULL,   -- usuarios.id con rol agricultor
    hectarea_id   INT        NOT NULL,
    inicio        DATE       NOT NULL CONSTRAINT DF_asig_inicio DEFAULT (CAST(SYSUTCDATETIME() AS DATE)),
    fin           DATE       NULL,
    activo        BIT        NOT NULL CONSTRAINT DF_asig_activo DEFAULT (1),
    created_at    DATETIME2(0) NOT NULL CONSTRAINT DF_asig_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_asig_user FOREIGN KEY (agricultor_id) REFERENCES dbo.usuarios(id),
    CONSTRAINT FK_asig_hect FOREIGN KEY (hectarea_id)   REFERENCES dbo.hectareas(id)
  );

  -- Un agricultor solo puede tener UNA asignación activa a la vez (opcional; quita si permite varias)
  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_asig_agricultor_activo' AND object_id=OBJECT_ID('dbo.asignaciones'))
    CREATE UNIQUE INDEX UX_asig_agricultor_activo
      ON dbo.asignaciones(agricultor_id)
      WHERE activo = 1;

  -- Una hectárea solo puede tener UNA asignación activa a la vez
  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_asig_hectarea_activa' AND object_id=OBJECT_ID('dbo.asignaciones'))
    CREATE UNIQUE INDEX UX_asig_hectarea_activa
      ON dbo.asignaciones(hectarea_id)
      WHERE activo = 1;
END;
GO

-- 6.3) Reporte de cosecha (conteos aptos / no aptos por sesión)
IF OBJECT_ID('dbo.reporte_cosecha','U') IS NULL
BEGIN
  CREATE TABLE dbo.reporte_cosecha(
    id            BIGINT IDENTITY(1,1) PRIMARY KEY,
    agricultor_id INT         NOT NULL,
    hectarea_id   INT         NOT NULL,
    ts            DATETIME2(0) NOT NULL CONSTRAINT DF_repC_ts DEFAULT SYSUTCDATETIME(),
    aptos         INT         NOT NULL CHECK (aptos    >= 0),
    no_aptos      INT         NOT NULL CHECK (no_aptos >= 0),
    fuente        NVARCHAR(30) NOT NULL CONSTRAINT DF_repC_fuente DEFAULT (N'YOLO'),
    created_at    DATETIME2(0) NOT NULL CONSTRAINT DF_repC_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_repC_user FOREIGN KEY (agricultor_id) REFERENCES dbo.usuarios(id),
    CONSTRAINT FK_repC_hect FOREIGN KEY (hectarea_id)   REFERENCES dbo.hectareas(id)
  );

  -- Índices útiles para filtros y dashboards
  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_repC_agricultor_ts' AND object_id=OBJECT_ID('dbo.reporte_cosecha'))
    CREATE INDEX IX_repC_agricultor_ts ON dbo.reporte_cosecha(agricultor_id, ts DESC);

  IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_repC_hectarea_ts' AND object_id=OBJECT_ID('dbo.reporte_cosecha'))
    CREATE INDEX IX_repC_hectarea_ts ON dbo.reporte_cosecha(hectarea_id, ts DESC);
END;
GO

/* =========================================================
   7) VISTAS PARA DASHBOARDS
   ========================================================= */

-- 7.1) Dashboard por agricultor (detalle por hectárea)
CREATE OR ALTER VIEW dbo.vw_dashboard_agricultor AS
SELECT
  rc.agricultor_id,
  u.username      AS usuario,
  u.email,
  u.is_active,
  rc.hectarea_id,
  h.codigo        AS codigo_hectarea,
  h.nombre        AS nombre_hectarea,
  SUM(rc.aptos)      AS total_aptos,
  SUM(rc.no_aptos)   AS total_no_aptos,
  SUM(rc.aptos + rc.no_aptos) AS total_registrados,
  CAST(100.0 * NULLIF(SUM(rc.aptos), 0) / NULLIF(SUM(rc.aptos + rc.no_aptos), 0) AS DECIMAL(5,2)) AS pct_aptos,
  MIN(rc.ts)      AS primera_fecha,
  MAX(rc.ts)      AS ultima_fecha
FROM dbo.reporte_cosecha rc
JOIN dbo.usuarios  u ON u.id = rc.agricultor_id
JOIN dbo.hectareas h ON h.id = rc.hectarea_id
GROUP BY rc.agricultor_id, u.username, u.email, u.is_active, rc.hectarea_id, h.codigo, h.nombre;
GO

-- 7.2) Dashboard del supervisor (resumen por hectárea)
CREATE OR ALTER VIEW dbo.vw_dashboard_supervisor AS
SELECT
  rc.hectarea_id,
  h.codigo        AS codigo_hectarea,
  h.nombre        AS nombre_hectarea,
  SUM(rc.aptos)      AS total_aptos,
  SUM(rc.no_aptos)   AS total_no_aptos,
  SUM(rc.aptos + rc.no_aptos) AS total_registrados,
  CAST(100.0 * NULLIF(SUM(rc.aptos), 0) / NULLIF(SUM(rc.aptos + rc.no_aptos), 0) AS DECIMAL(5,2)) AS pct_aptos,
  COUNT(DISTINCT rc.agricultor_id) AS agricultores_participantes,
  MIN(rc.ts)      AS primera_fecha,
  MAX(rc.ts)      AS ultima_fecha
FROM dbo.reporte_cosecha rc
JOIN dbo.hectareas h ON h.id = rc.hectarea_id
GROUP BY rc.hectarea_id, h.codigo, h.nombre;
GO

/* =========================================================
   8) UTILIDADES DE VERIFICACIÓN RÁPIDA
   ========================================================= */

-- Hectáreas con su asignación activa (si existe)
CREATE OR ALTER VIEW dbo.vw_hectareas_asignadas AS
SELECT
  h.id, h.codigo, h.nombre, h.activa,
  a.agricultor_id,
  u.username AS agricultor,
  a.inicio, a.fin, a.activo
FROM dbo.hectareas h
LEFT JOIN dbo.asignaciones a ON a.hectarea_id = h.id AND a.activo = 1
LEFT JOIN dbo.usuarios u ON u.id = a.agricultor_id;
GO

/* 6.4) ACTIVIDAD DE CAMPO (TRANSACCIONAL) */
IF OBJECT_ID('dbo.actividad_campo','U') IS NULL
BEGIN
  CREATE TABLE dbo.actividad_campo (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    agricultor_id       INT        NOT NULL,
    hectarea_id         INT        NOT NULL,
    tipo                VARCHAR(20) NOT NULL, -- siembra|riego|fumigacion|cosecha|otros
    fecha_hora          DATETIME    NOT NULL,
    cantidad            DECIMAL(10,2)    NULL,
    unidad              NVARCHAR(20)     NULL,
    costo               DECIMAL(12,2)    NOT NULL DEFAULT(0),
    notas               NVARCHAR(500)    NULL,
    estado              VARCHAR(10)      NOT NULL DEFAULT('pendiente'), -- pendiente|aprobado|rechazado
    supervisor_id       INT              NULL,
    comentario_supervisor NVARCHAR(500)  NULL,
    activo              BIT              NOT NULL DEFAULT(1),
    fecha_creacion      DATETIME         NOT NULL DEFAULT(GETDATE()),
    fecha_actualizacion DATETIME         NOT NULL DEFAULT(GETDATE()),
    fecha_revision      DATETIME         NULL,
    CONSTRAINT CK_actividad_campo_tipo
      CHECK (tipo IN ('siembra','riego','fumigacion','cosecha','otros')),
    CONSTRAINT CK_actividad_campo_estado
      CHECK (estado IN ('pendiente','aprobado','rechazado')),
    CONSTRAINT FK_actividad_campo_agricultor FOREIGN KEY (agricultor_id) REFERENCES dbo.usuarios(id),
    CONSTRAINT FK_actividad_campo_hectarea   FOREIGN KEY (hectarea_id)   REFERENCES dbo.hectareas(id)
  );

  CREATE INDEX IX_actividad_campo_agricultor_fecha
    ON dbo.actividad_campo(agricultor_id, fecha_hora DESC) INCLUDE (estado, tipo, activo);
  CREATE INDEX IX_actividad_campo_hectarea_fecha
    ON dbo.actividad_campo(hectarea_id, fecha_hora DESC)   INCLUDE (estado, tipo, activo);
  CREATE INDEX IX_actividad_campo_estado
    ON dbo.actividad_campo(estado) WHERE estado='pendiente';
END
GO

IF OBJECT_ID('dbo.cosecha_detalle','U') IS NULL
BEGIN
  CREATE TABLE dbo.cosecha_detalle (
    actividad_id INT PRIMARY KEY,  -- 1:1 con actividad_campo
    aptos        INT           NOT NULL DEFAULT(0),
    no_aptos     INT           NOT NULL DEFAULT(0),
    cajas        DECIMAL(10,2) NULL,
    kilos        DECIMAL(10,2) NULL,
    CONSTRAINT FK_cosecha_detalle_actividad
      FOREIGN KEY (actividad_id) REFERENCES dbo.actividad_campo(id) ON DELETE CASCADE
  );
END
GO

IF OBJECT_ID('dbo.trg_actividad_campo_touch','TR') IS NOT NULL
  DROP TRIGGER dbo.trg_actividad_campo_touch;
GO
CREATE TRIGGER dbo.trg_actividad_campo_touch
ON dbo.actividad_campo
AFTER UPDATE
AS
BEGIN
  SET NOCOUNT ON;
  UPDATE ac SET fecha_actualizacion = GETDATE()
  FROM dbo.actividad_campo ac
  JOIN inserted i ON i.id = ac.id;
END
GO


-- 6.5) Trigger: actividad_campo (cosecha aprobada) => inserta en reporte_cosecha
IF OBJECT_ID('dbo.trg_actividad_to_reportes_cosecha','TR') IS NOT NULL
  DROP TRIGGER dbo.trg_actividad_to_reportes_cosecha;
GO
CREATE TRIGGER dbo.trg_actividad_to_reportes_cosecha
ON dbo.actividad_campo
AFTER UPDATE
AS
BEGIN
  SET NOCOUNT ON;

  ;WITH aprobadas AS (
    SELECT i.id, i.agricultor_id, i.hectarea_id, i.fecha_hora
    FROM inserted i
    JOIN deleted  d ON d.id = i.id
    WHERE i.activo = 1
      AND i.tipo = 'cosecha'
      AND i.estado = 'aprobado'
      AND (d.estado <> 'aprobado' OR d.estado IS NULL)
  )
  INSERT INTO dbo.reporte_cosecha(agricultor_id, hectarea_id, ts, aptos, no_aptos, fuente)
  SELECT a.agricultor_id,
         a.hectarea_id,
         a.fecha_hora,
         ISNULL(cd.aptos,0),
         ISNULL(cd.no_aptos,0),
         N'ACTIVIDAD'
  FROM aprobadas a
  LEFT JOIN dbo.cosecha_detalle cd ON cd.actividad_id = a.id;
END
GO


/* 9) STORED PROCEDURES — CONTROL DE COSECHA */
IF OBJECT_ID('dbo.sp_RegistrarActividadCampo','P') IS NOT NULL
  DROP PROCEDURE dbo.sp_RegistrarActividadCampo;
GO
CREATE PROCEDURE dbo.sp_RegistrarActividadCampo
  @agricultor_id INT,
  @hectarea_id   INT,
  @tipo          VARCHAR(20),
  @fecha_hora    DATETIME,
  @cantidad      DECIMAL(10,2) = NULL,
  @unidad        NVARCHAR(20)  = NULL,
  @costo         DECIMAL(12,2) = 0,
  @notas         NVARCHAR(500) = NULL,
  @aptos         INT = NULL,
  @no_aptos      INT = NULL,
  @cajas         DECIMAL(10,2) = NULL,
  @kilos         DECIMAL(10,2) = NULL
AS
BEGIN
  SET NOCOUNT ON;
  INSERT INTO dbo.actividad_campo(agricultor_id, hectarea_id, tipo, fecha_hora, cantidad, unidad, costo, notas)
  VALUES (@agricultor_id, @hectarea_id, @tipo, @fecha_hora, @cantidad, @unidad, @costo, @notas);
  DECLARE @new_id INT = SCOPE_IDENTITY();
  IF @tipo = 'cosecha'
  BEGIN
    INSERT INTO dbo.cosecha_detalle(actividad_id, aptos, no_aptos, cajas, kilos)
    VALUES (@new_id, ISNULL(@aptos,0), ISNULL(@no_aptos,0), @cajas, @kilos);
  END
  SELECT @new_id AS actividad_id;
END
GO

IF OBJECT_ID('dbo.sp_ListarActividadesAgricultor','P') IS NOT NULL
  DROP PROCEDURE dbo.sp_ListarActividadesAgricultor;
GO
CREATE PROCEDURE dbo.sp_ListarActividadesAgricultor
  @agricultor_id INT,
  @desde DATETIME = NULL,
  @hasta DATETIME = NULL
AS
BEGIN
  SET NOCOUNT ON;
  SELECT ac.id, ac.agricultor_id, ac.hectarea_id, ac.tipo, ac.fecha_hora,
         ac.cantidad, ac.unidad, ac.costo, ac.notas,
         ac.estado, ac.supervisor_id, ac.comentario_supervisor,
         ac.activo, ac.fecha_creacion, ac.fecha_actualizacion, ac.fecha_revision,
         h.codigo AS codigo_hectarea,
         cd.aptos, cd.no_aptos, cd.cajas, cd.kilos
  FROM dbo.actividad_campo ac
  JOIN dbo.hectareas h    ON h.id = ac.hectarea_id
  LEFT JOIN dbo.cosecha_detalle cd ON cd.actividad_id = ac.id
  WHERE ac.agricultor_id = @agricultor_id
    AND ac.activo = 1
    AND (@desde IS NULL OR ac.fecha_hora >= @desde)
    AND (@hasta IS NULL OR ac.fecha_hora <= @hasta)
  ORDER BY ac.fecha_hora DESC;
END
GO

IF OBJECT_ID('dbo.sp_ListarActividadesSupervisor','P') IS NOT NULL
  DROP PROCEDURE dbo.sp_ListarActividadesSupervisor;
GO
CREATE PROCEDURE dbo.sp_ListarActividadesSupervisor
  @estado VARCHAR(10) = NULL, -- NULL = todos
  @desde  DATETIME = NULL,
  @hasta  DATETIME = NULL
AS
BEGIN
  SET NOCOUNT ON;
  SELECT ac.id, ac.agricultor_id, ac.hectarea_id, ac.tipo, ac.fecha_hora,
         ac.cantidad, ac.unidad, ac.costo, ac.notas,
         ac.estado, ac.supervisor_id, ac.comentario_supervisor,
         ac.activo, ac.fecha_creacion, ac.fecha_actualizacion, ac.fecha_revision,
         u.username AS agricultor, h.codigo AS codigo_hectarea,
         cd.aptos, cd.no_aptos, cd.cajas, cd.kilos
  FROM dbo.actividad_campo ac
  JOIN dbo.hectareas h ON h.id = ac.hectarea_id
  JOIN dbo.usuarios  u ON u.id = ac.agricultor_id
  LEFT JOIN dbo.cosecha_detalle cd ON cd.actividad_id = ac.id
  WHERE ac.activo = 1
    AND (@estado IS NULL OR ac.estado = @estado)
    AND (@desde IS NULL OR ac.fecha_hora >= @desde)
    AND (@hasta IS NULL OR ac.fecha_hora <= @hasta)
  ORDER BY ac.fecha_hora DESC;
END
GO

IF OBJECT_ID('dbo.sp_ActualizarEstadoActividad','P') IS NOT NULL
  DROP PROCEDURE dbo.sp_ActualizarEstadoActividad;
GO
CREATE PROCEDURE dbo.sp_ActualizarEstadoActividad
  @actividad_id INT,
  @estado       VARCHAR(10), -- 'aprobado' | 'rechazado' | 'pendiente'
  @supervisor_id INT,
  @comentario    NVARCHAR(500) = NULL
AS
BEGIN
  SET NOCOUNT ON;
  IF @estado NOT IN ('pendiente','aprobado','rechazado')
  BEGIN RAISERROR('Estado inválido', 16, 1); RETURN; END
  UPDATE dbo.actividad_campo
     SET estado = @estado,
         supervisor_id = @supervisor_id,
         comentario_supervisor = @comentario,
         fecha_revision = GETDATE()
   WHERE id = @actividad_id
     AND activo = 1;
  SELECT @@ROWCOUNT AS rows_affected;
END
GO

IF OBJECT_ID('dbo.sp_EliminarActividad','P') IS NOT NULL
  DROP PROCEDURE dbo.sp_EliminarActividad;
GO
CREATE PROCEDURE dbo.sp_EliminarActividad
  @actividad_id INT,
  @agricultor_id INT
AS
BEGIN
  SET NOCOUNT ON;
  UPDATE dbo.actividad_campo
     SET activo = 0
   WHERE id = @actividad_id
     AND agricultor_id = @agricultor_id
     AND estado = 'pendiente'
     AND activo = 1;
  SELECT @@ROWCOUNT AS rows_affected;
END
GO


CREATE OR ALTER VIEW dbo.vw_cosecha_semanal_agricultor AS
SELECT
  ac.agricultor_id,
  ac.hectarea_id,
  DATEADD(WEEK, DATEDIFF(WEEK, 0, ac.fecha_hora), 0) AS semana_inicio,
  SUM(ISNULL(cd.aptos,0))    AS aptos,
  SUM(ISNULL(cd.no_aptos,0)) AS no_aptos
FROM dbo.actividad_campo ac
LEFT JOIN dbo.cosecha_detalle cd ON cd.actividad_id = ac.id
WHERE ac.activo = 1 AND ac.tipo = 'cosecha' AND ac.estado = 'aprobado'
GROUP BY ac.agricultor_id, ac.hectarea_id, DATEADD(WEEK, DATEDIFF(WEEK, 0, ac.fecha_hora), 0);
GO

