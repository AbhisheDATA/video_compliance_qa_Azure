import requests
import threading
import time
import json

BASE_URL = "http://localhost:8000"

def call_audit():
    print("--- Starting Audit Request ---")
    payload = {"video_url": "https://youtu.be/dT7S75eYhcQ"}
    try:
        response = requests.post(f"{BASE_URL}/audit", json=payload, timeout=600)
        print("\n--- Audit Response Received ---")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"\n--- Audit Request Failed: {e} ---")

def poll_health():
    print("--- Starting Health Polling (checking responsiveness) ---")
    for i in range(10):
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            duration = time.time() - start
            print(f"Health check {i+1}: {response.status_code} (took {duration:.2f}s)")
        except Exception as e:
            print(f"Health check {i+1} FAILED: {e}")
        time.sleep(5)

if __name__ == "__main__":
    # Start the audit in a separate thread
    audit_thread = threading.Thread(target=call_audit)
    audit_thread.start()
    
    # Wait a few seconds for audit to hit the download/indexing phase
    time.sleep(5)
    
    # Poll health to see if the server is still responsive
    poll_health()
    
    audit_thread.join()
