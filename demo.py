import requests
import time
from datetime import datetime, timedelta

USER_API = "http://localhost:8001"
AUTH_API = "http://localhost:8000"
DRIVER_API = "http://localhost:9001"  # Added Driver API

def run_demo():
    print("\n=== 1. SETUP: Creating Entities ===")
    
    # Create Driver
    try:
        res = requests.post(f"{AUTH_API}/register/driver", json={
            "name": "Demo Driver",
            "phone": "7777777777",
            "vehicle_type": "car",
            "vehicle_model": "Sedan",
            "license_plate": "KA-01-DEMO"
        })
        driver_id = res.json()['id']
        print(f"✅ Created Driver ID: {driver_id}")
    except Exception as e:
        driver_id = 1
        print(f"⚠️ Using Driver ID {driver_id} (Reason: {e})")

    # Create User
    try:
        res = requests.post(f"{AUTH_API}/register/rider", json={
            "name": "Professor",
            "phone": "9876543210",
            "email": "prof@college.edu"
        })
        user_id = res.json()['id']
        print(f"✅ Created User ID: {user_id}")
    except Exception as e:
        user_id = 1
        print(f"⚠️ Using User ID {user_id} (Reason: {e})")

    # Subscribe
    requests.post(f"{USER_API}/users/{user_id}/subscribe")
    print(f"✅ User {user_id} Subscribed")

    # Schedule Ride
    now = datetime.now()
    soon = (now + timedelta(minutes=2)).strftime("%H:%M")  # 2 minutes ahead

    print(f"\n=== 2. AUTOMATION TEST ===")
    print(f"🕒 Scheduling Ride for: {soon}:00")

    requests.post(f"{USER_API}/users/{user_id}/commute", json={
        "home_lat": 12.93,
        "home_lon": 77.61,
        "work_lat": 12.97,
        "work_lon": 77.60,
        "morning_time": f"{soon}:00",
        "evening_time": "18:00:00",
        "fixed_price": 37.0
    })

    print("✅ Schedule Saved.")

    print("\n=== 3. WAITING FOR SYSTEM... ===")
    print("👉 Waiting 20 seconds for Scheduler & Matcher to run...")
    time.sleep(20)

    print("\n=== 4. DRIVER INTERACTION ===")
    try:
        res = requests.get(f"{DRIVER_API}/drivers/{driver_id}/assigned")
        data = res.json()
        
        if data.get('assigned'):
            ride_id = data['ride']['id']
            print(f"✅ Driver Service reports: Ride {ride_id} assigned to Driver {driver_id}!")

            # Driver Accepts
            requests.post(f"{DRIVER_API}/drivers/{driver_id}/accept")
            print(f"✅ Driver has ACCEPTED the ride.")

            # Verify Ride Status
            print("\n=== 5. CHECKING RIDE STATUS ===")
            res = requests.get(f"{USER_API}/ride-status/{ride_id}")
            res_json = res.json()

            print("📌 DEBUG ride-status response:", res_json)

            # Extract status safely
            status = (
                res_json.get("status") or
                res_json.get("ride", {}).get("status") or
                res_json.get("state") or
                "UNKNOWN"
            )

            if status == "UNKNOWN":
                print("❌ Could not find 'status' in the response!")
            else:
                print(f"✅ Final Ride Status: {status}")
        
        else:
            print("❌ Driver was not assigned a ride yet. (Scheduler may be slow)")

    except Exception as e:
        print(f"❌ Error talking to Driver Service: {e}")


if __name__ == "__main__":
    run_demo()
