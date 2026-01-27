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
CASSANDRA_KEYSPACE = "vehicle_analytics"

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
    
    results = session.execute("SELECT camera_id, location, timestamp, vehicle_number, snapshot_url FROM vehicle_sightings WHERE vehicle_number = %s", [vehicle_number])
    
    processed_rows = []
    for r in results:
        if str(r.timestamp).startswith(date_filter):
            processed_rows.append((r.camera_id, r.location, str(r.timestamp), r.vehicle_number, r.snapshot_url))
    
    cluster.shutdown()

    # 4. Format Report
    if not processed_rows:
        return f"No records found for vehicle {vehicle_number} on {date_filter}."

    # Header
    report = f"\nREPORT FOR VEHICLE {vehicle_number} (FROM CASSANDRA)\n"
    report += "-" * 80 + "\n"
    report += f"{'Camera':<10} {'Location':<25} {'Timestamp':<20} {'Vehicle No.':<15} {'Snapshot'}\n"
    report += "-" * 80 + "\n"

    for row in processed_rows:
        cam, loc, ts, veh, snap = row
        report += f"{cam:<10} {loc:<25} {ts:<20} {veh:<15} {snap}\n"
    
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
    test_query = "report for vehicle KA01JJ8967 movements yesterday"
    print(demo_ai_analytics(test_query))
