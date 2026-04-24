# Student Dropout Prediction System

A Big Data pipeline and web dashboard for predicting student dropout risk in real time. The system processes large-scale educational data using **Apache Spark**, stores predictions in **HBase**, and visualises actionable insights via a **Flask** web application.

---

## System Architecture

The pipeline follows five sequential stages:

1. **Data Ingestion** — Raw student CSV files uploaded to HDFS at `/user/ie501/oulad_raw/`
2. **ETL** — PySpark cleans, joins, and engineers features; writes Parquet to `/user/ie501/oulad_processed/`
3. **Training** — Spark MLlib classifiers trained and evaluated with class weighting
4. **Storage** — Predictions written to HBase table `student_predictions`; model results to `model_evaluations`
5. **Visualisation** — Flask app reads from an in-memory HBase cache and renders the dashboard

---

## Prerequisites

| Software     | Version                        |
| ------------ | ------------------------------ |
| OS           | Linux / macOS / Windows (WSL2) |
| Java (JDK)   | 8, 11, or 17                   |
| Hadoop       | 3.x                            |
| Apache Spark | 3.x + PySpark                  |
| HBase        | 2.x                            |
| Python       | 3.9+                           |

---

## Dataset

This project uses the **Open University Learning Analytics Dataset (OULAD)**.  
Download and place the raw CSV files under `data/raw/`:

```
IE501.F2/
└── data/
    ├── processed/              # Auto-generated intermediate results
    └── raw/
        ├── assessments.csv
        ├── courses.csv
        ├── studentAssessment.csv
        ├── studentInfo.csv
        ├── studentRegistration.csv
        ├── studentVle.csv
        └── vle.csv
```

---

## Installation

```bash
# 1. Clone the repository
git clone git@github.com:phongnh-zb/IE501.F2.git
cd IE501.F2

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt
```

---

## Project Structure

```
IE501.F2/
├── main.py                        # Master orchestrator — runs the full pipeline
├── requirements.txt
├── Dockerfile
├── docker-compose.yaml
├── configs/
│   ├── config.py                  # Python constants (single source of truth)
│   └── config.sh                  # Shell mirror of config.py
├── scripts/
│   ├── start_services.sh          # Start Hadoop, HBase, Thrift
│   ├── stop_services.sh
│   ├── setup_hdfs.sh              # Upload local data to HDFS
│   ├── run_job.sh                 # Run Spark jobs manually
│   ├── status.sh                  # Check service health
│   ├── reset_hdfs.sh
│   └── verify_env.sh
├── common/
│   └── hbase_client.py            # HBase table utilities (ensure_table, truncate_table)
├── src/
│   ├── etl/
│   │   ├── extract.py             # Reads OULAD CSVs from HDFS
│   │   ├── transform.py           # Feature engineering (20 features incl. clicks_per_day)
│   │   └── load.py                # Writes Parquet to HDFS
│   ├── models/
│   │   ├── train.py               # Classifiers + class weighting (20 training features)
│   │   ├── evaluate.py            # AUC, Accuracy, Precision, Recall, F1, CV
│   │   ├── explain.py             # Feature importance extraction
│   │   └── registry.py           # Save/load models to HDFS
│   └── storage/
│       ├── hbase_writer.py        # Writes 19 features to HBase (excludes clicks_per_day)
│       └── model_results_writer.py
└── webapp/
    ├── app.py                     # Flask app factory
    ├── auth/
    │   ├── db.py                  # SQLite user CRUD
    │   ├── create_user.py         # CLI tool to create admin/lecturer accounts
    │   ├── models.py              # User(UserMixin), role & module access
    │   ├── routes.py              # /login, /logout
    │   ├── manager.py             # Flask-Login setup
    │   └── decorators.py          # @admin_required
    ├── routes/                    # One blueprint per page
    │   ├── api.py                 # /api/* JSON endpoints + PDF downloads
    │   ├── dashboard.py
    │   ├── students.py
    │   ├── cohort.py
    │   ├── features.py
    │   ├── models.py
    │   ├── pipeline.py
    │   ├── profile.py
    │   └── admin_users.py
    ├── services/
    │   ├── cache.py               # HBase scan → in-memory cache (10 min TTL)
    │   ├── recommendations.py     # Per-student risk recommendations
    │   └── pdf_export.py          # ReportLab PDF generation (student/cohort/model)
    ├── templates/
    └── static/
        ├── css/                   # One self-contained CSS file per page
        └── js/                    # One JS module per page
```

---

## Running the Pipeline

### Option 1 — Automatic (recommended)

```bash
python3 main.py
```

Wait for `SUCCESS! ENTIRE PIPELINE COMPLETED`.

### Option 2 — Step by step

```bash
bash scripts/start_services.sh     # Start Hadoop, HBase, Thrift
bash scripts/setup_hdfs.sh         # Upload data to HDFS
python3 main.py --step etl         # ETL only
python3 main.py --step train       # Training only
python3 main.py --step save        # Write to HBase only
```

### Option 3 — Docker

```bash
docker-compose up -d
```

---

## Web Dashboard

Start the Flask server after the pipeline has completed:

```bash
python3 webapp/app.py
# Open http://localhost:5001
```

