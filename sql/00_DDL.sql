-- =============================================
-- Internet Speed Monitoring Database - FIXED VERSION
-- =============================================
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'InternetSpeed_DB')
BEGIN
    CREATE DATABASE InternetSpeed_DB;
    PRINT 'Database InternetSpeed_DB created.';
END
GO

USE InternetSpeed_DB;
GO

SET NOCOUNT ON;
GO

------------------------------------------------------
-- Drop tables in reverse dependency order (if needed for re-creation)
------------------------------------------------------
--DROP TABLE IF EXISTS dbo.internet_speeds;
--DROP TABLE IF EXISTS dbo.time_metadata;
--DROP TABLE IF EXISTS dbo.result_metadata;
--DROP TABLE IF EXISTS dbo.servers;
--GO

------------------------------------------------------
-- 1. Servers (dimension table)
------------------------------------------------------
CREATE TABLE dbo.servers (
    server_id              INT             PRIMARY KEY,
    server_name            NVARCHAR(100)   NOT NULL,
    server_host            NVARCHAR(150)   NOT NULL,
    server_location        NVARCHAR(100),
    server_country         NVARCHAR(100),
    server_ip              NVARCHAR(45),
    server_port            INT,
    server_latitude        DECIMAL(9,6),
    server_longitude       DECIMAL(9,6),
    first_seen_utc         DATETIME2(3)    DEFAULT SYSUTCDATETIME(),
    last_seen_utc          DATETIME2(3)    DEFAULT SYSUTCDATETIME(),
    isp                    NVARCHAR(150)
);
PRINT 'Table dbo.servers created.';
GO

------------------------------------------------------
-- 2. Result Metadata
------------------------------------------------------
CREATE TABLE dbo.result_metadata (
    result_id              NVARCHAR(50)    PRIMARY KEY,
    result_url             NVARCHAR(500),
    result_persisted       BIT             DEFAULT 0,
    measured_at_utc        DATETIME2(3)    NOT NULL,
    created_at_utc         DATETIME2(3)    DEFAULT SYSUTCDATETIME()
);
PRINT 'Table dbo.result_metadata created.';
GO

------------------------------------------------------
-- 3. Time Dimension - EXPLICIT DATETIME2(3) everywhere
------------------------------------------------------
CREATE TABLE dbo.time_metadata (
    time_id             DATETIME2(3)    NOT NULL
        CONSTRAINT PK_time_metadata PRIMARY KEY,

    local_tz            DATETIME2(3)    NOT NULL,
    date_key            INT             NOT NULL,
    year                SMALLINT        NOT NULL,
    month               TINYINT         NOT NULL,
    month_name          NVARCHAR(10)    NOT NULL,
    day                 TINYINT         NOT NULL,
    day_of_week         TINYINT         NOT NULL,
    day_of_week_name    NVARCHAR(10)    NOT NULL,
    week_of_year        TINYINT         NOT NULL,
    quarter             TINYINT         NOT NULL,
    hour                TINYINT         NOT NULL,
    is_weekend          BIT             NOT NULL,
    is_holiday          BIT             NOT NULL
);
PRINT 'Table dbo.time_metadata created.';
GO

------------------------------------------------------
-- 4. Internet Speeds (fact table)
------------------------------------------------------
CREATE TABLE dbo.internet_speeds (
    id                     BIGINT          IDENTITY(1,1)   PRIMARY KEY,
    result_id              NVARCHAR(50)    NOT NULL,
    server_id              INT             NOT NULL,
    measured_at_utc        DATETIME2(3)    NOT NULL,
    download_mbps          DECIMAL(12,3)   NOT NULL,
    upload_mbps            DECIMAL(12,3)   NOT NULL,
    latency_ms             DECIMAL(8,3),
    jitter_ms              DECIMAL(8,3),
    packet_loss_pct        DECIMAL(5,2),

    -- Foreign Keys - now matching precision
    CONSTRAINT FK_internet_speeds_result
        FOREIGN KEY (result_id)
        REFERENCES dbo.result_metadata(result_id),

    CONSTRAINT FK_internet_speeds_server
        FOREIGN KEY (server_id)
        REFERENCES dbo.servers(server_id),

    CONSTRAINT FK_internet_speeds_time
        FOREIGN KEY (measured_at_utc)
        REFERENCES dbo.time_metadata(time_id)
);
PRINT 'Table dbo.internet_speeds created.';
GO

PRINT '=== DATABASE SETUP COMPLETE ===';
GO