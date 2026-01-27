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

    # 1. Create Keyspace
    print("[+] Creating keyspace 'vehicle_analytics'...")
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS vehicle_analytics 
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
    """)

    # 2. Use Keyspace
    session.set_keyspace('vehicle_analytics')

    # 3. Create Table
    # Partition Key: vehicle_number (for tracking specific vehicle movements)
    # Clustering Columns: timestamp (for time-ordered history)
    print("[+] Creating table 'vehicle_sightings'...")
    session.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_sightings (
            vehicle_number text,
            timestamp timestamp,
            camera_id text,
            location text,
            snapshot_url text,
            PRIMARY KEY (vehicle_number, timestamp)
        ) WITH CLUSTERING ORDER BY (timestamp DESC);
    """)

    # 4. Create Secondary Indexes for non-partition queries
    print("[+] Creating indices for location and camera_id...")
    session.execute("CREATE INDEX IF NOT EXISTS ON vehicle_sightings (location);")
    session.execute("CREATE INDEX IF NOT EXISTS ON vehicle_sightings (camera_id);")

    print("[+] Cassandra Setup Complete.")
    cluster.shutdown()

if __name__ == "__main__":
    setup_cassandra()
