#!/usr/bin/env bash
# ============================================================
# M6 — Benchmark de generadores (Opción C: golden estratificado 75, k=10)
# Judge: openai/gpt-5.6-luna | Métricas: correctness, faithfulness, answer_relevancy
#
# k=10 = mismo k que la corrida final de M4 (voyage4lite_baseline_final) y que
# el default de producción (unified_search / context_retriever). Comparabilidad
# directa con M4: las 50 queries de M4 están dentro del golden 75.
#
# Requiere:
#   - API local corriendo en $API_URL (default http://localhost:8000)
#   - api/.env con OPENROUTER_API_KEY (+ APP_API_KEY si el endpoint pide auth)
#   - Venv con deepeval: api/tarea2/bin/python
#
# Uso:   ./scripts/run_m6_benchmark.sh
# Logs:  evaluation_notebooks/raw_results/m6optc_<tag>.log  (+ CSV/JSON agregado)
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."   # api/
PY="$(pwd)/tarea2/bin/python"
GOLDEN="../evaluation_notebooks/goldens/golden_se_75_estratificado.json"
OUT="../evaluation_notebooks/raw_results"
API_URL="${API_URL:-http://localhost:8000}"
JUDGE="openai/gpt-5.6-luna"
K="${K:-10}"

# ── Sanity checks ──
if ! curl -s -m 5 -o /dev/null -w "%{http_code}" "$API_URL/" | grep -q 200; then
  echo "❌ API no responde en $API_URL — ¿está corriendo uvicorn?" >&2
  exit 1
fi
[ -f "$GOLDEN" ] || { echo "❌ Golden no existe: $GOLDEN" >&2; exit 1; }
[ -x "$PY" ] || { echo "❌ Python del venv no encontrado: $PY" >&2; exit 1; }

echo "== Benchmark M6 (Opción C) — judge: $JUDGE | k=$K =="
echo "Golden: $GOLDEN ($(wc -l < "$GOLDEN") entradas)"

# ── Corridas secuenciales (1 generador a la vez) ──
for spec in \
  "deepseek|deepseek/deepseek-v4-flash" \
  "ling|inclusionai/ling-2.6-flash" \
  "gemini|google/gemini-3.5-flash-lite"; do
  tag="${spec%%|*}"
  model="${spec##*|}"
  echo ""
  echo "▶ [$tag] generando con $model ..."

  # ── Modo resume: si ya existe un CSV de esta corrida, continuar sobre él ──
  append_args=()
  if compgen -G "$OUT/m6optc_${tag}_golden_se_75_estratificado_*.csv" > /dev/null; then
    existing_csv=$(ls -t "$OUT"/m6optc_${tag}_golden_se_75_estratificado_*.csv | head -1)
    echo "  ↻ Resume detectado: $(basename "$existing_csv") — se saltan las queries ya evaluadas"
    append_args=(--append-to "$existing_csv")
  fi

  "$PY" scripts/run_eval.py \
    --api-url "$API_URL" \
    --golden-json "$GOLDEN" \
    --scenario-name "m6optc_$tag" \
    --search-method vector_only \
    --search-type tickets_only \
    --k "$K" \
    --judge-model "$JUDGE" \
    --metrics correctness faithfulness answer_relevancy \
    --generator-model "$model" \
    "${append_args[@]}" \
    > "$OUT/m6optc_$tag.log" 2>&1
  echo "✅ [$tag] listo → $OUT/m6optc_$tag.log"
done

echo ""
echo "=== BENCHMARK M6 (Opción C) COMPLETO ==="
echo "Resultados: $OUT/m6optc_*_aggregate.json"
