-- SQLBook: Code
-- Active: 1767041094165@@localhost@1433@InternetSpeed_DB
SELECT TOP 1
    t.local_tz,
    i.download_mbps,
    i.upload_mbps,
    i.latency_ms
FROM dbo.internet_speeds i
JOIN dbo.time_metadata t
    ON i.measured_at_utc = t.time_id
ORDER BY t.local_tz DESC;