#!/usr/bin/env bash
# =============================================================================
# bootstrap_envs.sh — recreate the project's Python environments from scratch.
#
# Three isolated environments:
#   api              -> api/tarea2                    (RAG service)
#   backend          -> agent_app/backend/backend_venv (LangGraph agent)
#   frontend         -> agent_app/frontend/frontend_venv (Streamlit UI)
#
# Usage:
#   ./scripts/bootstrap_envs.sh                 # create missing envs only
#   ./scripts/bootstrap_envs.sh --recreate      # delete and rebuild all
#   ./scripts/bootstrap_envs.sh --only api      # one target (api|backend|frontend)
#   ./scripts/bootstrap_envs.sh --check         # verify only, never installs
#   ./scripts/bootstrap_envs.sh --with-eval     # api: add requirements.eval.txt
#   ./scripts/bootstrap_envs.sh --with-dev      # api: add requirements.dev.txt (implies eval)
#   ./scripts/bootstrap_envs.sh --lock          # write requirements.lock.txt per env
#   ./scripts/bootstrap_envs.sh --python 3.13   # force interpreter
#
# Requires Python 3.12 or 3.13. Exits non-zero on any failure.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ── Defaults ─────────────────────────────────────────────────────────────────
TARGETS=()
RECREATE=0
CHECK_ONLY=0
WITH_EVAL=0
WITH_DEV=0
WRITE_LOCK=0
PYTHON_BIN_OVERRIDE=""

RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; DIM=$'\e[2m'; RST=$'\e[0m'
ok()   { printf '%s  ok  %s %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '%s warn %s %s\n' "$YEL" "$RST" "$*"; }
fail() { printf '%s FAIL %s %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
step() { printf '\n%s==>%s %s\n' "$DIM" "$RST" "$*"; }

# ── Args ─────────────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --recreate)   RECREATE=1 ;;
    --check)      CHECK_ONLY=1 ;;
    --with-eval)  WITH_EVAL=1 ;;
    --with-dev)   WITH_DEV=1; WITH_EVAL=1 ;;
    --lock)       WRITE_LOCK=1 ;;
    --python)     PYTHON_BIN_OVERRIDE="${2:-}"; shift ;;
    --only)       IFS=',' read -ra _t <<< "${2:-}"; TARGETS+=("${_t[@]}"); shift ;;
    -h|--help)    sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            fail "opción desconocida: $1 (usá --help)" ;;
  esac
  shift
done

if [ ${#TARGETS[@]} -eq 0 ]; then TARGETS=(api backend frontend); fi
for t in "${TARGETS[@]}"; do
  case "$t" in api|backend|frontend) ;; *) fail "target inválido: '$t' (api|backend|frontend)" ;; esac
done

# ── Interpreter ──────────────────────────────────────────────────────────────
find_python() {
  if [ -n "$PYTHON_BIN_OVERRIDE" ]; then
    command -v "$PYTHON_BIN_OVERRIDE" >/dev/null 2>&1 || fail "no existe el intérprete '$PYTHON_BIN_OVERRIDE'"
    echo "$PYTHON_BIN_OVERRIDE"; return
  fi
  for cand in python3.13 python3.12 python3; do
    if command -v "$cand" >/dev/null 2>&1; then
      ver="$("$cand" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "")"
      case "$ver" in
        3.13|3.12) echo "$cand"; return ;;
      esac
    fi
  done
  fail "no encontré Python 3.12 ni 3.13. Instalá uno y volvé a correr el script."
}
PYTHON="$(find_python)"
PYVER="$("$PYTHON" -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])')"

step "Intérprete: $PYTHON ($PYVER)"
case "$PYVER" in
  3.12.*|3.13.*) ok "versión soportada" ;;
  *) warn "probado en 3.12 y 3.13; '$PYVER' puede fallar" ;;
esac

# ── Target table ─────────────────────────────────────────────────────────────
venv_for()   { case "$1" in api) echo "api/tarea2";; backend) echo "agent_app/backend/backend_venv";; frontend) echo "agent_app/frontend/frontend_venv";; esac; }
reqs_for()   { case "$1" in api) echo "api/requirements.txt";; backend) echo "agent_app/backend/requirements.txt";; frontend) echo "agent_app/frontend/requirements.txt";; esac; }
workdir_for(){ case "$1" in api) echo "api";; backend) echo "agent_app/backend";; frontend) echo "agent_app/frontend";; esac; }

