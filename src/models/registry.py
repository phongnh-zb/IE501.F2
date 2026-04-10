import os
from datetime import datetime

from configs.config import HDFS_MODEL_PATH


def save_model(model, model_name, run_id=None):
    if model is None:
        print(">>> [REGISTRY] No model to save — skipping.")
        return None

    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Sanitise model name for use as a path segment
    safe_name = model_name.replace(" ", "_").lower()
    path      = os.path.join(HDFS_MODEL_PATH, f"{safe_name}_{run_id}")

    print(f">>> [REGISTRY] Saving {model_name} to {path} ...")
    try:
        model.write().overwrite().save(path)
        print(f">>> [REGISTRY] Model saved successfully.")
        return path
    except Exception as e:
        print(f">>> [REGISTRY] Save failed: {e}")
        return None


def load_model(model_class, model_name, run_id):
    safe_name = model_name.replace(" ", "_").lower()
    path      = os.path.join(HDFS_MODEL_PATH, f"{safe_name}_{run_id}")
    print(f">>> [REGISTRY] Loading {model_name} from {path} ...")
    try:
        model = model_class.load(path)
        print(f">>> [REGISTRY] Model loaded successfully.")
        return model
    except Exception as e:
        print(f">>> [REGISTRY] Load failed: {e}")
        return None


def list_saved_models(spark):
    try:
        fs    = spark._jvm.org.apache.hadoop.fs.FileSystem.get(spark._jsc.hadoopConfiguration())
        path  = spark._jvm.org.apache.hadoop.fs.Path(HDFS_MODEL_PATH)
        if not fs.exists(path):
            return []
        statuses = fs.listStatus(path)
        return sorted([str(s.getPath().getName()) for s in statuses])
    except Exception as e:
        print(f">>> [REGISTRY] Cannot list models: {e}")
        return []