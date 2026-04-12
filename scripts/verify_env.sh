#!/bin/bash
# Verifies that all tools required by the pipeline are installed and accessible.
# Exits with code 1 on the first missing dependency so main.py can abort early.

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PROJECT_ROOT/configs/config.sh"

GREEN='\033[0;32m'; RED='\033[0;31m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✔  $1${RESET}"; }
fail() { echo -e "${RED}✘  $1${RESET}"; exit 1; }

echo ">>> [ENV] Verifying environment..."

command -v java        >/dev/null 2>&1 && ok "java"        || fail "java not found — install JDK 8/11/17"
command -v hadoop      >/dev/null 2>&1 && ok "hadoop"      || fail "hadoop not found — check HADOOP_HOME"
command -v spark-submit>/dev/null 2>&1 && ok "spark-submit" || fail "spark-submit not found — check SPARK_HOME"
command -v hbase       >/dev/null 2>&1 && ok "hbase"       || fail "hbase not found — check HBASE_HOME"
command -v python3     >/dev/null 2>&1 && ok "python3"     || fail "python3 not found"

python3 - <<'EOF'
import importlib.util, sys
missing = [p for p in ["pyspark","happybase","flask","reportlab"] if not importlib.util.find_spec(p)]
if missing:
    print(f"\033[91m✘  Missing Python packages: {', '.join(missing)}\033[0m")
    print("   Run: pip install -r requirements.txt")
    sys.exit(1)
EOF
[ $? -eq 0 ] && ok "Python packages"

echo -e "✔ Environment is OK.${RESET}"