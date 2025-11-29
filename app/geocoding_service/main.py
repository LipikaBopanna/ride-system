# app/geocoding_service/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from app.common.schemas import GeoCodeResult

app = FastAPI(title="Mock Geocoding Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- MOCK DATABASE of locations in Bengaluru ---
MOCK_LOCATIONS = {
    "home": GeoCodeResult(name="Home (Koramangala)", lat=12.9345, lon=77.6110),
    "work": GeoCodeResult(name="Work (MG Road)", lat=12.9745, lon=77.6060),
    "majestic": GeoCodeResult(name="Majestic Station", lat=12.9767, lon=77.5713),
    "airport": GeoCodeResult(name="Kempegowda Airport (BLR)", lat=13.1986, lon=77.7066),
    "lalbagh": GeoCodeResult(name="Lalbagh Botanical Garden", lat=12.9507, lon=77.5848)
}

@app.get("/search", response_model=List[GeoCodeResult])
def search_location(query: str):
    # Simple mock search: filters keys that start with the query
    query = query.lower()
    results = [loc for key, loc in MOCK_LOCATIONS.items() if key.startswith(query)]
    if not results and len(query) < 3:
         results = [MOCK_LOCATIONS['home'], MOCK_LOCATIONS['work']]
    return results