-- SQLBook: Code
SELECT
    MIN(t.local_tz) AS min_dt,
    MAX(t.local_tz) AS max_dt
FROM
    dbo.time_metadata t;