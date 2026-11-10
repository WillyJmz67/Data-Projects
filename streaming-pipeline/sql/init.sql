-- Initialize database schema for streaming metrics
--
-- IMPORTANT: the column list here must match the INSERT in
-- spark_streaming/structured_streaming.py (write_to_postgres). If they drift,
-- the Spark job logs "column ... does not exist" on every micro-batch, swallows
-- the exception and PostgreSQL stays empty while the pipeline looks healthy.
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
    -- Required by "ON CONFLICT DO NOTHING" in the Spark job: without a unique
    -- constraint the clause is a no-op and re-processed windows get duplicated.
    CONSTRAINT uq_realtime_metrics_window UNIQUE (window_start, window_end, page, event_type)
);

-- Create index for fast queries
CREATE INDEX IF NOT EXISTS idx_realtime_metrics_window ON realtime_metrics(window_start, window_end);
CREATE INDEX IF NOT EXISTS idx_realtime_metrics_page ON realtime_metrics(page);
CREATE INDEX IF NOT EXISTS idx_realtime_metrics_event_type ON realtime_metrics(event_type);

-- Create a view for latest metrics (last 5 minutes)
CREATE OR REPLACE VIEW latest_metrics AS
SELECT
    window_start,
    window_end,
    page,
    event_type,
    event_count,
    unique_users,
    unique_sessions,
    revenue,
    purchase_count,
    error_count,
    -- event_count spans the window, so divide by the window length in seconds
    -- (1 minute window => /60), not by the slide.
    (event_count::float / NULLIF(EXTRACT(EPOCH FROM (window_end - window_start)), 0)) as events_per_second
FROM realtime_metrics
WHERE window_start >= NOW() - INTERVAL '5 minutes'
ORDER BY window_start DESC, event_count DESC;

-- Create a view for aggregated metrics by page
-- NOTE: unique_users / unique_sessions are DISTINCT counts computed per window.
-- They are NOT additive: summing them across overlapping sliding windows
-- double-counts the same user. We therefore report MAX (best per-window estimate)
-- instead of SUM, and keep SUM only for the additive counters.
CREATE OR REPLACE VIEW page_metrics AS
SELECT
    page,
    SUM(event_count) as total_events,
    MAX(unique_users) as peak_unique_users,
    SUM(revenue) as total_revenue,
    SUM(purchase_count) as total_purchases,
    SUM(error_count) as total_errors,
    MAX(window_end) as last_update
FROM realtime_metrics
WHERE window_start >= NOW() - INTERVAL '1 hour'
GROUP BY page
ORDER BY total_events DESC;

-- Create a view for aggregated metrics by event type
CREATE OR REPLACE VIEW event_type_metrics AS
SELECT
    event_type,
    SUM(event_count) as total_events,
    SUM(revenue) as total_revenue,
    MAX(window_end) as last_update
FROM realtime_metrics
WHERE window_start >= NOW() - INTERVAL '1 hour'
GROUP BY event_type
ORDER BY total_events DESC;
