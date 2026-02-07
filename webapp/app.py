import logging
import math
import threading
import time

import happybase
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# --- CONFIG ---
logging.basicConfig(level=logging.INFO)
logger = app.logger

HBASE_HOST = 'localhost'
HBASE_PORT = 9090
TABLE_NAME = 'student_predictions'
CACHE_INTERVAL = 600  # 10 minutes

# --- GLOBAL CACHE ---
SYSTEM_CACHE = {
    "data": [],         
    "last_updated": None,
    "is_ready": False   
}

def fetch_all_data_from_hbase():
    """Background Task: Sync HBase to RAM"""
    connection = None
    data_buffer = []
    
    try:
        logger.info(">>> [CACHE] Starting data synchronization from HBase...")
        start_time = time.time()
        
        connection = happybase.Connection(host=HBASE_HOST, port=HBASE_PORT, timeout=60000)
        connection.open()
        table = connection.table(TABLE_NAME)
        
        for key, value in table.scan():
            try:
                data_buffer.append({
                    'id': key.decode('utf-8'),
                    'clicks': float(value.get(b'info:clicks', b'0')),
                    'score': float(value.get(b'info:avg_score', b'0')),
                    'risk': int(value.get(b'prediction:risk_label', b'0'))
                })
            except Exception:
                continue

        SYSTEM_CACHE["data"] = data_buffer
        SYSTEM_CACHE["last_updated"] = time.strftime("%H:%M:%S")
        SYSTEM_CACHE["is_ready"] = True
        
        duration = time.time() - start_time
        logger.info(f">>> [CACHE] ✅ Synchronization complete. Loaded {len(data_buffer)} records in {duration:.2f}s.")
        
    except Exception as e:
        logger.error(f">>> [CACHE] ❌ Sync Error: {e}")
    finally:
        if connection: connection.close()

def background_scheduler():
    """Update cache every 10 minutes"""
    while True:
        fetch_all_data_from_hbase()
        logger.info(f">>> [SCHEDULER] Sleeping for {CACHE_INTERVAL}s...")
        time.sleep(CACHE_INTERVAL)

t = threading.Thread(target=background_scheduler, daemon=True)
t.start()


# --- IN-MEMORY PROCESSING ---
def get_data_from_memory(page=1, page_size=50, search_query="", sort_by="id", order="asc"):
    if not SYSTEM_CACHE["is_ready"]:
        return {'data': [], 'total_pages': 0, 'total_records': 0, 'page': 1}

    all_data = SYSTEM_CACHE["data"]
    
    # Filter
    if search_query:
        q = search_query.lower()
        filtered_data = [x for x in all_data if q in x['id'].lower()]
    else:
        filtered_data = list(all_data)

    # Sort
    reverse = (order == 'desc')
    try:
        filtered_data.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
    except Exception as e:
        logger.error(f"Sort Error: {e}")

    # Paginate
    total_records = len(filtered_data)
    total_pages = math.ceil(total_records / page_size) if total_records > 0 else 1
    
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        'data': filtered_data[start:end],
        'page': page,
        'total_pages': total_pages,
        'total_records': total_records
    }
    
def get_student_by_id(student_id):
    if not SYSTEM_CACHE["is_ready"]:
        return None
    for st in SYSTEM_CACHE["data"]:
        if st['id'] == student_id:
            return st
    return None

def generate_smart_recommendations(student):
    """
    Generates text based on specific Score and Clicks values
    instead of static hardcoded strings.
    """
    recs = []
    score = student['score']
    clicks = student['clicks']
    risk = student['risk']

    # Analyze ACADEMIC PERFORMANCE (Score)
    if score == 0:
        recs.append("URGENT: No academic record found. Please verify if the student has submitted any assignments.")
    elif score < 40:
        recs.append(f"Critical Academic Alert: Current average ({score:.1f}) is failing. Immediate intervention required.")
    elif 40 <= score < 60:
        recs.append(f"Warning: Score ({score:.1f}) is borderline pass. Focus on upcoming quizzes to improve safety margin.")
    elif score >= 90:
        recs.append("Achievement: Outstanding academic performance. Consider this student for peer-tutoring roles.")

    # Analyze ENGAGEMENT (Clicks)
    if clicks < 10:
        recs.append("Disengagement Alert: Almost zero interaction with VLE. Check for login issues or withdrawal intent.")
    elif clicks < 50:
        recs.append(f"Low Activity: Only {int(clicks)} clicks recorded. Encourage viewing lecture materials and forums.")
    elif clicks > 500:
        recs.append("High Engagement: Student is very active. Ensure this effort translates into assessment results.")

    # Analyze RISK CORRELATION (Combinations)
    if risk == 1:
        if score > 70:
            recs.append("Anomaly Detected: Student has good scores but is predicted 'High Risk'. Likely due to sudden drop in recent activity.")
        if clicks > 200 and score < 50:
            recs.append("Efficiency Issue: High effort (clicks) but low scores. Student may be struggling to understand the material.")
        if not recs: # Fallback
            recs.append("General Risk: The predictive model indicates a high probability of dropout based on historical patterns.")
    
    # SAFE STATE
    if risk == 0 and not recs:
        recs.append("Student is on track. No specific interventions needed at this time.")

    return recs

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/students')
def students():
    if not SYSTEM_CACHE["is_ready"]:
        return render_template('loading.html')

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    search = request.args.get('search', '', type=str)
    sort_by = request.args.get('sort_by', 'id', type=str)
    order = request.args.get('order', 'asc', type=str)

    result = get_data_from_memory(page, page_size, search, sort_by, order)
    
    return render_template(
        'students.html', 
        students=result['data'],
        page=result['page'],
        total_pages=result['total_pages'],
        total_records=result['total_records'],
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        order=order,
        last_updated=SYSTEM_CACHE["last_updated"]
    )
    
@app.route('/api/student/<student_id>')
def api_student_detail(student_id):
    student = get_student_by_id(student_id)
    
    if not student:
        return jsonify({'error': 'Not found'}), 404
        
    # USE THE NEW DYNAMIC ENGINE
    recommendations = generate_smart_recommendations(student)

    return jsonify({
        'info': student,
        'recommendations': recommendations
    })

@app.route('/api/realtime-data')
def realtime_data():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({'raw_data': [], 'summary': {'total':0, 'risk':0, 'safe':0}})

    data_sample = SYSTEM_CACHE["data"]
    total = len(data_sample)
    risk = sum(1 for x in data_sample if x['risk'] == 1)
    safe = total - risk
    
    return jsonify({
        'raw_data': data_sample,
        'summary': {
            'total': len(SYSTEM_CACHE["data"]),
            'risk': risk,
            'safe': safe,
            'last_updated': SYSTEM_CACHE["last_updated"]
        }
    })
    
@app.route('/api/refresh-cache', methods=['POST'])
def refresh_cache():
    """Endpoint to force update data from HBase immediately"""
    try:
        # Run sync immediately in main thread
        fetch_all_data_from_hbase()
        return jsonify({
            'status': 'success', 
            'message': 'Cache updated successfully',
            'last_updated': SYSTEM_CACHE["last_updated"]
        })
    except Exception as e:
        logger.error(f"Manual Refresh Failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001, use_reloader=False)