# ── Per-target install list ──────────────────────────────────────────────────
install_specs() {
  local t="$1"
  case "$t" in
    api)
      echo "-r requirements.txt"
      [ "$WITH_EVAL" = 1 ] && echo "-r requirements.eval.txt"
      [ "$WITH_DEV"  = 1 ] && echo "-r requirements.dev.txt"
      ;;
    *) echo "-r requirements.txt" ;;
  esac
}

# ── Verify one env ───────────────────────────────────────────────────────────
verify_env() {
  local t="$1" venv; venv="$(venv_for "$t")"
  local py="$ROOT/$venv/bin/python"
  [ -x "$py" ] || { warn "$t: falta $venv (corré sin --check para crearlo)"; return 1; }

  "$py" -c 'import sys; assert sys.version_info[:2] in ((3,12),(3,13)), sys.version' \
    || { warn "$t: intérprete inesperado"; return 1; }

  if out="$("$py" -m pip check 2>&1)"; then ok "$t: pip check limpio"; else warn "$t: pip check -> $out"; return 1; fi

  local wd; wd="$(workdir_for "$t")"
  ( cd "$ROOT/$wd" && "$py" -m compileall -q . -x '(/venv/|_venv/|tarea2/)' >/dev/null ) \
    && ok "$t: compileall" || { warn "$t: compileall falló"; return 1; }

  case "$t" in
    api)       "$py" -c 'import fastapi, motor, pinecone, deepeval, langchain_openai, openai' 2>/dev/null ;;
    backend)   "$py" -c 'import fastapi, motor, langgraph, langchain_openai, httpx' 2>/dev/null ;;
    frontend)  "$py" -c 'import streamlit, requests, dotenv' 2>/dev/null ;;
  esac && ok "$t: import smoke" || { warn "$t: import smoke falló"; return 1; }
  return 0
}

# ── Modes ────────────────────────────────────────────────────────────────────
if [ "$CHECK_ONLY" = 1 ]; then
  step "Modo --check (no instala nada)"
  rc=0
  for t in "${TARGETS[@]}"; do verify_env "$t" || rc=1; done
  exit $rc
fi

for t in "${TARGETS[@]}"; do
  venv="$(venv_for "$t")"; wd="$(workdir_for "$t")"
  step "[$t] $venv"

  if [ "$RECREATE" = 1 ] && [ -d "$ROOT/$venv" ]; then
    echo "  eliminando $venv"
    rm -rf "$ROOT/$venv"
  fi

  if [ ! -x "$ROOT/$venv/bin/python" ]; then
    echo "  creando venv con $PYTHON"
    "$PYTHON" -m venv "$ROOT/$venv" || fail "$t: no pude crear el venv"
  else
    echo "  venv existente (usá --recreate para rehacerlo)"
  fi

  py="$ROOT/$venv/bin/python"
  "$py" -m pip install --quiet --upgrade pip wheel >/dev/null || fail "$t: no pude actualizar pip"

  # shellcheck disable=SC2046
  ( cd "$ROOT/$wd" && "$py" -m pip install --quiet $(install_specs "$t" | tr '\n' ' ') ) \
    || fail "$t: la instalación falló"
  ok "$t: paquetes instalados"

  verify_env "$t" || fail "$t: la verificación falló"

  if [ "$WRITE_LOCK" = 1 ] && [ "$t" = "api" ] && [ "$WITH_DEV" = 1 ]; then
    lock="$ROOT/api/requirements.lock.txt"
  else
    lock="$ROOT/$(dirname "$(reqs_for "$t")")/requirements.lock.txt"
  fi
  if [ "$WRITE_LOCK" = 1 ]; then
    { echo "# Generated by scripts/bootstrap_envs.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
      echo "# Python $PYVER — do not edit by hand; regenerate with --lock"; \
      "$py" -m pip freeze --exclude-editable; } > "$lock"
    ok "$t: lock escrito en ${lock#"$ROOT/"}"
  fi
done

step "Listo"
printf '  Verificar:      ./scripts/bootstrap_envs.sh --check\n'
printf '  Tests de API:   cd api && ./tarea2/bin/python -m pytest tests -q\n'
