# AI Vehicle Analytics System

A production-grade Natural Language Interface for querying vehicle surveillance data using Hybrid AI search backed by **Apache Cassandra**.

## Project Structure

```
ai_vehicle_analytics/
├── api_server.py                # Production FastAPI service (MAIN)
├── semantic_search.py           # Core Hybrid AI search engine logic
├── manage_cassandra.py          # Unified tool for Data Sync, Verification & Clearing
├── final_comparison.py          # Side-by-side validation (CQL vs AI Search)
├── setup_cassandra.py           # Infrastructure setup (Keyspace/Tables)
├── .env                         # Production environment configuration
├── .env.example                 # Config template for new environments
├── requirements.txt             # Python dependencies
├── ULTIMATE_CASSANDRA_VERIFICATION.md  # Final 100% precision report
└── ai_analytics_engine.py       # Alternative Prototype (Text-to-CQL)
```

## Setup & Installation (Local Development)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dheepa-g/ai_vehicle_analytics.git
   cd ai_vehicle_analytics
   ```

2. **Initialize Environment**:
   ```bash
   # Use the provided defaults or edit .env for custom IPs
   cp .env.example .env
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Cassandra Infrastructure**:
   Ensure your Cassandra Docker container is running, then create the keyspace:
   ```bash
   python3 setup_cassandra.py
   ```

5. **Sync Sample Data**:
   ```bash
   python3 manage_cassandra.py sync
   ```

## Production Deployment Steps

To deploy this service on a **separate server**, follow these steps:

### 1. Infrastructure Setup
Ensure the server has Python 3.10+ installed and access to a Cassandra node (Standard port 9042).

### 2. Configure Environment
Update the `.env` file on the server to point to your production details:
```bash
nano .env
```
Update:
- `VA_CASSANDRA_HOST`: IP of your Cassandra cluster.
- `VA_DEVICE`: Set to `cuda` if GPU is available, else `cpu`.

### 3. Launch Service
Run the API server:
```bash
python3 api_server.py
```

## API Endpoints

### POST `/search`
The primary endpoint for natural language queries.

**Request:**
```json
{
  "query": "all vehicles at warehouse today",
  "top_k": 10,
  "threshold": 0.15
}
```

## Search Capability

The engine handles complex semantic and relative time queries:
- *"Who entered through the main gate entrance on 27/1/2026?"*
- *"Show me suspicious late-night activities"* (Matches 12AM-5AM)
- *"Find any delivery trucks near the warehouse yesterday"*

## Verification & Accuracy

Confirm the system is operational and accurate by running the verification report:
```bash
python3 final_comparison.py
```
This generates a side-by-side comparison of **Cassandra Ground Truth (CQL)** vs **AI Results**, currently confirmed at **100% Match**.

## Technology Stack

- **FastAPI**: Web framework
- **SentenceTransformers**: Embeddings via `all-MiniLM-L6-v2`
- **Apache Cassandra**: NoSQL Database for scalable sightings storage
- **PyTorch**: ML inference engine

## License
MIT
