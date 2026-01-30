import os
import sys
import sqlite3
import logging
import time
import re
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any, Set

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

# Check availability of ML libraries
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("CRITICAL: sentence-transformers not installed. Service will fail.")

# --- Configuration & Logging ---

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("vehicle_analytics")

class Settings(BaseSettings):
    APP_NAME: str = "AI Vehicle Analytics Service"
    VERSION: str = "1.0.0"
    # Model Configuration
    MODEL_NAME: str = "all-MiniLM-L6-v2"
    DEVICE: str = "cpu"  # Force CPU for stability on generic hosts, change to 'cuda' or 'mps' if needed
    
    # Database Configuration
    DB_TYPE: str = "cassandra"  # default to cassandra
    DB_NAME: str = "vehicles.db"
    CASSANDRA_HOST: str = "127.0.0.1"
    CASSANDRA_KEYSPACE: str = "ilens_ladakh"
    
    # Search Configuration
    DEFAULT_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.20 
    
    # Configuration for environment variables and .env file
    # Priority: 1. ENV, 2. .env file, 3. Defaults
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="VA_",
        extra="ignore"
    )

settings = Settings()

logger.info(f"Configuration loaded: {settings.APP_NAME} v{settings.VERSION}")

# --- Data Models (Pydantic) ---

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, example="suspicious activity last night")
    top_k: Optional[int] = Field(settings.DEFAULT_TOP_K, ge=1, le=20, description="Max results to return")
    threshold: Optional[float] = Field(settings.SIMILARITY_THRESHOLD, ge=0.0, le=1.0, description="Minimum similarity score")

class VehicleRecord(BaseModel):
    camera_id: str
    camera_name: Optional[str] = "N/A"
    location: str
    timestamp: str
    vehicle_no: str
    snapshotpath: str
    videopath: Optional[str] = "N/A"
    score: Optional[float] = Field(None, description="Similarity score of the match")

class SearchResponse(BaseModel):
    count: int
    query: str
    matches: List[VehicleRecord]
    execution_time_ms: float

# --- Core Logic Engine ---

