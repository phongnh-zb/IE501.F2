import os

HDFS_NAMENODE    = "hdfs://localhost:9000"
HDFS_BASE_PATH   = f"{HDFS_NAMENODE}/user/ie501/oulad_raw/"
HDFS_OUTPUT_PATH = f"{HDFS_NAMENODE}/user/ie501/oulad_processed/"
HDFS_MODEL_PATH  = f"{HDFS_NAMENODE}/user/ie501/models/"

FILE_STUDENT_INFO         = "studentInfo.csv"
FILE_STUDENT_VLE          = "studentVle.csv"
FILE_STUDENT_ASSESSMENT   = "studentAssessment.csv"
FILE_STUDENT_REGISTRATION = "studentRegistration.csv"
FILE_ASSESSMENTS          = "assessments.csv"
FILE_VLE                  = "vle.csv"
FILE_COURSES              = "courses.csv"

APP_NAME = "OULAD_Pipeline"
MASTER   = "local[*]"

HBASE_HOST          = os.environ.get("HBASE_HOST", "localhost")
HADOOP_HOST         = os.environ.get("HADOOP_HOST", "localhost")
HBASE_PORT          = 9090
TABLE_NAME          = "student_predictions"
MODEL_RESULTS_TABLE = "model_evaluations"
CACHE_INTERVAL      = 600

FLASK_PORT  = 5001
SECRET_KEY  = os.environ.get("SECRET_KEY", "dev-key-change-before-production")
DB_PATH     = os.path.join(os.path.dirname(__file__), '..', 'data', 'auth', 'users.db')

# ── Model selection weights ───────────────────────────────────────────────────
# Weighted composite score used to pick the best model after evaluation.
# Weights must sum to 1.0. Adjust to reprioritise operational vs ranking metrics.
# cv_auc is 0.0 for non-Spark-ML models (e.g. XGBoost) — its weight still
# applies but effectively does not contribute for those models.
MODEL_SELECTION_WEIGHTS = {
    "auc":     0.40,   # discrimination across all thresholds
    "f1":      0.30,   # balanced precision/recall at deployment threshold
    "recall":  0.20,   # catching dropouts matters more than false alarms
    "cv_auc":  0.10,   # cross-validation stability
}