# Internet Speed Measurement & Monitoring Pipeline for Lesotho's ISPs 

This project implements an automated, reproducible pipeline for **measuring, storing, and analysing internet performance** using the Ookla Speedtest CLI, Python, and SQL Server.

It is designed for:
- long-running, high-frequency measurement (e.g. every 15–30 minutes),
- structured storage suitable for dashboards and research,
- eventual multi-participant data collection and analysis.

---

## What this project does

On a fixed schedule, the system:

1. Runs an internet speed test using the **Ookla Speedtest CLI**
2. Parses and standardises the raw JSON output
3. Stores results in a **relational SQL Server schema**, including:
   - speed and latency metrics (fact table),
   - server metadata (dimension table),
   - time/calendar metadata (dimension table).
4. Avoids unnecessary external API calls by **caching server metadata**
5. Logs execution for monitoring and debugging

The pipeline is designed to run unattended for months.

---

## Project structure

```internet-speed-test/
├── speedtest.py          # Run speedtest CLI and transform raw JSON
├── ingest.py             # Database connection, enrichment, inserts
├── helpers.py            # Time dimension + holiday logic
├── push.py               # Entry point (orchestrates a single run)
├── run_speedtest.sh      # Shell wrapper used by cron
├── logs/
│   └── cron.log          # Cron execution logs
├── env/                  # Python virtual environment
└── README.md

---

## Key design principles

### Separation of concerns
- `speedtest.py`  
  **Pure data collection and transformation**.  
  No database access. No unnecessary API calls.

- `ingest.py`  
  **All database logic lives here**, including:
  - checking whether a server already exists,
  - enriching server metadata only when needed,
  - inserting facts and dimensions safely.

- `helpers.py`  
  Calendar logic, including:
  - local time conversion (Africa/Maseru),
  - weekends,
  - Lesotho public holidays.

---

## Database schema (conceptual)

### Fact table
- `internet_speeds`
  - download_mbps
  - upload_mbps
  - latency_ms
  - jitter_ms
  - packet_loss_pct
  - measured_at_utc
  - server_id
  - result_id

### Dimensions
- `servers`
  - server_id (PK)
  - server_name
  - location, country
  - latitude, longitude (cached)
  - first_seen_utc, last_seen_utc

- `time_metadata`
  - time_id (UTC timestamp)
  - local time
  - hour, day, week, month, quarter
  - weekend flag
  - Lesotho public holiday flag

---

## External dependencies

### System dependencies
- macOS
- Docker (for SQL Server)
- Homebrew
- Ookla Speedtest CLI

Install Speedtest CLI:

```bash
brew install speedtest
```