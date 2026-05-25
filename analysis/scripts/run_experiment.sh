#!/bin/bash
# run_experiment.sh — Runs a full experiment: 5 repetitions with restart between each.
# Usage: ./run_experiment.sh <monolith|microservices> <idle|steady|rampup|extended>

ARCH=$1
SCENARIO=$2
JMETER_HOME=${JMETER_HOME:-/usr/local/apache-jmeter}
RESULTS_DIR="$(dirname "$0")/../results"
LOAD_TESTS_DIR="$(dirname "$0")/../../load-tests"

if [[ -z "$ARCH" || -z "$SCENARIO" ]]; then
  echo "Usage: $0 <monolith|microservices> <idle|steady|rampup|extended>"
  exit 1
fi

if [[ "$ARCH" == "monolith" ]]; then
  COMPOSE_DIR="$(dirname "$0")/../../monolith"
  JMETER_PLAN="$LOAD_TESTS_DIR/monolith-test-plan.jmx"
else
  COMPOSE_DIR="$(dirname "$0")/../../microservices"
  JMETER_PLAN="$LOAD_TESTS_DIR/microservices-test-plan.jmx"
fi

mkdir -p "$RESULTS_DIR"

echo "╔══════════════════════════════════════════════════════╗"
echo "  B2B Memory Benchmark: $ARCH / $SCENARIO"
echo "╚══════════════════════════════════════════════════════╝"

for RUN in 1 2 3 4 5; do
  echo ""
  echo "──────────────────────────────────────────────────────"
  echo "  Run $RUN / 5"
  echo "──────────────────────────────────────────────────────"

  # 1. Clean restart
  echo "[1/5] Stopping containers..."
  docker compose -f "$COMPOSE_DIR/docker-compose.yml" down -v --remove-orphans 2>/dev/null

  echo "[2/5] Starting containers..."
  docker compose -f "$COMPOSE_DIR/docker-compose.yml" up -d --build

  # 2. Wait for app to be healthy
  echo "[3/5] Waiting for services to be healthy..."
  sleep 30

  # 3. Warmup (5 min)
  echo "[4/5] Warmup period (5 min)..."
  sleep 300

  # 4. Run JMeter scenario (enable only the relevant thread group)
  echo "[5/5] Running JMeter scenario: $SCENARIO..."
  if [[ "$SCENARIO" == "idle" ]]; then
    # Idle = no JMeter, just collect baseline for 10 min
    sleep 600
  elif [[ "$SCENARIO" == "steady" ]]; then
    $JMETER_HOME/bin/jmeter -n -t "$JMETER_PLAN" \
      -Jenabled_scenario="S1 - Steady Load (50u)" \
      -l "$RESULTS_DIR/${ARCH}_${SCENARIO}_run${RUN}_jmeter.csv"
  elif [[ "$SCENARIO" == "rampup" ]]; then
    $JMETER_HOME/bin/jmeter -n -t "$JMETER_PLAN" \
      -Jenabled_scenario="S2 - Ramp-Up (0-200u)" \
      -l "$RESULTS_DIR/${ARCH}_${SCENARIO}_run${RUN}_jmeter.csv"
  elif [[ "$SCENARIO" == "extended" ]]; then
    $JMETER_HOME/bin/jmeter -n -t "$JMETER_PLAN" \
      -Jenabled_scenario="S3 - Extended Load (100u/30min)" \
      -l "$RESULTS_DIR/${ARCH}_${SCENARIO}_run${RUN}_jmeter.csv"
  fi

  # 5. Collect Prometheus metrics
  echo "  Collecting metrics from Prometheus..."
  python3 "$(dirname "$0")/analyze.py" \
    --arch "$ARCH" \
    --scenario "$SCENARIO" \
    --run "$RUN" \
    --duration 10

  echo "  Run $RUN complete."
done

echo ""
echo "All 5 runs done. Generating comparison charts..."
python3 "$(dirname "$0")/analyze.py" \
  --arch "$ARCH" \
  --scenario "$SCENARIO" \
  --run 5 \
  --duration 10

echo "Done! Results in: $RESULTS_DIR"
