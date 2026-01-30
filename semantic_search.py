import sqlite3
import os
import sys

# Try importing dependencies
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    DEPENDENCIES_MET = True
except ImportError:
    DEPENDENCIES_MET = False

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vehicles.db')

class LocalSearchEngine:
    def __init__(self):
        print("\n[+] Initializing Local Search Engine...")
        print("    Loading Embedding Model (all-MiniLM-L6-v2)... (This happens once)")
        # This is a small, fast, and free model that runs locally
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.stored_data = []

    def load_data_from_db(self, db_type="cassandra", host="127.0.0.1", keyspace="ilens_ladakh"):
        """Reads DB and converts rows to natural language 'documents'."""
        if db_type == "cassandra":
            from cassandra.cluster import Cluster
            cluster = Cluster([host])
            session = cluster.connect(keyspace)
            rows = session.execute("SELECT camera_id, camera_name, location, timestamp, vehicle_no, snapshotpath, videopath FROM vehicle_analysis_report")
            processed_rows = []
            for row in rows:
                processed_rows.append((row.camera_id, row.camera_name, row.location, str(row.timestamp), row.vehicle_no, row.snapshotpath, row.videopath))
            rows = processed_rows
            cluster.shutdown()
        else:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT camera_id, location, timestamp, vehicle_number, snapshot_url FROM vehicle_sightings")
            rows = cursor.fetchall()
            conn.close()

        self.stored_data = []
        documents = []
        
        print(f"    Indexing {len(rows)} records from {db_type} database...")
        for row in rows:
            cam_id, cam_name, loc, ts, veh, snap, vid = row
            # Create a descriptive sentence for the model to "understand"
            text_desc = f"Vehicle {veh} was seen at {loc} (Camera {cam_id}, {cam_name}) on {ts}."
            
            documents.append(text_desc)
            self.stored_data.append({
                "text": text_desc,
                "raw": row
            })
        
        # Convert text to vectors
        embeddings = self.model.encode(documents)
        
        # Build FAISS index for fast searching
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings).astype('float32'))
        print("    Indexing Complete.\n")

    def search(self, query, top_k=5):
        """Finds the most relevant records for the query."""
        print(f"--- Searching for: '{query}' ---")
        
        # Convert text to vectors
        query_vector = self.model.encode([query], show_progress_bar=False)
        
        # Search index
        distances, indices = self.index.search(np.array(query_vector).astype('float32'), top_k)
        
        results = []
        print("\nTop Matching Results:")
        for idx in indices[0]:
            if idx < len(self.stored_data):
                match = self.stored_data[idx]
                results.append(match)
                print(f"  > {match['text']}")
        
        return results

    def format_report_table(self, results):
        report = f"\nREPORT GENERATED FROM SEARCH MATCHES\n"
        report += "-" * 110 + "\n"
        report += f"{'Cam ID':<10} {'Cam Name':<15} {'Location':<25} {'Timestamp':<20} {'Vehicle No.':<15} {'Snapshot'}\n"
        report += "-" * 110 + "\n"

        for item in results:
            cam_id, cam_name, loc, ts, veh, snap, vid = item['raw']
            report += f"{cam_id:<10} {cam_name:<15} {loc:<25} {ts:<20} {veh:<15} {snap}\n"
        return report

if __name__ == "__main__":
    if not DEPENDENCIES_MET:
        print("Error: Missing libraries. Please run:")
        print("pip install sentence-transformers faiss-cpu numpy")
        sys.exit(1)

    # 1. Setup Engine
    engine = LocalSearchEngine()
    engine.load_data_from_db()

    # 2. Test Query
    # Note: We can ask vaguely now, no exact keyword matching needed
    user_query = "Where was vehicle TN09AB105 seen lately?"
    
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])

    # 3. Search
    matches = engine.search(user_query)
    
    # 4. Show Table
    print(engine.format_report_table(matches))