class AnalyticsEngine:
    def __init__(self):
        self.model = None
        self.embeddings = None
        self.stored_data: List[Dict[str, Any]] = []
        self.locations: Set[str] = set()
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), settings.DB_NAME)

    def initialize(self):
        """Loads model and indexes data. Can be slow."""
        if not ML_AVAILABLE:
            logger.critical("ML Libraries missing. Engine cannot start.")
            raise RuntimeError("Missing dependencies")

        logger.info(f"Loading AI Model: {settings.MODEL_NAME}...")
        self.model = SentenceTransformer(settings.MODEL_NAME, device=settings.DEVICE)
        
        # Initial Indexing
        self.refresh_index()

    def refresh_index(self):
        """Reloads data from SQLite and rebuilds in-memory vector index."""
        logger.info(f"Indexing data from {self.db_path}...")
        
        # 1. Logic Check: If SQLite, check file exists. If Cassandra, proceed to try block.
        if settings.DB_TYPE == "sqlite" and not os.path.exists(self.db_path):
            logger.warning(f"SQLite Database file not found at {self.db_path}. Index will be empty.")
            self.stored_data = []
            self.embeddings = None
            return

        try:
            if settings.DB_TYPE == "cassandra":
                from cassandra.cluster import Cluster
                logger.info(f"Connecting to Cassandra at {settings.CASSANDRA_HOST}...")
                cluster = Cluster([settings.CASSANDRA_HOST])
                session = cluster.connect(settings.CASSANDRA_KEYSPACE)
                rows = session.execute("SELECT camera_id, camera_name, location, timestamp, vehicle_no, snapshotpath, videopath FROM vehicle_analysis_report")
                # Cassandra rows are slightly different in structure (named tuples)
                # But we can iterate over them similarly
                processed_rows = []
                for row in rows:
                    # Standardize to second-precision for consistency across components
                    clean_ts = row.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    processed_rows.append((row.camera_id, row.camera_name, row.location, clean_ts, row.vehicle_no, row.snapshotpath, row.videopath))
                rows = processed_rows
                cluster.shutdown()
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT camera_id, location, timestamp, vehicle_number, snapshot_url FROM vehicle_sightings")
                rows = cursor.fetchall()
                conn.close()
        except Exception as e:
            logger.error(f"Database error ({settings.DB_TYPE}): {e}")
            raise

        documents = []
        new_stored_data = []
        unique_locs = set()
        
        for row in rows:
            cam, cam_name, loc, ts, veh, snap, vid = row
            unique_locs.add(loc)
            
            # Extract number from CAM_003 -> 3
            cam_num = "".join(filter(str.isdigit, cam))
            cam_human = f"Cam {cam_num}" if cam_num else cam
            
            # Construct a rich semantic sentence
            # We add keywords like 'plate', 'seen at' to help the model context
            text_desc = f"Vehicle with license plate {veh} was seen at {loc} ({cam}, {cam_human}, Camera {cam_num}) on {ts}."
            
            documents.append(text_desc)
            new_stored_data.append({
                "text": text_desc,
                "raw": {
                    "camera_id": cam,
                    "camera_name": cam_name,
                    "location": loc,
                    "timestamp": ts,
                    "vehicle_no": veh,
                    "snapshotpath": snap,
                    "videopath": vid
                }
            })

            # Add time-of-day descriptors to help semantic search
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            hour = dt.hour
            time_desc = ""
            if 0 <= hour < 5: time_desc = "middle of the night, late night, suspicious hours"
            elif 5 <= hour < 9: time_desc = "early morning, dawn"
            elif 9 <= hour < 12: time_desc = "morning"
            elif 12 <= hour < 17: time_desc = "afternoon"
            elif 17 <= hour < 21: time_desc = "evening, dusk"
            else: time_desc = "night, late evening"
            
            # Enrich the text description
            enriched_text = f"{text_desc} It was during the {time_desc}."
            documents[-1] = enriched_text
            new_stored_data[-1]["text"] = enriched_text

        if documents:
            # Convert to Tensor for PyTorch/util compatibility
            logger.info("Encoding documents into vectors...")
            self.embeddings = self.model.encode(documents, convert_to_tensor=True)
            self.stored_data = new_stored_data
            self.locations = unique_locs
            logger.info(f"Successfully indexed {len(self.stored_data)} records and {len(self.locations)} locations.")
        else:
            logger.warning("Database is empty. No records indexed.")
            self.stored_data = []
            self.embeddings = None

    def extract_cam_filters(self, query: str) -> Set[str]:
        """Extracts camera IDs from natural language query like 'cam 3' or 'cam_004'."""
        patterns = [
            r"cam(?:era)?[\s_]*(\d+)",
        ]
        
        found_cams = set()
        for pattern in patterns:
            matches = re.finditer(pattern, query.lower())
            for match in matches:
                num_str = match.group(1).lstrip('0')
                if not num_str: num_str = "0"
                # Standardize to CAM_00X format
                formatted = f"CAM_{int(num_str):03d}"
                found_cams.add(formatted)
        
        return found_cams

    def extract_date_filters(self, query: str) -> Set[str]:
        """Detects relative date terms (today, yesterday) and explicit YYYY-MM-DD dates."""
        q = query.lower()
        now = datetime.now()
        found_dates = set()
        
        # 1. Relative Dates
        if "today" in q:
            found_dates.add(now.strftime('%Y-%m-%d'))
        if "yesterday" in q:
            found_dates.add((now - timedelta(days=1)).strftime('%Y-%m-%d'))
        if "day before yesterday" in q:
            found_dates.add((now - timedelta(days=2)).strftime('%Y-%m-%d'))
            
        # 2. Explicit Dates (YYYY-MM-DD or DD/MM/YYYY)
        # Match YYYY-MM-DD
        iso_pattern = r"\b(\d{4}-\d{2}-\d{2})\b"
        matches = re.finditer(iso_pattern, q)
        for match in matches:
            found_dates.add(match.group(1))

        # Match DD/MM/YYYY or D/M/YYYY
        local_pattern = r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b"
        matches = re.finditer(local_pattern, q)
        for match in matches:
            day, month, year = match.groups()
            try:
                # Standardize to YYYY-MM-DD
                dt = datetime(int(year), int(month), int(day))
                found_dates.add(dt.strftime('%Y-%m-%d'))
            except ValueError:
                continue
            
        # 3. Date Ranges (last N days)
        range_match = re.search(r"last (\d+) days", q)
        if range_match:
            days = int(range_match.group(1))
            for i in range(days + 1):
                found_dates.add((now - timedelta(days=i)).strftime('%Y-%m-%d'))
                
        return found_dates

    def extract_vehicle_filters(self, query: str) -> Set[str]:
        """Detects vehicle plate patterns and explicit 'unknown' keyword."""
        q = query.upper()
        found = set()
        
        # 1. Standard Plates
        pattern = r"([A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{1,4})"
        matches = re.finditer(pattern, q)
        for match in matches:
            found.add(match.group(1))
            
        # 2. Unknown keyword
        if "UNKNOWN" in q or "NO PLATE" in q or "UNIDENTIFIED" in q:
            found.add("UNKNOWN")
            
        return found

    def extract_location_filters(self, query: str) -> Set[str]:
        """Checks if the query contains any of the known location names with high precision."""
        q = query.lower()
        found = set()
        
        # Priority 1: Full Exact Match (highest precision)
        for loc in self.locations:
            if loc.lower() in q:
                found.add(loc)
        
        # Priority 2: Keyword match ONLY if no full match was found to avoid leakage
        # (e.g., "Main Gate Entrance" shouldn't trigger "Main Gate" if both exist)
        if not found:
            for loc in self.locations:
                loc_lower = loc.lower()
                keywords = [k for k in re.split(r'[\s_]+', loc_lower) if len(k) > 4]
                for kw in keywords:
                    if kw in q:
                        found.add(loc)
                        break
                        
        return found

    def search(self, query: str, top_k: int, threshold: float) -> List[VehicleRecord]:
        if self.embeddings is None or not self.stored_data:
            return []

        # 1. Detection: Are there specific hard filters?
        requested_cams = self.extract_cam_filters(query)
        requested_dates = self.extract_date_filters(query)
        requested_vehicles = self.extract_vehicle_filters(query)
        requested_locations = self.extract_location_filters(query)
        
        if requested_cams:
            logger.debug(f"Extracted hard camera filters: {requested_cams}")
        if requested_dates:
            logger.debug(f"Extracted hard date filters: {requested_dates}")
        if requested_vehicles:
            logger.debug(f"Extracted hard vehicle filters: {requested_vehicles}")
        if requested_locations:
            logger.debug(f"Extracted hard location filters: {requested_locations}")

        # 1.5 Special Keywords Detection
        q_low = query.lower()
        is_comprehensive = any(kw in q_low for kw in ["all ", "complete", "everything", "every "])
        is_suspicious_query = any(kw in q_low for kw in ["suspicious", "late night", "unusual"])
        
        if is_comprehensive:
            logger.debug("Comprehensive query detected ('all'). Expanding top_k.")
            top_k = max(top_k, 50)

        # 2. Encode query
        query_embedding = self.model.encode(query, convert_to_tensor=True, show_progress_bar=False)
        
        # 3. Perform Semantic Search (Initial pool)
        # Fetch significantly more results if filters are present
        has_filters = bool(requested_cams or requested_dates or requested_vehicles or requested_locations or is_suspicious_query)
        search_k = top_k * 50 if has_filters else top_k
        hits = util.semantic_search(query_embedding, self.embeddings, top_k=search_k)[0]
        
        results = []
        for hit in hits:
            score = hit['score']
            idx = hit['corpus_id']
            
            # THE FILTERING LOGIC
            # Bypass threshold for 'all' queries with date filters
            effective_threshold = 0.05 if (is_comprehensive and requested_dates) else threshold
            if score < effective_threshold:
                continue
                
            if idx < len(self.stored_data):
                record_data = self.stored_data[idx]['raw']
                
                # APPLY HARD FILTERS
                
                # Suspicious Time Filter (00:00 - 05:00)
                if is_suspicious_query:
                    rec_hour = int(record_data['timestamp'].split(' ')[1].split(':')[0])
                    if not (0 <= rec_hour < 6): # Allow up to 5:59 AM
                        continue
                
                # APPLY HARD FILTERS (Hybrid Logic Override)
                
                # Camera Filter
                if requested_cams and record_data['camera_id'] not in requested_cams:
                    continue
                
                # Date Filter
                if requested_dates:
                    record_date = record_data['timestamp'].split(' ')[0]
                    if record_date not in requested_dates:
                        continue
                
                # Vehicle Filter
                if requested_vehicles and record_data['vehicle_no'] not in requested_vehicles:
                    continue
                    
                # Location Filter
                if requested_locations and record_data['location'] not in requested_locations:
                    continue

                # Add score to record
                record_obj = VehicleRecord(**record_data, score=round(score, 4))
                results.append(record_obj)
                
                # Stop if we reached top_k requested after filtering
                if len(results) >= top_k:
                    break
                
        return results

    def generate_report(self, matches: List[VehicleRecord], query: str) -> str:
        if not matches:
            return f"No matching records found for query: '{query}' (Try adjusting threshold?)"
            
        report_lines = []
        report_lines.append(f"AI ANALYTICS REPORT")
        report_lines.append(f"Query: '{query}' | matches: {len(matches)}")
        report_lines.append("-" * 100)
        report_lines.append(f"{'Camera':<10} {'Location':<25} {'Timestamp':<20} {'Vehicle No.':<12} {'Match%':<8} {'Snapshot'}")
        report_lines.append("-" * 100)
        
        for m in matches:
            score_pct = f"{int(m.score * 100)}%"
            report_lines.append(
                f"{m.camera_id:<10} {m.location:<25} {m.timestamp:<20} {m.vehicle_no:<12} {score_pct:<8} {m.snapshotpath}"
            )
        return "\n".join(report_lines)

