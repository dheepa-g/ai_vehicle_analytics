import os
import sys
import sqlite3
import re
from datetime import datetime, timedelta

# Try importing LangChain
try:
    from langchain_community.utilities import SQLDatabase
    from cassandra.cluster import Cluster
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

CASSANDRA_HOST = "127.0.0.1"
CASSANDRA_KEYSPACE = "ilens_ladakh"

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vehicles.db')

def demo_ai_analytics(query_text):
    """
    Simulates the AI's logic using regex to demonstrate the output format 
    without needing an API Key immediately.
    """
    print(f"\n--- Processing Query: '{query_text}' (DEMO MODE) ---")
    
    # 1. Extract intents (Simulating NLU)
    vehicle_match = re.search(r'([A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4})', query_text)
    
    if "yesterday" in query_text.lower():
        date_filter = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        date_filter = datetime.now().strftime('%Y-%m-%d')

    if not vehicle_match:
        return "Could not identify a vehicle number in the query."

    vehicle_number = vehicle_match.group(1)
    
    # 3. Execute Cassandra Query (Logic mapping)
    print(f"Executing Cassandra lookup for vehicle: {vehicle_number} on {date_filter}")
    cluster = Cluster([CASSANDRA_HOST])
    session = cluster.connect(CASSANDRA_KEYSPACE)
    
    results = session.execute("SELECT camera_id, camera_name, location, timestamp, vehicle_no, snapshotpath, videopath FROM vehicle_analysis_report WHERE vehicle_no = %s", [vehicle_number])
    
    processed_rows = []
    for r in results:
        if str(r.timestamp).startswith(date_filter):
            processed_rows.append((r.camera_id, r.camera_name, r.location, str(r.timestamp), r.vehicle_no, r.snapshotpath, r.videopath))
    
    cluster.shutdown()

    # 4. Format Report
    if not processed_rows:
        return f"No records found for vehicle {vehicle_number} on {date_filter}."

    # Header
    report = f"\nREPORT FOR VEHICLE {vehicle_number} (FROM CASSANDRA)\n"
    report += "-" * 110 + "\n"
    report += f"{'Cam ID':<10} {'Cam Name':<15} {'Location':<25} {'Timestamp':<20} {'Vehicle No.':<15} {'Snapshot'}\n"
    report += "-" * 110 + "\n"

    for row in processed_rows:
        cam_id, cam_name, loc, ts, veh, snap, vid = row
        report += f"{cam_id:<10} {cam_name:<15} {loc:<25} {ts:<20} {veh:<15} {snap}\n"
    
    return report

def real_ai_analytics(query_text, api_key):
    """
    Uses LangChain and OpenAI to perform real AI analytics.
    """
    if not LANGCHAIN_AVAILABLE:
        return "Error: LangChain libraries not installed. Please pip install langchain langchain-openai langchain-community sqlalchemy."

    print(f"\n--- Processing Query: '{query_text}' (REAL AI MODE) ---")
    
    # Setup DB
    db = SQLDatabase.from_uri(f"sqlite:///{get_db_path()}")
    
    # Setup LLM
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=api_key)
    
    # Create Chain
    chain = create_sql_query_chain(llm, db)
    
    # Generate SQL
    response = chain.invoke({"question": query_text})
    
    # Clean SQL (sometimes generic LLMs wrap in markdown)
    sql_query = response.strip().replace('```sql', '').replace('```', '')
    print(f"AI Generated SQL: {sql_query}")
    
    # Execute (Safety: In production, consider read-only permissions)
    result = db.run(sql_query)
    
    # Note: For strict formatting like the table requested, usually we do a second LLM pass
    # or just fetch the raw data and format it in Python like the Demo Mode.
    # Here allows the LLM to just return the data string, but we can format it better.
    
    return f"Raw Data Result:\n{result}"


if __name__ == "__main__":
    yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    test_query = f"report for vehicle TN09AB105 movements yesterday"
    print(demo_ai_analytics(test_query))
