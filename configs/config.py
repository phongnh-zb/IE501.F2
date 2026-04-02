JAVA_17_HOME = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"

HDFS_NAMENODE = "hdfs://localhost:9000"
HDFS_BASE_PATH = f"{HDFS_NAMENODE}/user/ie501/oulad_raw/"
HDFS_OUTPUT_PATH = f"{HDFS_NAMENODE}/user/ie501/oulad_processed/"
HDFS_MODEL_PATH = f"{HDFS_NAMENODE}/user/ie501/models/"

FILE_STUDENT_INFO = "studentInfo.csv"
FILE_STUDENT_VLE = "studentVle.csv"
FILE_STUDENT_ASSESSMENT = "studentAssessment.csv"

APP_NAME = "OULAD_Pipeline"
MASTER = "local[*]"

HBASE_HOST = "localhost"
HBASE_PORT = 9090
TABLE_NAME = "student_predictions"
CACHE_INTERVAL = 600