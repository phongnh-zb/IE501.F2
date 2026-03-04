# Student Dropout Prediction System

A Big Data pipeline and monitoring dashboard designed to predict student dropout risks in real-time. This system processes massive educational datasets using **Apache Spark**, stores predictions in **HBase**, and visualizes actionable insights via a **Flask** web application.

---

## System Architecture

The project follows a standard Big Data ETL & Machine Learning pipeline:

1.  **Data Ingestion:** Raw student logs (CSV) are uploaded to **HDFS**.
2.  **Processing (ETL):** **PySpark** cleans, aggregates, and transforms the raw data.
3.  **Machine Learning:** Spark ML models (**Logistic Regression**, **Random Forest Classifier**, and **GBT Classifier**) are trained to predict the "Risk Probability" based on _Average Scores_ and _Interaction Clicks_.
4.  **Storage:** Predictions are stored in **HBase** for low-latency access.
5.  **Visualization:** A **Flask** web app fetches data via **Thrift** and displays it on a real-time dashboard.

---

## Prerequisites

Ensure the following software is installed and configured on your machine:

- **Operating System:** Linux / Windows/ macOS.
- **Java:** JDK 8, 11, or 17 (Required for Hadoop/Spark).
- **Hadoop:** v3.x (HDFS & YARN running).
- **Spark:** v3.x (with PySpark).
- **HBase:** v2.x (Standalone or Pseudo-distributed).
- **Python:** v3.9+.

---

## Prepare Data

Before running the project, you must download the dataset and place it in the correct folder.

1.  **Download Dataset:**
    This project uses the **Open University Learning Analytics Dataset (OULAD)**.

2.  **Setup Folder Structure:**
    Create a `data/` folder in the project root and extract the files there. You need these 3 specific files:

    ```text
    IE501.F2/
    ├── data/
    │   ├── processed/             # Empty folder for intermediate results
    │   └── raw/                   # Place your CSV files here
    │       ├── assessments.csv
    │       ├── courses.csv
    │       ├── studentAssessment.csv
    │       ├── studentInfo.csv
    │       ├── studentRegistration.csv
    │       ├── studentVle.csv
    │       └── vle.csv
    ```

---

## Installation

1.  **Clone the Repository:**

```bash
git clone git@github.com:phongnh-zb/IE501.F2.git
cd IE501.F2
```

2.  **Install Python Dependencies:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Project Structure

```text
IE501.F2/
├── main.py                   # MASTER SCRIPT (Runs the entire pipeline)
├── README.md                 # Project Documentation
├── requirements.txt          # Python dependencies
├── data/                     # Raw datasets (place your CSVs here)
├── scripts/                  # Shell scripts for automation
│   ├── start_services.sh     # Starts Hadoop, HBase, and Thrift
│   ├── setup_hdfs.sh         # Uploads local data to HDFS
    └── run_job.sh            # Runs Spark jobs manually
├── src/                      # Source Code for Big Data Jobs
│   ├── etl_job.py            # Cleans and aggregates data (Spark)
│   ├── train_model.py        # Trains ML Model (Spark ML)
│   ├── save_to_hbase.py      # Writes results to HBase
│   └── utils.py              # Helper functions (Spark Session)
└── webapp/                   # Web Application
    ├── app.py                # Flask Backend
    ├── templates/            # HTML Templates
    │   ├── index.html        # Dashboard
    │   ├── students.html     # Student List
    │   ├── navbar.html       # Partial Component
    │   └── footer.html       # Partial Component
    └── static/               # JS & CSS
        └── js/               # Frontend Logic
```

---

## How to Run

### Option 1: Automatic Execution (Recommended)

We have provided a master orchestrator script that starts services, cleans data, trains the model, and updates the database in one go.

```bash
python3 main.py
```

Wait for the script to print `SUCCESS! ENTIRE PIPELINE COMPLETED`.

### Option 2: Manual Execution

If you want to run step-by-step for debugging:

1. **Start Services:**

```bash
./scripts/start_services.sh
```

2. **Set up HDFS:**

```bash
./scripts/setup_hdfs.sh
```

3. **Run ETL & Training:**

```bash
./scripts/run_job.sh
```

---

## Launching the Web Dashboard

Once the pipeline has successfully saved data to HBase, start the web server:

1. **Run Flask App:**

```bash
python3 webapp/app.py
```

2. **Access the Dashboard:**
   Open your browser and navigate to: **http://localhost:5001**

---

## Troubleshooting

### Web App shows "System Loading..." forever

- **Cause:** The Flask app cannot find any data in the In-Memory Cache (usually because HBase is empty or the pipeline hasn't run).
- **Solution:**
  - Check if HBase is running: `jps | grep HMaster`
  - Check if data was written: Run `hbase shell` then `count 'student_predictions'`.
  - Restart the pipeline: `python3 main.py`.

### Connection Refused (Port 9090)

- **Cause:** HBase Thrift server is not running or crashed.
- **Solution:**
  - Run: `hbase thrift start -p 9090`
  - Check logs: `tail -f logs/hbase-*-thrift-*.log`

### Address already in use (Port 5001)

- **Cause:** The Flask app is already running in another terminal.
- **Solution:**
  - Find the process: `lsof -i :5001`
  - Kill it: `kill -9 <PID>`

### Windows/WSL2 Issues

- **Cause:** Line ending differences (`CRLF` vs `LF`) in shell scripts causes syntax errors.
- **Solution:** Run `dos2unix scripts/*.sh` before executing to fix the format.