### Creating the Admin account (if none exists)

```bash
python3 webapp/auth/create_user.py \
  --username <admin> \
  --password <password> \
  --role admin \
  --full-name "Administrator" \
  --email admin@example.com \
  --modules AAA,BBB,CCC,DDD,EEE,FFF,GGG
```

### Pages

| Page          | Access         | Description                                                         |
| ------------- | -------------- | ------------------------------------------------------------------- |
| **Login**     | Public         | Authentication · auto-lock after 5 failed attempts                  |
| **Dashboard** | All            | Risk overview · donut chart · score vs engagement scatter           |
| **Profile**   | All            | View and edit personal info · change password                       |
| **Students**  | All            | Paginated table · search/filter · detail panel · CSV & PDF export   |
| **Cohort**    | All            | Filter by module × presentation · stats strip · charts · PDF export |
| **Features**  | All            | Per-feature histograms · box plots · Pearson correlation matrix     |
| **Models**    | All            | Model comparison · feature importance · AUC history · PDF export    |
| **Pipeline**  | **Admin only** | Live Hadoop/HBase/Thrift status · deployment guide                  |
| **Users**     | **Admin only** | Lecturer CRUD · module access control · block/unblock accounts      |

---

## Machine Learning

### Classifiers

| Model                  | Weight support | Notes                                                        |
| ---------------------- | -------------- | ------------------------------------------------------------ |
| Logistic Regression    | ✓              | `maxIter=100`                                                |
| Random Forest          | ✓              | `numTrees=20, seed=42`                                       |
| Gradient Boosted Trees | ✓              | `maxIter=20, maxDepth=5, seed=42`                            |
| Linear SVC             | ✗              | Trained unweighted · AUC from decision scores (approximate)  |
| XGBoost                | ✓              | `n_estimators=100, max_depth=6` · requires `xgboost` package |

> XGBoost is included only when the `xgboost` package is available.

Class imbalance is handled via inverse-frequency class weighting applied to all models that support `weightCol`.

### Best model selection

The best model is selected automatically by a **composite score**:

```
composite = 0.40 × AUC + 0.30 × F1 + 0.20 × Recall + 0.10 × CV-AUC
```

### Risk tiers

| Tier | Label        | Meaning                |
| ---- | ------------ | ---------------------- |
| 3    | 🔴 Critical  | Very high dropout risk |
| 2    | 🟠 High Risk | High dropout risk      |
| 1    | 🟡 Watch     | Needs monitoring       |
| 0    | 🟢 Safe      | On track               |

---

## Features

**20 features** are computed during ETL (`transform.py`).  
**19** are stored in HBase and displayed in the dashboard — `clicks_per_day` is used for ML training only and is not written to HBase.

| Group              | HBase column name    | In HBase | In ML model |
| ------------------ | -------------------- | -------- | ----------- |
| **VLE Engagement** | `total_clicks`       | ✓        | ✓           |
|                    | `active_days`        | ✓        | ✓           |
|                    | `active_weeks`       | ✓        | ✓           |
|                    | `engagement_ratio`   | ✓        | ✓           |
|                    | `forum_clicks`       | ✓        | ✓           |
|                    | `quiz_clicks`        | ✓        | ✓           |
|                    | `resource_clicks`    | ✓        | ✓           |
|                    | `clicks_per_day`     | —        | ✓           |
| **Academic**       | `avg_score`          | ✓        | ✓           |
|                    | `weighted_avg_score` | ✓        | ✓           |
|                    | `submission_rate`    | ✓        | ✓           |
|                    | `avg_days_early`     | ✓        | ✓           |
|                    | `exam_score`         | ✓        | ✓           |
|                    | `tma_score`          | ✓        | ✓           |
|                    | `cma_score`          | ✓        | ✓           |
| **Registration**   | `withdrew_early`     | ✓        | ✓           |
|                    | `days_before_start`  | ✓        | ✓           |
| **Demographics**   | `num_prev_attempts`  | ✓        | ✓           |
|                    | `imd_band_encoded`   | ✓        | ✓           |
|                    | `disability_encoded` | ✓        | ✓           |

---

## HDFS Layout

```
/user/ie501/
├── oulad_raw/          # Raw OULAD CSV files
├── oulad_processed/    # Feature-engineered Parquet output
└── models/             # Saved Spark ML model artefacts
```

## HBase Tables

| Table                 | Contents                                                |
| --------------------- | ------------------------------------------------------- |
| `student_predictions` | One row per enrollment · risk tier · 19 features        |
| `model_evaluations`   | One row per training run · metrics · feature importance |

---

## Troubleshooting

**Dashboard shows "System Loading..." indefinitely**

- HBase is empty or the pipeline has not run yet.
- Verify: `hbase shell` → `count 'student_predictions'`
- Fix: `python3 main.py`

**Connection refused on port 9090**

- HBase Thrift server is not running.
- Fix: `hbase thrift start -p 9090`

**Port 5001 already in use**

- Find: `lsof -i :5001`
- Kill: `kill -9 <PID>`

**Shell script syntax errors on Windows/WSL2**

- Fix: `dos2unix scripts/*.sh`
