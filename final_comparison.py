import requests
import json
import os
import logging
from datetime import datetime, timedelta
from cassandra.cluster import Cluster

# Suppress noisy driver logs
logging.getLogger('cassandra').setLevel(logging.ERROR)

BASE_URL = "http://localhost:8000"
CASSANDRA_HOST = "127.0.0.1"
CASSANDRA_KEYSPACE = "ilens_ladakh"

def get_cassandra_records(session, query_type, params=()):
    """Executes CQL logic to get ground truth records for specific test cases."""
    rows = []
    
    if query_type == "plate_date":
        # Params: (vehicle_no, date_prefix)
        veh, date_pre = params
        results = session.execute("SELECT * FROM vehicle_analysis_report WHERE vehicle_no = %s", [veh])
        for r in results:
            if str(r.timestamp).startswith(date_pre):
                rows.append(r)
    
    elif query_type == "location_only":
        # Params: (location_name,)
        loc = params[0]
        results = session.execute("SELECT * FROM vehicle_analysis_report WHERE location = %s ALLOW FILTERING", [loc])
        rows = list(results)

    elif query_type == "location_date":
        # Params: (location_keyword, date_prefix)
        loc_kw, date_pre = params
        results = session.execute("SELECT * FROM vehicle_analysis_report")
        for r in results:
            if loc_kw in r.location and str(r.timestamp).startswith(date_pre):
                rows.append(r)

    elif query_type == "date_only":
        date_pre = params[0]
        results = session.execute("SELECT * FROM vehicle_analysis_report")
        for r in results:
            if str(r.timestamp).startswith(date_pre):
                rows.append(r)

    elif query_type == "unknown_warehouse":
        results = session.execute("SELECT * FROM vehicle_analysis_report WHERE vehicle_no = 'UNKNOWN'")
        for r in results:
            if "Warehouse" in r.location:
                rows.append(r)

    elif query_type == "suspicious":
        results = session.execute("SELECT * FROM vehicle_analysis_report")
        for r in results:
            if 0 <= r.timestamp.hour <= 5:
                rows.append(r)

    # Standardize result format
    res = []
    for r in rows:
        res.append({
            'vehicle_no': r.vehicle_no,
            'location': r.location,
            'timestamp': r.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'camera_id': r.camera_id,
            'camera_name': getattr(r, 'camera_name', 'N/A'),
            'snapshotpath': getattr(r, 'snapshotpath', 'N/A'),
            'videopath': getattr(r, 'videopath', 'N/A')
        })
    return res

def get_api_records(nl_query):
    try:
        response = requests.post(f"{BASE_URL}/search", json={"query": nl_query})
        if response.status_code == 200:
            return response.json().get('matches', [])
    except Exception as e:
        print(f"API Error: {e}")
    return []

def print_test_case(session, title, nl_query, query_type, params):
    db_records = get_cassandra_records(session, query_type, params)
    api_records = get_api_records(nl_query)
    
    print(f"### {title}")
    print(f"**Query**: `{nl_query}`")
    print(f"\n| Source | vehicle_no | location | timestamp | camera_id | camera_name | snapshotpath | videopath | Score |")
    
    # Sort for consistent display
    db_records.sort(key=lambda x: x['timestamp'])
    api_records.sort(key=lambda x: x['timestamp'])

    # Display DB rows first
    for row in db_records:
        print(f"| **Cassandra** | {row.get('vehicle_no')} | {row.get('location')} | {row.get('timestamp')} | {row.get('camera_id')} | {row.get('camera_name', 'N/A')} | {row.get('snapshotpath', 'N/A')} | {row.get('videopath', 'N/A')} | - |")
    
    # Display API rows
    for row in api_records:
        # Normalize fields from API response
        v_num = row.get('vehicle_no') or row.get('vehicle_number', 'N/A')
        cam_id = row.get('camera') or row.get('camera_id', 'N/A')
        snap = row.get('snapshotpath') or row.get('snapshot', 'N/A')
        vid = row.get('videopath', 'N/A')
        cam_name = row.get('camera_name', 'N/A')

        
        # Check match against DB records
        match_symbol = "✅" if any(d['timestamp'] == row['timestamp'] and d['vehicle_no'] == v_num for d in db_records) else "⚠️"
        
        print(f"| *AI Result* | {v_num} | {row['location']} | {row['timestamp']} | {cam_id} | {cam_name} | {snap} | {vid} | {match_symbol} {row.get('score', 0):.4f} |")
    print("\n---\n")

def run_final_analysis():
    print("# Final Database (Cassandra) vs AI Analytics Comparison Report\n")
    
    # 1. Health Check
    print("## System Health Check")
    try:
        resp = requests.get(f"{BASE_URL}/health").json()
        print(json.dumps(resp, indent=2))
    except:
        print("API is OFFLINE. Cannot run analysis.")
        return
    print("\n---\n")

    # 2. Connect to Cassandra
    cluster = Cluster([CASSANDRA_HOST])
    session = cluster.connect(CASSANDRA_KEYSPACE)

    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today_local = datetime.now().strftime('%-d/%-m/%Y')

    # Case 1: Specific Plate + Date
    print_test_case(session, "1. Specific Vehicle Tracking", f"TN09AB105 movements on {yesterday}", "plate_date", ("TN09AB105", yesterday))

    # Case 2: Semantic Location
    print_test_case(session, "2. Semantic Location Discovery", "vehicles at Location_6 yesterday", "location_date", ("Location_6", yesterday))

    # Case 3: Explicit Historical Search
    print_test_case(session, "3. Explicit Historical Search (YYYY-MM-DD)", f"all traffic on {yesterday}", "date_only", (yesterday,))

    # Case 4: Unknown Vehicle Detection
    print_test_case(session, "4. Unknown Vehicle Detection", "List of unknown vehicles spotted in warehouse", "unknown_warehouse", ())

    # Case 5: Localized Date Format
    print_test_case(session, "5. Localized Date Format (DD/MM/YYYY)", f"all vehicles that entered Location_6 on {today_local}", "location_date", ("Location_6", today))

    # Case 6: Semantic Suspicious Activity
    print_test_case(session, "6. Semantic Suspicious Activity (Last 2 Days)", "show suspicious activities in last 2 days", "suspicious", ())

    cluster.shutdown()

if __name__ == "__main__":
    run_final_analysis()
