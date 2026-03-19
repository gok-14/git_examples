import requests
import time
from database import print_db, init_db
from dotenv import load_dotenv
import os

load_dotenv()

BACKEND_URL = "http://127.0.0.1:5000"
API_KEY = os.getenv("API_KEY")

# -----------------------------
# Send Single Location
# -----------------------------
def send_location(owner_mobile, vehicle_id, driver_name, latitude, longitude, speed, status):
    try:
        response = requests.post(
            f"{BACKEND_URL}/fleet/location",
            headers={"X-API-Key": API_KEY},
            json={
                "owner_id": owner_mobile,   # backend still expects owner_id
                "vehicle_id": vehicle_id,
                "driver_name": driver_name,
                "latitude": latitude,
                "longitude": longitude,
                "speed": speed,
                "status": status
            }
        )

        print(f"Status Code : {response.status_code}")
        print(f"Raw Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect — is backend.py running?")
    except Exception as e:
        print(f"❌ Error: {e}")


# -----------------------------
# Broadcast Message
# -----------------------------
def send_broadcast(message):

    try:

        response = requests.post(
            f"{BACKEND_URL}/fleet/broadcast",
            headers={"X-API-Key": API_KEY},
            json={"message": message}
        )

        print(f"Status Code : {response.status_code}")
        print(f"Raw Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect — is backend.py running?")
    except Exception as e:
        print(f"❌ Error: {e}")


# -----------------------------
# Simulate Moving Vehicle
# -----------------------------
def simulate_moving(owner_mobile):

    route = [
        {"lat": 13.7563, "lng": 100.5018, "speed": 0,  "status": "idle"},
        {"lat": 13.7580, "lng": 100.5035, "speed": 30, "status": "moving"},
        {"lat": 13.7600, "lng": 100.5060, "speed": 55, "status": "moving"},
        {"lat": 13.7625, "lng": 100.5080, "speed": 60, "status": "moving"},
        {"lat": 13.7640, "lng": 100.5100, "speed": 20, "status": "moving"},
        {"lat": 13.7650, "lng": 100.5110, "speed": 0,  "status": "stopped"},
    ]

    print(f"\n🚛 Simulating vehicle — {len(route)} updates...\n")

    for i, point in enumerate(route):

        print(f"Update {i+1}/{len(route)} → {point['status']} at {point['speed']} km/h")

        send_location(
            owner_mobile,
            "TRK-001",
            "John Doe",
            point["lat"],
            point["lng"],
            point["speed"],
            point["status"]
        )

        time.sleep(5)


# -----------------------------
# Main Menu
# -----------------------------
if __name__ == "__main__":

    if not API_KEY:
        print("❌ API_KEY not found in .env — check your .env file!")
        exit()

    print(f"✅ API Key loaded: {API_KEY[:6]}******")

    while True:

        print("\n=============================")
        print("   Fleet POC — Dummy App")
        print("=============================")
        print("1. Send single location update")
        print("2. Simulate moving vehicle")
        print("3. Send broadcast message")
        print("4. View database")
        print("5. Exit")
        print("=============================")

        choice = input("Choose (1-5): ").strip()

        if choice == "1":

            owner_mobile = input("Owner Mobile (e.g. 9876543210): ").strip()

            send_location(
                owner_mobile,
                "TRK-001",
                "John Doe",
                13.7563,
                100.5018,
                60,
                "moving"
            )

        elif choice == "2":

            owner_mobile = input("Owner Mobile (e.g. 9876543210): ").strip()

            simulate_moving(owner_mobile)

        elif choice == "3":

            msg = input("Broadcast message: ").strip()

            send_broadcast(msg)

        elif choice == "4":

            init_db()
            print_db()

        elif choice == "5":

            print("Bye!")
            break

        else:

            print("❌ Invalid choice — enter 1 to 5")