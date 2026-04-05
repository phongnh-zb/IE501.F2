#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PROJECT_ROOT/configs/config.sh"

# Local data directory path (relative to this script)
LOCAL_DATA_DIR="$PROJECT_ROOT/data/raw"

# Create directory on HDFS
echo ">>> Creating HDFS directory: $HDFS_BASE_PATH"
hdfs dfs -mkdir -p "$HDFS_BASE_PATH"

# Upload data
echo ">>> Uploading files from $LOCAL_DATA_DIR to HDFS..."

# Only upload .csv files to avoid uploading nested processed folders
hdfs dfs -put -f "$LOCAL_DATA_DIR"/*.csv "$HDFS_BASE_PATH"

# Verify results
hdfs dfs -ls "$HDFS_BASE_PATH"

echo ">>> Completed! Data is ready on HDFS."