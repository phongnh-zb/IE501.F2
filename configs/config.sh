# Shell mirror of configs/config.py.
# When a value changes in config.py it must be updated here too.
# Usage: . "$(cd "$(dirname "$0")/.." && pwd)/configs/config.sh"
#
# Python-only constants (not mirrored here):
#   FILE_*   — individual CSV filenames read by PySpark; no shell script needs them
#   APP_NAME — Spark session name; shell scripts never create a SparkSession

HDFS_NAMENODE="hdfs://localhost:9000"
HDFS_BASE_PATH="${HDFS_NAMENODE}/user/ie501/oulad_raw"
HDFS_OUTPUT_PATH="${HDFS_NAMENODE}/user/ie501/oulad_processed"
HDFS_MODEL_PATH="${HDFS_NAMENODE}/user/ie501/models"

MASTER="local[*]"

HBASE_HOST="localhost"
HBASE_PORT=9090
HBASE_THRIFT_INFO_PORT=9095
TABLE_NAME="student_predictions"
MODEL_RESULTS_TABLE="model_evaluations"
CACHE_INTERVAL=600

FLASK_PORT=5001