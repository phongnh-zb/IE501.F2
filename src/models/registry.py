import os

from configs import config


def save_model(model, model_name, base_path=None):
    path = os.path.join(base_path or config.HDFS_MODEL_PATH, model_name.replace(" ", "_"))

    print(f">>> [REGISTRY] Saving '{model_name}' to: {path}")
    model.write().overwrite().save(path)
    print(f">>> [REGISTRY] Model saved successfully.")

    return path


def load_model(model_class, model_name, base_path=None):
    path = os.path.join(base_path or config.HDFS_MODEL_PATH, model_name.replace(" ", "_"))

    print(f">>> [REGISTRY] Loading '{model_name}' from: {path}")
    model = model_class.load(path)
    print(f">>> [REGISTRY] Model loaded successfully.")

    return model