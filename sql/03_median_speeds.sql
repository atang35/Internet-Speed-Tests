-- SQLBook: Code
WITH hourly AS (
    SELECT
        DATEADD(hour, DATEDIFF(hour, 0, t.local_tz), 0) AS hour_bucket,
        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY i.download_mbps)
            OVER (PARTITION BY DATEADD(hour, DATEDIFF(hour, 0, t.local_tz), 0))
            AS median_download_mbps,

        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY i.upload_mbps)
            OVER (PARTITION BY DATEADD(hour, DATEDIFF(hour, 0, t.local_tz), 0))
            AS median_upload_mbps,

        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY i.latency_ms)
            OVER (PARTITION BY DATEADD(hour, DATEDIFF(hour, 0, t.local_tz), 0))
            AS median_latency_ms
    FROM dbo.internet_speeds i
    JOIN dbo.time_metadata t
        ON i.measured_at_utc = t.time_id
)
SELECT DISTINCT
    hour_bucket,
    median_download_mbps,
    median_upload_mbps,
    median_latency_ms
FROM hourly
ORDER BY hour_bucket;