# --- Application Lifecycle ---

engine = AnalyticsEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("System Startup: Initializing Engine...")
    engine.initialize()
    yield
    # Shutdown
    logger.info("System Shutdown.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    description="Natural Language Interface for Video Analytics Database"
)

# CORS (Allow all for demo purposes, restrict in real prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "records_indexed": len(engine.stored_data),
        "model": settings.MODEL_NAME,
        "database": engine.db_path
    }

@app.post("/admin/refresh", status_code=status.HTTP_200_OK)
def trigger_refresh_index():
    """Force the engine to re-read the database without restarting server."""
    start = time.time()
    engine.refresh_index()
    duration = time.time() - start
    return {"status": "refreshed", "duration_seconds": round(duration, 3), "count": len(engine.stored_data)}

@app.post("/search", response_model=SearchResponse)
def perform_search(request: SearchRequest):
    start_time = time.time()
    
    # Run search
    matches = engine.search(request.query, request.top_k, request.threshold)
    
    # Format text report
    # report_text = engine.generate_report(matches, request.query)
    
    execution_time = (time.time() - start_time) * 1000
    
    return SearchResponse(
        count=len(matches),
        query=request.query,
        matches=matches,
        # formatted_report=report_text,
        execution_time_ms=round(execution_time, 2)
    )

if __name__ == "__main__":
    import uvicorn
    # Production settings: access log on, workers=1 (since model is heavy, one worker is safer unless using shared memory)
    logger.info("Starting Uvicorn Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
