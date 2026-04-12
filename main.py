import os
import socket
import subprocess
import sys
import time

GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
RESET  = '\033[0m'
BLUE   = '\033[94m'


def print_header(step_name):
    print("\n" + "=" * 60)
    print(f"{BLUE}>>> STEP: {step_name}{RESET}")
    print("=" * 60)


def run_command(command, step_name):
    """Run a shell command, print timing, return success bool."""
    print_header(step_name)
    start_time = time.time()
    try:
        subprocess.run(command, shell=True, check=True, text=True)
        duration = time.time() - start_time
        print(f"\n{GREEN}✔ COMPLETED: {step_name} in {duration:.2f} seconds.{RESET}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n{RED}✘ FAILED: {step_name} encountered an error! (Code: {e.returncode}){RESET}")
        return False


def run_step(fn, step_name):
    """Call a Python function in-process, print timing, return success bool."""
    print_header(step_name)
    start_time = time.time()
    try:
        fn()
        duration = time.time() - start_time
        print(f"\n{GREEN}✔ COMPLETED: {step_name} in {duration:.2f} seconds.{RESET}")
        return True
    except Exception as e:
        print(f"\n{RED}✘ FAILED: {step_name} — {e}{RESET}")
        return False


def wait_for_service(host, port, service_name, timeout=60):
    print(f">>> [HBASE] Waiting for {service_name} to fully start (Port {port})...", end="", flush=True)
    start_wait = time.time()
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(f"\n✔ {service_name} is ready.{RESET}")
                return True
        except Exception:
            pass
        if time.time() - start_wait > timeout:
            print(f"\n{RED}✘ ERROR: Timed out waiting for {service_name}. Please check logs.{RESET}")
            return False
        time.sleep(1)
        print(".", end="", flush=True)


def main():
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    from src.etl_job import main as run_etl
    from src.save_to_hbase import main as run_hbase
    from src.train_job import main as run_train

    total_start = time.time()
    print(f"{YELLOW}>>> STARTING STUDENT DROPOUT PREDICTION PIPELINE PROCESS{RESET}")
    print(f"Project Directory: {PROJECT_ROOT}\n")

    # --- STEP 0: VERIFY ENVIRONMENT ---
    if not run_command(f"bash {PROJECT_ROOT}/scripts/verify_env.sh", "0. VERIFY ENVIRONMENT"):
        sys.exit(1)

    # --- STEP 1: START INFRASTRUCTURE (shell — Hadoop/HBase/Thrift) ---
    def _start_services():
        subprocess.run(
            f"bash {PROJECT_ROOT}/scripts/start_services.sh",
            shell=True, check=True, text=True,
        )
        if not wait_for_service('localhost', 9090, "HBase Thrift Server"):
            raise RuntimeError("HBase Thrift Server did not become ready in time.")

    if not run_step(_start_services, "1. START SERVICES (HADOOP/HBASE)"):
        sys.exit(1)

    # --- STEP 2: DATA INGESTION (shell — hdfs dfs -put) ---
    if not run_command(f"bash {PROJECT_ROOT}/scripts/setup_hdfs.sh", "2. INGEST DATA TO HDFS"):
        sys.exit(1)

    # --- STEP 3: ETL (in-process Spark job) ---
    if not run_step(run_etl, "3. PROCESS DATA (ETL - SPARK)"):
        sys.exit(1)

    # --- STEP 4: MODEL TRAINING (in-process Spark ML) ---
    if not run_step(run_train, "4. TRAIN MODEL"):
        sys.exit(1)

    # --- STEP 5: SAVE TO HBASE (in-process HappyBase write) ---
    if not run_step(run_hbase, "5. SAVE RESULTS TO HBASE"):
        sys.exit(1)

    total_duration = time.time() - total_start
    print("\n" + "=" * 60)
    print(f"{GREEN}SUCCESS! ENTIRE PIPELINE COMPLETED IN {total_duration:.2f}s{RESET}")
    print("=" * 60)


if __name__ == "__main__":
    main()