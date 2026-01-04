-- SQLBook: Code
SELECT
    t.local_tz,
    i.download_mbps,
    i.upload_mbps,
    i.latency_ms,
    i.jitter_ms
FROM dbo.internet_speeds i
JOIN dbo.time_metadata t
    ON i.measured_at_utc = t.time_id
WHERE t.local_tz >= ? AND t.local_tz < ?
ORDER BY t.local_tz;