from fastapi import FastAPI, HTTPException
from database import ride_db  # adjust to your actual DB import

app = FastAPI()

@app.get("/ride-status/{ride_id}")
def ride_status(ride_id: int):
    ride = ride_db.get(ride_id)  # fix to your actual retrieval function
    
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    return {
        "ride_id": ride.id,
        "status": ride.status,
        "driver_id": ride.driver_id,
        "rider_id": ride.user_id
    }
