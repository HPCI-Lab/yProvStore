# yProvStore Performance Test Suite

Locust-based performance and load testing for the yProvStore storage API.  
Each scenario lives in its own file under `scenarios/` and can be run independently.

## Prerequisites

1. **Docker stack running** (PostgreSQL + PgBouncer + MinIO + API):
   ```bash
   docker compose up -d
   ```

2. **Install Python dependencies** (in a virtualenv):
   ```bash
   pip install -r requirements.txt
   ```

3. **Create the results directory**:
   ```bash
   mkdir -p results
   ```

## Environment Variables

All variables have sensible defaults. Override as needed:

| Variable | Default | Description |
|---|---|---|
| `TARGET_HOST` | `http://localhost:8000` | API base URL |
| `TEST_USER_PASSWORD` | `PerfTest1234!` | Password for auto-created test users |
| `TEST_USER_COUNT` | `50` | Number of test users to pre-register |
| `ZSTD_LEVEL` | `1` | Zstd compression level |
| `USER_COUNTS` | `1,5,10,25,50,100,200` | User counts for scalability sweep |
| `WAIT_TIME_MIN` | `0.2` | Min wait between tasks (seconds) |
| `WAIT_TIME_MAX` | `0.5` | Max wait between tasks (seconds) |
| `REQUEST_TIMEOUT` | `120` | HTTP request timeout (seconds) |
| `PAGINATION_SEED_COUNT` | `200` | Documents to seed for pagination test |
| `SUSTAINED_RUN_TIME` | `30m` | Duration for sustained load test |
| `SWEEP_RUN_TIME` | `3m` | Duration per step in scalability sweep |
| `SWEEP_SPAWN_RATE` | `10` | Spawn rate for scalability sweep |

## Test Scenarios

### T1 — Document Upload Throughput
Measures upload RPS and latency for uncompressed PROV-JSON at 4 size tiers.
```bash
locust -f scenarios/test_upload_documents.py --headless -u 50 -r 5 --run-time 5m --csv=results/upload_docs
```

### T2 — Document Download Throughput
Seeds documents, then measures download performance across size tiers.
```bash
locust -f scenarios/test_download_documents.py --headless -u 50 -r 5 --run-time 5m --csv=results/download_docs
```

### T3 — Compressed vs Uncompressed Upload
Two user classes (raw vs `Content-Encoding: zstd`) run side-by-side.
```bash
locust -f scenarios/test_compressed_upload.py --headless -u 50 -r 5 --run-time 5m --csv=results/compressed_upload
```

### T4 — Compressed vs Uncompressed Download
Two user classes (plain vs `Accept-Encoding: zstd`) downloading the same documents.
```bash
locust -f scenarios/test_compressed_download.py --headless -u 50 -r 5 --run-time 5m --csv=results/compressed_download
```

### T5 — Artifact Upload Throughput
Full presigned-URL proxy flow: get URL → PUT file.
```bash
locust -f scenarios/test_upload_artifacts.py --headless -u 30 -r 5 --run-time 5m --csv=results/upload_artifacts
```

### T6 — Artifact Download Throughput
Full presigned-URL proxy flow: get URL → GET file.
```bash
locust -f scenarios/test_download_artifacts.py --headless -u 30 -r 5 --run-time 5m --csv=results/download_artifacts
```

### T7 — Scalability (Concurrent Users)
Mixed 70/30 read-write workload. Run at each user count to produce a scalability curve.

**Single point:**
```bash
locust -f scenarios/test_scalability.py --headless -u 25 -r 5 --run-time 3m --csv=results/scalability_25
```

**Full sweep** (automated, iterates all user counts):
```bash
python scenarios/run_scalability_sweep.py
```

### T8 — Mixed Workload
Realistic concurrent usage: document upload/download, artifact upload/download, metadata reads, listing.
```bash
locust -f scenarios/test_mixed_workload.py --headless -u 50 -r 5 --run-time 10m --csv=results/mixed_workload
```

### T9 — Metadata Operations
Read/write metadata latency (DB-bound, not I/O-bound).
```bash
locust -f scenarios/test_metadata_operations.py --headless -u 30 -r 5 --run-time 5m --csv=results/metadata_ops
```

### T10 — Pagination & Listing
Listing performance with different page sizes, deep pagination, date filters.
```bash
locust -f scenarios/test_pagination_listing.py --headless -u 30 -r 5 --run-time 5m --csv=results/pagination
```

### T11 — Document Size Impact
Sequential (no concurrency), precise per-request timing across all size tiers, compressed vs uncompressed.
```bash
python scenarios/test_document_sizes.py --iterations 50 --output results/size_impact.csv
```

### T12 — Sustained Load / Endurance
Moderate traffic over 30–60 minutes to detect degradation, memory leaks, connection exhaustion.
```bash
locust -f scenarios/test_sustained_load.py --headless -u 25 -r 5 --run-time 30m --csv=results/sustained
```

## Analyzing Results

### Text summary of a single test
```bash
python analysis/analyze_results.py --stats results/upload_docs_stats.csv
```

### Merge scalability sweep CSVs
```bash
python analysis/analyze_results.py --sweep-dir results/ --prefix scalability
```

### Analyze T11 size-impact results
```bash
python analysis/analyze_results.py --size-impact results/size_impact.csv
```

## Generating Plots

```bash
# Compressed vs uncompressed bar charts
python analysis/plot_results.py --stats results/compressed_upload_stats.csv

# Scalability curve (RPS + p95 vs user count)
python analysis/plot_results.py --scalability results/scalability_merged.csv

# Size impact curves
python analysis/plot_results.py --size-impact results/size_impact.csv

# Sustained load timeline
python analysis/plot_results.py --sustained results/sustained_stats_history.csv
```

Plots are saved to `results/plots/` as PNG files.

## Document Size Tiers

| Tier | Target | Content |
|---|---|---|
| `small` | ~1 KB | Minimal PROV-JSON (1 activity, 2 entities, 2 relations) |
| `medium` | ~64 KB | PROV-JSON with ~200 activities/entities |
| `large` | ~1 MB | PROV-JSON with ~3000 activities/entities |
| `xlarge` | ~10 MB | PROV-JSON with ~30000 activities/entities |

Valid PROV-JSON is used instead of random bytes to give realistic zstd compression ratios (~60-85% savings on structured JSON, vs ~0% on random data).

## Notes

- **Authentication**: Tests automatically register and login `TEST_USER_COUNT` users. Tokens are cached per worker process.
- **Seeding**: Download-oriented tests (T2, T4, T6) seed documents/artifacts on startup before load generation begins.
- **No blockchain tests**: Excluded from this suite.
- **Locust Web UI**: Remove `--headless` to use the browser-based dashboard for interactive testing.
