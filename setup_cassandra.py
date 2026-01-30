import sys
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import time

def setup_cassandra():
    print("[+] Connecting to Cassandra cluster at 127.0.0.1...")
    try:
        cluster = Cluster(['127.0.0.1'])
        session = cluster.connect()
    except Exception as e:
        print(f"[!] Error connecting to Cassandra: {e}")
        print("    Ensure Cassandra is running (e.g., via Docker: docker run --name cassandra -p 9042:9042 -d cassandra)")
        sys.exit(1)



    # 2. Use Keyspace
    session.set_keyspace('ilens_ladakh')

    # 3. Create Table
    # Partition Key: vehicle_no (for tracking specific vehicle movements)
    # Clustering Columns: timestamp (for time-ordered history)
    print("[+] Creating table 'vehicle_analysis_report'...")
    session.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_analysis_report (
            vehicle_no text,
            timestamp timestamp,
            camera_id text,
            camera_name text,
            location text,
            snapshotpath text,
            videopath text,
            PRIMARY KEY (vehicle_no, timestamp)
        ) WITH CLUSTERING ORDER BY (timestamp DESC);
    """)

    # 4. Create Secondary Indexes for non-partition queries
    print("[+] Creating indices for location and camera_id...")
    session.execute("CREATE INDEX IF NOT EXISTS ON vehicle_analysis_report (location);")
    session.execute("CREATE INDEX IF NOT EXISTS ON vehicle_analysis_report (camera_id);")

    print("[+] Cassandra Setup Complete.")
    cluster.shutdown()

if __name__ == "__main__":
    setup_cassandra()
