# Shell mirror of configs/config.py.
# When a value changes in config.py it must be updated here too.
# Usage: . "$(cd "$(dirname "$0")/.." && pwd)/configs/config.sh"

HDFS_NAMENODE="hdfs://localhost:9000"
HDFS_BASE_PATH="${HDFS_NAMENODE}/user/ie501/oulad_raw"
HDFS_OUTPUT_PATH="${HDFS_NAMENODE}/user/ie501/oulad_processed"
HDFS_MODEL_PATH="${HDFS_NAMENODE}/user/ie501/models"

MASTER="local[*]"

HBASE_HOST="localhost"
HBASE_PORT=9090
HBASE_THRIFT_INFO_PORT=9095
TABLE_NAME="student_predictions"
CACHE_INTERVAL=600

FLASK_PORT=5001