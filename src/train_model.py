import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pyspark.ml.classification import (GBTClassifier, LogisticRegression,
                                       RandomForestClassifier)
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.feature import VectorAssembler

from configs import config
from src.utils import get_spark_session


def main():
    spark = get_spark_session("OULAD_Training", config.MASTER)
    spark.sparkContext.setLogLevel("ERROR")
    
    # Read processed data
    print(f">>> [TRAIN] Reading processed data from: {config.HDFS_OUTPUT_PATH}")
    try:
        df = spark.read.parquet(config.HDFS_OUTPUT_PATH)
    except Exception as e:
        print(">>> ERROR: Processed data not found. Ensure ETL step ran successfully.")
        raise e
    
    # Feature Engineering
    print(">>> [TRAIN] Preparing features...")
    assembler = VectorAssembler(inputCols=["total_clicks", "avg_score"], outputCol="features")
    data_vectorized = assembler.transform(df)
    
    # Split Data (80% Train, 20% Test)
    train_data, test_data = data_vectorized.randomSplit([0.8, 0.2], seed=42)
    
    # Define Models to Train
    # We will loop through this list to train multiple algorithms
    classifiers = {
        "Logistic Regression": LogisticRegression(labelCol="label", featuresCol="features"),
        "Random Forest": RandomForestClassifier(labelCol="label", featuresCol="features", numTrees=20),
        "Gradient Boosted Trees": GBTClassifier(labelCol="label", featuresCol="features", maxIter=20, maxDepth=5)
    }

    evaluator = BinaryClassificationEvaluator(labelCol="label")
    
    print(f"STARTING MODEL TRAINING & EVALUATION")

    best_model_name = ""
    best_auc = 0.0

    # Training Loop
    for name, algo in classifiers.items():
        print(f"\n>>> Training {name}...")
        start_time = time.time()
        
        # Train
        model = algo.fit(train_data)
        
        # Predict
        predictions = model.transform(test_data)
        
        # Evaluate
        auc = evaluator.evaluate(predictions)
        duration = time.time() - start_time
        
        print(f"-> Finished in {duration:.2f}s")
        print(f"-> AUC Score: {auc:.4f}")

        # Track Best Model
        if auc > best_auc:
            best_auc = auc
            best_model_name = name

    print(f"FINAL RESULTS")
    print(f"Best Performing Model: {best_model_name}")
    print(f"Best AUC Score: {best_auc:.4f}")
    
    spark.stop()

if __name__ == "__main__":
    main()