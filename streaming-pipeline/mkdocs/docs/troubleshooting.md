# Troubleshooting

## Services won't start

```bash
# Which container is unhealthy?
docker compose ps

# Full logs for one service
docker compose logs -f kafka
docker compose logs -f minio

# Restart one service
docker compose restart kafka
```

### `bitnami/minio` or `minio/minio` cannot be pulled

Both namespaces no longer serve MinIO images on Docker Hub. The compose file
pins `bitnamilegacy/minio:2024.1.16-debian-11-r0` and
`bitnamilegacy/minio-client:2024.1.16-debian-11-r0` instead. If you change the
tag, check it first:

```bash
docker manifest inspect bitnamilegacy/minio:2024.1.16-debian-11-r0
```

## Kafka

### Connection refused

```bash
# Broker reachable?
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Zookeeper ready? (`cub` ships with the Confluent images; `nc` does not)
docker exec zookeeper cub zk-ready localhost:2181 40
```

### The producer connects but nothing is consumed

Remember the listeners. Clients **inside** the Docker network must use
`kafka:29092`; clients on the host (including `producer.py` run directly) use
`localhost:9092`. Using the wrong one connects to nothing.

## Spark

### The job runs but MinIO and PostgreSQL stay empty

This is the classic silent failure. Check, in order:

1. **Are events arriving?** `docker exec kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic web-events`
2. **Are timestamps parsed?** The job must use `to_timestamp(col("timestamp"))`.
   With a strict pattern such as `yyyy-MM-dd'T'HH:mm:ss'Z'`, the microsecond
   timestamps produced by `producer.py` fail to parse, `event_timestamp` becomes
   `NULL`, the watermark never advances and the query emits **zero** windows
   forever — with no error in the log.
3. **Did the PostgreSQL insert fail?** Look for `[ERROR] Batch ... PostgreSQL
   write failed` on stderr. `column ... does not exist` means `sql/init.sql` and
   the `INSERT` in `structured_streaming.py` have drifted apart.

### Batch job crashes or a worker is lost

```bash
docker compose logs spark-worker-1
```

The workers are started with `--memory 2G --cores 2`. Note that setting
`SPARK_WORKER_MEMORY` as an environment variable does **nothing**: the
`apache/spark` image entrypoint just execs the command, so memory must be a CLI
flag in `docker-compose.yml`.

## Flink

### The job jar is not found

Build it first — the container mounts the source directory, not a prebuilt jar:

```bash
cd flink_job && mvn clean package
docker exec -it flink-jobmanager flink run \
  -c com.streaming.flink.WebEventsFlinkJob \
  /opt/flink/usrlib/target/web-events-flink-1.0.jar
```

### The Prometheus target `flink-jobmanager:9249` is down

The Prometheus reporter is not enabled by default. `FLINK_PROPERTIES` must
contain all three lines:

```yaml
metrics.reporters: prom
metrics.reporter.prom.factory.class: org.apache.flink.metrics.prometheus.PrometheusReporterFactory
metrics.reporter.prom.port: 9249
```

Note that Flink's REST port `8081` serves JSON, **not** Prometheus text format,
so scraping `8081/metrics` never works.

## MinIO

### Prometheus reports `minio` as down

`/minio/v2/metrics/cluster` requires authentication unless
`MINIO_PROMETHEUS_AUTH_TYPE: "public"` is set on the MinIO service.

### `mc: command not found` or bucket missing

The bucket creator container exits once it finishes, so `docker exec` cannot be
used against it. Run a one-off:

```bash
docker compose run --rm --entrypoint sh minio-bucket-creator \
  -c 'mc alias set minio http://minio:9000 minioadmin minioadmin123 && mc ls minio/metrics'
```

Or open the console at <http://localhost:9001> (`minioadmin` / `minioadmin123`).

## Grafana

### Panels show "Datasource <uid> was not found"

Panels reference datasources **by uid**. The uids declared in
`grafana/datasources/datasources.yml` must match the ones baked into the
dashboard JSON (`prometheus` and `postgres`). If Grafana assigns a random uid,
every panel breaks even though the datasource itself tests fine.

### Dashboards are empty but the datasources work

1. Check targets: <http://localhost:9090/targets>
2. Check the dashboard time range (top-right, default `now-1h`)
3. Confirm rows exist: `docker exec postgres psql -U streaming_user -d streaming_metrics -c "SELECT count(*) FROM realtime_metrics;"`
4. Spark panels only: confirm the real metric names at
   <http://localhost:8080/metrics/prometheus/>

## Numbers look too high

`event_count` from a **sliding** window is counted in two windows
(10:00–10:01 and 10:00:30–10:01:30), so summing across windows double-counts.
Likewise `unique_users` is a per-window distinct count and is not additive — the
dashboards use `MAX`, not `SUM`, for exactly that reason.
