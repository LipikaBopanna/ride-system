# app/notifier/main.py
import asyncio
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from typing import Dict, Any

app = FastAPI(title="Notifier Service (SSE)")

driver_queues: Dict[int, asyncio.Queue] = {}
rider_queues: Dict[int, asyncio.Queue] = {}

async def driver_event_generator(q: asyncio.Queue):
    try:
        while True:
            data = await q.get()
            yield f"data: {json.dumps(data)}\n\n"
    except asyncio.CancelledError:
        return

async def rider_event_generator(q: asyncio.Queue):
    try:
        while True:
            data = await q.get()
            yield f"data: {json.dumps(data)}\n\n"
    except asyncio.CancelledError:
        return

@app.get("/events/driver/{driver_id}")
async def driver_events(driver_id: int):
    q = driver_queues.get(driver_id)
    if q is None:
        q = asyncio.Queue()
        driver_queues[driver_id] = q
    return EventSourceResponse(driver_event_generator(q))

@app.get("/events/rider/{user_id}")
async def rider_events(user_id: int):
    q = rider_queues.get(user_id)
    if q is None:
        q = asyncio.Queue()
        rider_queues[user_id] = q
    return EventSourceResponse(rider_event_generator(q))

@app.post("/driver/request")
async def push_driver_request(payload: Dict[str, Any]):
    driver_id = payload.get("driver_id")
    if not driver_id:
        return JSONResponse({"status":"error","detail":"driver_id required"}, status_code=400)
    q = driver_queues.get(driver_id)
    data = {"type": "ride_request", "ride": payload.get("ride")}
    if q:
        await q.put(data)
        print(f"Notifier: pushed ride_request to driver {driver_id}")
        return JSONResponse({"status":"pushed"})
    # queue if not connected
    q = asyncio.Queue()
    driver_queues[driver_id] = q
    await q.put(data)
    print(f"Notifier: queued ride_request for driver {driver_id} (driver not connected)")
    return JSONResponse({"status":"queued"})

@app.post("/ride/accepted")
async def ride_accepted(payload: Dict[str, Any]):
    # payload must include user_id, ride_id, driver dict
    user_id = payload.get("user_id")
    if not user_id:
        return JSONResponse({"status":"error","detail":"user_id required"}, status_code=400)
    q = rider_queues.get(user_id)
    data = {"type":"ride_accepted", "ride_id": payload.get("ride_id"), "driver": payload.get("driver")}
    if q:
        await q.put(data)
        print(f"Notifier: notified rider {user_id} about acceptance")
        return JSONResponse({"status":"notified"})
    q = asyncio.Queue()
    rider_queues[user_id] = q
    await q.put(data)
    print(f"Notifier: queued acceptance for rider {user_id}")
    return JSONResponse({"status":"queued"})
