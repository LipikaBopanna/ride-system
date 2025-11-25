from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from app.common.schemas import GeoCodeResult
import httpx

app = FastAPI(title="Real Geocoding Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fallback locations in case the external API is slow/down
MOCK_BACKUP = [
    {"name": "Koramangala", "lat": 12.9345, "lon": 77.6110},
    {"name": "MG Road", "lat": 12.9745, "lon": 77.6060},
    {"name": "Indiranagar", "lat": 12.9784, "lon": 77.6408},
    {"name": "Whitefield", "lat": 12.9698, "lon": 77.7500},
    {"name": "HSR Layout", "lat": 12.9121, "lon": 77.6446}
]

@app.get("/search", response_model=List[GeoCodeResult])
async def search_location(query: str):
    if not query or len(query) < 3: return []
    
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 5, "addressdetails": 1}
    headers = {"User-Agent": "MiniUberClone/1.0"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=5.0)
            data = response.json()
            results = []
            for item in data:
                # Get the main name (e.g., "Phoenix Mall")
                name = item.get('display_name', '').split(',')[0]
                results.append(GeoCodeResult(name=name, lat=float(item['lat']), lon=float(item['lon'])))
            
            # If API returns nothing, check backup
            if not results:
                raise Exception("No API results")
                
            return results
    except Exception:
        # Fallback to local data so the demo never fails
        return [GeoCodeResult(**loc) for loc in MOCK_BACKUP if query.lower() in loc['name'].lower()]

@app.get("/reverse", response_model=GeoCodeResult)
async def reverse_geocode(lat: float, lon: float):
    """ Converts Lat/Lon to a readable address name """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json"}
    headers = {"User-Agent": "MiniUberClone/1.0"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=5.0)
            data = response.json()
            # Extract street or area name
            address = data.get('address', {})
            name = address.get('road') or address.get('suburb') or address.get('city') or "Unknown Location"
            return GeoCodeResult(name=name, lat=lat, lon=lon)
    except:
        return GeoCodeResult(name=f"{lat:.4f}, {lon:.4f}", lat=lat, lon=lon)