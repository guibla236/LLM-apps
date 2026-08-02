#!/usr/bin/env bash
set -euo pipefail

API_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$API_DIR/scripts/ingest_stackexchange_dataset.py"
VENV_PYTHON="$API_DIR/tarea2/bin/python"
LOG_DIR="$API_DIR/logs"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/ingest_pipeline_${TIMESTAMP}.log"
LATEST_LINK="$LOG_DIR/ingest_pipeline_latest.log"
ENV_FILE="$API_DIR/.env"

COMMUNITIES=(
    "devops:53"
    "networkengineering:476"
    "sharepoint:1691"
    "webapps:1906"
    "dba:2502"
    "android:2830"
    "security:3069"
    "unix:6173"
    "apple:6696"
    "serverfault:7969"
    "askubuntu:9975"
    "superuser:17425"
)

mkdir -p "$LOG_DIR"
rm -f "$LATEST_LINK"
ln -s "$LOG_FILE" "$LATEST_LINK"
exec > >(tee -a "$LOG_FILE") 2>&1

echo ""
echo "========================================================"
echo "  StackExchange Ingest Pipeline"
echo "  Inicio: $(date)"
echo "========================================================"
echo "Log: $LOG_FILE"
echo ""

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# run_py: ejecuta codigo Python con .env cargado.
# Usa heredoc para evitar problemas de quoting.
run_py() {
    "$VENV_PYTHON" /dev/stdin "${@:2}" <<PYEOF
from dotenv import load_dotenv
load_dotenv("$ENV_FILE")
$1
PYEOF
}

verify_community() {
    local comm="$1"
    local expected="$2"
    log "[VERIFY] Verificando $comm (esperado: ~$expected)..."

    local result
    result=$(run_py "
import os
from pymongo import MongoClient
try:
    client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=5000)
    db = client[os.getenv('MONGODB_DB_NAME')]
    c = db.qa_pairs.count_documents({'community': '$comm'})
    print(c)
except Exception as e:
    print(f'ERROR:{e}')
" 2>/dev/null) || result="ERROR:timeout"

    if [[ "$result" == ERROR:* ]]; then
        log "[VERIFY] ⚠ No se pudo verificar ($result)"
        return 1
    fi

    local dev=100
    if [ "$expected" -gt 0 ]; then
        local diff=$((result - expected))
        diff=${diff#-}
        dev=$((diff * 100 / expected))
    fi

    if [ "$result" -gt 0 ] && [ "$dev" -le 5 ]; then
        log "[VERIFY] OK $comm: $result / $expected (${dev}% desviacion)"
        return 0
    elif [ "$result" -gt 0 ]; then
        log "[VERIFY] WARN $comm: $result / $expected (${dev}% desviacion)"
        return 1
    else
        log "[VERIFY] FAIL $comm: vacio (deberia tener ~$expected)"
        return 1
    fi
}

verify_all() {
    log ""
    log "=== VERIFICACION GLOBAL ==="
    run_py '
import os
from pymongo import MongoClient
from pinecone import Pinecone
from collections import Counter

expected = {"superuser":17425,"askubuntu":9975,"serverfault":7969,"apple":6696,"unix":6173,"android":2830,"security":3069,"dba":2502,"webapps":1906,"sharepoint":1691,"networkengineering":476,"devops":53}

client = MongoClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=10000)
db = client[os.getenv("MONGODB_DB_NAME")]
all_comms = [d["community"] for d in db.qa_pairs.find({}, {"community": 1})]
counts = Counter(all_comms)
ok = 0
nok = 0
for comm in sorted(expected.keys()):
    actual = counts.get(comm, 0)
    exp = expected[comm]
    pct = abs(actual - exp) / exp * 100 if exp else 100
    if pct <= 5 and actual > 0:
        status = "OK"
        ok += 1
    elif actual > 0:
        status = "WARN"
        nok += 1
    else:
        status = "FAIL"
        nok += 1
    print(f"  [{status}] {comm:>25}: {actual:>6} / {exp} ({pct:.1f}%)")

total = sum(counts.values())
all_ids = list(db.qa_pairs.find({}, {"ticketId": 1}))
dups = len(all_ids) - len(set(d["ticketId"] for d in all_ids))
print(f"")
print(f"  Total MongoDB: {total} docs | Duplicados: {dups}")

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
stats = index.describe_index_stats()
ns = stats["namespaces"].get("kb-se-all", {}).get("vector_count", 0)
print(f"  Pinecone kb-se-all: {ns} vectors")
print(f"  Comunidades OK: {ok} | Faltantes/Incompletas: {nok}")
exit(0 if nok == 0 else 1)
' 2>&1
}

# ── Pipeline ─────────────────────────────────────────────────────────────────

for entry in "${COMMUNITIES[@]}"; do
    comm="${entry%%:*}"
    expected="${entry##*:}"

    log ""
    log "============================================"
    log "  Procesando: $comm ($expected pares esperados)"
    log "============================================"

    if verify_community "$comm" "$expected"; then
        log "[SKIP] $comm ya completa, saltando."
        continue
    fi

    log "[INGEST] Ejecutando ingesta de $comm..."
    if "$VENV_PYTHON" "$SCRIPT" --communities "$comm" 2>&1; then
        log "[INGEST] OK Ingesta de $comm completada."
    else
        ec=$?
        log "[INGEST] ERROR: Ingesta de $comm fallo con codigo $ec (continuando...)"
    fi

    if verify_community "$comm" "$expected"; then
        log "[VERIFY] OK Verificacion de $comm"
    else
        log "[VERIFY] WARN Verificacion de $comm muestra problemas"
    fi

    verify_all || true
    log "[INFO] Progreso: $(date)"
done

log ""
log "============================================"
log "  PIPELINE COMPLETADO"
log "  Fin: $(date)"
log "============================================"
log ""
verify_all
