import os

# Java Home Configuration (Adjust if your path differs)
JAVA_17_HOME = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"

# --- HDFS CONFIGURATION (Used for Automated Pipeline) ---
# Default HDFS Address
HDFS_NAMENODE = "hdfs://localhost:9000"

# Input Path (Where setup_hdfs.sh uploaded the raw files)
HDFS_BASE_PATH = f"{HDFS_NAMENODE}/user/ie501/oulad_raw/"

# Output Path (Where etl_job.py will save processed files)
HDFS_OUTPUT_PATH = f"{HDFS_NAMENODE}/user/ie501/oulad_processed/"

# Model Path (Where trained models are saved/loaded)
HDFS_MODEL_PATH = f"{HDFS_NAMENODE}/user/ie501/models/"

# File Names
FILE_STUDENT_INFO = "studentInfo.csv"
FILE_STUDENT_VLE = "studentVle.csv"
FILE_STUDENT_ASSESSMENT = "studentAssessment.csv"

# Spark Config
APP_NAME = "OULAD_Pipeline"
MASTER = "local[*]"