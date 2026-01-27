# AI Vehicle Analytics System

A production-grade Natural Language Interface for querying vehicle surveillance data using semantic search.

## Project Structure

```
ai_vehicle_analytics/
├── api_server.py              # Production FastAPI service (MAIN)
├── setup_database.py          # Database initialization script
├── vehicles.db                # SQLite database with vehicle sightings
├── requirements.txt           # Python dependencies
├── ai_analytics_engine.py     # Text-to-SQL approach (alternative)
├── semantic_search.py         # Standalone semantic search demo
├── APPROACHES.md              # Comparison of different AI approaches
├── ANALYSIS_REPORT.md         # Performance analysis
└── IMPLEMENTATION_PLAN.md     # Initial design document
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python3 setup_database.py
```

### 3. Start the API Server
```bash
python3 api_server.py
```

The server will start at `http://localhost:8000`

### 4. Query the System

**Using curl:**
```bash
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "show me vehicle KA01JJ8967 movements yesterday"}'
```

**Using the interactive docs:**
Open `http://localhost:8000/docs` in your browser.

## API Endpoints

### POST /search
Search for vehicle sightings using natural language.

**Request:**
```json
{
  "query": "vehicles at warehouse yesterday",
  "top_k": 5,           // Optional: max results (default: 5)
  "threshold": 0.30     // Optional: min similarity score (default: 0.30)
}
```

**Response:**
```json
{
  "count": 3,
  "query": "vehicles at warehouse yesterday",
  "matches": [...],
  "formatted_report": "...",
  "execution_time_ms": 12.5
}
```

### GET /health
Check service status and indexed record count.

### POST /admin/refresh
Reload data from database without restarting the server.

## Configuration

Set environment variables with `VA_` prefix:

```bash
export VA_SIMILARITY_THRESHOLD=0.35
export VA_DEFAULT_TOP_K=10
export VA_MODEL_NAME="all-MiniLM-L6-v2"
```

## Features

- ✅ **Natural Language Queries**: Ask questions in plain English
- ✅ **Semantic Search**: Understands meaning, not just keywords
- ✅ **Threshold Filtering**: Automatically removes irrelevant results
- ✅ **Production Ready**: Logging, error handling, CORS support
- ✅ **Fast**: Responses in ~10ms after initial model load
- ✅ **Free & Offline**: No API keys required, runs locally

## Example Queries (By Type)

### 1. Hard Vehicle Filter (Exact Plate)
Use this to find a specific car with 100% precision.
- `"give me complete report for vehicle KA05XY9999"`
- `"where was MH02AB1234 seen?"`

### 2. Hard Camera Filter (Specific Cam)
Use this to narrow down to specific hardware locations.
- `"which vehicles passed through cam 3 today?"`
- `"activity at cam 4 and cam 5 yesterday"`

### 3. Hard Date Filter (Relative Time)
Use this to strictly filter by time windows.
- `"vehicles at warehouse today"`
- `"any visitors yesterday"`
- `"traffic day before yesterday"`

### 4. Semantic Search (Concept Matching)
Use this for abstract or fuzzy search terms.
- `"Are there any cars moving in the middle of the night?"` (Matches 3 AM records)
- `"suspicious activity near exit gate"` (Matches 'Exit Gate' location)
- `"delivery trucks at dock"` (Matches 'Warehouse Dock' via semantic similarity)

### 5. Hybrid (The Power User Query)
Combines all above for ultimate precision.
- `"show me movements for visitor KA01JJ8967 at cam 1 and cam 3 yesterday and today"`

## Technology Stack

- **FastAPI**: Web framework
- **SentenceTransformers**: Semantic embeddings (all-MiniLM-L6-v2)
- **SQLite**: Database
- **PyTorch**: ML backend

## Next Steps

To use with your real database:
1. Update `setup_database.py` to connect to your actual database
2. Modify the schema mapping in `api_server.py` (lines 117-137)
3. Adjust `SIMILARITY_THRESHOLD` based on your data
4. Deploy behind Nginx/Docker for production

## License

MIT
