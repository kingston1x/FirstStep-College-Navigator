#!/usr/bin/env bash
# run.sh — FirstStep full pipeline runner (macOS / Linux)
# Usage: bash run.sh
# Run from the repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

BOLD='\033[1m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

step() { echo -e "\n${BOLD}${GREEN}[$1]${NC} $2"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
die()  { echo -e "${RED}[error]${NC} $1"; exit 1; }

echo -e "${BOLD}================================================${NC}"
echo -e "${BOLD}  FirstStep — Full Pipeline Runner (macOS)${NC}"
echo -e "${BOLD}================================================${NC}"

# ── Step 0: Virtual environment ───────────────────────────────────────────────
step "0/5" "Setting up virtual environment..."

if [ ! -f ".venv/bin/activate" ]; then
    echo "  No .venv found — creating one..."
    python3 -m venv .venv || die "Failed to create virtual environment."
fi

source .venv/bin/activate
echo "  Python: $(python --version)"

# ── Step 1: Install dependencies (skip if nothing changed) ────────────────────
step "1/5" "Checking dependencies..."

HASH_FILE=".venv/install.hash"
NEW_HASH=$(md5 -q backend/requirements.txt frontend/requirements.txt 2>/dev/null || \
           md5sum backend/requirements.txt frontend/requirements.txt | awk '{print $1}' | tr -d '\n')
OLD_HASH=""
[ -f "$HASH_FILE" ] && OLD_HASH=$(cat "$HASH_FILE")

if [ "$NEW_HASH" = "$OLD_HASH" ]; then
    echo "  Dependencies unchanged — skipping install."
else
    echo "  Installing backend dependencies..."
    pip install -q -r backend/requirements.txt || die "Backend pip install failed."
    echo "  Installing frontend dependencies..."
    pip install -q -r frontend/requirements.txt || die "Frontend pip install failed."
    echo "$NEW_HASH" > "$HASH_FILE"
    echo "  Done."
fi

# ── Step 2: Clean the data ────────────────────────────────────────────────────
step "2/5" "Running cleaner.py..."

python backend/cleaner.py \
    --input  data/raw/Scholarships.csv \
    --output data/clean/scholarships_clean.csv \
    || die "cleaner.py failed."

echo "  Cleaned CSV written to data/clean/scholarships_clean.csv"

# ── Step 3: Matcher self-test ──────────────────────────────────────────────────
step "3/5" "Running matcher.py self-test..."

python backend/matcher.py --csv data/clean/scholarships_clean.csv \
    || die "matcher.py self-test failed."

# ── Step 4: Evaluate ──────────────────────────────────────────────────────────
step "4/5" "Evaluating model..."

python backend/evaluate.py \
    --csv   data/clean/scholarships_clean.csv \
    --truth evaluation/ground_truth.csv \
    || die "evaluate.py failed."

# ── Step 5: Launch backend + frontend ─────────────────────────────────────────
step "5/5" "Starting backend and frontend..."

export SCHOLARSHIPS_CSV="$REPO_ROOT/data/clean/scholarships_clean.csv"

# Load .env if present (for GEMINI_API_KEY etc.)
if [ -f ".env" ]; then
    set -a; source .env; set +a
    echo "  Loaded .env"
fi

# Kill any leftover processes on our ports when this script exits
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    [ -n "${BACKEND_PID:-}" ]  && kill "$BACKEND_PID"  2>/dev/null || true
    [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start Flask backend
python backend/app.py &
BACKEND_PID=$!
echo "  Backend started (PID $BACKEND_PID, port 5000)"

echo "  Waiting for backend to boot..."
sleep 3

# Verify backend is up before launching frontend
if ! curl -sf http://localhost:5000/ > /dev/null 2>&1; then
    warn "Backend health check failed — frontend may not show results until it's ready."
fi

# Start Streamlit frontend
(cd frontend && streamlit run app.py) &
FRONTEND_PID=$!
echo "  Frontend started (PID $FRONTEND_PID)"

echo ""
echo -e "${BOLD}================================================${NC}"
echo -e "  Backend  → http://localhost:5000"
echo -e "  Frontend → http://localhost:8501"
echo -e "${BOLD}================================================${NC}"
echo -e "  Press ${BOLD}Ctrl+C${NC} to stop both servers."
echo ""

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
