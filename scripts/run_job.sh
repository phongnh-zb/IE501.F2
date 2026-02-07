#!/bin/bash

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Run ETL Step (Cleaning & Feature Engineering)
echo ">>> [STEP 1/2] Running ETL Job (etl_job.py)..."
spark-submit "$PROJECT_ROOT/src/etl_job.py"

# Check if step 1 failed, stop immediately if so
if [ $? -eq 0 ]; then
    echo ">>> ETL Successful!"
else
    echo ">>> ERROR: ETL Job failed. Stopping pipeline."
    exit 1
fi

echo "--------------------------------------------------------"

# Run Model Training Step
echo ">>> [STEP 2/2] Running Model Training (train_model.py)..."
spark-submit "$PROJECT_ROOT/src/train_model.py"

if [ $? -eq 0 ]; then
    echo ">>> Training Successful!"
else
    echo ">>> ERROR: Training Job failed."
    exit 1
fi
