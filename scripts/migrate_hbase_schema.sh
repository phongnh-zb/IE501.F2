#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PROJECT_ROOT/configs/config.sh"

echo ">>> [MIGRATE] Checking HBase schema..."

# ── Required schema ───────────────────────────────────────────────────────────
# Format: "TABLE_VAR:cf1 cf2 cf3"
# Add new column families here as the project evolves.
SCHEMA=(
    "$TABLE_NAME:info prediction"
    "$MODEL_RESULTS_TABLE:metrics info importance tuning"
)

# ── Check and migrate each table ──────────────────────────────────────────────
MIGRATED=0

for ENTRY in "${SCHEMA[@]}"; do
    TABLE="${ENTRY%%:*}"
    FAMILIES="${ENTRY##*:}"

    DESCRIBE=$(echo "describe '$TABLE'" | hbase shell 2>/dev/null)

    # Skip if table does not exist yet — ensure_table creates it on first write
    if ! echo "$DESCRIBE" | grep -q "NAME =>"; then
        echo "  Table '$TABLE' not found — skipping (will be created on first run)."
        continue
    fi

    for CF in $FAMILIES; do
        if echo "$DESCRIBE" | grep -q "NAME => '$CF'"; then
            : # already present — no-op
        else
            echo ">>> [MIGRATE] Adding column family '$CF' to '$TABLE'..."
            echo "alter '$TABLE', NAME => '$CF'" | hbase shell 2>/dev/null \
                && echo "    ✔ '$CF' added to '$TABLE'." \
                || echo "    ✘ Failed to add '$CF' to '$TABLE'."
            MIGRATED=$((MIGRATED + 1))
        fi
    done
done

if [ "$MIGRATED" -eq 0 ]; then
    echo "✔ Schema is up to date — no migration needed."
fi