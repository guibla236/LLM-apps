#!/usr/bin/env bash
# =============================================================================
# M2 Re-evaluation Runner — vector_only + hybrid (en secuencia, nocturno)
#
# Ejecuta las dos evaluaciones M2 contra el retrieval corregido (kb-se-all +
# BM25 real), guarda CSVs + agregados, y loguea todo con salida EN VIVO.
#
# Uso:
#   ./run_m2_eval.sh                 # usa API key de .env (APP_API_KEY)
#   APP_API_KEY=xxx ./run_m2_eval.sh # key explícita
#
# Salida: evaluation_notebooks/raw_results/m2_rerun_*_{vector_only,hybrid}_*.csv
# Log:    evaluation_notebooks/raw_results/m2_rerun_YYYYMMDD_HHMMSS.log
# =============================================================================
set -uo pipefail

API_URL="${API_URL:-http://localhost:8000}"
GOLDEN_JSON="${GOLDEN_JSON:-../evaluation_notebooks/goldens/golden_se_200.json}"
LIMIT="${LIMIT:-50}"               # protocolo M2: solo 50 muestras (seed 42, barajado)
K="${K:-10}"
DELAY="${DELAY:-2.0}"
JUDGE_MODEL="${JUDGE_MODEL:-deepseek/deepseek-v4-flash}"
API_KEY="${APP_API_KEY:-}"

# Ruta absoluta para no depender del cwd
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${OUT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)/evaluation_notebooks/raw_results}"
LOG_FILE="${OUT_DIR}/m2_rerun_$(date +%Y%m%d_%H%M%S).log"

