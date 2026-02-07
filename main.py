import os
import socket
import subprocess
import sys
import time

# --- COLOR CONFIGURATION ---
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BLUE = '\033[94m'

def print_header(step_name):
    print("\n" + "="*60)
    print(f"{BLUE}>>> STEP: {step_name}{RESET}")
    print("="*60)

def run_command(command, step_name):
    print_header(step_name)
    start_time = time.time()
    
    try:
        # Run command and show output directly
        result = subprocess.run(command, shell=True, check=True, text=True)
        duration = time.time() - start_time
        print(f"\n{GREEN}✔ COMPLETED: {step_name} in {duration:.2f} seconds.{RESET}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n{RED}✘ FAILED: {step_name} encountered an error! (Code: {e.returncode}){RESET}")
        return False

def wait_for_service(host, port, service_name, timeout=60):
    print(f"⏳ Waiting for {service_name} to fully start (Port {port})...", end="", flush=True)
    start_wait = time.time()
    
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"\n{GREEN}✔ {service_name} is ready!{RESET}")
                return True
        except Exception:
            pass

        # Check for timeout
        if time.time() - start_wait > timeout:
            print(f"\n{RED}✘ ERROR: Timed out waiting for {service_name}. Please check logs.{RESET}")
            return False
        
        # Wait 1s before retrying
        time.sleep(1)
        print(".", end="", flush=True)

def main():
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    total_start = time.time()

    print(f"{YELLOW}>>> STARTING STUDENT DROPOUT PREDICTION PIPELINE PROCESS{RESET}")
    print(f"Project Directory: {PROJECT_ROOT}\n")

    # --- STEP 1: START INFRASTRUCTURE (SERVICES) ---
    # Call shell script to start Hadoop/HBase/Thrift if not running
    cmd_services = f"bash {PROJECT_ROOT}/scripts/start_services.sh"
    if not run_command(cmd_services, "1. START SERVICES (HADOOP/HBASE)"):
        sys.exit(1)

    # Important: Python must wait for Thrift (Port 9090) to actually open a connection
    # Because the shell script only sends the "start" command and exits while Java is still loading in the background.
    if not wait_for_service('localhost', 9090, "HBase Thrift Server"):
        print(f"{RED}Stopping program because infrastructure is not ready.{RESET}")
        sys.exit(1)

    # --- STEP 2: DATA INGESTION ---
    cmd_ingest = f"bash {PROJECT_ROOT}/scripts/setup_hdfs.sh"
    if not run_command(cmd_ingest, "2. INGEST DATA TO HDFS"): sys.exit(1)

    # --- STEP 3: ETL PROCESSING (Spark) ---
    cmd_etl = f"python3 {PROJECT_ROOT}/src/etl_job.py"
    if not run_command(cmd_etl, "3. PROCESS DATA (ETL - SPARK)"): sys.exit(1)

    # --- STEP 4: MODEL TRAINING (Spark ML) ---
    cmd_train = f"python3 {PROJECT_ROOT}/src/train_model.py"
    if not run_command(cmd_train, "4. TRAIN MODEL"): sys.exit(1)

    # --- STEP 6: SAVE TO HBASE ---
    cmd_hbase = f"python3 {PROJECT_ROOT}/src/save_to_hbase.py"
    if not run_command(cmd_hbase, "5. SAVE RESULTS TO HBASE"): sys.exit(1)

    # --- SUMMARY ---
    total_duration = time.time() - total_start
    print("\n" + "="*60)
    print(f"{GREEN}SUCCESS! ENTIRE PIPELINE COMPLETED IN {total_duration:.2f}s{RESET}")
    print("="*60)

if __name__ == "__main__":
    main()