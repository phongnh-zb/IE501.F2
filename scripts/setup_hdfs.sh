#!/bin/bash

# Local data directory path (relative to this script)
LOCAL_DATA_DIR="$(cd "$(dirname "$0")/../data/raw" && pwd)"
# Destination path on HDFS
HDFS_DEST_DIR="/user/ie400/oulad_raw"

# Create directory on HDFS
echo ">>> Creating HDFS directory: $HDFS_DEST_DIR"
hdfs dfs -mkdir -p $HDFS_DEST_DIR

# Upload data
echo ">>> Uploading files from $LOCAL_DATA_DIR to HDFS..."

# Only upload .csv files to avoid uploading nested processed folders
hdfs dfs -put -f $LOCAL_DATA_DIR/*.csv $HDFS_DEST_DIR/

# Verify results
hdfs dfs -ls $HDFS_DEST_DIR/

echo ">>> Completed! Data is ready on HDFS."