# Python del venv del proyecto (no depende de que el venv esté activo)
if [ -x "$SCRIPT_DIR/../tarea2/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/../tarea2/bin/python"
elif [ -x "$SCRIPT_DIR/tarea2/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/tarea2/bin/python"
else
    PYTHON="python"
fi

# ── OpenRouter usage/balance ──
# Consulta el endpoint /auth/key (usage_daily acumulado del día) y /credits (saldo total).
# Usa load_dotenv como la app para no depender del formato del .env.
openrouter_usage() {
    "$PYTHON" - "$SCRIPT_DIR" <<'PYEOF'
import json, os, sys, urllib.request
sys.path.insert(0, sys.argv[1])
from dotenv import load_dotenv
load_dotenv(os.path.join(sys.argv[1], "..", ".env"))
key = os.getenv("OPENROUTER_API_KEY")
if not key:
    print(json.dumps({"error": "no OPENROUTER_API_KEY"})); sys.exit(0)
out = {}
try:
    req = urllib.request.Request("https://openrouter.ai/api/v1/auth/key", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.load(r)["data"]
        out["usage_daily"] = d.get("usage_daily")
        out["limit_remaining"] = d.get("limit_remaining")
        out["limit"] = d.get("limit")
except Exception as e:
    out["error"] = str(e)
try:
    req = urllib.request.Request("https://openrouter.ai/api/v1/credits", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.load(r)["data"]
        out["total_credits"] = d.get("total_credits")
        out["total_usage"] = d.get("total_usage")
        out["balance"] = round(d.get("total_credits", 0) - d.get("total_usage", 0), 4)
except Exception as e:
    out["error"] = str(e)
print(json.dumps(out))
PYEOF
}

fmt_usd() { printf "$%.2f" "$1"; }

# ── Preflight ──
echo "▶ API en: $API_URL (health check)"
HEALTH=$(curl -s -m 5 "$API_URL/health" 2>/dev/null) || HEALTH=""
if [ -z "$HEALTH" ]; then
    # algunos deployments no exponen /health; probamos el endpoint de búsqueda
    echo "  ⚠ /health sin respuesta, verificando puerto..."
    if ! curl -s -m 5 -o /dev/null "$API_URL/"; then
        echo "  ❌ API no responde en $API_URL. ¿Está corriendo?"
        exit 1
    fi
    echo "  ✓ API responde"
else
    echo "  ✓ $HEALTH"
fi

if [ -z "$API_KEY" ]; then
    echo "  ⚠ APP_API_KEY no está en el entorno — el eval usará la del .env (auto-detect)"
fi

if [ ! -f "$GOLDEN_JSON" ]; then
    echo "  ❌ Golden file no existe: $GOLDEN_JSON"
    exit 1
fi

mkdir -p "$OUT_DIR"

echo ""
echo "======================================================================"
echo "  M2 RE-EVALUATION (nocturno)"
echo "  Golden:     $GOLDEN_JSON"
echo "  Muestras:   $LIMIT (protocolo M2: primeras N del golden barajado seed 42)"
echo "  k:          $K | delay: ${DELAY}s | judge: $JUDGE_MODEL"
echo "  Output dir: $OUT_DIR"
echo "  Log file:   $LOG_FILE"
echo "======================================================================"

# ── Saldo inicial de OpenRouter ──
USAGE_START=$(openrouter_usage)
BALANCE_START=$(echo "$USAGE_START" | "$PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(d.get('balance','?'))" 2>/dev/null || echo "?")
LIMIT_REMAIN=$(echo "$USAGE_START" | "$PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(d.get('limit_remaining','?'))" 2>/dev/null || echo "?")
echo "  OpenRouter: saldo ≈ \$$BALANCE_START | límite diario restante ≈ \$$LIMIT_REMAIN"
echo ""

# ── Helper para correr un escenario con salida en vivo + log persistente ──
run_scenario() {
    local name="$1"
    local method="$2"
    echo ""
    echo "############################################################"
    echo "  ▶ [$name] search_method=$method  —  $(date '+%H:%M:%S')"
    echo "############################################################"
    echo ""

    # Costo del escenario: usage_daily antes y después
    local usage_before
    usage_before=$(openrouter_usage | "$PYTHON" -c "import json,sys; print(json.load(sys.stdin).get('usage_daily', 0))" 2>/dev/null || echo 0)

    # tee -a: muestra en vivo Y persiste; sin buffering de tail
    "$PYTHON" "$SCRIPT_DIR/run_eval.py" \
        --api-url "$API_URL" \
        --golden-json "$GOLDEN_JSON" \
        --scenario-name "$name" \
        --search-method "$method" \
        --search-type tickets_only \
        --k "$K" \
        --delay "$DELAY" \
        --judge-model "$JUDGE_MODEL" \
        --limit "$LIMIT" \
        --output-dir "$OUT_DIR" \
        ${API_KEY:+--api-key "$API_KEY"} \
        2>&1 | tee -a "$LOG_FILE"

    local exit_code=${PIPESTATUS[0]}
    if [ $exit_code -ne 0 ]; then
        echo "  ❌ [$name] terminó con error (exit $exit_code) — $(date '+%H:%M:%S')"
        return $exit_code
    fi

    # Costo del escenario
    local usage_after
    usage_after=$(openrouter_usage | "$PYTHON" -c "import json,sys; print(json.load(sys.stdin).get('usage_daily', 0))" 2>/dev/null || echo 0)
    local cost
    cost=$(echo "$usage_after - $usage_before" | "$PYTHON" -c "import sys; print(f'{float(sys.stdin.read()):.4f}')" 2>/dev/null || echo "?")
    echo "  ✅ [$name] completado — $(date '+%H:%M:%S') | costo judge ≈ \$$cost"
    return 0
}

# ── Escenario 1: Vector Only ──
run_scenario "m2_rerun_vector_only" "vector_only"
VEC_STATUS=$?

# ── Escenario 2: Hybrid (BM25 + Vector) ──
run_scenario "m2_rerun_hybrid" "hybrid"
HYB_STATUS=$?

# ── Resumen final ──
echo ""
echo "======================================================================"
echo "  RESUMEN FINAL — $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"
echo "  vector_only: $( [ $VEC_STATUS -eq 0 ] && echo '✅ OK' || echo "❌ exit $VEC_STATUS")"
echo "  hybrid:      $( [ $HYB_STATUS -eq 0 ] && echo '✅ OK' || echo "❌ exit $HYB_STATUS")"
echo ""

# ── Costo total del día (delta de usage_daily) ──
USAGE_END=$(openrouter_usage)
BALANCE_END=$(echo "$USAGE_END" | "$PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(d.get('balance','?'))" 2>/dev/null || echo "?")
COST_DAY=$(echo "$USAGE_END" | "$PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(round(d.get('usage_daily',0),4))" 2>/dev/null || echo "?")
echo "  OpenRouter — uso acumulado de HOY: \$$COST_DAY | saldo actual: \$$BALANCE_END"
echo "  (el costo por escenario se mostró al completar cada uno; el delta de usage_daily"
echo "   es la mejor aproximación del costo del judge durante la corrida)"
echo ""
echo "  Log completo: $LOG_FILE"
echo "  CSVs:"
ls -1 "$OUT_DIR"/m2_rerun_*_golden_se_200_*.csv 2>/dev/null | sed 's/^/    /'
echo ""
echo "  💤 Listo — podés ir a dormir."
echo "======================================================================"
