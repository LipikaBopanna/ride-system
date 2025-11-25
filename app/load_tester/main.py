import time
import httpx
import random
import os
import sys

print("--- Load Tester: Service Started. ---")

# URLs (Use internal Docker names)
AUTH_API = "http://auth-service:8000"
REQ_API = "http://request-handler:7001"
USER_API = "http://user-service:6000"
DRIVER_API = "http://driver-service:9000"

def wait_for_service(url, name):
    """Repeatedly tries to connect to a service until it works."""
    print(f"--- Load Tester: Waiting for {name} at {url}... ---")
    for i in range(30): # Try for 60 seconds
        try:
            httpx.get(f"{url}/docs", timeout=1.0)
            print(f"--- Load Tester: {name} is UP! ---")
            return True
        except:
            time.sleep(2)
    print(f"--- Load Tester: {name} failed to start. ---")
    return False

def run_load_test():
    # 1. WAIT for services to be ready
    if not wait_for_service(AUTH_API, "Auth Service"): return
    if not wait_for_service(REQ_API, "Request Handler"): return

    print("--- Load Tester: System is ready. Starting Stress Test... ---")
    
    # 2. Create Drivers & Users (Mock Data)
    with httpx.Client() as client:
        # Create 50 Drivers
        for i in range(50):
            try:
                client.post(f"{AUTH_API}/register/driver", json={
                    "name": f"Driver_{i}", "phone": f"555{i:04d}", "vehicle_type": "car",
                    "vehicle_model": "Etios", "license_plate": f"KA-01-{i}"
                })
            except: pass
        print("--- Load Tester: 50 Drivers Created. ---")

        # Create 200 Users & Request Rides
        print("--- Load Tester: Simulating 200 Ride Requests... ---")
        for i in range(200):
            try:
                # Register
                res = client.post(f"{AUTH_API}/register/rider", json={
                    "name": f"User_{i}", "phone": f"999{i:04d}", "email": f"u{i}@test.com"
                })
                # Auto-verify
                if res.status_code == 200:
                     client.post(f"{AUTH_API}/verify/otp", json={"phone": f"999{i:04d}", "otp": "123456"})
                     uid = res.json()['id']
                     
                     # Request Ride
                     client.post(f"{REQ_API}/ride/request", json={
                         "user_id": uid, "pickup_lat": 12.9, "pickup_lon": 77.6, "pickup_name": "A",
                         "drop_lat": 12.95, "drop_lon": 77.65, "dropoff_name": "B", "price": 100.0
                     })
            except: pass

    print("--- LOAD TEST COMPLETE. ---")

if __name__ == "__main__":
    run_load_test()