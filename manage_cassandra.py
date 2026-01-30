import sys
import argparse
from cassandra.cluster import Cluster
from datetime import datetime, timedelta

CASSANDRA_HOST = '127.0.0.1'
CASSANDRA_KEYSPACE = 'ilens_ladakh'

def get_session():
    cluster = Cluster([CASSANDRA_HOST])
    return cluster, cluster.connect(CASSANDRA_KEYSPACE)

def insert_data(session):
    print("[+] Syncing sample records to Cassandra...")
    
    # Clear existing data first
    print("    Clearing existing records...")
    session.execute("TRUNCATE vehicle_analysis_report")

    today = datetime.now()
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)
    
    sample_data = [
        ('TN09AB105', yesterday.replace(hour=8, minute=30, second=20), 'CAM_6', 'Camera_6', 'Location_6', '/snapshots/car_6.jpg', '/videos/car_6.mp4'),
        ('TN09AB101', yesterday.replace(hour=8, minute=35, second=20), 'CAM_2', 'Camera_2', 'Location_2', '/snapshots/car_2.jpg', '/videos/car_2.mp4'),
        ('TN09AB109', yesterday.replace(hour=17, minute=15, second=20), 'CAM_10', 'Camera_10', 'Location_10', '/snapshots/car_10.jpg', '/videos/car_10.mp4'),
        ('TN09AB105', today.replace(hour=10, minute=0, second=20), 'CAM_6', 'Camera_6', 'Location_6', '/snapshots/car_6_2.jpg', '/videos/car_6_2.mp4'),
        ('TN09AB102', day_before.replace(hour=14, minute=0, second=0), 'CAM_3', 'Camera_3', 'Location_3', '/snapshots/car_3.jpg', '/videos/car_3.mp4'),
        ('TN09AB102', yesterday.replace(hour=10, minute=30, second=0), 'CAM_3', 'Camera_3', 'Location_3', '/snapshots/car_3_2.jpg', '/videos/car_3_2.mp4'),
        ('TN09AB104', yesterday.replace(hour=11, minute=15, second=0), 'CAM_5', 'Camera_5', 'Location_5', '/snapshots/car_5.jpg', '/videos/car_5.mp4'),
        ('TN09AB105', today.replace(hour=13, minute=0, second=0), 'CAM_6', 'Camera_6', 'Location_6', '/snapshots/car_6_3.jpg', '/videos/car_6_3.mp4'),
        ('TN09AB100', today.replace(hour=13, minute=5, second=0), 'CAM_1', 'Camera_1', 'Location_1', '/snapshots/car_1.jpg', '/videos/car_1.mp4'),
        ('TN09AB107', today.replace(hour=3, minute=15, second=0), 'CAM_8', 'Camera_8', 'Location_8', '/snapshots/car_8.jpg', '/videos/car_8.mp4'),
    ]

    query = session.prepare("""
        INSERT INTO vehicle_analysis_report (vehicle_no, timestamp, camera_id, camera_name, location, snapshotpath, videopath)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """)

    for veh, ts, cam_id, cam_name, loc, snap, vid in sample_data:
        session.execute(query, [veh, ts, cam_id, cam_name, loc, snap, vid])

    print(f"[+] Successfully inserted {len(sample_data)} records.")

def clear_data(session):
    print("[+] Clearing all vehicle sighting records from Cassandra...")
    session.execute("TRUNCATE vehicle_analysis_report")
    print("    Done.")

def verify_data(session):
    print("\n[+] Verifying records in Cassandra...")
    
    # 1. Count records
    row_count = session.execute("SELECT COUNT(*) FROM vehicle_analysis_report")
    count = row_count[0].count
    print(f"    Total records: {count}")

    # 2. Show latest
    print("\n    Latest 5 Records:")
    rows = session.execute("SELECT * FROM vehicle_analysis_report LIMIT 5")
    
    print(f"    {'Vehicle':<15} {'Timestamp':<25} {'Camera ID':<10} {'Camera Name':<15} {'Location':<15} {'Snapshot'}")
    print("    " + "-" * 115)
    for row in rows:
        ts_str = row.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {row.vehicle_no:<15} {ts_str:<25}   {row.camera_id:<10} {row.camera_name:<15} {row.location:<15} {row.snapshotpath}")
    print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Cassandra Vehicle Data")
    parser.add_argument("action", choices=["insert", "verify", "sync", "clear"], help="Action to perform: insert data, verify data, sync (both), or clear (truncate)")
    
    args = parser.parse_args()
    
    cluster = None
    try:
        cluster, session = get_session()
        
        if args.action == "insert":
            insert_data(session)
        elif args.action == "verify":
            verify_data(session)
        elif args.action == "clear":
            clear_data(session)
        elif args.action in ["sync", "both"]:
            insert_data(session)
            verify_data(session)
            
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        if cluster:
            cluster.shutdown()
