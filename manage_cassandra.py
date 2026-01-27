import sys
import argparse
from cassandra.cluster import Cluster
from datetime import datetime, timedelta

CASSANDRA_HOST = '127.0.0.1'
CASSANDRA_KEYSPACE = 'vehicle_analytics'

def get_session():
    cluster = Cluster([CASSANDRA_HOST])
    return cluster, cluster.connect(CASSANDRA_KEYSPACE)

def insert_data(session):
    print("[+] Syncing sample records to Cassandra...")
    
    # Clear existing data first
    print("    Clearing existing records...")
    session.execute("TRUNCATE vehicle_sightings")

    today = datetime.now()
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)
    
    sample_data = [
        ('CAM_001', 'Main Gate Entrance', yesterday.replace(hour=8, minute=30, second=20), 'KA01JJ8967', 'http://cloud.storage/snap1.jpg'),
        ('CAM_002', 'Parking Lot B', yesterday.replace(hour=8, minute=35, second=20), 'KA01JJ8967', 'http://cloud.storage/snap2.jpg'),
        ('CAM_003', 'Exit Gate North', yesterday.replace(hour=17, minute=15, second=20), 'KA01JJ8967', 'http://cloud.storage/snap3.jpg'),
        ('CAM_001', 'Main Gate Entrance', today.replace(hour=10, minute=0, second=20), 'KA01JJ8967', 'http://cloud.storage/snap5.jpg'),
        ('CAM_004', 'Warehouse Dock A', day_before.replace(hour=14, minute=0, second=0), 'TN09ZZ1111', 'http://cloud.storage/snap6.jpg'),
        ('CAM_004', 'Warehouse Dock A', yesterday.replace(hour=10, minute=30, second=0), 'TN09ZZ1111', 'http://cloud.storage/snap7.jpg'),
        ('CAM_005', 'Warehouse Exit', yesterday.replace(hour=11, minute=15, second=0), 'TN09ZZ1111', 'http://cloud.storage/snap8.jpg'),
        ('CAM_001', 'Main Gate Entrance', today.replace(hour=13, minute=0, second=0), 'KA05XY9999', 'http://cloud.storage/snap9.jpg'),
        ('CAM_002', 'Parking Lot VIP', today.replace(hour=13, minute=5, second=0), 'KA05XY9999', 'http://cloud.storage/snap10.jpg'),
        ('CAM_001', 'Main Gate Entrance', today.replace(hour=14, minute=30, second=0), 'KA05XY9999', 'http://cloud.storage/snap11.jpg'),
        ('CAM_003', 'Exit Gate North', today.replace(hour=3, minute=15, second=0), 'MH02AB1234', 'http://cloud.storage/snap4.jpg'),
        ('CAM_004', 'Warehouse Dock A', yesterday.replace(hour=23, minute=45, second=0), 'UNKNOWN', 'http://cloud.storage/snap12.jpg'),
        ('CAM_001', 'Main Gate Entrance', today.replace(hour=2, minute=10, second=0), 'UNKNOWN', 'http://cloud.storage/snap13.jpg'),
    ]

    query = session.prepare("""
        INSERT INTO vehicle_sightings (camera_id, location, timestamp, vehicle_number, snapshot_url)
        VALUES (?, ?, ?, ?, ?)
    """)

    for cam, loc, ts, veh, snap in sample_data:
        session.execute(query, [cam, loc, ts, veh, snap])

    print(f"[+] Successfully inserted {len(sample_data)} records.")

def clear_data(session):
    print("[+] Clearing all vehicle sighting records from Cassandra...")
    session.execute("TRUNCATE vehicle_sightings")
    print("    Done.")

def verify_data(session):
    print("\n[+] Verifying records in Cassandra...")
    
    # 1. Count records
    row_count = session.execute("SELECT COUNT(*) FROM vehicle_sightings")
    count = row_count[0].count
    print(f"    Total records: {count}")

    # 2. Show latest
    print("\n    Latest 5 Records:")
    rows = session.execute("SELECT * FROM vehicle_sightings LIMIT 5")
    
    print(f"    {'Camera':<10}  {'Timestamp':<25} {'Vehicle':<15} {'Location':<25} {'Snapshot'}")
    print("    " + "-" * 115)
    for row in rows:
        ts_str = row.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {row.camera_id:<10} {ts_str:<25}   {row.vehicle_number:<15} {row.location:<25} {row.snapshot_url}")
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
