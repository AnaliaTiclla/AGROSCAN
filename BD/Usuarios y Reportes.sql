USE AgroScanDB;
GO

-- 3) Usuarios
IF OBJECT_ID('dbo.usuarios','U') IS NULL
BEGIN
  CREATE TABLE dbo.usuarios (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    username       NVARCHAR(80)   NOT NULL,
    email          NVARCHAR(120)  NOT NULL,
    password_hash  NVARCHAR(64)   NOT NULL,  -- compatible con tu SQLite (sha256 hex)
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
    CONSTRAINT FK_reportes_usuarios  FOREIGN KEY (usuario_id)  REFERENCES dbo.usuarios(id) ON DELETE CASCADE,
    CONSTRAINT FK_reportes_estados   FOREIGN KEY (estado_id)   REFERENCES dbo.reporte_estados(id)
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

-- Verificación rápida
SELECT 'roles' t, COUNT(*) c FROM dbo.roles
UNION ALL SELECT 'reporte_estados', COUNT(*) FROM dbo.reporte_estados
UNION ALL SELECT 'usuarios', 0
UNION ALL SELECT 'reportes', 0;
