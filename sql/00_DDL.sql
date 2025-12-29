IF DB_ID('InternetSpeed_DB') IS NULL
BEGIN
    CREATE DATABASE InternetSpeed_DB;
END
GO

USE InternetSpeed_DB;
GO

IF OBJECT_ID('dbo.internet_speeds', 'U') IS NULL
BEGIN 
    CREATE TABLE dbo.internet_speeds (
        id              BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        measured_at_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),  -- fallback if app forgets
        
        download_mbps   DECIMAL(12,3) NOT NULL,
        upload_mbps     DECIMAL(12,3) NOT NULL,
        latency_ms      DECIMAL(10,2) NOT NULL,
        jitter_ms       DECIMAL(10,2)     NULL,
        packet_loss_pct DECIMAL(5,2)     NULL,   -- assuming percentage 0.00-100.00

        isp             NVARCHAR(200)    NULL,

        server_id       NVARCHAR(50)     NULL,
        server_name     NVARCHAR(200)    NULL,
        server_location NVARCHAR(200)    NULL,
        server_country  NVARCHAR(100)    NULL,

        default_gateway_ip NVARCHAR(50) NULL,
        router_label       NVARCHAR(200) NULL,
        router_model       NVARCHAR(200) NULL,
        connection_type    NVARCHAR(50)  NULL,

        latitude           FLOAT         NULL,
        longitude          FLOAT         NULL,   -- fixed typo
        location_accuracy_m FLOAT        NULL,
        location_source    NVARCHAR(50)  NULL,

        raw_json        NVARCHAR(MAX)    NULL,
        
        inserted_at_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),

        -- Optional: prevent nonsense values
        CONSTRAINT CHK_Speeds_Positive 
            CHECK (download_mbps >= 0 AND upload_mbps >= 0 AND latency_ms >= 0)
    );
    -- GO is not needed here

    -- Time-based index (most common query pattern)
    CREATE NONCLUSTERED INDEX IX_internet_speeds_measured_at_utc
    ON dbo.internet_speeds(measured_at_utc DESC);
    
    -- Per-router time series
    CREATE NONCLUSTERED INDEX IX_internet_speeds_router_label_time
    ON dbo.internet_speeds(router_label, measured_at_utc DESC)
    INCLUDE (download_mbps, upload_mbps, latency_ms);
    
    -- If you add wifi_ssid later:
    -- CREATE NONCLUSTERED INDEX IX_internet_speeds_wifi_ssid_time
    -- ON dbo.internet_speeds(wifi_ssid, measured_at_utc DESC);
END
GO