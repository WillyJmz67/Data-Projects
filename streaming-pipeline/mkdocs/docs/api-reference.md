# API Reference

Every interface in the pipeline: command-line arguments, environment variables,
network endpoints, Kafka topics and the database schema.

## Producer — `producer/producer.py`

```bash
python producer.py [--bootstrap-servers HOST:PORT] [--topic NAME]
                   [--interval MS] [--max-events N] [--create-topic]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--bootstrap-servers` | `localhost:9092` | Kafka bootstrap servers |
| `--topic` | `web-events` | Target topic |
| `--interval` | `200` | Milliseconds between events (200 ms ≈ 5 events/s) |
| `--max-events` | none (infinite) | Stop after N events |
| `--create-topic` | off | Create the topic (3 partitions) before producing |

Produced payload (JSON, keyed by `user_id` so a user stays on one partition):

```json
{
  "event_id": "evt_1774972428199_4821",
  "timestamp": "2026-09-30T16:53:48.199822Z",
  "user_id": "user_4321",
  "session_id": "session_998",
  "page": "/products/electronics",
  "event_type": "page_view",
  "device_type": "mobile",
  "browser": "Chrome",
  "os": "Android 14",
  "country": "ES",
  "referrer": "https://www.google.com/",
  "user_agent": "Mozilla/5.0 ...",
  "screen_resolution": "390x844",
  "language": "es-ES",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "summer_sale"
}
```

`event_type`-specific fields are added only for the relevant event:

| `event_type` | Extra fields |
|--------------|--------------|
| `add_to_cart` | `product_id`, `quantity`, `price` |
| `purchase` | `order_id`, `total_amount`, `currency`, `items_count` |
| `search` | `search_query`, `results_count` |
| `video_play` | `video_id`, `video_duration` |
| `error` | `error_code`, `error_message` |

## Spark job — `spark_streaming/structured_streaming.py`

No CLI arguments; everything is configured through environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:29092` | Kafka bootstrap servers |
| `KAFKA_TOPIC` | `web-events` | Topic to consume |
| `KAFKA_CONSUMER_GROUP` | `spark-streaming-consumer` | Consumer group (required for lag metrics) |
| `MINIO_ENDPOINT` | `http://minio:9000` | S3A endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | S3A access key |
| `MINIO_SECRET_KEY` | `minioadmin123` | S3A secret key |
| `MINIO_BUCKET` | `metrics` | Target bucket |
| `POSTGRES_HOST` | `postgres` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `streaming_metrics` | Database |
| `POSTGRES_USER` | `streaming_user` | User |
| `POSTGRES_PASSWORD` | `streaming_pass` | Password |
| `CHECKPOINT_DIR` | `s3a://metrics/checkpoints` | Streaming checkpoint location |

Windowing constants (edit in the file):

| Constant | Value |
|----------|-------|
| `WINDOW_DURATION` | `1 minute` |
| `SLIDE_DURATION` | `30 seconds` |
| `WATERMARK_DELAY` | `2 minutes` |
| Trigger | `30 seconds` (processing time) |

Output columns, per `(window_start, window_end, page, event_type)`:
`event_count`, `unique_users`, `unique_sessions`, `revenue`, `purchase_count`,
`add_to_cart_count`, `error_count`, `processed_at`.

## Flink job — `flink_job/WebEventsFlinkJob.java`

```bash
flink run -c com.streaming.flink.WebEventsFlinkJob \
  /opt/flink/usrlib/target/web-events-flink-1.0.jar \
  --kafka.bootstrap.servers kafka:29092 \
  --input.topic web-events \
  --output.topic web-events-aggregated \
  --group.id flink-web-events-consumer
```

| Parameter | Default |
|-----------|---------|
| `kafka.bootstrap.servers` | `kafka:29092` |
| `input.topic` | `web-events` |
| `output.topic` | `web-events-aggregated` |
| `group.id` | `flink-web-events-consumer` |

Delivery guarantee is `EXACTLY_ONCE` (Kafka transactions, prefix
`flink-web-events`); checkpoints run every 30 s and are retained on
cancellation. Parallelism is fixed at 4 in the source.

## Kafka topics

| Topic | Created by | Partitions | Retention | Notes |
|-------|-----------|-----------|-----------|-------|
| `web-events` | `producer.py --create-topic` | 3 | 7 days | Key = `user_id` |
| `web-events-aggregated` | Flink sink | auto | 7 days | Aggregated metrics JSON |
| `__consumer_offsets` | Kafka | 1 | default | Internal |

## HTTP endpoints

| Service | URL | Notes |
|---------|-----|-------|
| Grafana | <http://localhost:3000> | `admin` / `admin123` |
| Prometheus | <http://localhost:9090> | `/targets`, `/graph` |
| Spark Master UI | <http://localhost:8080> | also `/metrics/prometheus/` |
| Flink Web UI | <http://localhost:8081> | JSON REST API |
| MinIO S3 API | <http://localhost:9000> | `/minio/v2/metrics/cluster` |
| MinIO Console | <http://localhost:9001> | `minioadmin` / `minioadmin123` |
| Node Exporter | <http://localhost:9100> | `/metrics` |
| Kafka Exporter | <http://localhost:9308> | `/metrics` |
| Flink metrics | `flink-jobmanager:9249` | Prometheus reporter, not exposed to the host |

## Database schema

`sql/init.sql` is the single source of truth.

```sql
CREATE TABLE IF NOT EXISTS realtime_metrics (
    id BIGSERIAL PRIMARY KEY,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    page VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_count BIGINT NOT NULL,
    unique_users BIGINT NOT NULL,
    unique_sessions BIGINT NOT NULL DEFAULT 0,
    revenue DOUBLE PRECISION NOT NULL DEFAULT 0,
    purchase_count BIGINT NOT NULL DEFAULT 0,
    add_to_cart_count BIGINT NOT NULL DEFAULT 0,
    error_count BIGINT NOT NULL DEFAULT 0,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_realtime_metrics_window
        UNIQUE (window_start, window_end, page, event_type)
);
```

The unique constraint is what makes the job's `ON CONFLICT DO NOTHING` insert
idempotent, so a retried micro-batch does not duplicate rows.

### Views

| View | Window | Contents |
|------|--------|----------|
| `latest_metrics` | last 5 min | Per-window rows plus `events_per_second` |
| `page_metrics` | last 1 h | Per page: totals plus `peak_unique_users` |
| `event_type_metrics` | last 1 h | Per event type: totals |

`unique_users` and `unique_sessions` are distinct counts **per window** and are
not additive across overlapping windows, so the views report `MAX`, never `SUM`.

## Prometheus metrics used by the dashboards

| Metric | Source |
|--------|--------|
| `kafka_topic_partition_current_offset` | Kafka Exporter |
| `kafka_consumergroup_lag` | Kafka Exporter |
| `node_cpu_seconds_total`, `node_memory_*`, `node_network_*` | Node Exporter |
| `flink_jobmanager_job_lastCheckpointDuration` | Flink reporter |
| `flink_jobmanager_job_lastCheckpointSize` | Flink reporter |
| `flink_taskmanager_job_task_numRecordsOutPerSecond` | Flink reporter |
| `minio_cluster_usage_total_bytes`, `minio_cluster_usage_free_bytes`, `minio_s3_requests_total` | MinIO |
| `spark_streaming_*` | Spark UI servlet — confirm the exact names |
