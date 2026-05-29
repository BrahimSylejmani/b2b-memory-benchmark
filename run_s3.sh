#!/bin/bash
# run_s3.sh — Runs full S3 (Extended Load) experiment for both architectures.
# 5 repetitions each, clean restart between runs.
# S3: 100 users, 35 min duration, 60s ramp-up.

set -e

JMETER="/opt/homebrew/bin/jmeter"
RESULTS_DIR="/Users/bimisylejmani/b2b-memory-benchmark/analysis/results"
LOAD_TESTS="/Users/bimisylejmani/b2b-memory-benchmark/load-tests"
MONO_COMPOSE="/Users/bimisylejmani/b2b-memory-benchmark/monolith/docker-compose.yml"
MICRO_COMPOSE="/Users/bimisylejmani/b2b-memory-benchmark/microservices/docker-compose.yml"
ANALYZE="/Users/bimisylejmani/b2b-memory-benchmark/analysis/scripts/analyze.py"

PROMETHEUS_MONO="http://localhost:9090"
PROMETHEUS_MICRO="http://localhost:9091"

log() { echo "[$(date '+%H:%M:%S')] $1"; }

wait_for_health() {
    local url=$1
    local name=$2
    local max_attempts=60
    for i in $(seq 1 $max_attempts); do
        if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q "200"; then
            log "  $name is healthy"
            return 0
        fi
        sleep 5
    done
    log "  WARNING: $name did not become healthy in time"
    return 1
}

run_single() {
    local arch=$1
    local run=$2
    local compose_file=$3
    local jmx_file=$4
    local prom_url=$5
    local health_url=$6

    log "══════════════════════════════════════════"
    log "  $arch — Run $run / 5"
    log "══════════════════════════════════════════"

    # 1. Stop and clean
    log "  [1/6] Stopping containers..."
    docker compose -f "$compose_file" down -v --remove-orphans 2>/dev/null || true
    sleep 5

    # 2. Start fresh
    log "  [2/6] Starting containers..."
    docker compose -f "$compose_file" up -d --build
    sleep 10

    # 3. Wait for health
    log "  [3/6] Waiting for services..."
    wait_for_health "$health_url" "$arch"
    sleep 20

    # 4. Warmup (5 min) — let JVM settle and Prometheus scrape baseline
    log "  [4/6] Warmup (5 minutes)..."
    sleep 300

    # 5. Run JMeter S3 (35 min)
    log "  [5/6] Running JMeter S3 (35 min, 100 users)..."
    "$JMETER" -n -t "$jmx_file" \
        -l "$RESULTS_DIR/${arch}-s3-run${run}.jtl" \
        -j "$RESULTS_DIR/${arch}-s3-run${run}-jmeter.log" \
        2>&1 | tail -5

    # 6. Collect Prometheus metrics
    log "  [6/6] Collecting metrics from Prometheus..."
    PROMETHEUS_URL="$prom_url" python3 "$ANALYZE" \
        --arch "$arch" \
        --scenario extended \
        --run "$run" \
        --duration 30

    # 7. Delete JTL to save disk space (metrics already in JSON)
    rm -f "$RESULTS_DIR/${arch}-s3-run${run}.jtl"
    rm -f "$RESULTS_DIR/${arch}-s3-run${run}-jmeter.log"
    log "  JTL deleted to save space. Metrics saved in JSON."

    log "  Run $run complete!"
    echo ""
}

# ── Clean old S3 data ──────────────────────────────────────────────────────
log "Cleaning old S3 data..."
rm -f "$RESULTS_DIR"/monolith_extended_run*.json
rm -f "$RESULTS_DIR"/monolith-s3-run*.jtl
rm -f "$RESULTS_DIR"/monolith-s3-run*.log
rm -f "$RESULTS_DIR"/monolith_extended_stats.csv
rm -f "$RESULTS_DIR"/microservices_extended_run*.json
rm -f "$RESULTS_DIR"/microservices-s3-run*.jtl
rm -f "$RESULTS_DIR"/microservices-s3-run*.log
rm -f "$RESULTS_DIR"/microservices_extended_stats.csv
log "Old S3 data cleaned."

# ── Stop anything running ─────────────────────────────────────────────────
log "Stopping any running containers..."
docker compose -f "$MONO_COMPOSE" down -v --remove-orphans 2>/dev/null || true
docker compose -f "$MICRO_COMPOSE" down -v --remove-orphans 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "  S3 EXTENDED LOAD — MONOLITH (5 runs)"
echo "  100 users × 35 min × 5 repetitions"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

for RUN in 1 2 3 4 5; do
    run_single "monolith" "$RUN" "$MONO_COMPOSE" \
        "$LOAD_TESTS/monolith-s3.jmx" \
        "$PROMETHEUS_MONO" \
        "http://localhost:8080/actuator/health"
done

# Stop monolith stack
log "Stopping monolith stack..."
docker compose -f "$MONO_COMPOSE" down -v --remove-orphans 2>/dev/null || true
sleep 10

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "  S3 EXTENDED LOAD — MICROSERVICES (5 runs)"
echo "  100 users × 35 min × 5 repetitions"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

for RUN in 1 2 3 4 5; do
    run_single "microservices" "$RUN" "$MICRO_COMPOSE" \
        "$LOAD_TESTS/microservices-s3.jmx" \
        "$PROMETHEUS_MICRO" \
        "http://localhost:8081/actuator/health"
done

# Stop everything
log "Stopping all containers..."
docker compose -f "$MICRO_COMPOSE" down -v --remove-orphans 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "  S3 COMPLETE — All 10 runs finished!"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
log "Results saved to: $RESULTS_DIR"
ls -la "$RESULTS_DIR"/*extended* 2>/dev/null
