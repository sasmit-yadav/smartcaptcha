import requests
import json

# Test session start first
session_url = "http://localhost:8000/api/session/start"
session_payload = {
    "sessionId": "test-session-123",
    "meta": {
        "sessionId": "test-session-123",
        "startTime": 1234567890,
        "userAgent": "test",
        "platform": "test",
        "screenWidth": 1920,
        "screenHeight": 1080,
        "deviceType": "desktop",
        "source": "demo"
    }
}

try:
    print("Starting session...")
    response = requests.post(session_url, json=session_payload)
    print(f"Session Start Status: {response.status_code}")
    print(f"Session Start Response: {response.json()}")
    
    # Now test telemetry endpoint
    telemetry_url = "http://localhost:8000/api/telemetry"
    telemetry_payload = {
        "sessionId": "test-session-123",
        "meta": {
            "sessionId": "test-session-123",
            "startTime": 1234567890,
            "userAgent": "test",
            "platform": "test",
            "screenWidth": 1920,
            "screenHeight": 1080,
            "deviceType": "desktop",
            "source": "demo"
        },
        "events": [
            {
                "type": "mm",
                "t": 1234567890,
                "x": 100,
                "y": 200
            },
            {
                "type": "cl",
                "t": 1234567891,
                "x": 150,
                "y": 250,
                "target": "button"
            }
        ],
        "timestamp": 1234567890
    }
    
    print("\nSending telemetry...")
    response = requests.post(telemetry_url, json=telemetry_payload)
    print(f"Telemetry Status: {response.status_code}")
    print(f"Telemetry Response: {response.json()}")
    print("Telemetry test successful!")
    
except Exception as e:
    print(f"Error: {e}")
